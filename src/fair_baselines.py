"""Same-model placement comparators and common exact evidence production.

SPDX-License-Identifier: MIT
These are formulations implemented here, not reproductions of named network
placement systems. All exact routes use the original certificate schema.
"""
from __future__ import annotations

from fractions import Fraction
import heapq

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, linprog, milp
from scipy.sparse import coo_matrix

from checker_compile import compile_for_checking
from dag import INF, _selected_distance, _shortest_path, topological
from model import validate_model
from solver import _coverage_potential, _fractional_lp, _round_fractional

METHODS = ("dense-lp", "sparse-lp", "compact-milp", "explicit-milp", "cover-greedy")


class EnumerationLimit(RuntimeError):
    pass


def compact_matrix(graph, model, k):
    """Identical sparse potential formulation for LP and binary MILP."""
    m, n = len(model["monitors"]), len(graph["nodes"])
    rr, cc, vv = [], [], []
    for i, edge in enumerate(graph["edges"]):
        rr.extend((i, i)); cc.extend((m + edge["v"], m + edge["u"])); vv.extend((1., -1.))
        if edge["kind"] == "monitor":
            rr.append(i); cc.append(edge["monitor"]); vv.append(-1.)
    matrix = coo_matrix((vv, (rr, cc)), shape=(len(graph["edges"]), m+n)).tocsc()
    objective = np.array([x[2] for x in model["monitors"]] + [0]*n, dtype=float)
    lower = np.zeros(m+n)
    upper = np.array([1]*m + [k]*n, dtype=float)
    upper[m + graph["source"]] = 0
    lower[m + graph["target"]] = k
    return objective, matrix, lower, upper


def observation_sets(model, cap=32768):
    """Direct physical-state DP; deduplicate identical sets before the cap.

    This avoids a deliberately weak path-list baseline: unmonitored branching
    does not multiply rows. No compiler or placement solver is used here.
    The cap bounds total stored (vertex, bit, observed-mask) states, including
    partial paths, rather than confusing exhaustion with model infeasibility.
    """
    order = validate_model(model)
    source, target, initial = model["obligation"]
    hosted = [0]*model["nodes"]
    for i, (v, _, _) in enumerate(model["monitors"]):
        hosted[v] |= 1 << i
    adjacency = [[] for _ in hosted]
    for u, v, b, a in model["edges"]:
        adjacency[u].append((v, b, a))
    states = [[set(), set()] for _ in hosted]
    states[source][initial].add(0)
    stored = 1
    rows = set()
    for u in order:
        for bit in (0, 1):
            for before in states[u][bit]:
                mask = before | (hosted[u] if bit == 0 else 0)
                if u == target:
                    rows.add(mask)
                    continue
                for v, boundary, action in adjacency[u]:
                    if bit == boundary == 1:
                        continue
                    flags = (bit,) if action == "keep" else (1,) if action == "restrict" else ((1,) if bit else (0, 1))
                    for nxt in flags:
                        if mask not in states[v][nxt]:
                            stored += 1
                            if stored > cap:
                                raise EnumerationLimit(f"observation-state cap {cap} exceeded")
                            states[v][nxt].add(mask)
    return sorted(rows), stored


def _cover_selection(model, rows):
    k = model["failures"] + 1
    residual = [k]*len(rows)
    selected = set()
    costs = [x[2] for x in model["monitors"]]
    while any(residual):
        options = []
        for i, cost in enumerate(costs):
            if i in selected:
                continue
            gain = sum(r > 0 and bool(mask & (1 << i)) for r, mask in zip(residual, rows))
            if gain:
                options.append((Fraction(cost, gain), cost, i))
        if not options:
            raise ValueError("multicover unexpectedly infeasible")
        i = min(options)[2]
        selected.add(i)
        residual = [max(0, r-int(bool(mask & (1 << i)))) for r, mask in zip(residual, rows)]
    return selected


