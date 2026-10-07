"""Portable owned DAG regression with a literal path-enumerating reference.

SPDX-License-Identifier: MIT. No historical implementation or private paths.
Run separately from the retained 29-method Linux suite.
"""
from copy import deepcopy
from fractions import Fraction
from itertools import product
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import dag


def tiny_graph(n, arcs, source=0, target=None):
    edges = [dict(id=eid, u=u, v=v, kind=kind, monitor=mid)
             for eid, u, v, kind, mid in arcs]
    return dict(nodes=tuple(range(n)), edges=tuple(edges), source=source,
                target=n-1 if target is None else target,
                out=tuple(tuple(e for e in edges if e["u"] == u) for u in range(n)),
                **{"in": tuple(tuple(e for e in edges if e["v"] == v) for v in range(n))})


def literal_paths(graph, length):
    """Enumerate all tiny paths, then minimize length and reversed edge IDs.

    Reversed IDs implement the specified final-edge tie first, recursively.
    Does not call a DAG scan, topological routine or production compiler.
    """
    paths = [[] for _ in graph["nodes"]]
    def visit(u, distance, path):
        paths[u].append((distance, tuple(reversed([e["id"] for e in path])), path))
        for e in graph["edges"]:
            if e["u"] == u:
                visit(e["v"], distance + length(e), path + [e])
    visit(graph["source"], 0, [])
    winners = [min(row, key=lambda p:p[:2]) if row else None for row in paths]
    return ([p[0] if p is not None else 10**18 for p in winners],
            winners[graph["target"]][2] if winners[graph["target"]] else [])


class PreparedDAGRegression(unittest.TestCase):
    def test_all_four_vertex_forward_graphs_and_monitor_subsets(self):
        slots = [(0,1), (0,2), (0,3), (1,2), (1,3), (2,3)]
        for bits in product((0,1), repeat=6):
            arcs = [(f"e{5-i:05d}", u, v, "monitor" if i%2 else "ordinary", i//2 if i%2 else None)
                    for i,(u,v) in enumerate(slots) if bits[i]]
            graph = tiny_graph(4, list(reversed(arcs)))
            order = tuple(dag.topological(graph))
            for selected_bits in product((0,1), repeat=3):
                selected = {i for i,b in enumerate(selected_bits) if b}
                length = lambda e: int(e["kind"] == "monitor" and e["monitor"] in selected)
                expected = literal_paths(graph, length)
                self.assertEqual(expected, dag.selected_distance(graph, selected))
                self.assertEqual(expected, dag._selected_distance(graph, selected, order))

    def test_fractional_weights_tied_predecessors_and_isolated_nodes(self):
        graph = tiny_graph(6, [("z",0,1,"ordinary",None), ("y",0,2,"ordinary",None),
                               ("a",2,3,"ordinary",None), ("b",1,3,"ordinary",None),
                               ("x",3,4,"ordinary",None)], target=4)
        length = lambda e: Fraction(1,2) if e["u"] == 0 else Fraction(0)
        expected = literal_paths(graph, length)
        self.assertEqual(["y","a","x"], [e["id"] for e in expected[1]])
        self.assertEqual(expected, dag.shortest_path(graph, length))
        self.assertEqual(expected, dag._shortest_path(graph, length, tuple(dag.topological(graph))))

    def test_empty_unreachable_and_source_target_cases(self):
        for graph in [tiny_graph(1, []), tiny_graph(4, []), tiny_graph(4, [("a",0,1,"monitor",0)])]:
            expected = literal_paths(graph, lambda e: 0)
            self.assertEqual(expected, dag.shortest_path(graph, lambda e:0))

    def test_public_wrappers_revalidate_cycles_before_length_callback(self):
        graph = tiny_graph(2, [("a",0,1,"ordinary",None), ("b",1,0,"ordinary",None)])
        with patch.object(dag, "_shortest_path", side_effect=AssertionError("must not scan")):
            with self.assertRaisesRegex(ValueError, "expected a DAG"):
                dag.shortest_path(graph, lambda e:0)
            with self.assertRaisesRegex(ValueError, "expected a DAG"):
                dag.selected_distance(graph, set())

    def test_prepared_scan_has_no_order_calls_and_does_not_mutate_graph(self):
        graph = tiny_graph(3, [("a",0,1,"monitor",0), ("b",1,2,"monitor",1)])
        snapshot = deepcopy(graph)
        order = tuple(dag.topological(graph))
        with patch.object(dag, "topological", side_effect=AssertionError("unexpected preparation")):
            for selected in [set(), {0}, {1}, {0,1}]:
                self.assertEqual(literal_paths(graph, lambda e:int(e["monitor"] in selected)),
                                 dag._selected_distance(graph, selected, order))
        self.assertEqual(snapshot, graph)

    def test_no_cache_across_mutable_inputs(self):
        graph = tiny_graph(3, [("a",0,1,"monitor",0), ("b",1,2,"monitor",1)])
        selected = {0}
        self.assertEqual(1, dag.selected_distance(graph, selected)[0][2])
        selected.add(1)
        self.assertEqual(2, dag.selected_distance(graph, selected)[0][2])
        graph["edges"][0]["monitor"] = 2
        self.assertEqual(1, dag.selected_distance(graph, selected)[0][2])

    def test_finite_sentinel_boundary_unchanged(self):
        graph = tiny_graph(2, [("a",0,1,"ordinary",None)])
        self.assertEqual(([0,10**18], []), dag.shortest_path(graph, lambda e:10**18))


if __name__ == "__main__":
    unittest.main()
