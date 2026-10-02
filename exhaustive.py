#!/usr/bin/env python3
"""Enumerate and differentially check the complete three-vertex model universe."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import resource
import sys
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from bounds import install_limits
from checker_compile import compile_for_checking
from exhaustive_cases import EXPECTED_CASES, bounded_exhaustive_cases
from model import validate_model
from oracle import brute_force_optimum, compiled_observations, physical_observations
from producer_compile import compile_model


def run():
    rows = []
    status_counts = {"optimal": 0, "infeasible": 0, "vacuous": 0}
    max_realizations = 0
    max_compiled_nodes = 0
    max_compiled_edges = 0
    seen = set()

    for model in bounded_exhaustive_cases():
        validate_model(model)
        if model["case"] in seen:
            raise AssertionError("duplicate exhaustive case identifier")
        seen.add(model["case"])

        producer_graph = compile_model(model)
        checker_graph = compile_for_checking(model)
        if (producer_graph["nodes"] != checker_graph["nodes"] or
                producer_graph["edges"] != checker_graph["edges"]):
            raise AssertionError("compiler mismatch for " + model["case"])

        physical = physical_observations(model)
        compiled = compiled_observations(producer_graph)
        if physical != compiled:
            raise AssertionError("semantic mismatch for " + model["case"])

        status, selected, cost = brute_force_optimum(model, physical)
        status_counts[status] += 1
        max_realizations = max(max_realizations, len(physical))
        max_compiled_nodes = max(max_compiled_nodes, len(producer_graph["nodes"]))
        max_compiled_edges = max(max_compiled_edges, len(producer_graph["edges"]))
        rows.append({
            "case": model["case"],
            "edge_code": ";".join(
                f"{u}{v}{boundary}{action[0]}"
                for u, v, boundary, action in model["edges"]
            ),
            "monitor_mask": sum(1 << vertex for vertex, _, _ in model["monitors"]),
            "initial_restriction": model["obligation"][2],
            "failures": model["failures"],
            "status": status,
            "oracle_cost": "" if cost is None else cost,
            "selected": ";".join(map(str, selected)),
            "realizations": len(physical),
            "compiled_nodes": len(producer_graph["nodes"]),
            "compiled_edges": len(producer_graph["edges"]),
        })

    if len(rows) != EXPECTED_CASES or len(seen) != EXPECTED_CASES:
        raise AssertionError("incomplete exhaustive universe")
    summary = {
        "schema": "vcm-exhaustive-summary-1",
        "universe": {
            "vertices": 3,
            "source": 0,
            "target": 2,
            "forward_edge_slots": 3,
            "edge_options_per_slot": 7,
            "monitor_choice": "zero or one export monitor at each vertex; costs 1,2,3",
            "initial_restriction_values": 2,
            "failure_budgets": "all integers from zero through monitor count",
        },
        "expected_cases": EXPECTED_CASES,
        "total_cases": len(rows),
        "status_counts": status_counts,
        "max_realizations": max_realizations,
        "max_compiled_nodes": max_compiled_nodes,
        "max_compiled_edges": max_compiled_edges,
        "all_case_ids_unique": True,
        "all_models_valid": True,
        "all_compilers_equal": True,
        "all_semantics_equal": True,
        "all_bruteforce_classifications_complete": True,
    }
    return rows, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    install_limits()
    start = time.perf_counter()
    start_cpu = time.process_time()
    rows, summary = run()
    resources = {
        "wall_seconds": time.perf_counter() - start,
        "cpu_seconds": time.process_time() - start_cpu,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "workers": 1,
    }
    args.out.mkdir(parents=True, exist_ok=False)
    with (args.out / "cases.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (args.out / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.out / "resources.json").write_text(
        json.dumps(resources, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({**summary, **resources}, sort_keys=True))


if __name__ == "__main__":
    main()