def selection(model, graph, method, cap=32768):
    """Primal computation only; exact status and witness handled uniformly."""
    k, m = model["failures"] + 1, len(model["monitors"])
    meta = {}
    if method == "dense-lp":
        x, objective = _fractional_lp(graph, model, k)
        _, selected, _ = _round_fractional(graph, model, x, k)
        return set(selected), {"solver_objective": objective}
    if method in ("sparse-lp", "compact-milp"):
        objective, matrix, lower, upper = compact_matrix(graph, model, k)
        meta.update(matrix_rows=matrix.shape[0], matrix_columns=matrix.shape[1], matrix_nnz=matrix.nnz,
                    matrix_bytes=matrix.data.nbytes+matrix.indices.nbytes+matrix.indptr.nbytes)
        if method == "sparse-lp":
            result = linprog(objective, A_ub=matrix, b_ub=np.zeros(matrix.shape[0]),
                             bounds=list(zip(lower, upper)), method="highs-ds",
                             options={"dual_feasibility_tolerance": 1e-9,
                                      "primal_feasibility_tolerance": 1e-9})
        else:
            result = milp(objective, integrality=np.array([1]*m+[0]*(len(lower)-m)),
                          bounds=Bounds(lower, upper),
                          constraints=LinearConstraint(matrix, -np.inf, 0),
                          options={"mip_rel_gap": 0., "time_limit": 30.})
        if not result.success:
            raise RuntimeError(f"{method} stopped: {result.message}")
        if method == "sparse-lp":
            _, selected, _ = _round_fractional(graph, model, result.x[:m], k)
        else:
            if any(abs(v-round(v)) > 1e-6 for v in result.x[:m]):
                raise RuntimeError("nonintegral MILP output")
            selected = [i for i in range(m) if round(result.x[i]) == 1]
            meta["mip_nodes"] = int(result.mip_node_count or 0)
        meta["solver_objective"] = float(result.fun)
        return set(selected), meta
    rows, stored = observation_sets(model, cap)
    meta.update(observation_rows=len(rows), stored_observation_states=stored)
    if method == "cover-greedy":
        return _cover_selection(model, rows), meta
    if method != "explicit-milp":
        raise ValueError("unknown comparison method")
    rr, cc = [], []
    for r, mask in enumerate(rows):
        for i in range(m):
            if mask & (1 << i):
                rr.append(r); cc.append(i)
    matrix = coo_matrix((np.ones(len(rr)), (rr, cc)), shape=(len(rows), m)).tocsc()
    result = milp(np.array([x[2] for x in model["monitors"]], dtype=float),
                  integrality=np.ones(m), bounds=Bounds(0, 1),
                  constraints=LinearConstraint(matrix, k, np.inf),
                  options={"mip_rel_gap": 0., "time_limit": 30.})
    if not result.success:
        raise RuntimeError(f"explicit MILP stopped: {result.message}")
    if any(abs(v-round(v)) > 1e-6 for v in result.x):
        raise RuntimeError("nonintegral explicit MILP output")
    meta.update(matrix_rows=matrix.shape[0], matrix_columns=m, matrix_nnz=matrix.nnz,
                matrix_bytes=matrix.data.nbytes+matrix.indices.nbytes+matrix.indptr.nbytes,
                solver_objective=float(result.fun), mip_nodes=int(result.mip_node_count or 0))
    return {i for i in range(m) if round(result.x[i]) == 1}, meta


def integer_flow_witness(graph, model, k):
    """Integral successive-shortest-path flow with monitor overflow costs.

    Each augmenting unit earns k and pays 1 per overflow. Stop when its shortest
    residual cost is >= k. Reduced-cost Dijkstra maintains exact integer
    potentials; initial forward costs are 0 or 1. Reverse residual edges allow
    rerouting, so this is not greedy disjoint-path packing. Every route uses
    this same proof producer, independently of its chosen primal solution.
    """
    n = len(graph["nodes"])
    residual = [[] for _ in range(n)]
    capacity = sum(m[2] for m in model["monitors"]) + 1

    def arc(u, v, cap, cost):
        forward = [v, len(residual[v]), cap, cost, cap]
        backward = [u, len(residual[u]), 0, -cost, 0]
        residual[u].append(forward); residual[v].append(backward)
        return forward

    originals = []
    for edge in graph["edges"]:
        u, v = edge["u"], edge["v"]
        if edge["kind"] == "ordinary":
            originals.append((edge, arc(u, v, capacity, 0), None))
        else:
            originals.append((edge, arc(u, v, model["monitors"][edge["monitor"]][2], 0),
                              arc(u, v, capacity, 1)))
    source, target = graph["source"], graph["target"]
    potential, flow_value = [0]*n, 0
    while True:
        distance, previous = [INF]*n, [None]*n
        distance[source] = 0
        queue = [(0, source)]
        while queue:
            du, u = heapq.heappop(queue)
            if du != distance[u]:
                continue
            for i, (v, _, available, cost, _) in enumerate(residual[u]):
                if not available:
                    continue
                reduced = cost + potential[u] - potential[v]
                if reduced < 0:
                    raise AssertionError("negative reachable reduced cost")
                candidate = du + reduced
                if candidate < distance[v]:
                    distance[v], previous[v] = candidate, (u, i)
                    heapq.heappush(queue, (candidate, v))
        if distance[target] == INF or distance[target] + potential[target] - potential[source] >= k:
            break
        for v, d in enumerate(distance):
            if d != INF:
                potential[v] += d
        amount, v = capacity, target
        while v != source:
            u, i = previous[v]
            amount = min(amount, residual[u][i][2])
            v = u
        v = target
        while v != source:
            u, i = previous[v]
            edge = residual[u][i]
            edge[2] -= amount
            residual[v][edge[1]][2] += amount
            v = u
        flow_value += amount
    flow, overflow = [], []
    for edge, base, over in originals:
        value = base[4] - base[2]
        if over is not None:
            z = over[4] - over[2]
            value += z
            if z:
                overflow.append([edge["monitor"], z])
        if value:
            flow.append([edge["id"], value])
    return flow_value, flow, sorted(overflow), k*flow_value-sum(z for _, z in overflow)


