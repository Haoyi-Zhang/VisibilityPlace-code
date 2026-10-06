#!/usr/bin/env python3
"""Derive manuscript tables and plot data from retained campaign rows."""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from fractions import Fraction
import json
from pathlib import Path
import shutil


def read_csv(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fields=None):
    fields = fields or list(rows[0])
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def tex_table(path, column_spec, header, body, footer=None):
    lines = [r"\begin{tabular}{" + column_spec + "}", r"\toprule", header + r"\\", r"\midrule"]
    lines.extend(row + r"\\" for row in body)
    if footer is not None:
        lines.extend([r"\midrule", footer + r"\\"])
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--paper-data", type=Path)
    args = parser.parse_args()
    if args.out.exists() and any(args.out.iterdir()):
        raise ValueError("output directory must be absent or empty")
    args.out.mkdir(parents=True, exist_ok=True)
    rows = read_csv(args.results / "cases.csv")
    summary = json.loads((args.results / "summary.json").read_text())
    if len(rows) != summary["cases"]:
        raise ValueError("summary denominator mismatch")

    names = ["Tiny", "Layered", "Fan", "Infeasible", "Vacuous"]
    family_rows = []
    for family in names:
        group = [r for r in rows if r["family"] == family]
        family_rows.append({
            "family": family,
            "cases": len(group),
            "optimal": sum(r["status"] == "optimal" for r in group),
            "infeasible": sum(r["status"] == "infeasible" for r in group),
            "vacuous": sum(r["status"] == "vacuous" for r in group),
            "max_nodes": max(int(r["nodes"]) for r in group),
            "max_edges": max(int(r["physical_edges"]) for r in group),
            "max_monitors": max(int(r["monitors"]) for r in group),
        })
    write_csv(args.out / "families.csv", family_rows)
    tex_table(
        args.out / "families.tex", "lrrrrrrr",
        r"Family & $N$ & Opt. & Inf. & Vac. & $|V|_{\max}$ & $|E|_{\max}$ & $|M|_{\max}$",
        ["{family} & {cases} & {optimal} & {infeasible} & {vacuous} & {max_nodes} & {max_edges} & {max_monitors}".format(**r)
         for r in family_rows],
        "Total & {cases} & {optimal} & {infeasible} & {vacuous} & {max_physical_nodes} & {max_physical_edges} & {max_monitors}".format(**summary),
    )

    optimal = [r for r in rows if r["status"] == "optimal"]
    baseline_rows = []
    for family in ("Tiny", "Layered", "Fan"):
        group = [r for r in optimal if r["family"] == family]
        gp = [Fraction(int(r["greedy_cost"]), int(r["optimal_cost"])) for r in group]
        dp = [Fraction(int(r["degree_cost"]), int(r["optimal_cost"])) for r in group]
        baseline_rows.append({
            "family": family,
            "cases": len(group),
            "greedy_worse": sum(q > 1 for q in gp),
            "greedy_max": f"{float(max(gp)):.2f}",
            "degree_worse": sum(q > 1 for q in dp),
            "degree_max": f"{float(max(dp)):.2f}",
        })
    write_csv(args.out / "baselines.csv", baseline_rows)
    tex_table(
        args.out / "baselines.tex", "lrrrrr",
        r"Family & $N$ & repair worse & max ratio & degree worse & max ratio",
        ["{family} & {cases} & {greedy_worse} & {greedy_max} & {degree_worse} & {degree_max}".format(**r)
         for r in baseline_rows],
    )

    scaling = []
    for r in optimal:
        scaling.append({
            "case": r["case"],
            "family": r["family"],
            "physical_nodes": r["nodes"],
            "compiled_edges": r["compiled_edges"],
            "certificate_kib": f"{int(r['certificate_bytes']) / 1024.0:.6f}",
        })
    write_csv(args.out / "scaling.csv", scaling)

    fan = []
    for r in optimal:
        if r["family"] == "Fan":
            fan.append({
                "branches": int(r["nodes"]) - 3,
                "optimal": r["optimal_cost"],
                "path_repair": r["greedy_cost"],
                "degree": r["degree_cost"],
            })
    write_csv(args.out / "fan.csv", fan)

    macros = {
        "CampaignCases": summary["cases"],
        "OptimalCases": summary["optimal"],
        "InfeasibleCases": summary["infeasible"],
        "VacuousCases": summary["vacuous"],
        "ExactCases": summary["exact_oracle_cases"],
        "RejectedControls": summary["controls_rejected"],
        "MaxPhysicalNodes": summary["max_physical_nodes"],
        "MaxPhysicalEdges": summary["max_physical_edges"],
        "MaxMonitors": summary["max_monitors"],
        "MaxCompiledNodes": summary["max_compiled_nodes"],
        "MaxCompiledEdges": summary["max_compiled_edges"],
        "GreedyWorse": summary["greedy_worse"],
        "DegreeWorse": summary["degree_worse"],
    }
    (args.out / "summary-macros.tex").write_text(
        "".join("\\newcommand{\\%s}{%s}\n" % item for item in macros.items()),
        encoding="utf-8", newline="\n",
    )
    analysis = {
        "families": family_rows,
        "baselines": baseline_rows,
        "claim_scope": summary["claim_scope"],
        "timing_note": "single-environment descriptive measurements; correctness does not depend on timing",
    }
    (args.out / "analysis.json").write_text(
        json.dumps(analysis, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )
    if args.paper_data:
        args.paper_data.mkdir(parents=True, exist_ok=True)
        for name in ("families.tex", "baselines.tex", "scaling.csv", "fan.csv", "summary-macros.tex"):
            shutil.copyfile(args.out / name, args.paper_data / name)
    print("derived tables and plot data from {} case rows".format(len(rows)))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, csv.Error) as exc:
        raise SystemExit("analysis failed: " + str(exc))
