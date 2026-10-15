#!/usr/bin/env python3
"""Replay every serialized comparator result using standard-library checks.

This command does not import fair_baselines or any optimizer. It checks all
stored solutions, exact statuses/costs, repeated-run agreement and explicitly
recorded enumeration limits. SPDX-License-Identifier: MIT
"""
import argparse
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/"src"))
from checker import verify
from checker_compile import compile_for_checking
from dag import INF, selected_distance
from io_utils import load_json
from oracle import brute_force_optimum, physical_observations


def replay(directory):
    summary = load_json(directory/"summary.json")
    models = (load_json(ROOT/"inputs/suite.json") if summary["retained_models"] else []) + load_json(directory/"structured-inputs.json")
    by_case = {m["case"]: m for m in models}
    with (directory/"input-lineage.csv").open(encoding="utf-8", newline="") as handle:
        lineage = list(csv.DictReader(handle))
    sources = {"inputs/suite.json": load_json(ROOT/"inputs/suite.json"),
               "structured-inputs.json": load_json(directory/"structured-inputs.json")}
    assert len(lineage) == len(models) and len({r["case"] for r in lineage}) == len(models)
    for entry in lineage:
        assert sources[entry["source"]][int(entry["source_index"])] == by_case[entry["case"]]
    expected, observations = {}, {}
    for model in models:
        case = model["case"]
        if model["family"] == "Choice":
            width = int(case.removeprefix("Choice").split("x")[0])
            depth = len(model["monitors"])//width
            # Validate the structure on which the analytic oracle depends.
            layers = [[0]] + [list(range(1+i*width, 1+(i+1)*width)) for i in range(depth)]
            layers.append([1+width*depth])
            assert model["nodes"] == width*depth+2
            assert model["obligation"] == [0, model["nodes"]-1, 0]
            assert model["horizon"] == depth+1
            assert model["edges"] == [[u,v,0,"keep"] for left,right in zip(layers,layers[1:]) for u in left for v in right]
            assert [m[0] for m in model["monitors"]] == list(range(1, model["nodes"]-1))
            totals = [sum(m[2] for m in model["monitors"][i:i+width]) for i in range(0, len(model["monitors"]), width)]
            expected[case] = ("optimal", sum(sorted(totals)[:model["failures"]+1]))
        else:
            certificate = load_json(ROOT/"results/campaign/certificates"/(case+".json"))
            verify(model, certificate)
            expected[case] = (certificate["status"], certificate.get("cost"))
            if model["family"] == "Tiny" or (model["family"] == "Fan" and len(model["monitors"]) <= 12):
                observations[case] = physical_observations(model)
                status, _, cost = brute_force_optimum(model, observations[case])
                assert expected[case] == (status, cost)
    outputs, accepted, feasible = {}, 0, 0
    for method in summary["methods"]:
        outputs[method] = load_json(directory/(method+"-outputs.json"))
        for case, output in outputs[method].items():
            model = by_case[case]
            if output["status"] != "feasible":
                verify(model, output)
                assert (output["status"], output.get("cost")) == expected[case]
                accepted += 1
            else:
                chosen = output["selected"]
                assert chosen == sorted(set(chosen))
                assert all(type(i) is int and 0 <= i < len(model["monitors"]) for i in chosen)
                graph = compile_for_checking(model)
                distance, _ = selected_distance(graph, set(chosen))
                assert model["failures"]+1 <= distance[graph["target"]] < INF
                assert output["cost"] == sum(model["monitors"][i][2] for i in chosen)
                assert output["cost"] >= expected[case][1]
                if case in observations:
                    assert all(len(set(chosen).intersection(obs)) >= model["failures"]+1 for obs in observations[case])
                feasible += 1
    with (directory/"cases.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == len(models)*len(outputs)*summary["repetitions"]
    identifiers = set()
    for row in rows:
        key = (row["method"], row["case"], int(row["repetition"]))
        assert key not in identifiers
        assert 0 <= key[2] < summary["repetitions"] and key[0] in outputs and key[1] in by_case
        identifiers.add(key)
        if row["outcome"] == "enumeration_limit":
            assert row["method"] in ("explicit-milp", "cover-greedy")
            assert row["case"] not in outputs[row["method"]]
            assert row["status"] == "not_solved" and row["certified"] == "False"
        else:
            result = outputs[row["method"]][row["case"]]
            assert row["status"] == result["status"]
            assert row["cost"] == ("" if result.get("cost") is None else str(result["cost"]))
            assert float(row["total_ms"]) >= 0
            phases = ("input", "admission", "compile", "classification", "primal", "witness", "check", "serialize")
            assert sum(float(row[p+"_ms"]) for p in phases) <= float(row["total_ms"])+1e-6
    return dict(models=len(models), rows=len(rows), accepted_certificates=accepted,
                checked_feasible_selections=feasible, direct_subset_models=len(observations))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=ROOT/"results/fair-baselines")
    args = parser.parse_args()
    print(replay(args.results))
