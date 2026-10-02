"""Producer-side policy-to-hurdle compiler.

This implementation is deliberately separate from checker_compile.py.  They
share the input parser and graph container, not transition-building code.
"""
from __future__ import annotations

from graph_types import finalize_graph
from model import validate_model


def compile_model(model):
    validate_model(model)
    n = model["nodes"]
    target = model["obligation"][1]
    by_node = [[] for _ in range(n)]
    for monitor, (v, hook, cost) in enumerate(model["monitors"]):
        assert hook == "export"
        by_node[v].append(monitor)

    nodes = ["SRC", "SNK"]
    edges = []
    monitor_names = {}
    entries, exits = {}, {}

    for v in range(n):
        for restricted in (0, 1):
            prefix = f"q{v}r{restricted}"
            entry, exit_ = prefix + "i", prefix + "o"
            nodes.extend([entry, exit_])
            entries[v, restricted] = entry
            exits[v, restricted] = exit_
            cursor = entry
            visible = by_node[v] if restricted == 0 else []
            for monitor in visible:
                nxt = f"{prefix}m{monitor}"
                nodes.append(nxt)
                edges.append((cursor, nxt, "monitor", monitor, f"state:{v}:{restricted}"))
                monitor_names[monitor] = len(edges) - 1
                cursor = nxt
            edges.append((cursor, exit_, "ordinary", None, f"state-exit:{v}:{restricted}"))

    source, _, initial = model["obligation"]
    edges.append(("SRC", entries[source, initial], "ordinary", None, "obligation-entry"))
    for restricted in (0, 1):
        edges.append((exits[target, restricted], "SNK", "ordinary", None, "obligation-exit"))

    for physical_index, (u, v, boundary, action) in enumerate(model["edges"]):
        if u == target:
            continue
        for restricted in (0, 1):
            if restricted == 1 and boundary == 1:
                continue
            if action == "keep":
                next_flags = (restricted,)
            elif action == "restrict":
                next_flags = (1,)
            elif action == "either":
                next_flags = (1,) if restricted else (0, 1)
            else:
                raise AssertionError(action)
            for nxt in next_flags:
                edges.append((
                    exits[u, restricted], entries[v, nxt], "ordinary", None,
                    f"physical:{physical_index}:{restricted}:{nxt}",
                ))

    graph = finalize_graph(nodes, edges, "SRC", "SNK", {})
    monitor_edges = {}
    for edge in graph["edges"]:
        if edge["kind"] == "monitor":
            m = edge["monitor"]
            if m in monitor_edges:
                raise AssertionError("monitor label repeated by producer compiler")
            monitor_edges[m] = edge["id"]
    if len(monitor_edges) != len(model["monitors"]):
        raise AssertionError("each export component must occur exactly once")
    graph["monitor_edges"].update(monitor_edges)
    _assert_dag(graph)
    return graph


def _assert_dag(graph):
    indeg = [len(row) for row in graph["in"]]
    ready = [i for i, value in enumerate(indeg) if value == 0]
    order = []
    while ready:
        u = ready.pop()
        order.append(u)
        for edge in graph["out"][u]:
            v = edge["v"]
            indeg[v] -= 1
            if indeg[v] == 0:
                ready.append(v)
    if len(order) != len(graph["nodes"]):
        raise AssertionError("compiled graph is not acyclic")
