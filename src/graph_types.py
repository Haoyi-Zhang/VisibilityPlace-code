"""Small immutable-ish container helpers shared only as data structures."""
from __future__ import annotations


def finalize_graph(nodes, edges, source, target, monitor_edges):
    index = {name: i for i, name in enumerate(nodes)}
    if len(index) != len(nodes):
        raise AssertionError("duplicate compiled node")
    normalized = []
    for number, edge in enumerate(edges):
        eid = f"e{number:05d}"
        u, v, kind, monitor, origin = edge
        normalized.append({
            "id": eid,
            "u": index[u],
            "v": index[v],
            "kind": kind,
            "monitor": monitor,
            "origin": origin,
        })
    edge_index = {e["id"]: e for e in normalized}
    out = [[] for _ in nodes]
    inc = [[] for _ in nodes]
    for e in normalized:
        out[e["u"]].append(e)
        inc[e["v"]].append(e)
    return {
        "nodes": tuple(nodes),
        "node_index": index,
        "edges": tuple(normalized),
        "edge_index": edge_index,
        "out": tuple(tuple(row) for row in out),
        "in": tuple(tuple(row) for row in inc),
        "source": index[source],
        "target": index[target],
        "monitor_edges": dict(monitor_edges),
    }
