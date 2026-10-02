"""Malformed-certificate and out-of-class controls."""
from __future__ import annotations

from copy import deepcopy

from checker import Rejected, verify


def _expect_rejection(name, model, certificate):
    try:
        verify(model, certificate)
    except (Rejected, ValueError, AssertionError) as exc:
        return {"control": name, "outcome": "rejected", "reason": str(exc)}
    raise AssertionError("control was accepted: " + name)


def run_controls(models, certificates):
    by_case = {m["case"]: m for m in models}
    opt0 = deepcopy(certificates["T000"])
    opt1 = deepcopy(certificates["T001"])
    inf = deepcopy(certificates["I000"])
    vac = deepcopy(certificates["V000"])
    rows = []

    c = deepcopy(opt0); removed = c["selected"].pop(); c["cost"] -= by_case["T000"]["monitors"][removed][2]
    rows.append(_expect_rejection("remove-selected", by_case["T000"], c))
    c = deepcopy(opt0); c["cost"] += 1
    rows.append(_expect_rejection("wrong-primal-cost", by_case["T000"], c))
    c = deepcopy(opt0); c["potential"][0] = 1
    rows.append(_expect_rejection("nonzero-source-potential", by_case["T000"], c))
    c = deepcopy(opt0); c["potential"][1] = 0
    rows.append(_expect_rejection("low-sink-potential", by_case["T000"], c))
    c = deepcopy(opt0); c["potential"] = c["potential"][:-1]
    rows.append(_expect_rejection("short-potential", by_case["T000"], c))
    c = deepcopy(opt0); c["flow_value"] += 1
    rows.append(_expect_rejection("wrong-flow-value", by_case["T000"], c))
    c = deepcopy(opt0); c["flow"][0][1] += 1
    rows.append(_expect_rejection("flow-conservation", by_case["T000"], c))
    c = deepcopy(opt0); c["flow"] = list(reversed(c["flow"]))
    rows.append(_expect_rejection("unsorted-flow", by_case["T000"], c))
    c = deepcopy(opt0); c["flow"].insert(1, list(c["flow"][0]))
    rows.append(_expect_rejection("duplicate-flow-edge", by_case["T000"], c))
    c = deepcopy(opt1); c["overflow"] = []
    rows.append(_expect_rejection("missing-overflow", by_case["T001"], c))
    c = deepcopy(opt0); c["dual_value"] += 1
    rows.append(_expect_rejection("wrong-dual-objective", by_case["T000"], c))
    c = deepcopy(opt0); c["selected"] = [len(by_case["T000"]["monitors"])]
    rows.append(_expect_rejection("unknown-monitor", by_case["T000"], c))
    c = deepcopy(opt1); c["selected"] = list(reversed(c["selected"]))
    rows.append(_expect_rejection("unsorted-selected", by_case["T001"], c))
    c = {"schema":"vcm-certificate-1","case":"T000","status":"vacuous","k":1,"cost":0}
    rows.append(_expect_rejection("reachable-false-vacuity", by_case["T000"], c))

    empty_model = {
        "case": "Empty", "family": "Boundary", "nodes": 2, "edges": [],
        "monitors": [], "obligation": [0, 1, 0], "horizon": 0, "failures": 0,
    }
    empty_optimal = {
        "schema": "vcm-certificate-1", "case": "Empty", "status": "optimal",
        "k": 1, "selected": [], "cost": 0,
        "potential": [0, 1, 0, 0, 1, 1, 1, 1, 1, 1],
        "flow_value": 0, "flow": [], "overflow": [], "dual_value": 0,
    }
    rows.append(_expect_rejection("unreachable-false-optimal", empty_model, empty_optimal))
    c = deepcopy(inf); c["witness"] = c["witness"][:-1]
    rows.append(_expect_rejection("truncated-infeasible-witness", by_case["I000"], c))
    c = deepcopy(inf); c["all_monitor_count"] += 1
    rows.append(_expect_rejection("wrong-witness-count", by_case["I000"], c))
    c = deepcopy(vac); c["cost"] = 1
    rows.append(_expect_rejection("nonzero-vacuous-cost", by_case["V000"], c))
    c = deepcopy(vac); c["extra"] = 1
    rows.append(_expect_rejection("unexpected-field", by_case["V000"], c))

    bad_model = deepcopy(by_case["T000"]); bad_model["monitors"][0][1] = "local"
    rows.append(_expect_rejection("local-hook-outside-class", bad_model, opt0))
    bad_model = deepcopy(by_case["T000"]); bad_model["edges"].append([bad_model["nodes"]-1, 0, 0, "keep"])
    rows.append(_expect_rejection("cyclic-physical-model", bad_model, opt0))
    return rows
