# Reproduction and repair record

## Resource guard and retained campaign

The campaign uses one Python process and one worker under a 3 GiB address-space limit and a 2700-second CPU limit. It uses no GPU, model API, external compute, live network, device, private input, or attack traffic.

The deterministic suite contains 120 owned synthetic models: 36 Tiny, 48 Layered, 12 Fan, 12 Infeasible, and 12 Vacuous. Maximum declared dimensions are 500 physical vertices, 2,000 permitted physical edges (1,428 observed), 32 permitted monitor components (31 observed), and horizon 16 (14 observed). Retained outcomes are 96 optimal, 12 infeasible, and 12 vacuous. The maximum compiled graph has 2,033 vertices and 4,017 edges; the largest certificate is 16,711 bytes.

Direct physical semantics, independently compiled paths, and brute-force placement agree on 44 retained cases. All 120 retained certificates are accepted by the checker. All 21 retained malformed or out-of-class controls are rejected. The earlier Linux replay reports 24 passing contract tests. Five additional solver-free input/encoding tests bring the suite to 29; those five pass separately on Windows.

The historical retained campaign measured about 7.51 CPU seconds, 7.51 wall seconds, and 410,016 KiB peak process RSS. Its Python and dependency versions were not preserved and cannot be recovered from the evidence. These values are retained as descriptive observations; no version fingerprint is invented.

The supplied earlier Linux repair replay used the platform and dependencies recorded in `docs/environment.md`. The separate Windows standard-library run does not invoke the Linux launcher or producer. Its certificate, graph, oracle, and derived-data checks are not a fresh strict producer replay or replacements for historical resource observations.

## Complete bounded three-vertex universe

`exhaustive.py` enumerates every model in a declared finite universe rather than sampling it. Vertices are fixed as `0,1,2`, with source `0` and target `2`. Each of the three forward edge slots is absent or has one of six boundary/action combinations; each vertex has zero or one export monitor with fixed positive cost; the initial restriction bit takes both values; and the failure budget ranges from zero through the monitor count. The universe therefore has

```text
7^3 * 2 * sum_{M subseteq {0,1,2}} (|M|+1) = 13,720
```

models. Every model validates; producer and checker compilers agree edge-for-edge; direct physical observations equal compiled-path observations; and complete subset enumeration returns a status and optimum. The retained distribution is 1,640 optimal, 8,500 infeasible, and 3,580 vacuous. This is a complete check only for the stated three-vertex universe, not for all bounded inputs or the general theorem.

## Fixed-seed differential campaign

`fuzz.py` runs 192 generated small DAGs and eight targeted semantic edge cases under seed `20260918`. For every one of the 200 cases it requires:

1. edge-for-edge equality of producer and checker compiled graphs;
2. equality of direct physical realizations and compiled path observations;
3. equality of brute-force status/cost and producer output; and
4. acceptance of the emitted certificate by the independent checker.

The retained run has 25 optimal, 104 infeasible, and 71 vacuous cases and reaches 16 realizations in one model. Runtime fields are retained as observations but excluded from replay equality. This campaign is auxiliary implementation evidence, not a general proof or workload sample.

## Three-status regression and executable bounds

The supplied `Empty` model and `optimal` certificate were executed against the pre-repair checker and were accepted because the zero-flow/potential arithmetic did not independently require sink reachability. The repaired `optimal` branch first reconstructs the graph and rejects the same candidate with `declared optimal status has no realizable path`. The opposite forged status, a `vacuous` certificate on reachable case `T000`, is also rejected. Both directions are retained as controls and unit tests.

The parser admits monitor costs through `10^6` and rejects `10^6+1`. The certificate checker admits exact nonnegative integer fields through `10^18` (subject to tighter per-field bounds) and rejects `10^18+1`. Tests exercise the boundary and the first value outside it. These limits are implementation limits rather than assumptions of the mathematical theorem.

## Clean installation and commands

