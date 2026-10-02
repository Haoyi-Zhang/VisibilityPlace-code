"""Complete bounded universe of three-vertex export-policy models.

The universe is intentionally small and fully specified rather than random:

* physical vertices are 0, 1, 2 with source 0 and target 2;
* each forward pair (0,1), (0,2), (1,2) is absent or carries one of the
  six boundary/action combinations;
* each vertex either has no monitor or one positive-cost export monitor;
* the initial restriction bit is 0 or 1; and
* the failure budget ranges from 0 through the number of monitors.

There are 7^3 * 2 * sum_{M subseteq {0,1,2}} (|M|+1) = 13,720 models.
"""
from __future__ import annotations

from itertools import product

EDGE_SLOTS = ((0, 1), (0, 2), (1, 2))
EDGE_OPTIONS = (None,) + tuple(
    (boundary, action)
    for boundary in (0, 1)
    for action in ("keep", "restrict", "either")
)
EXPECTED_CASES = 7 ** len(EDGE_SLOTS) * 2 * sum(
    bin(mask).count("1") + 1 for mask in range(1 << 3)
)


def bounded_exhaustive_cases():
    """Yield every model in the declared three-vertex universe once."""
    ordinal = 0
    for edge_options in product(EDGE_OPTIONS, repeat=len(EDGE_SLOTS)):
        edges = []
        for (u, v), option in zip(EDGE_SLOTS, edge_options):
            if option is not None:
                boundary, action = option
                edges.append([u, v, boundary, action])
        for monitor_mask in range(1 << 3):
            # Distinct positive costs exercise weighted tie-breaking while the
            # mask still gives a canonical one-monitor-per-vertex universe.
            monitors = [[vertex, "export", vertex + 1]
                        for vertex in range(3) if monitor_mask & (1 << vertex)]
            for initial in (0, 1):
                for failures in range(len(monitors) + 1):
                    yield {
                        "case": f"E{ordinal:05d}",
                        "family": "Exhaustive",
                        "nodes": 3,
                        "edges": edges,
                        "monitors": monitors,
                        "obligation": [0, 2, initial],
                        "horizon": 2,
                        "failures": failures,
                    }
                    ordinal += 1
    if ordinal != EXPECTED_CASES:
        raise AssertionError(f"exhaustive universe count {ordinal} != {EXPECTED_CASES}")
