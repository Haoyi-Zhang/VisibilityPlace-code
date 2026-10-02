"""Exact DAG scans used by the producer and baselines."""
from __future__ import annotations

from collections import deque

INF = 10**18


def topological(graph):
    indeg = [len(row) for row in graph["in"]]
    ready = deque(i for i, degree in enumerate(indeg) if degree == 0)
    order = []
    while ready:
        u = ready.popleft()
        order.append(u)
        for edge in graph["out"][u]:
            v = edge["v"]
            indeg[v] -= 1
            if indeg[v] == 0:
                ready.append(v)
    if len(order) != len(graph["nodes"]):
        raise ValueError("expected a DAG")
    return order


def reachable(graph):
    seen = {graph["source"]}
    stack = [graph["source"]]
    while stack:
        u = stack.pop()
        for edge in graph["out"][u]:
            if edge["v"] not in seen:
                seen.add(edge["v"])
                stack.append(edge["v"])
    return graph["target"] in seen


def shortest_path(graph, edge_length):
    order = topological(graph)
    dist = [INF] * len(graph["nodes"])
    previous = [None] * len(graph["nodes"])
    dist[graph["source"]] = 0
    for u in order:
        if dist[u] == INF:
            continue
        for edge in graph["out"][u]:
            candidate = dist[u] + edge_length(edge)
            v = edge["v"]
            if candidate < dist[v] or (
                candidate == dist[v] and previous[v] is not None and
                edge["id"] < previous[v][1]["id"]
            ):
                dist[v] = candidate
                previous[v] = (u, edge)
    path = []
    if dist[graph["target"]] != INF:
        cursor = graph["target"]
        while cursor != graph["source"]:
            item = previous[cursor]
            if item is None:
                raise AssertionError("broken predecessor chain")
            cursor, edge = item
            path.append(edge)
        path.reverse()
    return dist, path


def selected_distance(graph, selected):
    return shortest_path(
        graph,
        lambda edge: 1 if edge["kind"] == "monitor" and edge["monitor"] in selected else 0,
    )