The recorded Linux replay environment and install commands are in `docs/environment.md`. In brief:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade 'pip==25.1.1'
python -m pip install -r requirements-producer.txt
```

`test.py`, `fuzz.py`, `pilot`, and `reproduce` call the producer and need NumPy/SciPy/NetworkX. `run.py check`, `compare`, and `audit.py` are standard-library-only once results exist.

Every output directory named below must be absent or empty:

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
python3 -S run.py check --model inputs/example-model.json \
                        --certificate inputs/example-certificate.json
```

## Strict and semantic comparison contracts

`--mode strict` compares all certificate objects, all 21 controls, the aggregate summary, and every non-runtime case field. `producer_ms` and `checker_ms` are excluded; `lp_objective`, `rounding_alpha`, selected-witness details, and certificate bytes participate. Strict audit compares all eight derived files. This is the fixed-environment object-replication contract.

`--mode semantic` revalidates every produced certificate and requires matching status and certified optimum. It also compares deterministic model dimensions, oracle flags, baselines, summary, and controls, while excluding floating producer diagnostics and witness identity. Semantic audit compares seven model/status/baseline-derived files and excludes the certificate-byte scaling file, because a distinct valid witness can have a different serialized size.

Thus a strict match establishes replication of the retained objects and diagnostic strings in the documented pinned environment; a semantic match establishes that newly produced objects have the retained statuses and optima and are valid under the current independent checker. Neither claim extends automatically to every future dependency release.

## Current-input validation rather than snapshot identity

Certificates carry the neutral `case` string but no model-content digest. Compiler identifiers follow input-array order. The checker always rebuilds and validates against the supplied current input; it does not claim that every model edit forces regeneration. A test increases a nonbinding horizon and confirms that the old object can remain valid. Reordering arrays may instead renumber identifiers and cause rejection. Only current-input acceptance establishes the reported result for that input.

## Repairs retained in the record

1. **Pilot subset.** The first seven-case pilot solved its scientific cases but its summary function referenced four control identifiers omitted from the subset. The repaired subset includes `T000`, `T001`, `I000`, `V000`, `L012`, `L037`, and `F007`.
2. **Deterministic derived data.** A legacy `scaling.csv` mixed deterministic graph/certificate fields with run-local timings. The analyzer now excludes timings from manuscript data.
3. **Checker dependency path.** Producer imports are lazy, and the checker command is tested under `python3 -S`.
4. **Strict integer and sparse bounds.** The checker requires exact integer types and rejects negative overflow, unknown identifiers, and overlong sparse/path lists.
5. **Label-cut citation.** The paper now states the path-length-two and frequency-two hardness restrictions separately.
6. **Three-status soundness.** The optimal branch now requires reconstructed reachability; both forged status directions are negative controls.
7. **Checker scan complexity.** Checker-side topological scans use deques without repeated `pop(0)`, queue sorting, or adjacency sorting; selected-list validation uses adjacent comparisons.
8. **Replay semantics.** Floating diagnostics now have an explicit strict/semantic contract rather than being ambiguously included or excluded.
9. **Snapshot wording and implementation bounds.** Documentation now matches the actual plain case identifier, input-order numbering, cost bound, and certificate-integer cap.

None of these repairs changes the 120 retained model statuses, optimum costs, certificate objects, baseline values, or plotted quantitative data.

Input decoding now rejects duplicate JSON object keys and non-JSON numeric constants. Policy actions and flow edge identifiers are type-checked before set/dictionary lookup, so malformed fields use the declared rejection interface rather than an uncaught `TypeError`. JSON and derived TeX writers explicitly select LF newlines: host newline conversion no longer changes certificate byte counts or deterministic derived files. The Windows run revalidates all retained certificates and controls, the 44 campaign oracles, all 13,720 universe models, and the 200 models' semantics/classifications. All five added tests pass, and regeneration from retained rows reproduces all eight derived files exactly. No fresh producer certificate was generated in that run.

## Interpretation

A successful strict replay in the recorded current environment reproduces the retained finite objects and floating diagnostics, excluding run-local milliseconds. A successful semantic replay regenerates valid proof objects with the retained statuses and optima. Neither is proof-assistant verification, independent peer review, evidence about deployed routing, or a guarantee against every software defect.
