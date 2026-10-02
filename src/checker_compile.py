"""Checker-side reconstruction of the policy compiler.

The control flow and naming logic are independently written from the producer
compiler so a producer defect is not accepted merely by replaying its output.
"""
from __future__ import annotations

from collections import deque

from graph_types import finalize_graph
from model import validate_model


def compile_for_checking(model):
    validate_model(model)
    n = model["nodes"]
    source_vertex, target_vertex, initial_flag = model["obligation"]
    monitors_at = {v: [] for v in range(n)}
    for mid, item in enumerate(model["monitors"]):
        monitors_at[item[0]].append(mid)

    names = ["SRC", "SNK"]
    arcs = []
    entry = {}
    leave = {}
    for vertex in range(n):
        for flag in [0, 1]:
            stem = "q{}r{}".format(vertex, flag)
            entry[vertex, flag] = stem + "i"
            leave[vertex, flag] = stem + "o"
            names += [entry[vertex, flag], leave[vertex, flag]]
            previous = entry[vertex, flag]
            component_sequence = monitors_at[vertex] if flag == 0 else []
            for component in component_sequence:
                following = stem + "m{}".format(component)
                names.append(following)
                arcs.append((previous, following, "monitor", component,
                             "state:{}:{}".format(vertex, flag)))
                previous = following
            arcs.append((previous, leave[vertex, flag], "ordinary", None,
                         "state-exit:{}:{}".format(vertex, flag)))

    arcs.append(("SRC", entry[source_vertex, initial_flag], "ordinary", None,
                 "obligation-entry"))
    for flag in [0, 1]:
        arcs.append((leave[target_vertex, flag], "SNK", "ordinary", None,
                     "obligation-exit"))

    for pidx, physical in enumerate(model["edges"]):
        u, v, boundary, action = physical
        if u == target_vertex:
            continue
        for flag in [0, 1]:
            if flag and boundary:
                continue
            destinations = []
            if action == "keep":
                destinations.append(flag)
            if action == "restrict":
                destinations.append(1)
            if action == "either":
                destinations.extend([1] if flag else [0, 1])
            for new_flag in destinations:
                arcs.append((leave[u, flag], entry[v, new_flag], "ordinary", None,
                             "physical:{}:{}:{}".format(pidx, flag, new_flag)))

    graph = finalize_graph(names, arcs, "SRC", "SNK", {})
    occurrence = {}
    for arc in graph["edges"]:
        component = arc["monitor"]
        if component is not None:
            if component in occurrence:
                raise AssertionError("repeated monitor in checker compiler")
            occurrence[component] = arc["id"]
    if set(occurrence) != set(range(len(model["monitors"]))):
        raise AssertionError("checker compiler lost a monitor")
    graph["monitor_edges"].update(occurrence)
    _dag_order(graph)
    return graph


def _dag_order(graph):
    indegree = [0] * len(graph["nodes"])
    for arc in graph["edges"]:
        indegree[arc["v"]] += 1
    available = deque(i for i, degree in enumerate(indegree) if degree == 0)
    result = []
    while available:
        u = available.popleft()
        result.append(u)
        for arc in graph["out"][u]:
            v = arc["v"]
            indegree[v] -= 1
            if indegree[v] == 0:
                available.append(v)
    if len(result) != len(graph["nodes"]):
        raise AssertionError("checker compiled a cycle")
    return result
