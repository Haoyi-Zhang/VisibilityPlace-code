#!/usr/bin/env python3
"""Audit replayed evidence against the retained deterministic record.

This script is intentionally standard-library only.  It does not invoke the
producer or trust solver diagnostics.  It checks exact certificates, semantic
campaign fields, control rejections, derived manuscript data, deterministic
small-model differential and bounded-exhaustive results, and evidence-ledger structure.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from checker import verify
from comparison import project_summary
from instances import all_cases
from io_utils import load_json

STRICT_IGNORED_FIELDS = {"producer_ms", "checker_ms"}
FUZZ_TIMING_FIELDS = {"wall_seconds", "cpu_seconds", "peak_rss_kib"}
SEMANTIC_CASE_FIELDS = (
    "case", "family", "status", "nodes", "physical_edges", "monitors",
    "horizon", "failures", "k", "compiled_nodes", "compiled_edges",
    "optimal_cost", "all_monitor_count", "greedy_cost", "degree_cost",
    "exact_oracle", "accepted",
)


def csv_rows(path: Path, ignored=frozenset()):
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return [{key: value for key, value in row.items() if key not in ignored}
            for row in rows]


def exact_file_tree(expected: Path, observed: Path):
    expected_files = sorted(p.relative_to(expected) for p in expected.rglob("*") if p.is_file())
    observed_files = sorted(p.relative_to(observed) for p in observed.rglob("*") if p.is_file())
    if expected_files != observed_files:
        raise ValueError("derived file inventory differs")
    for relative in expected_files:
        if (expected / relative).read_bytes() != (observed / relative).read_bytes():
            raise ValueError("derived file differs: " + str(relative))
    return len(expected_files)


def _campaign_rows(path: Path, mode: str):
    rows = csv_rows(path)
    if mode == "strict":
        return [{key: value for key, value in row.items()
                 if key not in STRICT_IGNORED_FIELDS} for row in rows]
    return [{key: row[key] for key in SEMANTIC_CASE_FIELDS} for row in rows]


def audit_campaign(observed: Path, mode: str):
    expected = ROOT / "results" / "campaign"
    if _campaign_rows(expected / "cases.csv", mode) != _campaign_rows(observed / "cases.csv", mode):
        raise ValueError("campaign " + mode + " rows differ")
    if csv_rows(expected / "controls.csv") != csv_rows(observed / "controls.csv"):
        raise ValueError("campaign controls differ")
    if project_summary(load_json(expected / "summary.json"), mode) != project_summary(load_json(observed / "summary.json"), mode):
        raise ValueError("campaign summary differs")
    models = {model["case"]: model for model in all_cases()}
    expected_names = sorted(path.name for path in (expected / "certificates").glob("*.json"))
    observed_names = sorted(path.name for path in (observed / "certificates").glob("*.json"))
    if expected_names != observed_names or len(expected_names) != len(models):
        raise ValueError("certificate inventory differs")
    for case, model in models.items():
        retained = load_json(expected / "certificates" / (case + ".json"))
        replayed = load_json(observed / "certificates" / (case + ".json"))
        verify(model, replayed)
        if mode == "strict":
            if retained != replayed:
                raise ValueError("certificate differs: " + case)
        elif (retained.get("status"), retained.get("cost")) != (replayed.get("status"), replayed.get("cost")):
            raise ValueError("certificate status or certified optimum differs: " + case)
    return len(models)


def audit_fuzz(observed: Path):
    expected = ROOT / "results" / "fuzz"
    if csv_rows(expected / "cases.csv") != csv_rows(observed / "cases.csv"):
        raise ValueError("differential-case rows differ")
    retained = {k: v for k, v in load_json(expected / "summary.json").items()
                if k not in FUZZ_TIMING_FIELDS}
    replayed = {k: v for k, v in load_json(observed / "summary.json").items()
                if k not in FUZZ_TIMING_FIELDS}
    if retained != replayed:
        raise ValueError("differential summary differs")
    if not all(replayed[key] for key in (
        "all_compilers_equal", "all_semantics_equal",
        "all_bruteforce_status_and_cost_equal", "all_certificates_accepted",
    )):
        raise ValueError("differential summary contains a failed obligation")
    return replayed["total_cases"]


def audit_exhaustive(observed: Path):
    expected = ROOT / "results" / "exhaustive"
    if csv_rows(expected / "cases.csv") != csv_rows(observed / "cases.csv"):
        raise ValueError("bounded-exhaustive rows differ")
    retained = load_json(expected / "summary.json")
    replayed = load_json(observed / "summary.json")
    if retained != replayed:
        raise ValueError("bounded-exhaustive summary differs")
    if replayed["total_cases"] != 13720 or replayed["expected_cases"] != 13720:
        raise ValueError("bounded-exhaustive universe is incomplete")
    if not all(replayed[key] for key in (
        "all_case_ids_unique", "all_models_valid", "all_compilers_equal",
        "all_semantics_equal", "all_bruteforce_classifications_complete",
    )):
        raise ValueError("bounded-exhaustive summary contains a failed obligation")
    return replayed["total_cases"]


def audit_ledgers():
    claims = csv_rows(ROOT / "claim_evidence_ledger.csv")
    if len({row["claim_id"] for row in claims}) != len(claims):
        raise ValueError("duplicate claim identifier")
    required_claim = set(claims[0])
    if any(set(row) != required_claim or any(not value.strip() for value in row.values()) for row in claims):
        raise ValueError("claim ledger has an empty or malformed row")

    resources = csv_rows(ROOT / "external_resources.csv")
    if any(not row["scholarly_or_official_url"].startswith("https://") for row in resources):
        raise ValueError("external resource lacks an HTTPS scholarly/official URL")

    references = csv_rows(ROOT / "docs" / "reference-audit.csv")
    if len(references) != 58 or len({row["key"] for row in references}) != 58:
        raise ValueError("reference audit must contain 58 unique manuscript keys")
    if any(row["cited"] != "yes" or not row["canonical_identifier"].strip()
           or not row["verification_source"].startswith("https://") for row in references):
        raise ValueError("reference audit has an uncited or unverifiable entry")
    return len(claims), len(resources), len(references)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--derived", type=Path, required=True)
    parser.add_argument("--fuzz", type=Path, required=True)
    parser.add_argument("--exhaustive", type=Path, required=True)
    parser.add_argument("--mode", choices=("semantic", "strict"), default="semantic")
    args = parser.parse_args()

    certificates = audit_campaign(args.campaign, args.mode)
    if args.mode == "strict":
        derived_files = exact_file_tree(ROOT / "results" / "derived", args.derived)
    else:
        semantic_derived = (
            "analysis.json", "baselines.csv", "baselines.tex", "families.csv",
            "families.tex", "fan.csv", "summary-macros.tex",
        )
        for name in semantic_derived:
            if (ROOT / "results" / "derived" / name).read_bytes() != (args.derived / name).read_bytes():
                raise ValueError("semantic derived file differs: " + name)
        derived_files = len(semantic_derived)
    fuzz_cases = audit_fuzz(args.fuzz)
    exhaustive_cases = audit_exhaustive(args.exhaustive)
    claims, resources, references = audit_ledgers()
    print(json.dumps({
        "accepted": True,
        "campaign_certificates": certificates,
        "derived_files": derived_files,
        "differential_cases": fuzz_cases,
        "bounded_exhaustive_cases": exhaustive_cases,
        "claim_rows": claims,
        "external_resource_rows": resources,
        "reference_rows": references,
        "comparison_mode": args.mode,
        "excluded_in_semantic_mode": sorted(STRICT_IGNORED_FIELDS | {"lp_objective", "rounding_alpha", "selected", "dual_value", "flow_value", "overflow", "certificate_bytes"}),
        "timing_fields_excluded": sorted(STRICT_IGNORED_FIELDS | FUZZ_TIMING_FIELDS),
    }, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, csv.Error, json.JSONDecodeError) as exc:
        print(json.dumps({"accepted": False, "reason": str(exc)}, sort_keys=True), file=sys.stderr)
        raise SystemExit(2)
