"""Fair-comparator regressions on owned benign inputs. SPDX-License-Identifier: MIT."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from checker import Rejected, verify
from fair_baselines import (METHODS, EnumerationLimit, certify, check_selection,
                            choice_optimum, classify, observation_sets, selection, structured_cases)
from instances import all_cases
from oracle import brute_force_optimum, physical_observations
from producer_compile import compile_model


class FairBaselineTests(unittest.TestCase):
    def test_all_retained_common_flow_certificates(self):
        # Use retained selected sets without calling any placement optimizer.
        import json
        for model in all_cases():
            original = json.loads((ROOT/"results/campaign/certificates"/(model["case"]+".json")).read_text())
            graph = compile_model(model)
            cert = classify(graph, model)
            if cert is None:
                cert = certify(graph, model, set(original["selected"]))
            self.assertTrue(verify(model, cert)["accepted"])
            self.assertEqual((original["status"], original.get("cost")), (cert["status"], cert.get("cost")))

    def test_exact_comparators_and_cover_feasibility(self):
        fixtures = [m for m in all_cases() if m["case"] in ("T000", "T001", "T002", "F000", "I000", "V000")]
        fixtures += structured_cases()[:2]
        for model in fixtures:
            graph = compile_model(model)
            observations = physical_observations(model)
            expected, _, cost = brute_force_optimum(model, observations)
            for method in METHODS:
                cert = classify(graph, model)
                if cert is None:
                    chosen, _ = selection(model, graph, method)
                    self.assertEqual("feasible", check_selection(model, chosen))
                    if method == "cover-greedy":
                        self.assertGreaterEqual(sum(model["monitors"][i][2] for i in chosen), cost)
                        continue
                    cert = certify(graph, model, chosen)
                self.assertEqual((expected, cost), (cert["status"], cert.get("cost")))
                verify(model, cert)

    def test_direct_dp_matches_realization_sets(self):
        for model in all_cases()[:36]:
            expected = sorted({sum(1 << i for i in obs) for obs in physical_observations(model)})
            actual, _ = observation_sets(model)
            self.assertEqual(expected, actual)

    def test_budget_exhaustion_is_not_infeasibility(self):
        model = structured_cases()[-1]
        with self.assertRaises(EnumerationLimit):
            observation_sets(model, cap=32)
        graph = compile_model(model)
        self.assertIsNone(classify(graph, model))
        selected, _ = selection(model, graph, "compact-milp")
        cert = certify(graph, model, selected)
        self.assertEqual(choice_optimum(model), cert["cost"])
        verify(model, cert)

    def test_nonoptimal_selection_cannot_borrow_optimum_witness(self):
        model = next(m for m in all_cases() if m["case"] == "F000")
        graph = compile_model(model)
        selected = set(range(1, len(model["monitors"])))
        self.assertEqual("feasible", check_selection(model, selected))
        with self.assertRaisesRegex(ValueError, "lower bound differ"):
            certify(graph, model, selected)

    def test_forged_or_changed_input_fails_original_checker(self):
        model = all_cases()[0]
        graph = compile_model(model)
        selected, _ = selection(model, graph, "compact-milp")
        cert = certify(graph, model, selected)
        bad = deepcopy(cert)
        bad["selected"] = []
        bad["cost"] = 0
        with self.assertRaises(Rejected):
            verify(model, bad)
        changed = deepcopy(model)
        for i in selected:
            changed["monitors"][i][2] += 1
        with self.assertRaises(Rejected):
            verify(changed, cert)


if __name__ == "__main__":
    unittest.main()
