# Repair localization and validation

| Requested issue | Implemented location | Executable or document validation |
|---|---|---|
| Unreachable object accepted as `optimal` | `src/checker.py`, optimal branch | Exact supplied object in `results/three-status-regression/`; pre-repair acceptance and post-repair rejection recorded; `test_unreachable_false_optimal_rejected`; `unreachable-false-optimal` control |
| Reachable object forged as `vacuous` | `src/checker.py`, vacuous branch; `src/controls.py` | `test_reachable_false_vacuity_rejected`; `reachable-false-vacuity` control |
| Trichotomy finite-reachability condition | `paper/main.tex`, Theorem 2; `docs/proofs.md` | Main theorem states `k <= lambda < +infinity`; end-to-end soundness separately checks reachability in the optimal branch |
| Star reduction outside the retained directed source language | `paper/main.tex`, Proposition 4; `paper/supplement.tex`; `docs/model.md`; `docs/proofs.md` | Wider undirected explicit-path model is defined; triangle orientation and bidirected two-cycle obstruction are stated; abstract/introduction/conclusion are narrowed |
| Checker scan complexity | `src/checker_compile.py`, `src/dag.py`, `src/model.py`, selected-list check in `src/checker.py` | Deque scans; no `pop(0)`, queue sorting, or adjacency sorting in checker admission/reconstruction paths; manuscript limits the linear claim to graph-plus-certificate scans in exact-integer operations |
| Snapshot-binding overclaim | `paper/main.tex`; `paper/supplement.tex`; `README.md`; `docs/model.md`; `docs/reproduction.md` | `test_certificate_is_revalidated_not_snapshot_bound` shows a valid old object can remain accepted after a nonbinding horizon change; no content digest is claimed |
| Reproducible environment and comparison semantics | `requirements-producer.txt`; `docs/environment.md`; `run.py`; `audit.py`; paper/supplement replay text | Both `--mode strict` and `--mode semantic` completed successfully; `lp_objective` and `rounding_alpha` participate only in strict comparison; historical dependency versions are explicitly unknown |
| Executable integer limits | `src/model.py`; `src/checker.py`; exact model/certificate schema text | `test_monitor_cost_admission_boundary` and `test_certificate_integer_admission_boundary` admit `10^6` / `10^18` endpoints and reject first-over values |
| Figure spacing and arrow routing | `paper/figures/compiler.tex`; `paper/figures/certificate.tex` | Final manuscript compiled and inspected at 300 dpi: `m_2` is separated from panel `(a)`; certificate labels are separated and arrows terminate at formula-box borders without crossing the formulas |
| Wrong repeated-label proposition number | `paper/main.tex`, `\label{prop:repeated}` and `Proposition~\ref{prop:repeated}` | Extracted final page 7 reads `Proposition 3`; LaTeX reports no undefined references |

Current replay totals are 24 passing contract tests, 21 rejected controls, 120 accepted retained certificates, 13,720 exhaustive finite-universe rows, and 200 fixed-seed differential rows. The retained 120 certificate objects and all quantitative plot data are unchanged by this repair.
