"""Reference producer for the acyclic state-unique export class.

The producer may use SciPy and NetworkX.  The emitted certificate is checked
with exact integer arithmetic by checker.py; neither dependency is trusted by
the checker.
"""
from __future__ import annotations

from fractions import Fraction
import math
import time

import networkx as nx
import numpy as np
from scipy.optimize import linprog

from dag import INF, reachable, selected_distance, shortest_path, topological
from dag import _selected_distance, _shortest_path
from producer_compile import compile_model


class ProductionError(RuntimeError):
    pass


def _fractional_lp(graph, model, k):
    m = len(model["monitors"])
    n = len(graph["nodes"])
    count = m + n
    c = np.zeros(count, dtype=float)
    for monitor, (_, _, cost) in enumerate(model["monitors"]):
        c[monitor] = cost
    rows = []
    rhs = []
    for edge in graph["edges"]:
        row = {}
        row[m + edge["v"]] = 1.0
        row[m + edge["u"]] = -1.0
        if edge["kind"] == "monitor":
            row[edge["monitor"]] = -1.0
        rows.append(row)
        rhs.append(0.0)
    target_row = {m + graph["target"]: -1.0}
    rows.append(target_row)
    rhs.append(-float(k))
    A = np.zeros((len(rows), count), dtype=float)
    for i, sparse in enumerate(rows):
        for j, value in sparse.items():
            A[i, j] = value
    bounds = [(0.0, 1.0)] * m + [(0.0, float(k))] * n
    bounds[m + graph["source"]] = (0.0, 0.0)
    result = linprog(
        c,
        A_ub=A,
        b_ub=np.array(rhs),
        bounds=bounds,
        method="highs-ds",
        options={"dual_feasibility_tolerance": 1e-9,
                 "primal_feasibility_tolerance": 1e-9},
    )
    if not result.success:
        raise ProductionError("compact hurdle LP failed: " + result.message)
    return result.x[:m], float(result.fun)


def _weighted_distances(graph, x, k, order=None):
    order = topological(graph) if order is None else order
    distance = [math.inf] * len(graph["nodes"])
    distance[graph["source"]] = 0.0
    for u in order:
        if not math.isfinite(distance[u]):
            continue
        for edge in graph["out"][u]:
            length = float(x[edge["monitor"]]) if edge["kind"] == "monitor" else 0.0
            candidate = distance[u] + length
            if candidate < distance[edge["v"]]:
                distance[edge["v"]] = candidate
    if distance[graph["target"]] < k - 2e-7:
        raise ProductionError("LP distances do not meet the hurdle")
    return [float(k) if not math.isfinite(value) else min(float(k), max(0.0, value))
            for value in distance]


def _alpha_candidates(distance):
    breakpoints = {0.0, 1.0}
    for value in distance:
        fraction = value - math.floor(value)
        if 1e-10 < fraction < 1.0 - 1e-10:
            breakpoints.add(fraction)
    ordered = sorted(breakpoints)
    candidates = []
    for a, b in zip(ordered, ordered[1:]):
        if b - a > 1e-10:
            candidates.append((a + b) / 2.0)
    if not candidates:
        candidates = [0.5]
    return candidates


def _crosses(distance_u, distance_v, alpha, k):
    if distance_v <= distance_u + 1e-10:
        return False
    for level in range(k):
        threshold = level + alpha
        if distance_u + 1e-10 < threshold <= distance_v + 1e-10:
            return True
    return False


def _round_fractional(graph, model, x, k, order=None):
    order = tuple(topological(graph)) if order is None else order
    distance = _weighted_distances(graph, x, k, order)
    candidates = []
    costs = [item[2] for item in model["monitors"]]
    for alpha in _alpha_candidates(distance):
        selected = set()
        for edge in graph["edges"]:
            if edge["kind"] == "monitor" and _crosses(
                distance[edge["u"]], distance[edge["v"]], alpha, k
            ):
                selected.add(edge["monitor"])
        exact_distance, _ = _selected_distance(graph, selected, order)
        if exact_distance[graph["target"]] >= k:
            cost = sum(costs[m] for m in selected)
            candidates.append((cost, tuple(sorted(selected)), alpha))
    if not candidates:
        raise ProductionError("threshold rounding produced no certified placement")
    return min(candidates)


def _coverage_potential(graph, selected, k, order=None):
    order = topological(graph) if order is None else order
    distance, _ = _selected_distance(graph, selected, order)
    potential = []
    for value in distance:
        potential.append(k if value == INF else min(k, int(value)))
    if potential[graph["target"]] != k:
        raise ProductionError("rounded placement is not k-covering")
    return potential


