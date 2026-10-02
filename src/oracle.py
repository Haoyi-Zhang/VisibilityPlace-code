"""Independent tiny-instance semantic and brute-force oracles."""
from __future__ import annotations

from itertools import product

from model import validate_model


def physical_observations(model, limit=200000):
    """Enumerate policy realizations without using either compiler."""
    validate_model(model)
    n = model["nodes"]
    source, target, initial = model["obligation"]
    adjacency = [[] for _ in range(n)]
    for edge_index, (u, v, boundary, action) in enumerate(model["edges"]):
        adjacency[u].append((edge_index, v, boundary, action))
    monitor_at = [[] for _ in range(n)]
    for monitor, (vertex, _, _) in enumerate(model["monitors"]):
        monitor_at[vertex].append(monitor)
    rows = []
    count = 0

    def visit(vertex, restricted, observed):
        nonlocal count
        count += 1
        if count > limit:
            raise ValueError("tiny semantic oracle limit exceeded")
        current = set(observed)
        if restricted == 0:
            current.update(monitor_at[vertex])
        if vertex == target:
            rows.append(tuple(sorted(current)))
            return
        for _, nxt, boundary, action in adjacency[vertex]:
            if restricted and boundary:
                continue
            if action == "keep":
                flags = (restricted,)
            elif action == "restrict":
                flags = (1,)
            else:
                flags = (1,) if restricted else (0, 1)
            for flag in flags:
                visit(nxt, flag, current)

    visit(source, initial, set())
    return sorted(rows)


def compiled_observations(graph, limit=200000):
    rows = []
    count = 0

    def visit(node, observed):
        nonlocal count
        count += 1
        if count > limit:
            raise ValueError("compiled path oracle limit exceeded")
        if node == graph["target"]:
            rows.append(tuple(sorted(observed)))
            return
        for edge in graph["out"][node]:
            nxt = set(observed)
            if edge["kind"] == "monitor":
                nxt.add(edge["monitor"])
            visit(edge["v"], nxt)

    visit(graph["source"], set())
    return sorted(rows)


def brute_force_optimum(model, observations):
    m = len(model["monitors"])
    if m > 12:
        raise ValueError("brute-force oracle admits at most 12 components")
    if not observations:
        return "vacuous", (), 0
    k = model["failures"] + 1
    if any(len(row) < k for row in observations):
        return "infeasible", (), None
    costs = [item[2] for item in model["monitors"]]
    best = None
    winner = None
    for bits in product((0, 1), repeat=m):
        chosen = {i for i, bit in enumerate(bits) if bit}
        if all(len(chosen.intersection(row)) >= k for row in observations):
            cost = sum(costs[i] for i in chosen)
            key = (cost, tuple(sorted(chosen)))
            if best is None or key < best:
                best = key
                winner = tuple(sorted(chosen))
    if best is None:
        return "infeasible", (), None
    return "optimal", winner, best[0]
