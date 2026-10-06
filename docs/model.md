# Frozen model and certificate interface

## 1. Input object

A model is a JSON object with exactly these fields:

| Field | Meaning | Executable bound |
|---|---|---|
| `case`, `family` | neutral alphanumeric strings | 1--32 characters |
| `nodes` | physical vertices numbered `0..nodes-1` | 1--500 |
| `edges` | `[u,v,boundary,action]` | at most 2,000; no parallel ordered pair |
| `monitors` | `[vertex,"export",positive_cost]` | at most 32; cost in `[1,10^6]` |
| `obligation` | `[source,target,initial_restriction]` | distinct endpoints; bit in `{0,1}` |
| `horizon` | upper bound on physical DAG path length | 0--16 and not below the actual longest path |
| `failures` | arbitrary selected-component losses tolerated | 0--number of monitors |

The physical graph must be acyclic. JSON booleans are rejected in integer fields even though Python treats booleans as integer subclasses. Decoding rejects duplicate object keys at every depth and non-JSON numeric constants. Policy actions and flow edge identifiers must be strings before lookup. The certified class rejects local hooks, repeated physical edge pairs, cycles, and undeclared fields. These numerical limits are implementation/resource limits; the mathematical arguments are stated for finite instances satisfying the structural assumptions.

`case` is a plain identifier. It is compared between a model and certificate, but it is not a cryptographic or canonical digest of model contents.

## 2. Policy transition semantics

A route state is `(v,r)`, where `v` is a physical vertex and `r` is a persistent restriction bit.

* A boundary edge is disabled when `r=1`.
* `keep` preserves `r`.
* `restrict` sets `r=1`.
* `either` permits both `0` and `1` from an unrestricted state, and only `1` from a restricted state.
* An export monitor at vertex `v` observes exactly when the state is `(v,0)`.
* A realization stops at its first arrival at the declared target.

The one-bit transition system is an owned abstraction. It is not a complete implementation of BGP decision processes, communities, route selection, convergence, or inter-AS economics.

## 3. Robust visibility obligation

Let `M(P)` be the set of monitor components observed on realization `P`, and let `S` be the selected placement. For a component-failure budget `f`, the safety-only obligation is

```text
for every realization P and every F subset of S with |F| <= f:
    (S \ F) intersects M(P).
```

This is equivalent to `|S intersect M(P)| >= f+1` for every realization. The checker reports an empty realization family as `vacuous`; it never merges that state with an ordinary optimum.

## 4. Policy-to-hurdle compiler

For each physical state `(v,r)`, the compiler creates an entry and exit vertex. At `(v,0)`, all export components hosted at `v` are serialized as distinct monitor edges; at `(v,1)`, the state has only an ordinary bypass. Ordinary transition edges implement the policy relation. A super-source enters the initial state, and each target state exits to a super-sink. Transitions leaving the physical target are suppressed.

Each monitor component labels exactly one compiled edge. For `n` physical vertices, `a` physical edges, and `m` components, the compiled graph has

* exactly `4n + m + 2` vertices, and
* at most `2n + m + 3a + 3` edges.

A physical topological order induces a compiled topological order. There is a bijection between policy realizations and compiled source--sink paths, preserving the observed component set.

Compiled names and edge numbers follow the current model's vertex, monitor-array, and edge-array order. The compiler does not first sort the model into a content-canonical representation.

## 5. Three mutually exclusive certificate schemas

All certificates include `schema`, `case`, `status`, and `k=failures+1`. Extra fields are rejected. Every certificate integer must have exact JSON-integer type and lie in `[0,10^18]` unless a field has a tighter bound below. Sparse lists must be no longer than the reconstructed vertex, edge, or monitor universe; entries must use known identifiers and strictly increasing canonical sparse order.

### Vacuous

The certificate carries integer cost zero. The checker independently reconstructs the graph and requires the sink to be unreachable.

### Infeasible

The certificate gives a contiguous source--sink path and its exact monitor-edge count. Its length cannot exceed the reconstructed edge count. The checker requires the path to reach the sink and to contain fewer than `k` monitor edges. Since this count assumes every component is available, no placement can satisfy the hurdle.

### Optimal

Before checking arithmetic, the checker independently requires the reconstructed sink to be reachable. The certificate then contains:

* sorted unique selected component identifiers and their exact cost;
* an integer potential `h` in `[0,k]` on every compiled vertex, with `h(source)=0` and `h(target)=k`;
* nonnegative integer source--sink flow entries `y` and value `F`;
* nonnegative integer overflow entries `z_m` for monitor edges; and
* the equality `cost = kF - sum(z_m)`.

For every ordinary edge `(u,v)`, the checker requires `h(v)-h(u) <= 0`. For monitor edge `m`, it requires `h(v)-h(u) <= 1` when selected and `<=0` otherwise. Flow must conserve exactly. The dual capacity condition is `y_m-z_m <= c_m`. Unknown identifiers, negative overflow, duplicate entries, and overlong sparse vectors are rejected before objective equality is accepted.

The separate reachability check is necessary: on an unreachable graph the potential and zero-flow arithmetic can otherwise be vacuously consistent. The regression suite includes the exact `Empty` false-optimal object that previously exposed this gap, plus the opposite reachable false-vacuity declaration.

## 6. Current-input validation, not snapshot binding

The checker reconstructs the graph from the model supplied at verification time and checks the certificate against that reconstruction. The schema contains no content digest and makes no promise that every changed input forces regeneration. For example, increasing a nonbinding declared horizon can leave an old certificate valid. Conversely, reordering edge or monitor arrays can renumber compiled identifiers and invalidate an otherwise semantically equivalent object. Only acceptance against the current input establishes the reported status and optimum for that input.

## 7. Excluded and wider models

The exact theorem does not cover:

* one physical component represented by multiple compiled edges;
* multiple independent source--target obligations optimized jointly in the directed source language;
* cyclic route-state semantics or unbounded convergence;
* monitor-site common-cause failures;
* probabilistic availability, traffic volume, or detection latency;
* live routing data or completeness of a discovered topology.

Repeated component labels already contain general minimum label `s-t` cut at `k=1`; known hardness holds under separate short-path and low-frequency restrictions, not the unsupported simultaneous `(2,2)` restriction.

A separate boundary result uses a **wider undirected explicit-path obligation model**: an undirected host graph, a set of monitorable vertices with costs, and a supplied family of simple host paths, each of which must contain a selected monitorable vertex. In that model, arbitrary demands encode vertex cover on a star. This is not a hardness proof obtained by merely adding several obligations to the present directed acyclic source language. A one-way orientation of a star cannot realize all leaf-to-leaf demands of a triangle, while putting both directions on every spoke creates directed two-cycles.
