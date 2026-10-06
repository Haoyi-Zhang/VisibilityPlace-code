# visibility-complete-monitor

This standalone repository produces and checks proof-carrying minimum-cost monitor placements for one explicitly bounded class of owned synthetic export-policy graphs. It accompanies the manuscript *Proof-Carrying Visibility Placement for Acyclic Export Policies*; it is not a BGP implementation, a live-network study, or a deployment recommendation.

## Scope

An input is a finite directed acyclic physical graph with one source--target obligation, a persistent restriction bit, edge actions `keep`, `restrict`, or `either`, boundary edges disabled while restricted, and positive-cost `export` monitor components. A component observes a realization only at its unrestricted vertex state. Tolerating `failures = f` arbitrary selected-component losses is equivalent to requiring at least `k = f + 1` selected observations on every realization.

The policy semantics compiles to a state-unique two-terminal `k`-hurdle graph. Production returns exactly one status:

* `vacuous`: the independently rebuilt sink is unreachable;
* `infeasible`: a checked reachable source--sink path contains fewer than `k` monitor components even when all components are available; or
* `optimal`: the independently rebuilt sink is reachable, and the selected components, integer coverage potential, and integer flow/overflow lower bound prove feasibility and minimum cost.

The optimal checker explicitly tests reachability before accepting the arithmetic witness. This keeps the three statuses mutually exclusive: an unreachable graph cannot be accepted as `optimal`, and a reachable graph cannot be accepted as `vacuous`.

The checker reconstructs the compiled graph using separately written transition logic and validates exact integers. Its acceptance path uses only the Python standard library, does not import SciPy or NetworkX, and does not trust the producer's LP objective, rounding threshold, or circulation trace. JSON booleans are not accepted as integers; unknown identifiers, negative values, extra fields, noncanonical sparse ordering, and sparse objects longer than their reconstructed universes are rejected.

The artifact contains no AS numbers, prefixes, announcements, devices, private data, live services, attack routes, or evasion workflow. A certificate is conditional on the supplied finite input and does not establish model completeness for a deployed network.

## Executable admission bounds

The mathematical statements are for finite admitted instances. The implementation additionally enforces resource-oriented bounds, including at most 500 physical vertices, 2,000 physical edges, 32 monitor components, horizon 16, monitor cost in `[1, 10^6]`, and every certificate integer in `[0, 10^18]` unless a field has a tighter schema bound. These are checker/parser limits, not theorem limits. Boundary and one-step-over-bound cases are exercised by the contract tests.

`case` is only a neutral string checked for equality; it is not a model-content digest. Compiled node and edge identifiers follow the current input-array order. The checker therefore revalidates a certificate against the supplied current input rather than proving immutable snapshot identity. A previously emitted object may continue to pass after a semantically irrelevant input change, while reordering arrays can renumber identifiers and invalidate it.

## Environment and installation

The retained historical campaign did not preserve recoverable interpreter or dependency versions. Its proof objects and recorded measurements are retained, but no missing version fingerprint is invented.

The earlier Linux repair and replay recorded in `docs/environment.md` used:

* Linux 6.18.44 x86-64, glibc 2.41;
* CPython 3.13.5 and pip 25.1.1;
* NumPy 2.3.5;
* SciPy 1.17.0, whose bundled HiGHS reports 1.8.0; and
* NetworkX 3.6.1.

Create a clean environment with the same producer dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade 'pip==25.1.1'
python -m pip install -r requirements-producer.txt
```

`test.py`, `fuzz.py`, campaign production, and the exact-oracle tests require the producer dependencies because they call the solver. `run.py check`, certificate comparison, and `audit.py` are standard-library-only after their inputs exist. The final `python3 -S` command below demonstrates the checker-only path with site packages disabled.

The Linux campaign launcher uses one worker, a 3 GiB address-space cap, and a 2700-second CPU cap. It requires the Unix `resource` module. The standard-library checker can be called directly on other hosts, but the campaign launchers are not Windows-compatible.

## Clean reproduction

Run from the repository root; each named output directory must be absent or empty:

```bash
python3 test.py
python3 exhaustive.py --out replay-exhaustive
python3 fuzz.py --out replay-fuzz
python3 run.py pilot --out replay-pilot
python3 run.py reproduce --out replay
python3 run.py compare --observed replay --mode semantic
python3 run.py compare --observed replay --mode strict
python3 analyze.py --results replay --out replay-derived
python3 audit.py --campaign replay --derived replay-derived \
  --fuzz replay-fuzz --exhaustive replay-exhaustive --mode semantic
python3 audit.py --campaign replay --derived replay-derived \
  --fuzz replay-fuzz --exhaustive replay-exhaustive --mode strict
python3 -S run.py check \
  --model inputs/example-model.json \
  --certificate inputs/example-certificate.json
