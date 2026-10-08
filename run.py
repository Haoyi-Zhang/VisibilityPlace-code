#!/usr/bin/env python3
"""Generate, solve, check, replay, or compare the deterministic campaign."""
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
from checker import Rejected, verify
from comparison import project_summary
from controls import run_controls
from instances import all_cases
from io_utils import fresh_directory, load_json, write_csv, write_json
from model import validate_model
from oracle import brute_force_optimum, compiled_observations, physical_observations
from producer_compile import compile_model


def _json_bytes(value):
    return len((json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def _evaluate(models, out):
    # Imported only for certificate production.  The ``check`` and ``compare``
    # commands therefore remain usable under ``python -S`` without SciPy or
    # NetworkX on the import path.
    from solver import degree_baseline, path_repair_baseline, solve

    start_wall = time.perf_counter()
    start_cpu = time.process_time()
    cert_dir = out / "certificates"
    cert_dir.mkdir()
    rows = []
    certificates = {}
    exact_count = 0
    for number, model in enumerate(models, 1):
        validate_model(model)
        certificate, meta = solve(model)
        check_start = time.perf_counter()
        checked = verify(model, certificate)
        checker_ms = 1000.0 * (time.perf_counter() - check_start)
        certificates[model["case"]] = certificate
        write_json(cert_dir / (model["case"] + ".json"), certificate)
        graph = compile_model(model)
        k = model["failures"] + 1
        greedy = degree = ""
        if certificate["status"] == "optimal":
            greedy = path_repair_baseline(model, graph, k)
            degree = degree_baseline(model, graph, k)
        exact = model["family"] == "Tiny" or (
            model["family"] == "Fan" and len(model["monitors"]) <= 12
        )
        if exact:
            raw_rows = physical_observations(model)
            compiled_rows = compiled_observations(graph)
            if raw_rows != compiled_rows:
                raise AssertionError("semantic/compiler path multiset mismatch: " + model["case"])
            oracle_status, _, oracle_cost = brute_force_optimum(model, raw_rows)
            if oracle_status != certificate["status"] or oracle_cost != certificate.get("cost"):
                raise AssertionError("brute-force optimum mismatch: " + model["case"])
            exact_count += 1
        rows.append({
            "case": model["case"],
            "family": model["family"],
            "status": certificate["status"],
            "nodes": model["nodes"],
            "physical_edges": len(model["edges"]),
            "monitors": len(model["monitors"]),
            "horizon": model["horizon"],
            "failures": model["failures"],
            "k": k,
            "compiled_nodes": meta["compiled_nodes"],
            "compiled_edges": meta["compiled_edges"],
            "selected": len(certificate.get("selected", [])),
            "optimal_cost": "" if certificate.get("cost") is None else certificate.get("cost", ""),
            "dual_value": "" if certificate["status"] != "optimal" else certificate["dual_value"],
            "flow_value": "" if certificate["status"] != "optimal" else certificate["flow_value"],
            "overflow": "" if certificate["status"] != "optimal" else sum(x[1] for x in certificate["overflow"]),
            "all_monitor_count": certificate.get("all_monitor_count", ""),
            "lp_objective": "" if meta["lp_objective"] is None else f"{meta['lp_objective']:.9f}",
            "rounding_alpha": "" if meta["rounding_alpha"] is None else f"{meta['rounding_alpha']:.9f}",
            "greedy_cost": "" if greedy is None else greedy,
            "degree_cost": "" if degree is None else degree,
            "producer_ms": f"{meta['producer_ms']:.6f}",
            "checker_ms": f"{checker_ms:.6f}",
            "certificate_bytes": _json_bytes(certificate),
            "exact_oracle": "yes" if exact else "no",
            "accepted": "yes" if checked["accepted"] else "no",
        })
    write_csv(out / "cases.csv", rows)
    controls = run_controls(models, certificates)
    write_csv(out / "controls.csv", controls)
    statuses = {name: sum(r["status"] == name for r in rows)
                for name in ("optimal", "infeasible", "vacuous")}
    optimal_rows = [r for r in rows if r["status"] == "optimal"]
    summary = {
        "cases": len(rows),
        "optimal": statuses["optimal"],
        "infeasible": statuses["infeasible"],
        "vacuous": statuses["vacuous"],
        "exact_oracle_cases": exact_count,
        "controls_rejected": sum(r["outcome"] == "rejected" for r in controls),
        "max_physical_nodes": max(r["nodes"] for r in rows),
        "max_physical_edges": max(r["physical_edges"] for r in rows),
        "max_monitors": max(r["monitors"] for r in rows),
        "max_horizon": max(r["horizon"] for r in rows),
        "max_compiled_nodes": max(r["compiled_nodes"] for r in rows),
        "max_compiled_edges": max(r["compiled_edges"] for r in rows),
        "max_certificate_bytes": max(r["certificate_bytes"] for r in rows),
        "greedy_worse": sum(int(r["greedy_cost"]) > int(r["optimal_cost"]) for r in optimal_rows),
        "degree_worse": sum(int(r["degree_cost"]) > int(r["optimal_cost"]) for r in optimal_rows),
        "claim_scope": "owned synthetic acyclic export-only policy models; no deployed BGP claim",
    }
    write_json(out / "summary.json", summary)
    resources = {
        "wall_seconds": time.perf_counter() - start_wall,
        "cpu_seconds": time.process_time() - start_cpu,
        "process_cpu_seconds_recorded": time.process_time(),
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "workers": 1,
        "address_space_limit_bytes": 3 * 1024**3,
        "cpu_limit_seconds": 2700,
    }
    write_json(out / "resources.json", resources)
    return summary


STRICT_IGNORED_FIELDS = {"producer_ms", "checker_ms"}
SEMANTIC_CASE_FIELDS = (
    "case", "family", "status", "nodes", "physical_edges", "monitors",
    "horizon", "failures", "k", "compiled_nodes", "compiled_edges",
    "optimal_cost", "all_monitor_count", "greedy_cost", "degree_cost",
    "exact_oracle", "accepted",
)


def _project_rows(path, mode):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if mode == "strict":
        return [{key: value for key, value in row.items()
                 if key not in STRICT_IGNORED_FIELDS} for row in rows]
    return [{key: row[key] for key in SEMANTIC_CASE_FIELDS} for row in rows]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("generate"); p.add_argument("--out", type=Path, required=True)
    for name in ("pilot", "reproduce"):
        p = sub.add_parser(name); p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("check")
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--certificate", type=Path, required=True)
    p = sub.add_parser("compare")
    p.add_argument("--observed", type=Path, required=True)
    p.add_argument("--mode", choices=("semantic", "strict"), default="semantic")
    args = parser.parse_args()
    install_limits()
    cases = all_cases()
    retained = ROOT / "inputs" / "suite.json"
    if retained.exists() and load_json(retained) != cases:
        raise ValueError("retained suite differs from deterministic generator")
    if args.command == "generate":
        write_json(args.out, cases)
        print("wrote 120 deterministic owned cases")
        return
    if args.command == "check":
        print(json.dumps(verify(load_json(args.model), load_json(args.certificate)), sort_keys=True))
        return
    if args.command == "compare":
        expected = ROOT / "results" / "campaign"
        if _project_rows(expected / "cases.csv", args.mode) != _project_rows(args.observed / "cases.csv", args.mode):
            raise ValueError(args.mode + " campaign fields differ")
        if project_summary(load_json(expected / "summary.json"), args.mode) != project_summary(load_json(args.observed / "summary.json"), args.mode):
            raise ValueError("summary differs")
        if _project_rows(expected / "controls.csv", "strict") != _project_rows(args.observed / "controls.csv", "strict"):
            raise ValueError("control outcomes or rejection reasons differ")
        models = {m["case"]: m for m in cases}
        for case, model in models.items():
            cert = load_json(args.observed / "certificates" / (case + ".json"))
            verify(model, cert)
            expected_cert = load_json(expected / "certificates" / (case + ".json"))
            if args.mode == "strict":
                if cert != expected_cert:
                    raise ValueError("certificate differs: " + case)
            elif (cert.get("status"), cert.get("cost")) != (expected_cert.get("status"), expected_cert.get("cost")):
                raise ValueError("certificate status or certified optimum differs: " + case)
        if args.mode == "strict":
            print("strict fixed-environment objects match: non-runtime rows, controls, and all 120 certificate objects")
        else:
            print("semantic fields and certified statuses/costs match; observed certificates were revalidated; floating diagnostics and witness identity excluded")
        return
    out = fresh_directory(args.out)
    if args.command == "pilot":
        # Include the four representatives used by malformed-certificate controls,
        # plus two scaling cases and one adversarial fan case.
        chosen = {"T000", "T001", "L012", "L037", "F007", "I000", "V000"}
        models = [m for m in cases if m["case"] in chosen]
    else:
        models = cases
    summary = _evaluate(models, out)
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, Rejected, AssertionError, OSError, MemoryError) as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}), file=sys.stderr)
        raise SystemExit(2)