def _dual_certificate(graph, model, k):
    total_cost = sum(item[2] for item in model["monitors"])
    capacity = total_cost + 1
    network = nx.DiGraph()
    for node in range(len(graph["nodes"])):
        network.add_node(("v", node), demand=0)
    edge_nodes = {}
    for edge in graph["edges"]:
        u = ("v", edge["u"])
        v = ("v", edge["v"])
        if edge["kind"] == "ordinary":
            q = ("o", edge["id"])
            network.add_node(q, demand=0)
            network.add_edge(u, q, capacity=capacity, weight=0)
            network.add_edge(q, v, capacity=capacity, weight=0)
            edge_nodes[edge["id"]] = (q, None)
        else:
            monitor = edge["monitor"]
            base = ("b", edge["id"])
            over = ("z", edge["id"])
            network.add_node(base, demand=0)
            network.add_node(over, demand=0)
            network.add_edge(u, base, capacity=model["monitors"][monitor][2], weight=0)
            network.add_edge(base, v, capacity=model["monitors"][monitor][2], weight=0)
            network.add_edge(u, over, capacity=capacity, weight=0)
            network.add_edge(over, v, capacity=capacity, weight=1)
            edge_nodes[edge["id"]] = (base, over)
    ret = ("return", 0)
    network.add_node(ret, demand=0)
    target = ("v", graph["target"])
    source = ("v", graph["source"])
    network.add_edge(target, ret, capacity=capacity, weight=-k)
    network.add_edge(ret, source, capacity=capacity, weight=0)
    network_cost, flow = nx.network_simplex(network)
    flow_value = int(flow[target][ret])
    positive_flow = []
    positive_overflow = []
    overflow_sum = 0
    for edge in graph["edges"]:
        base, over = edge_nodes[edge["id"]]
        u = ("v", edge["u"])
        if edge["kind"] == "ordinary":
            value = int(flow[u][base])
        else:
            base_value = int(flow[u][base])
            over_value = int(flow[u][over])
            value = base_value + over_value
            if over_value:
                positive_overflow.append([edge["monitor"], over_value])
                overflow_sum += over_value
        if value:
            positive_flow.append([edge["id"], value])
    dual_value = k * flow_value - overflow_sum
    if dual_value != -int(network_cost):
        raise ProductionError("dual extraction disagrees with circulation cost")
    return flow_value, positive_flow, positive_overflow, dual_value


def _path_witness(path):
    return [edge["id"] for edge in path]


def solve(model):
    start = time.perf_counter()
    graph = compile_model(model)
    k = model["failures"] + 1
    if not reachable(graph):
        certificate = {
            "schema": "vcm-certificate-1",
            "case": model["case"],
            "status": "vacuous",
            "k": k,
            "cost": 0,
        }
        return certificate, {
            "lp_objective": None,
            "rounding_alpha": None,
            "compiled_nodes": len(graph["nodes"]),
            "compiled_edges": len(graph["edges"]),
            "producer_ms": 1000.0 * (time.perf_counter() - start),
        }
    # Fresh graph owned by this solve; reuse the existing queue order only here.
    order = tuple(topological(graph))
    all_distance, all_path = _shortest_path(
        graph, lambda edge: 1 if edge["kind"] == "monitor" else 0, order
    )
    if all_distance[graph["target"]] < k:
        certificate = {
            "schema": "vcm-certificate-1",
            "case": model["case"],
            "status": "infeasible",
            "k": k,
            "witness": _path_witness(all_path),
            "all_monitor_count": int(all_distance[graph["target"]]),
        }
        return certificate, {
            "lp_objective": None,
            "rounding_alpha": None,
            "compiled_nodes": len(graph["nodes"]),
            "compiled_edges": len(graph["edges"]),
            "producer_ms": 1000.0 * (time.perf_counter() - start),
        }
    x, lp_objective = _fractional_lp(graph, model, k)
    cost, selected_tuple, alpha = _round_fractional(graph, model, x, k, order)
    selected = set(selected_tuple)
    potential = _coverage_potential(graph, selected, k, order)
    flow_value, flow, overflow, dual_value = _dual_certificate(graph, model, k)
    if dual_value != cost:
        raise ProductionError(
            "rounded primal cost {} disagrees with exact dual {}".format(cost, dual_value)
        )
    certificate = {
        "schema": "vcm-certificate-1",
        "case": model["case"],
        "status": "optimal",
        "k": k,
        "selected": list(selected_tuple),
        "cost": int(cost),
        "potential": potential,
        "flow_value": int(flow_value),
        "flow": flow,
        "overflow": sorted(overflow),
        "dual_value": int(dual_value),
    }
    return certificate, {
        "lp_objective": lp_objective,
        "rounding_alpha": alpha,
        "compiled_nodes": len(graph["nodes"]),
        "compiled_edges": len(graph["edges"]),
        "producer_ms": 1000.0 * (time.perf_counter() - start),
    }


def path_repair_baseline(model, graph, k):
    selected = set()
    costs = [item[2] for item in model["monitors"]]
    for _ in range(len(costs) + 1):
        distance, path = selected_distance(graph, selected)
        if distance[graph["target"]] >= k:
            return sum(costs[m] for m in selected)
        candidates = sorted(
            (costs[e["monitor"]], e["monitor"])
            for e in path
            if e["kind"] == "monitor" and e["monitor"] not in selected
        )
        if not candidates:
            return None
        selected.add(candidates[0][1])
    return None


def degree_baseline(model, graph, k):
    degree = [0] * model["nodes"]
    for u, v, _, _ in model["edges"]:
        degree[u] += 1
        degree[v] += 1
    ordering = []
    for monitor, (vertex, _, cost) in enumerate(model["monitors"]):
        ordering.append((Fraction(-degree[vertex], cost), cost, monitor))
    # More degree per cost first; then lower cost and stable monitor id.
    ordering.sort()
    selected = set()
    for _, _, monitor in ordering:
        selected.add(monitor)
        distance, _ = selected_distance(graph, selected)
        if distance[graph["target"]] >= k:
            return sum(model["monitors"][m][2] for m in selected)
    return None