```

The two comparison modes make different truthful claims:

* `strict` is fixed-environment object replication. It compares every certificate object, every control row, and every non-runtime campaign field, including the floating producer diagnostics `lp_objective` and `rounding_alpha`. It excludes only producer/checker milliseconds. Strict audit compares all eight deterministic derived files.
* `semantic` revalidates every replayed certificate and compares model dimensions, status, certified optimum, exact-oracle flags, baselines, summaries, and controls. It intentionally excludes floating producer diagnostics, witness identity, and the certificate-byte scaling file, so a different but valid optimum witness is permitted.

Neither mode is a claim about all future dependency releases. A strict match is strongest in the documented pinned environment; a semantic match establishes status/optimum agreement and current-checker validity.

## Retained evidence

* 120-model deterministic campaign: 96 optimal, 12 infeasible, and 12 vacuous certificates.
* 44 campaign cases with direct-semantics / compiled-path / brute-force oracle agreement.
* 21 malformed or out-of-class controls, including both a reachable false-vacuity declaration and the exact unreachable false-optimal candidate, all rejected.
* The original 24 contract tests, including the complete three-vertex universe check, both status-direction regressions, executable integer/cost bounds, current-input revalidation, strict type and sparse-bound checks, and a checker-only `python3 -S` subprocess; five added solver-free input/encoding tests bring the suite to 29 tests.
* A complete 13,720-model three-vertex universe: all forward-edge absence/policy choices, one-or-zero monitors per vertex, both initial restriction states, and every legal failure budget; compiler, path semantics, and brute-force classification agree on every case.
* 200 fixed-seed differential small models: 192 generated and 8 targeted; compiler, path semantics, brute-force optimum/status, and certificate acceptance agree on every case.

These finite checks are implementation evidence. They are not a proof of the general theorem, a representative Internet sample, or a portable performance claim.

The separate Windows Python 3.12.14 checks accept the 120 retained certificates, reject the 21 controls, and recheck the 44 campaign oracles, 13,720-model universe, and 200 models' compilation/semantics/subset classifications. All five added tests pass. All eight derived files regenerated from retained rows are byte-identical after explicit LF writing. This run did not generate producer certificates or run the original Linux test launcher: SciPy, NetworkX, and `resource` were unavailable. Historical resource observations remain separate.

Input decoding rejects duplicate JSON fields at every object depth and non-JSON numeric constants. Generated JSON and TeX use explicit LF endings, preserving certificate-byte accounting and derived-data comparisons across host newline conventions.

`.github/workflows/scientific-checks.yml` prepares the full finite schedule for the flat standalone repository on Ubuntu 24.04 with Python 3.13.5 and pinned producer libraries. The scientific schedule has a 15-minute wall bound; raw logs and outputs are uploaded even on failure. Both semantic and strict gates remain enabled. This workflow has not been remotely executed by the local checks described above.

## Repository map

* `run.py`: pilot, full production, checking, strict/semantic comparison, and command routing.
* `exhaustive.py`, `src/exhaustive_cases.py`: complete declared three-vertex universe.
* `fuzz.py`, `src/fuzz_cases.py`: fixed-seed generated and targeted differential cases.
* `audit.py`: standard-library artifact/result/reference audit with strict and semantic modes.
* `test.py`, `tests/`: contract and exact-oracle tests.
* `src/model.py`: strict bounded model parser and DAG/horizon checks.
* `src/producer_compile.py`: producer-side policy compiler.
* `src/checker_compile.py`: separately written checker-side compiler.
* `src/solver.py`: attributed hurdle LP/threshold construction, integer dual extraction, and baselines.
* `src/checker.py`: exact certificate checker.
* `src/oracle.py`: direct physical-semantics path enumerator and brute-force placement oracle.
* `src/controls.py`: malformed-certificate and out-of-class controls.
* `inputs/suite.json`: all 120 retained models.
* `results/campaign/`: certificates, primary rows, 21 controls, summary, and historical resource observations.
* `results/exhaustive/`: retained 13,720-case bounded-complete rows and summary.
* `results/fuzz/`: retained 200-case differential rows and summary.
* `results/derived/`: deterministic manuscript tables and plot inputs.
* `results/pilot/`: repaired discriminating pilot.
* `docs/model.md`, `docs/proofs.md`, `docs/reproduction.md`, `docs/environment.md`: executable contract, proof record, replay contract, and platform record.
* `docs/repair-validation.md` and `results/three-status-regression/`: localized repair map plus the exact pre/post three-status regression evidence.
* `docs/reference-audit.csv`: canonical source record for each of the 58 cited works.
* `claim_evidence_ledger.csv`: claim-to-proof/check/result map.
* `external_resources.csv`: external scholarly, standards, dependency, and workflow records; no external executable or paper bytes are bundled.

## License

See `LICENSE`. Publisher template files and scholarly papers are not part of this standalone repository.
