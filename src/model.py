"""Schema and resource-bound checks for owned synthetic export-policy DAGs."""
from __future__ import annotations

from collections import deque
import re

MODEL_KEYS = {
    "case", "family", "nodes", "edges", "monitors", "obligation",
    "horizon", "failures",
}
_ID = re.compile(r"^[A-Za-z0-9]{1,32}$")
ACTIONS = {"keep", "restrict", "either"}


def _integer(value, low, high):
    return type(value) is int and low <= value <= high


def topological_order(model):
    n = model["nodes"]
    indeg = [0] * n
    adj = [[] for _ in range(n)]
    for u, v, _, _ in model["edges"]:
        adj[u].append(v)
        indeg[v] += 1
    ready = deque(i for i, degree in enumerate(indeg) if degree == 0)
    order = []
    while ready:
        u = ready.popleft()
        order.append(u)
        for v in adj[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                ready.append(v)
    if len(order) != n:
        raise ValueError("physical graph must be acyclic")
    return order


def longest_path_length(model, order=None):
    order = topological_order(model) if order is None else order
    adj = [[] for _ in range(model["nodes"])]
    for u, v, _, _ in model["edges"]:
        adj[u].append(v)
    dist = [0] * model["nodes"]
    for u in order:
        for v in adj[u]:
            dist[v] = max(dist[v], dist[u] + 1)
    return max(dist, default=0)


def validate_model(model):
    if not isinstance(model, dict) or set(model) != MODEL_KEYS:
        raise ValueError("unexpected model fields")
    if not isinstance(model["case"], str) or not _ID.fullmatch(model["case"]):
        raise ValueError("case must be a neutral alphanumeric identifier")
    if not isinstance(model["family"], str) or not _ID.fullmatch(model["family"]):
        raise ValueError("family must be alphanumeric")
    n = model["nodes"]
    if not _integer(n, 1, 500):
        raise ValueError("nodes must be in [1,500]")
    if not _integer(model["horizon"], 0, 16):
        raise ValueError("horizon must be in [0,16]")
    edges = model["edges"]
    if not isinstance(edges, list) or len(edges) > 2000:
        raise ValueError("edges must be a list of at most 2000 entries")
    seen = set()
    for item in edges:
        if not isinstance(item, list) or len(item) != 4:
            raise ValueError("edge requires [source,target,boundary,action]")
        u, v, boundary, action = item
        if not _integer(u, 0, n - 1) or not _integer(v, 0, n - 1) or u == v:
            raise ValueError("bad physical endpoint")
        if not _integer(boundary, 0, 1) or action not in ACTIONS:
            raise ValueError("bad boundary or policy action")
        if (u, v) in seen:
            raise ValueError("parallel physical edges are excluded")
        seen.add((u, v))
    order = topological_order(model)
    if longest_path_length(model, order) > model["horizon"]:
        raise ValueError("declared horizon is shorter than a physical DAG path")
    monitors = model["monitors"]
    if not isinstance(monitors, list) or len(monitors) > 32:
        raise ValueError("monitors must be a list of at most 32 entries")
    for item in monitors:
        if not isinstance(item, list) or len(item) != 3:
            raise ValueError("monitor requires [node,hook,cost]")
        v, hook, cost = item
        if not _integer(v, 0, n - 1) or hook != "export" or not _integer(cost, 1, 10**6):
            raise ValueError("the certified class permits positive-cost export hooks only")
    if not _integer(model["failures"], 0, len(monitors)):
        raise ValueError("bad component-failure bound")
    obligation = model["obligation"]
    if not isinstance(obligation, list) or len(obligation) != 3:
        raise ValueError("obligation requires [source,target,initial_restriction]")
    source, target, initial = obligation
    if not _integer(source, 0, n - 1) or not _integer(target, 0, n - 1):
        raise ValueError("bad obligation endpoint")
    if source == target:
        raise ValueError("source and target must differ in this class")
    if not _integer(initial, 0, 1):
        raise ValueError("bad initial restriction bit")
    return order


def policy_successors(restricted, boundary, action):
    """Reference transition relation used only by neutral generators/oracles."""
    if restricted and boundary:
        return ()
    if action == "keep":
        return (restricted,)
    if action == "restrict":
        return (1,)
    if action == "either":
        return (1,) if restricted else (0, 1)
    raise ValueError("unknown action")
