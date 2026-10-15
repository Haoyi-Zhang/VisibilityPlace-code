# Same-information placement comparison

`fair_compare.py` compares formulations of the **same supplied model**, not
network-inference systems. Costs, monitor identities, the persistent policy
bit, first target arrival, and the universal loss allowance are unchanged.
The 120 retained JSON objects are imported without changing any model field.
`input-lineage.csv` identifies their source array positions; the ten additional
objects are retained verbatim in `structured-inputs.json`.

## Methods and guarantees

| Route | Primal computation | Evidence and acceptance |
| --- | --- | --- |
| `dense-lp` | Existing `solver._fractional_lp` and threshold rounding | Common exact potential/flow certificate; original `checker.verify` |
| `sparse-lp` | Same potential LP stored sparsely; existing threshold rounding | Same certificate producer and checker |
| `compact-milp` | Binary monitor variables, continuous bounded potentials, same sparse edge inequalities | Same certificate producer and checker; no hurdle rounding |
| `explicit-milp` | Direct policy-state observation-set DP, then binary weighted multicover | Same certificate producer and checker |
| `cover-greedy` | Same observation-set DP; repeatedly maximize remaining unit-demand coverage per cost | Independently reconstructed graph and exact selected-distance check; feasibility, **not optimality**, is reported |

