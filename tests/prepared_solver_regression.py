"""Producer conformance; requires the existing pinned producer dependencies.

SPDX-License-Identifier: MIT. Explicit separate CI step, no skipped solver tests.
Independent tiny physical enumerator and subset oracle, no historical code.
"""
from copy import deepcopy
from itertools import product
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import dag
import solver
from checker import verify
from controls import run_controls
from instances import all_cases
from io_utils import load_json
from producer_compile import compile_model


def fixtures():
    rows = [([], [], [0,1,0], 0),
            ([[0,1,0,"keep"]], [], [0,1,0], 0),
            ([[0,1,0,"keep"]], [[0,"export",3],[1,"export",5]], [0,1,0], 1),
            ([[0,1,0,"keep"]], [[0,"export",2],[0,"export",2]], [0,1,0], 0),
            ([[0,1,1,"keep"]], [[1,"export",1]], [0,1,1], 0),
            ([[0,1,0,"either"]], [[0,"export",4],[1,"export",1]], [0,1,0], 0),
            ([[0,1,0,"restrict"]], [[1,"export",1]], [0,1,0], 0),
            ([[0,1,0,"keep"]], [[0,"export",1]], [0,1,0], 1)]
    return [dict(case=f"Local{i}", family="Local", nodes=2, edges=e, monitors=m,
                 obligation=o, failures=f, horizon=1 if e else 0) for i,(e,m,o,f) in enumerate(rows)]


def literal_optimum(model):
    observations = []
    def walk(v, bit, seen):
        seen = seen | {i for i,m in enumerate(model["monitors"]) if m[0] == v and bit == 0}
        if v == model["obligation"][1]:
            observations.append(seen)
            return
        for u,w,b,a in model["edges"]:
            if u != v or (bit == 1 and b == 1):
                continue
            flags = {bit} if a == "keep" else {1} if a == "restrict" else {bit,1}
            for nxt in sorted(flags):
                walk(w,nxt,seen)
    walk(model["obligation"][0], model["obligation"][2], set())
    if not observations:
        return "vacuous", 0
    costs = []
    for bits in product((0,1), repeat=len(model["monitors"])):
        selected = {i for i,b in enumerate(bits) if b}
        if all(len(selected & seen) >= model["failures"]+1 for seen in observations):
            costs.append(sum(model["monitors"][i][2] for i in selected))
    return ("optimal", min(costs)) if costs else ("infeasible", None)


class PreparedSolverRegression(unittest.TestCase):
    def test_literal_finite_optima_and_invocation_order_counts(self):
        for model in fixtures():
            with patch.object(solver, "topological", wraps=dag.topological) as preparation, \
                 patch.object(dag, "topological", side_effect=AssertionError("repeated preparation")):
                certificate, _ = solver.solve(model)
            expected = literal_optimum(model)
            self.assertEqual(expected, (certificate["status"], certificate.get("cost")))
            self.assertEqual(0 if expected[0] == "vacuous" else 1, preparation.call_count)
            self.assertTrue(verify(model, certificate)["accepted"])

    def test_prepared_and_default_rounding_and_coverage_on_pilot(self):
        local = fixtures()[3]
        graph = compile_model(local)
        order = tuple(dag.topological(graph))
        for x in ([0.25,0.75],[0.75,0.25],[1.0,1.0]):
            args = (graph,local,x,1)
            self.assertEqual(solver._round_fractional(*args), solver._round_fractional(*args,order))
        names = {"T000","T001","L012","L037","F007","I000","V000"}
        for model in [m for m in all_cases() if m["case"] in names]:
            certificate, _ = solver.solve(model)
            self.assertTrue(verify(model, certificate)["accepted"])
            if certificate["status"] != "optimal":
                continue
            graph = compile_model(model)
            x, _ = solver._fractional_lp(graph, model, model["failures"]+1)
            order = tuple(dag.topological(graph))
            args = (graph,model,x,model["failures"]+1)
            self.assertEqual(solver._round_fractional(*args), solver._round_fractional(*args,order))
            args = (graph,set(certificate["selected"]),model["failures"]+1)
            self.assertEqual(solver._coverage_potential(*args), solver._coverage_potential(*args,order))

    def test_retained_controls_and_input_admission_remain_exact(self):
        models = all_cases()
        certificates = {m["case"]:load_json(ROOT/"results/campaign/certificates"/(m["case"]+".json"))
                        for m in models}
        self.assertEqual(21, len(run_controls(models, certificates)))
        for field,value,message in [("nodes",501,"nodes"), ("horizon",17,"horizon"),
                                    ("failures",True,"failure"), ("obligation",[0,0,0],"differ")]:
            model = deepcopy(fixtures()[2])
            model[field] = value
            with self.assertRaisesRegex(ValueError, message):
                solver.solve(model)


if __name__ == "__main__":
    unittest.main()
