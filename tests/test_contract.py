from copy import deepcopy
import json
from pathlib import Path
import sys
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from checker import Rejected, verify
from checker_compile import compile_for_checking
from exhaustive_cases import EXPECTED_CASES, bounded_exhaustive_cases
from fuzz_cases import deterministic_fuzz_cases
from instances import all_cases
from model import validate_model
from oracle import brute_force_optimum, compiled_observations, physical_observations
from producer_compile import compile_model
from solver import path_repair_baseline, solve


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = all_cases()
        cls.by_case = {m["case"]: m for m in cls.cases}

    def test_suite_size_and_identifiers(self):
        self.assertEqual(120, len(self.cases))
        self.assertEqual(120, len(self.by_case))

    def test_all_models_validate(self):
        for model in self.cases:
            validate_model(model)

    def test_compilers_are_structurally_equal(self):
        for model in self.cases:
            a = compile_model(model)
            b = compile_for_checking(model)
            self.assertEqual(a["nodes"], b["nodes"])
            self.assertEqual(a["edges"], b["edges"])

    def test_tiny_path_semantics(self):
        for model in self.cases[:36]:
            self.assertEqual(physical_observations(model), compiled_observations(compile_model(model)))

    def test_tiny_optima(self):
        for model in self.cases[:12]:
            cert, _ = solve(model)
            status, _, cost = brute_force_optimum(model, physical_observations(model))
            self.assertEqual(status, cert["status"])
            self.assertEqual(cost, cert.get("cost"))

    def test_representative_statuses(self):
        for case, status in [("T000", "optimal"), ("I000", "infeasible"), ("V000", "vacuous")]:
            cert, _ = solve(self.by_case[case])
            self.assertEqual(status, cert["status"])
            self.assertTrue(verify(self.by_case[case], cert)["accepted"])

    def test_primal_dual_equality(self):
        for case in ("T001", "L000", "L047", "F011"):
            cert, _ = solve(self.by_case[case])
            self.assertEqual(cert["cost"], cert["dual_value"])

    def test_fan_baseline_gap(self):
        model = self.by_case["F011"]
        cert, _ = solve(model)
        greedy = path_repair_baseline(model, compile_model(model), 1)
        self.assertGreater(greedy, cert["cost"])

    def test_removed_monitor_rejected(self):
        model = self.by_case["T000"]
        cert, _ = solve(model)
        bad = deepcopy(cert)
        bad["selected"] = []
        bad["cost"] = 0
        with self.assertRaises(Rejected):
            verify(model, bad)

    def test_flow_mutation_rejected(self):
        model = self.by_case["T001"]
        cert, _ = solve(model)
        bad = deepcopy(cert)
        bad["flow"][0][1] += 1
        with self.assertRaises(Rejected):
            verify(model, bad)

    def test_reachable_false_vacuity_rejected(self):
        model = self.by_case["T000"]
        bad = {"schema":"vcm-certificate-1","case":"T000","status":"vacuous","k":1,"cost":0}
        with self.assertRaisesRegex(Rejected, "realizable path"):
            verify(model, bad)

    def test_unreachable_false_optimal_rejected(self):
        model = {
            "case": "Empty", "family": "Boundary", "nodes": 2, "edges": [],
            "monitors": [], "obligation": [0, 1, 0], "horizon": 0, "failures": 0,
        }
        candidate = {
            "schema": "vcm-certificate-1", "case": "Empty", "status": "optimal",
            "k": 1, "selected": [], "cost": 0,
            "potential": [0, 1, 0, 0, 1, 1, 1, 1, 1, 1],
            "flow_value": 0, "flow": [], "overflow": [], "dual_value": 0,
        }
        with self.assertRaisesRegex(Rejected, "no realizable path"):
            verify(model, candidate)

    def test_local_hook_rejected(self):
        model = deepcopy(self.by_case["T000"])
        model["monitors"][0][1] = "local"
        with self.assertRaises(ValueError):
            validate_model(model)


    def test_fixed_seed_differential_fuzz(self):
        counts = {"optimal": 0, "infeasible": 0, "vacuous": 0}
        for model in deterministic_fuzz_cases(count=64, seed=20260918):
            validate_model(model)
            producer_graph = compile_model(model)
            checker_graph = compile_for_checking(model)
            self.assertEqual(producer_graph["nodes"], checker_graph["nodes"])
            self.assertEqual(producer_graph["edges"], checker_graph["edges"])
            observations = physical_observations(model)
            self.assertEqual(observations, compiled_observations(producer_graph))
            oracle_status, _, oracle_cost = brute_force_optimum(model, observations)
            certificate, _ = solve(model)
            self.assertEqual(oracle_status, certificate["status"], model["case"])
            self.assertEqual(oracle_cost, certificate.get("cost"), model["case"])
            self.assertTrue(verify(model, certificate)["accepted"])
            counts[oracle_status] += 1
        self.assertTrue(all(value > 0 for value in counts.values()), counts)

    def test_bounded_exhaustive_three_vertex_universe(self):
        counts = {"optimal": 0, "infeasible": 0, "vacuous": 0}
        total = 0
        for model in bounded_exhaustive_cases():
            validate_model(model)
            producer_graph = compile_model(model)
            checker_graph = compile_for_checking(model)
            self.assertEqual(producer_graph["nodes"], checker_graph["nodes"])
            self.assertEqual(producer_graph["edges"], checker_graph["edges"])
            observations = physical_observations(model)
            self.assertEqual(observations, compiled_observations(producer_graph))
            status, _, _ = brute_force_optimum(model, observations)
            counts[status] += 1
            total += 1
        self.assertEqual(EXPECTED_CASES, total)
        self.assertEqual(
            {"optimal": 1640, "infeasible": 8500, "vacuous": 3580}, counts
        )

    def test_boolean_certificate_integer_rejected(self):
        model = self.by_case["T000"]
        cert, _ = solve(model)
        for field in ("k", "cost", "flow_value", "dual_value"):
            bad = deepcopy(cert)
            bad[field] = True
            with self.subTest(field=field), self.assertRaises(Rejected):
                verify(model, bad)

        vac_model = self.by_case["V000"]
        vac, _ = solve(vac_model)
        vac["cost"] = False
        with self.assertRaises(Rejected):
            verify(vac_model, vac)

        inf_model = self.by_case["I000"]
        inf, _ = solve(inf_model)
        inf["all_monitor_count"] = True
        with self.assertRaises(Rejected):
            verify(inf_model, inf)

    def test_negative_overflow_rejected(self):
        model = self.by_case["T001"]
        cert, _ = solve(model)
        bad = deepcopy(cert)
        if bad["overflow"]:
            bad["overflow"][0][1] = -1
        else:
            bad["overflow"] = [[0, -1]]
        with self.assertRaises(Rejected):
            verify(model, bad)

    def test_unknown_flow_edge_rejected(self):
        model = self.by_case["T000"]
        cert, _ = solve(model)
        bad = deepcopy(cert)
        bad["flow"] = [["not-an-edge", 1]]
        with self.assertRaises(Rejected):
            verify(model, bad)


    def test_oversized_sparse_lists_rejected(self):
        model = self.by_case["T000"]
        cert, _ = solve(model)
        bad = deepcopy(cert)
        bad["flow"] = [["x{:04d}".format(i), 1] for i in range(len(compile_model(model)["edges"]) + 1)]
        with self.assertRaises(Rejected):
            verify(model, bad)
        bad = deepcopy(cert)
        bad["overflow"] = [[i, 1] for i in range(len(model["monitors"]) + 1)]
        with self.assertRaises(Rejected):
            verify(model, bad)

        inf_model = self.by_case["I000"]
        inf, _ = solve(inf_model)
        inf["witness"] = inf["witness"] * (len(compile_model(inf_model)["edges"]) + 1)
        with self.assertRaises(Rejected):
            verify(inf_model, inf)


    def test_monitor_cost_admission_boundary(self):
        model = deepcopy(self.by_case["T000"])
        model["monitors"][0][2] = 10**6
        validate_model(model)
        model["monitors"][0][2] = 10**6 + 1
        with self.assertRaises(ValueError):
            validate_model(model)

    def test_certificate_integer_admission_boundary(self):
        model = {
            "case": "IntBound", "family": "Boundary", "nodes": 2,
            "edges": [[0, 1, 0, "keep"]],
            "monitors": [[0, "export", 1]],
            "obligation": [0, 1, 0], "horizon": 1, "failures": 0,
        }
        certificate, _ = solve(model)
        bound = 10**18
        certificate["flow_value"] = bound
        certificate["flow"] = [[edge_id, bound] for edge_id, _ in certificate["flow"]]
        certificate["overflow"] = [[0, bound - 1]]
        certificate["dual_value"] = 1
        self.assertTrue(verify(model, certificate)["accepted"])

        for field in ("flow_value", "dual_value"):
            bad = deepcopy(certificate)
            bad[field] = bound + 1
            with self.subTest(field=field), self.assertRaises(Rejected):
                verify(model, bad)
        bad = deepcopy(certificate)
        bad["flow"][0][1] = bound + 1
        with self.assertRaises(Rejected):
            verify(model, bad)
        bad = deepcopy(certificate)
        bad["overflow"][0][1] = bound + 1
        with self.assertRaises(Rejected):
            verify(model, bad)

    def test_certificate_is_revalidated_not_snapshot_bound(self):
        model = deepcopy(self.by_case["T000"])
        certificate, _ = solve(model)
        current_input = deepcopy(model)
        current_input["horizon"] = 16
        self.assertNotEqual(model, current_input)
        self.assertTrue(verify(current_input, certificate)["accepted"])

    def test_checker_command_without_site_packages(self):
        completed = subprocess.run(
            [sys.executable, "-S", str(ROOT / "run.py"), "check",
             "--model", str(ROOT / "inputs" / "example-model.json"),
             "--certificate", str(ROOT / "inputs" / "example-certificate.json")],
            cwd=ROOT, text=True, capture_output=True, check=False, timeout=30,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertTrue(json.loads(completed.stdout)["accepted"])

    def test_retained_certificates_when_present(self):
        cert_dir = ROOT / "results" / "campaign" / "certificates"
        if not cert_dir.exists():
            self.skipTest("campaign not materialized yet")
        for model in self.cases:
            cert = json.loads((cert_dir / (model["case"] + ".json")).read_text())
            self.assertTrue(verify(model, cert)["accepted"])


if __name__ == "__main__":
    unittest.main()