The compact MILP minimizes `sum(cost[i]*x[i])`, with `x[i]` binary, source
potential zero, target potential `k`, potentials in `[0,k]`, and each edge
inequality `d[v]-d[u] <= x[i]` for a monitor edge or `<= 0` otherwise.
The explicit MILP has one inequality `sum(x[i] for i in O) >= k` for each
distinct observation set `O`. SciPy's
[`milp` interface](https://docs.scipy.org/doc/scipy-1.17.0/reference/generated/scipy.optimize.milp.html)
uses integer variables bounded to `[0,1]`, a zero relative gap, and a 30-second
solver limit. An unsuccessful solve raises an error; it is not relabeled as
infeasible. These are standard formulations implemented here, not claims to
reproduce a named operational monitor-placement algorithm. For `k=1`, the
coverage-per-cost rule is the weighted set-cover greedy rule; for larger `k`
the implementation decrements residual demands one unit at a time. No new
approximation guarantee is asserted.

All exact routes pay for the same local integer successive-shortest-path
flow/overflow producer. It uses integer capacities, reduced-cost Dijkstra,
and reverse residual edges; it is not disjoint-path greedy packing. A route
is successful only if its independently chosen primal cost equals this lower
bound and the original certificate checker accepts. The common witness stage
is **not** the historical NetworkX circulation timing. The default `solve`
continues to use NetworkX; its import is deferred to the circulation function
so that these primal-stage comparisons need not import it. Original retained
objects and historical results are unchanged.

## Workloads that discriminate representations

The retained suite includes shared mandatory gates and all three statuses.
The additional `Choice` products have `(width,depth)` equal to `(2,4)`,
`(2,8)`, `(2,14)`, `(3,6)`, and `(4,8)`, each at `k=1` and `k=3`, with fixed
nonuniform positive costs. All vertices in adjacent layers are connected by
`keep` edges. Each realization chooses one monitored vertex in each layer;
there are `width**depth` distinct observation sets. This varies incidence,
not the number of random repetitions. The executable horizon and monitor
bounds are respected, including 32 monitors in the largest product.

For these products, a path's minimum selected count is the number of fully
selected layers. Partial layers can always be avoided. Thus the independent
oracle sums the `k` cheapest complete layer costs. The replay command checks
that the actual supplied edges, monitor locations, obligation and horizon
have exactly this form before applying that oracle.

The explicit DP deduplicates masks at every physical state, not merely at
the target. In particular, exponential branching among unmonitored vertices
does not force exponential duplicate output. The main comparison bounds the
total stored partial `(vertex,bit,mask)` states at 32,768. Exceeding this
budget is recorded as `enumeration_limit`, **not** problem infeasibility.
An additional 262,144-state run on the ten products distinguishes this
representation budget from an inability of generic optimization to solve
the admitted problem.

## Cost boundary and acquisition

Each method runs sequentially in its own fresh process, with three repetitions
and reversed case order in the middle repetition. Per-case wall time includes:

1. Reading an individual JSON file and strict decoding.
2. Explicit model admission.
3. Compilation (including its own admission, counted rather than subtracted).
4. Exact status classification.
5. Primal construction and solving, including explicit-state DP where used.
6. Common certificate production for exact optimal results.
7. Original certificate checking, or explicitly feasibility-only checking.
8. Serializing the checked result to JSON.

Total time is measured directly, not obtained by summing medians. Input-file
metadata and instrumentation overhead remain in total time. The reported
process peak RSS is the method's entire batch high-water mark, including
imports, results retained in memory and serialization, not per-case auxiliary
space or an incremental-memory estimate. Library import and complete cold
batch times are reported separately. The first solve still includes any lazy
solver initialization. Offline direct subset oracles run in the parent, outside
both measured worker time and worker RSS. All 44 original oracle models are
rechecked, and all retained certified costs are revalidated for comparison.

The file adapter materializes already supplied model objects. It acquires no
new routing fact. The supplied artifact contains no router configuration,
BMP/MRT event corpus, relationship-labelled native topology or monitor cost
inventory from which the policy tuple could be inferred. A native adapter
would additionally need a documented mapping of configuration/interface facts
to the persistent bit and boundary/actions, component failure identities,
the initial bit, costs and a complete acyclic obligation graph. Those inputs
and validation against their native semantics are not present. Accordingly,
these measurements close the **model-JSON-to-checked-result** cost comparison;
they do not price collecting or validating deployment facts.

## Retained results and reproduction

The Windows 11 / Python 3.12.14 run uses NumPy 2.5.4 and SciPy 1.17.0.
It is separate from the historical Linux/NetworkX campaign. The main result
directory contains 1,950 rows: 130 models, five methods, three repetitions.
All three compact routes solve and certify every model. Explicit multicover
solves all 120 retained models and six product models at the 32,768-state budget;
the two largest product shapes, each at both tested `k` values (four models),
exceed that budget. All completed
exact routes have cost ratio 1. Coverage-per-cost greedy is feasible on every
completed model, costs more than optimum on 70 of its 102 reachable feasible
models, and has maximum observed ratio 1.875. Its status is not upgraded to
optimal even when its cost happens to match.

On the 48 retained Layered models (144 measurements per route), median total
times are 16.463 ms for dense LP, 12.016 ms for sparse LP, 9.682 ms for compact
MILP, and 8.035 ms for explicit MILP. Whole-batch peak process RSS is 275.49,
89.81, 89.69 and 86.50 MiB, respectively. These results do not establish a
speed or solution-quality advantage for hurdle LP over generic MILP. The
compact encoding supports either optimization route and the same exact
model-facing evidence interface.

At 262,144 states, explicit MILP completes all ten product models and again
returns the same checked optimum as both LP variants and compact MILP. The
largest `Choice4x8k3` input generates 65,536 distinct constraints with 524,288
nonzeros and stores 152,917 partial observation states, versus 343 compact
edge inequalities with 718 nonzeros. The high-budget run's whole-batch peak
RSS is 239.58 MiB for explicit MILP and 78.31 MiB for compact MILP. Thus the
lower-budget limits are representation-budget outcomes, not evidence that
generic optimization cannot solve the problem. Expanded-run greedy has
maximum ratio 19/7 (approximately 2.714), and all ten product solutions have
strict cost gaps; these unfavorable rows are retained as well.

From the standalone artifact root, in an environment containing NumPy and
SciPy (NetworkX is not required for these commands):

```bash
python3 -B tests/test_fair_baselines.py
python3 -B fair_compare.py --out replay-fair --work /private/replay-fair-work
python3 -B fair_compare.py --out replay-fair-expanded --work /private/replay-fair-expanded-work \
  --structured-only --cap 262144
python3 -B -S verify_fair.py --results results/fair-baselines
python3 -B -S verify_fair.py --results results/fair-baselines-expanded
```

Output/work directories must be absent or empty. `--work` holds intermediate
model files and captured diagnostic streams and should be outside published
artifacts. Scientific rows, actual checked outputs, summaries and resource
observations go to `--out`. A replay may change witness identity and timing;
the standalone replay checks the supplied current model, exact status/cost,
the feasible selections, the analytic product optimum and all recorded rows.
