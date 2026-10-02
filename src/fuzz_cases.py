"""Deterministic small-model generator for exhaustive differential checking.

These cases are not a performance benchmark.  They are intentionally small so
that a third, direct policy-semantics implementation and complete subset search
can independently check every generated certificate.
"""
from __future__ import annotations

from random import Random


def _model(case, nodes, edges, monitors, obligation, failures, family="Fuzz"):
    return {
        "case": case,
        "family": family,
        "nodes": nodes,
        "edges": sorted(edges),
        "monitors": monitors,
        "obligation": obligation,
        "horizon": nodes - 1,
        "failures": failures,
    }


def _targeted_cases():
    """Edge cases that random sampling should not be trusted to hit."""
    return [
        # Reachable with no components: infeasible already at k=1.
        _model("Q000", 2, [[0, 1, 0, "keep"]], [], [0, 1, 0], 0),
        # The first boundary blocks an initially restricted realization.
        _model("Q001", 3, [[0, 1, 1, "keep"], [1, 2, 0, "keep"]],
               [[1, "export", 2]], [0, 2, 1], 0),
        # Source and target monitors both count under first-arrival semantics.
        _model("Q002", 2, [[0, 1, 0, "keep"]],
               [[0, "export", 3], [1, "export", 5]], [0, 1, 0], 1),
        # Two independently priced components share one physical host.
        _model("Q003", 3, [[0, 1, 0, "keep"], [1, 2, 0, "keep"]],
               [[1, "export", 7], [1, "export", 2]], [0, 2, 0], 1),
        # Either creates two state realizations; restriction hides later hooks.
        _model("Q004", 4,
               [[0, 1, 0, "either"], [1, 2, 0, "keep"], [2, 3, 0, "keep"]],
               [[0, "export", 4], [2, "export", 1], [3, "export", 3]],
               [0, 3, 0], 0),
        # A target-outgoing edge must be ignored by first-arrival semantics.
        _model("Q005", 4,
               [[0, 1, 0, "keep"], [1, 2, 0, "keep"], [2, 3, 0, "keep"]],
               [[1, "export", 2], [3, "export", 1]], [0, 2, 0], 0),
        # One path is boundary-suppressed only after the restriction action.
        _model("Q006", 5,
               [[0, 1, 0, "restrict"], [1, 4, 1, "keep"],
                [0, 2, 0, "keep"], [2, 3, 0, "keep"], [3, 4, 0, "keep"]],
               [[1, "export", 1], [2, "export", 4], [4, "export", 2]],
               [0, 4, 0], 0),
        # Two available components are insufficient for two arbitrary losses plus one survivor.
        _model("Q007", 3, [[0, 1, 0, "keep"], [1, 2, 0, "keep"]],
               [[1, "export", 1], [0, "export", 2]], [0, 2, 1], 2),
    ]


def deterministic_fuzz_cases(count=192, seed=20260918):
    """Return targeted cases plus ``count`` fixed-seed random DAG models."""
    rng = Random(seed)
    cases = _targeted_cases()
    actions = ("keep", "restrict", "either")
    for index in range(count):
        n = rng.randint(2, 8)
        edges = []
        # Edges always point forward, so acyclicity and horizon are structural.
        for u in range(n - 1):
            for v in range(u + 1, n):
                if rng.random() < 0.28:
                    boundary = int(rng.random() < 0.28)
                    action = actions[rng.randrange(len(actions))]
                    edges.append([u, v, boundary, action])
        # Periodically force a backbone to guarantee reachable examples while
        # retaining independent random policy labels on the other cases.
        if index % 3 == 0:
            present = {(u, v) for u, v, _, _ in edges}
            for u in range(n - 1):
                if (u, u + 1) not in present:
                    edges.append([u, u + 1, 0, "keep"])
        if not edges:
            edges.append([0, n - 1, 1, "keep"])

        monitor_count = rng.randint(0, min(8, n + 2))
        monitors = []
        for _ in range(monitor_count):
            # Sampling with replacement deliberately exercises co-located
            # components, while each component identity remains unique.
            monitors.append([rng.randrange(n), "export", rng.randint(1, 11)])
        failures = rng.randint(0, min(3, monitor_count))
        initial = rng.randint(0, 1)
        cases.append(_model(
            "R{:03d}".format(index), n, edges, monitors,
            [0, n - 1, initial], failures,
        ))
    return cases
