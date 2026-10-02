# Three-status regression evidence

This directory records the exact unreachable `optimal` candidate supplied for the repair and the observed pre-repair and post-repair outcomes. The pre-repair output is a retained execution observation, not a result that the current code is expected to reproduce. The current code must reject the object, and `tests/test_contract.py::test_unreachable_false_optimal_rejected` plus the `unreachable-false-optimal` campaign control enforce that requirement.

The opposite direction is represented by the `reachable-false-vacuity` control and test. Together they exercise mutual exclusion between the vacuous and optimal branches.
