"""Exact, solver-independent certificate checker."""
from __future__ import annotations

from checker_compile import compile_for_checking
from dag import reachable


class Rejected(ValueError):
    pass


def _integer(value, low=0, high=10**18):
    return type(value) is int and low <= value <= high


def _exact_keys(obj, keys):
    if not isinstance(obj, dict) or set(obj) != set(keys):
        raise Rejected("unexpected certificate fields")


def verify(model, certificate):
    graph = compile_for_checking(model)
    if not isinstance(certificate, dict):
        raise Rejected("certificate must be an object")
    common = {"schema", "case", "status", "k"}
    if certificate.get("schema") != "vcm-certificate-1":
        raise Rejected("unknown certificate schema")
    if certificate.get("case") != model["case"]:
        raise Rejected("case mismatch")
    k = model["failures"] + 1
    if not _integer(certificate.get("k"), 1, len(model["monitors"]) + 1) or certificate["k"] != k:
        raise Rejected("failure threshold mismatch")
    status = certificate.get("status")

    if status == "vacuous":
        _exact_keys(certificate, common | {"cost"})
        if not _integer(certificate["cost"], 0, 0):
            raise Rejected("vacuous cost must be the integer zero")
        if reachable(graph):
            raise Rejected("declared vacuity has a realizable path")
        return _result(graph, status, 0, 0)

    if status == "infeasible":
        _exact_keys(certificate, common | {"witness", "all_monitor_count"})
        witness = certificate["witness"]
        if not isinstance(witness, list) or not witness:
            raise Rejected("missing infeasibility path")
        if len(witness) > len(graph["edges"]):
            raise Rejected("infeasibility path is too long")
        current = graph["source"]
        count = 0
        for edge_id in witness:
            if not isinstance(edge_id, str) or edge_id not in graph["edge_index"]:
                raise Rejected("unknown witness edge")
            edge = graph["edge_index"][edge_id]
            if edge["u"] != current:
                raise Rejected("witness is not a contiguous source path")
            current = edge["v"]
            count += int(edge["kind"] == "monitor")
        if current != graph["target"]:
            raise Rejected("witness does not reach the sink")
        if (not _integer(certificate["all_monitor_count"], 0, len(model["monitors"]))
                or count >= k or certificate["all_monitor_count"] != count):
            raise Rejected("witness does not prove infeasibility")
        return _result(graph, status, None, count)

    if status != "optimal":
        raise Rejected("unknown status")
    _exact_keys(certificate, common | {
        "selected", "cost", "potential", "flow_value", "flow",
        "overflow", "dual_value",
    })
    if not reachable(graph):
        raise Rejected("declared optimal status has no realizable path")
    selected_list = certificate["selected"]
    if not isinstance(selected_list, list) or any(not _integer(x, 0, len(model["monitors"]) - 1)
                                                  for x in selected_list):
        raise Rejected("bad selected monitor list")
    if any(right <= left for left, right in zip(selected_list, selected_list[1:])):
        raise Rejected("selected monitors must be sorted and unique")
    selected = set(selected_list)
    cost = sum(model["monitors"][m][2] for m in selected)
    if not _integer(certificate["cost"]) or certificate["cost"] != cost:
        raise Rejected("placement cost mismatch")

    potential = certificate["potential"]
    if not isinstance(potential, list) or len(potential) != len(graph["nodes"]):
        raise Rejected("bad potential length")
    if any(not _integer(value, 0, k) for value in potential):
        raise Rejected("potentials must be integers in [0,k]")
    if potential[graph["source"]] != 0 or potential[graph["target"]] != k:
        raise Rejected("potential endpoints do not certify k coverage")
    for edge in graph["edges"]:
        allowance = 1 if edge["kind"] == "monitor" and edge["monitor"] in selected else 0
        if potential[edge["v"]] - potential[edge["u"]] > allowance:
            raise Rejected("local potential inequality failed")

    flow_value = certificate["flow_value"]
    if not _integer(flow_value):
        raise Rejected("bad flow value")
    flow_entries = certificate["flow"]
    if not isinstance(flow_entries, list):
        raise Rejected("flow must be a list")
    if len(flow_entries) > len(graph["edges"]):
        raise Rejected("too many sparse flow entries")
    y = {edge["id"]: 0 for edge in graph["edges"]}
    last = None
    for item in flow_entries:
        if not isinstance(item, list) or len(item) != 2:
            raise Rejected("flow entry requires [edge,value]")
        edge_id, value = item
        if edge_id not in y or not _integer(value, 1):
            raise Rejected("bad positive flow entry")
        if last is not None and edge_id <= last:
            raise Rejected("flow entries must be strictly edge-sorted")
        last = edge_id
        y[edge_id] = value
    balance = [0] * len(graph["nodes"])
    for edge in graph["edges"]:
        value = y[edge["id"]]
        balance[edge["u"]] += value
        balance[edge["v"]] -= value
    for vertex, value in enumerate(balance):
        expected = flow_value if vertex == graph["source"] else -flow_value if vertex == graph["target"] else 0
        if value != expected:
            raise Rejected("flow conservation failed")

    overflow_entries = certificate["overflow"]
    if not isinstance(overflow_entries, list):
        raise Rejected("overflow must be a list")
    if len(overflow_entries) > len(model["monitors"]):
        raise Rejected("too many sparse overflow entries")
    overflow = {m: 0 for m in range(len(model["monitors"]))}
    previous = -1
    for item in overflow_entries:
        if not isinstance(item, list) or len(item) != 2:
            raise Rejected("overflow entry requires [monitor,value]")
        monitor, value = item
        if not _integer(monitor, 0, len(model["monitors"]) - 1) or not _integer(value, 1):
            raise Rejected("bad overflow entry")
        if monitor <= previous:
            raise Rejected("overflow entries must be strictly monitor-sorted")
        previous = monitor
        overflow[monitor] = value
    for monitor, edge_id in graph["monitor_edges"].items():
        if y[edge_id] - overflow[monitor] > model["monitors"][monitor][2]:
            raise Rejected("dual monitor capacity inequality failed")
    dual = k * flow_value - sum(overflow.values())
    if not _integer(certificate["dual_value"]) or certificate["dual_value"] != dual or dual != cost:
        raise Rejected("primal and dual objectives do not match")
    return _result(graph, status, cost, dual)


def _result(graph, status, cost, dual):
    return {
        "accepted": True,
        "status": status,
        "cost": cost,
        "dual_value": dual,
        "compiled_nodes": len(graph["nodes"]),
        "compiled_edges": len(graph["edges"]),
    }
