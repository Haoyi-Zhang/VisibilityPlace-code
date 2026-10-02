#!/usr/bin/env python3
"""Run fixed-seed differential checks on small policy models."""
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
from checker import verify
from checker_compile import compile_for_checking
from fuzz_cases import deterministic_fuzz_cases
from model import validate_model
from oracle import brute_force_optimum, compiled_observations, physical_observations
from producer_compile import compile_model
from solver import solve


def run(count, seed):
    cases = deterministic_fuzz_cases(count=count, seed=seed)
    status_counts = {"optimal": 0, "infeasible": 0, "vacuous": 0}
    rows = []
    max_realizations = 0
    for model in cases:
        validate_model(model)
        producer_graph = compile_model(model)
        checker_graph = compile_for_checking(model)
        if producer_graph["nodes"] != checker_graph["nodes"] or producer_graph["edges"] != checker_graph["edges"]:
            raise AssertionError("compiler mismatch for " + model["case"])
        physical = physical_observations(model)
        compiled = compiled_observations(producer_graph)
        if physical != compiled:
            raise AssertionError("semantic mismatch for " + model["case"])
        oracle_status, _, oracle_cost = brute_force_optimum(model, physical)
        certificate, _ = solve(model)
        checked = verify(model, certificate)
        if certificate["status"] != oracle_status:
            raise AssertionError("status mismatch for " + model["case"])
        if certificate.get("cost") != oracle_cost:
            raise AssertionError("cost mismatch for " + model["case"])
        status_counts[oracle_status] += 1
        max_realizations = max(max_realizations, len(physical))
        rows.append({
            "case": model["case"],
            "status": oracle_status,
            "oracle_cost": "" if oracle_cost is None else oracle_cost,
            "realizations": len(physical),
            "physical_nodes": model["nodes"],
            "physical_edges": len(model["edges"]),
            "monitors": len(model["monitors"]),
            "k": model["failures"] + 1,
            "compiled_nodes": checked["compiled_nodes"],
            "compiled_edges": checked["compiled_edges"],
        })
    return rows, {
        "schema": "vcm-fuzz-summary-1",
        "seed": seed,
        "random_cases": count,
        "targeted_cases": len(cases) - count,
        "total_cases": len(cases),
        "status_counts": status_counts,
        "max_realizations": max_realizations,
        "all_compilers_equal": True,
        "all_semantics_equal": True,
        "all_bruteforce_status_and_cost_equal": True,
        "all_certificates_accepted": True,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=192)
    parser.add_argument("--seed", type=int, default=20260918)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if not 0 <= args.count <= 1000:
        raise SystemExit("count must be in [0,1000]")
    install_limits()
    start = time.perf_counter()
    start_cpu = time.process_time()
    rows, summary = run(args.count, args.seed)
    summary["wall_seconds"] = time.perf_counter() - start
    summary["cpu_seconds"] = time.process_time() - start_cpu
    summary["peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        with (args.out / "cases.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["case"])
            writer.writeheader()
            writer.writerows(rows)
        (args.out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