def classify(graph, model):
    k = model["failures"] + 1
    distances, path = _shortest_path(graph, lambda e: int(e["kind"] == "monitor"), topological(graph))
    common = dict(schema="vcm-certificate-1", case=model["case"], k=k)
    if distances[graph["target"]] == INF:
        return dict(common, status="vacuous", cost=0)
    if distances[graph["target"]] < k:
        return dict(common, status="infeasible", witness=[e["id"] for e in path],
                    all_monitor_count=int(distances[graph["target"]]))
    return None


def certify(graph, model, selected):
    k = model["failures"] + 1
    potential = _coverage_potential(graph, selected, k)
    value, flow, overflow, bound = integer_flow_witness(graph, model, k)
    cost = sum(model["monitors"][i][2] for i in selected)
    if cost != bound:
        raise ValueError("primal and independently produced lower bound differ")
    return dict(schema="vcm-certificate-1", case=model["case"], status="optimal", k=k,
                selected=sorted(selected), cost=cost, potential=potential,
                flow_value=value, flow=flow, overflow=overflow, dual_value=bound)


def check_selection(model, selected):
    """Exact feasibility only, explicitly not an optimality certificate."""
    if any(type(i) is not int or not 0 <= i < len(model["monitors"]) for i in selected):
        raise ValueError("invalid component identifier")
    graph = compile_for_checking(model)
    distances, _ = _selected_distance(graph, set(selected), topological(graph))
    if distances[graph["target"]] == INF:
        return "vacuous"
    if distances[graph["target"]] < model["failures"] + 1:
        raise ValueError("selection is not robust")
    return "feasible"


def structured_cases():
    """Complete layered choice products with nonuniform costs, no randomness.

    Vary distinct observation sets, k, and the location of cheap full layers.
    All are inside the existing 32-component and 16-hop admission limits.
    """
    models = []
    for width, depth in ((2, 4), (2, 8), (2, 14), (3, 6), (4, 8)):
        layers = [[0]] + [list(range(1+i*width, 1+(i+1)*width)) for i in range(depth)]
        target = 1+depth*width
        layers.append([target])
        edges = [[u, v, 0, "keep"] for left, right in zip(layers, layers[1:]) for u in left for v in right]
        monitors = [[v, "export", 1+((depth-i)*3+j*5)%11]
                    for i, layer in enumerate(layers[1:-1]) for j, v in enumerate(layer)]
        for k in (1, 3):
            model = dict(case=f"Choice{width}x{depth}k{k}", family="Choice", nodes=target+1,
                         edges=edges, monitors=monitors, obligation=[0, target, 0],
                         horizon=depth+1, failures=k-1)
            validate_model(model)
            models.append(model)
    return models


def choice_optimum(model):
    """Independent closed-form oracle for generated complete layer products.

    A path chooses one component per layer. Its minimum selected count equals
    the number of fully selected layers. Positive costs imply selecting the k
    cheapest full layers is optimal; partial layers cannot improve coverage.
    """
    if model["family"] != "Choice":
        raise ValueError("not a generated choice instance")
    width = int(model["case"].split("x")[0].removeprefix("Choice"))
    costs = [m[2] for m in model["monitors"]]
    totals = [sum(costs[i:i+width]) for i in range(0, len(costs), width)]
    return sum(sorted(totals)[:model["failures"]+1])
