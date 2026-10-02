"""Deterministic owned synthetic cases for the certified policy class."""
from __future__ import annotations

from math import ceil
from random import Random


def _model(case, family, nodes, edges, monitors, obligation, horizon, failures):
    return {
        "case": case,
        "family": family,
        "nodes": nodes,
        "edges": sorted(edges),
        "monitors": monitors,
        "obligation": obligation,
        "horizon": horizon,
        "failures": failures,
    }


def _layer_nodes(sizes):
    layers = []
    cursor = 0
    for size in sizes:
        layer = list(range(cursor, cursor + size))
        layers.append(layer)
        cursor += size
    return layers


def _connected_pairs(left, right, rng, extra_degree):
    pairs = set()
    for i, u in enumerate(left):
        pairs.add((u, right[i % len(right)]))
    for j, v in enumerate(right):
        pairs.add((left[j % len(left)], v))
    for u in left:
        candidates = list(right)
        rng.shuffle(candidates)
        for v in candidates[:extra_degree]:
            pairs.add((u, v))
    return sorted(pairs)


def _layered_case(case, family, total_nodes, layer_count, k, monitor_count, seed,
                  tiny=False):
    """Create a reachable DAG with k mandatory visible singleton gates."""
    rng = Random(seed)
    intermediate_layers = layer_count - 2
    if intermediate_layers < k + 1:
        raise ValueError("need a branch layer after mandatory gates")
    remaining = total_nodes - 2 - k
    branch_layers = intermediate_layers - k
    if remaining < branch_layers:
        raise ValueError("too few nodes")
    base, extra = divmod(remaining, branch_layers)
    branch_sizes = [base + (1 if i < extra else 0) for i in range(branch_layers)]
    sizes = [1] + [1] * k + branch_sizes + [1]
    layers = _layer_nodes(sizes)
    edges = []
    for layer_index, (left, right) in enumerate(zip(layers, layers[1:])):
        pairs = _connected_pairs(left, right, rng, 1 if tiny else 2)
        for u, v in pairs:
            on_backbone = u == left[0] and v == right[0]
            if layer_index < k or on_backbone:
                boundary, action = 0, "keep"
            else:
                action = rng.choices(
                    ["keep", "restrict", "either"], weights=[5, 2, 3], k=1
                )[0]
                boundary = int(rng.random() < 0.22)
            edges.append([u, v, boundary, action])
    gate_nodes = [layers[i][0] for i in range(1, k + 1)]
    other_nodes = [v for layer in layers[1:-1] for v in layer if v not in gate_nodes]
    rng.shuffle(other_nodes)
    chosen_nodes = gate_nodes + other_nodes[:max(0, monitor_count - len(gate_nodes))]
    monitors = []
    for position, vertex in enumerate(chosen_nodes):
        if position < len(gate_nodes):
            cost = rng.randint(7, 25)
        else:
            cost = rng.randint(1, 20)
        monitors.append([vertex, "export", cost])
    return _model(
        case, family, total_nodes, edges, monitors,
        [layers[0][0], layers[-1][0], 0], layer_count - 1, k - 1,
    )


def tiny_cases():
    cases = []
    for index in range(36):
        rng = Random(7000 + index)
        k = 1 + index % 3
        layers = max(5 + index % 4, k + 3)
        min_nodes = 2 + k + (layers - 2 - k)
        nodes = min_nodes + rng.randint(2, 7)
        monitors = min(10, max(k + 2, nodes - 2))
        cases.append(_layered_case(
            f"T{index:03d}", "Tiny", nodes, layers, k, monitors,
            7000 + index, tiny=True,
        ))
    return cases


def scalable_cases():
    sizes = [32, 48, 64, 80, 96, 128, 160, 192, 224, 256, 320, 400, 500]
    cases = []
    for index in range(48):
        nodes = sizes[index % len(sizes)]
        k = 1 + index % 4
        # At most fourteen physical hops; the brief permits sixteen.
        intermediate = min(13, max(k + 2, ceil((nodes - 2 - k) / 42) + k))
        layer_count = intermediate + 2
        monitor_count = min(32, max(k + 6, nodes // 16))
        cases.append(_layered_case(
            f"L{index:03d}", "Layered", nodes, layer_count, k,
            monitor_count, 11000 + index,
        ))
    return cases


def fan_cases():
    cases = []
    for index in range(12):
        branches = 4 + index
        source, common = 0, 1
        branch_nodes = list(range(2, 2 + branches))
        target = 2 + branches
        edges = [[source, common, 0, "keep"]]
        edges += [[common, branch, 0, "keep"] for branch in branch_nodes]
        edges += [[branch, target, 0, "keep"] for branch in branch_nodes]
        common_cost = max(2, branches // 2)
        monitors = [[common, "export", common_cost]]
        monitors += [[branch, "export", 1] for branch in branch_nodes]
        cases.append(_model(
            f"F{index:03d}", "Fan", target + 1, edges, monitors,
            [source, target, 0], 3, 0,
        ))
    return cases


def infeasible_cases():
    cases = []
    for index in range(12):
        k = 2 + index % 4
        length = k + 2 + index % 3
        nodes = length + 1
        edges = [[u, u + 1, 0, "keep"] for u in range(length)]
        monitors = [[u, "export", 1 + (u + index) % 5] for u in range(1, k)]
        # Off-path-looking components are placed after the target-relevant prefix,
        # but the unique chain still contains only k-1 total components.
        cases.append(_model(
            f"I{index:03d}", "Infeasible", nodes, edges, monitors,
            [0, nodes - 1, 0], length, k - 1,
        ))
    return cases


def vacuous_cases():
    cases = []
    for index in range(12):
        length = 3 + index % 5
        nodes = length + 1
        edges = []
        for u in range(length):
            boundary = 1 if u == 0 else 0
            edges.append([u, u + 1, boundary, "keep"])
        monitors = [[u, "export", 1 + (u % 4)] for u in range(1, min(nodes, 7))]
        failures = min(index % 3, len(monitors))
        cases.append(_model(
            f"V{index:03d}", "Vacuous", nodes, edges, monitors,
            [0, nodes - 1, 1], length, failures,
        ))
    return cases


def all_cases():
    cases = tiny_cases() + scalable_cases() + fan_cases() + infeasible_cases() + vacuous_cases()
    assert len(cases) == 120
    assert len({item["case"] for item in cases}) == 120
    return cases
