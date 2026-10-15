#!/usr/bin/env python3
"""Reproduce same-information baselines; no network or package installation.

Use --work for private intermediates and --out for scientific results. Each
method runs in its own fresh, sequential subprocess. Timings include file
read/decode, admission, compilation, classification, primal production, common
integer evidence, independent checking and output serialization. Library
startup is separately reported, not silently charged to only the first case.
"""
from __future__ import annotations

import argparse
import csv
import ctypes
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))


def peak_rss_bytes():
    if os.name != "nt":
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024)
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in ("PeakWorkingSetSize", "WorkingSetSize",
                "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage",
                "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(counters.PeakWorkingSetSize)


def worker(args):
    import_start = time.perf_counter()
    import numpy
    import scipy
    from checker import verify
    from fair_baselines import (EnumerationLimit, certify, check_selection,
                                classify, selection)
    from io_utils import parse_json
    from model import validate_model
    from producer_compile import compile_model
    import_ms = 1000*(time.perf_counter()-import_start)
    rows, evidence = [], {}
    files = sorted(args.input_dir.glob("*.json"))
    for repetition in range(args.repetitions):
        # Reverse order on alternate repetitions to expose order effects.
        for file in (files if repetition % 2 == 0 else list(reversed(files))):
            start = time.perf_counter()
            row = {"case": file.stem, "method": args.worker, "repetition": repetition,
                   "outcome": "completed", "certified": False, "feasible": False,
                   "cost": None, "selected": [], "oracle": "not_run", "oracle_cost": None}
            before = start
            def stamp(name):
                nonlocal before
                now = time.perf_counter()
                row[name+"_ms"] = 1000*(now-before)
                before = now
            model = parse_json(file.read_text(encoding="utf-8"))
            stamp("input")
            row.update(family=model["family"], nodes=model["nodes"], physical_edges=len(model["edges"]),
                       monitors=len(model["monitors"]), k=model["failures"]+1,
                       input_bytes=file.stat().st_size)
            validate_model(model)
            stamp("admission")
            graph = compile_model(model)
            stamp("compile")
            row.update(compiled_nodes=len(graph["nodes"]), compiled_edges=len(graph["edges"]))
            certificate = classify(graph, model)
            stamp("classification")
            selected = set()
            try:
                if certificate is None:
                    selected, meta = selection(model, graph, args.worker, args.cap)
                    row.update(meta)
                stamp("primal")
                if certificate is None and args.worker != "cover-greedy":
                    certificate = certify(graph, model, selected)
                stamp("witness")
                if certificate is not None:
                    checked = verify(model, certificate)
                    row.update(status=checked["status"], cost=checked["cost"], certified=True,
                               feasible=checked["status"] in ("optimal", "vacuous"),
                               selected=certificate.get("selected", []))
                    output = certificate
                else:
                    status = check_selection(model, selected)
                    row.update(status=status, feasible=True, selected=sorted(selected),
                               cost=sum(model["monitors"][i][2] for i in selected))
                    output = {"case": model["case"], "status": status,
                              "selected": sorted(selected), "cost": row["cost"]}
                stamp("check")
                encoded = json.dumps(output, sort_keys=True, separators=(",", ":"))
                row["output_bytes"] = len(encoded.encode("utf-8"))
                stamp("serialize")
                if repetition == 0:
                    evidence[model["case"]] = output
            except EnumerationLimit as exc:
                stamp("primal")
                row.update(outcome="enumeration_limit", status="not_solved", reason=str(exc))
            # Unexpected solver/checker errors abort the run rather than becoming
            # a misleading successful status or a missing unfavorable row.
            row["total_ms"] = 1000*(time.perf_counter()-start)
            rows.append(row)
    return dict(rows=rows, evidence=evidence, import_ms=import_ms,
                peak_process_rss_bytes=peak_rss_bytes(),
                python=sys.version, numpy=numpy.__version__, scipy=scipy.__version__,
                platform=platform.platform())


def main(args):
    from checker import verify
    from fair_baselines import METHODS, choice_optimum, structured_cases
    from io_utils import fresh_directory, load_json, write_csv, write_json
    from oracle import brute_force_optimum, physical_observations
    out = fresh_directory(args.out)
    work = fresh_directory(args.work)
    inputs = work / "inputs"
    inputs.mkdir()
    source_start = time.perf_counter()
    retained = [] if args.structured_only else load_json(ROOT / "inputs/suite.json")
    source_read_ms = 1000*(time.perf_counter()-source_start)
    models = retained + structured_cases()
    write_json(out / "structured-inputs.json", structured_cases())
    write_csv(out / "input-lineage.csv", [dict(case=m["case"],
        source="inputs/suite.json" if i < len(retained) else "structured-inputs.json",
        source_index=i if i < len(retained) else i-len(retained),
        transformation="exact model object; JSON serialization only") for i,m in enumerate(models)])
    for model in models:
        write_json(inputs / (model["case"]+".json"), model)
    all_rows, resources = [], {}
    for method in METHODS:
        command = [sys.executable, "-B", str(Path(__file__).resolve()), "--worker", method,
                   "--input-dir", str(inputs), "--repetitions", str(args.repetitions), "--cap", str(args.cap)]
        start = time.perf_counter()
        completed = subprocess.run(command, check=True, capture_output=True, text=True, timeout=900)
        payload = json.loads(completed.stdout)
        resources[method] = {k:v for k,v in payload.items() if k not in ("rows", "evidence")}
        resources[method]["cold_batch_wall_ms"] = 1000*(time.perf_counter()-start)
        # Console streams, including library warnings, remain private.
        (work / (method+".stderr.txt")).write_text(completed.stderr, encoding="utf-8")
        all_rows.extend(payload["rows"])
        write_json(out / (method+"-outputs.json"), payload["evidence"])
        print(method, len(payload["rows"]), "rows", flush=True)
    # Independent oracles are in the parent, outside BOTH worker timings and
    # worker RSS. They cannot inflate a method's reported process memory.
    oracle_rows, observations_by_case, expected = {}, {}, {}
    for model in models:
        case = model["case"]
        if model["family"] == "Choice":
            expected[case] = ("optimal", choice_optimum(model))
            oracle_rows[case] = dict(oracle="layer_product", oracle_cost=choice_optimum(model))
        else:
            cert = load_json(ROOT/"results/campaign/certificates"/(case+".json"))
            verify(model, cert)
            expected[case] = (cert["status"], cert.get("cost"))
            if model["family"] == "Tiny" or (model["family"] == "Fan" and len(model["monitors"]) <= 12):
                observations = physical_observations(model)
                status, _, cost = brute_force_optimum(model, observations)
                assert expected[case] == (status, cost)
                observations_by_case[case] = observations
                oracle_rows[case] = dict(oracle="direct_subset", oracle_cost=cost, oracle_status=status)
    costs = {}
    for row in all_rows:
        row.update(oracle_rows.get(row["case"], {"oracle": "retained_checked_optimum"}))
        if row["outcome"] == "completed":
            status, cost = expected[row["case"]]
            if row["certified"]:
                assert (row["status"], row["cost"]) == (status, cost)
            elif cost is not None:
                assert row["cost"] >= cost
            if row["case"] in observations_by_case and row["feasible"]:
                assert all(len(set(row["selected"]).intersection(obs)) >= row["k"]
                           for obs in observations_by_case[row["case"]])
        if row["certified"]:
            key = row["case"]
            value = (row["status"], row["cost"])
            if key in costs:
                assert costs[key] == value, (key, value, costs[key])
            costs[key] = value
    fields = sorted(set().union(*(row.keys() for row in all_rows)))
    write_csv(out / "cases.csv", all_rows, fields)
    summary = dict(models=len(models), retained_models=len(retained), structured_models=len(models)-len(retained),
                   repetitions=args.repetitions, observation_state_cap=args.cap,
                   retained_suite_read_ms=source_read_ms, methods={})
    for method in METHODS:
        selected_rows = [r for r in all_rows if r["method"] == method]
        done = [r for r in selected_rows if r["outcome"] == "completed"]
        gaps = [r["cost"]/costs[r["case"]][1] for r in done if r["status"] in ("optimal", "feasible")]
        family_results = {}
        for family in sorted({r["family"] for r in selected_rows}):
            subset = [r for r in done if r["family"] == family]
            family_results[family] = {"completed": len(subset),
                **{phase+"_median_ms": statistics.median([r.get(phase+"_ms", 0.) for r in subset]) if subset else None
                   for phase in ("input", "admission", "compile", "classification", "primal", "witness", "check", "serialize", "total")}}
        summary["methods"][method] = dict(completed=len(done),
            enumeration_limits=len(selected_rows)-len(done), certified=sum(r["certified"] for r in done),
            max_quality_ratio=max(gaps), above_optimum=sum(x > 1 for x in gaps), families=family_results)
    write_json(out / "summary.json", summary)
    write_json(out / "resources.json", resources)
    print(json.dumps({k:v for k,v in summary.items() if k != "methods"}, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--work", type=Path)
    parser.add_argument("--worker")
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--cap", type=int, default=32768)
    parser.add_argument("--structured-only", action="store_true")
    args = parser.parse_args()
    if args.repetitions < 1 or args.cap < 1:
        parser.error("positive repetitions and cap required")
    if args.worker:
        print(json.dumps(worker(args), sort_keys=True))
    else:
        if args.out is None or args.work is None:
            parser.error("--out and --work required")
        main(args)
