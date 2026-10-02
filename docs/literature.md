# Literature and venue-calibration record

This record separates theorem dependence, routing motivation, and writing calibration. It is not a systematic review. Access labels state what was actually checked: **full technical pass** means the complete accessible article was read for problem, model, mechanism, evidence, and limits; **targeted technical pass** means the relevant technical sections, evaluation structure, and assumptions were checked; **publisher/structure pass** means the official record, abstract, section/evidence organization, and bibliographic data were checked but the article is not used to support a theorem.

## Technical dependence and closest-work delta

| Work | Access level | What it establishes | Delta retained here |
|---|---|---|---|
| Birge-Lee, Apostolaki, and Rexford, *Global BGP Attacks that Evade Route Monitoring* (PAM 2025; arXiv 2024) | full technical pass | Export behavior can prevent a globally relevant route from reaching a monitored feed; results and mitigations are conditional on interfaces and vantage points. | Motivation only. No attack is reproduced. The project gives certificates for an owned finite defensive abstraction. |
| Dean, Griffis, Parekh, and Whitley, *Approximation Algorithms for k-Hurdle Problems* (Algorithmica 2011) | full technical pass | The two-terminal state-unique hurdle problem has the LP, threshold-rounding, and flow structure used by the producer. | The optimizer is prior work. The retained result is the policy-state membership theorem, exact status interface, and independently checkable integer certificate. |
| Zhang and Fu, *The Label Cut Problem with Respect to Path Length and Label Frequency* (TCS 2016) | targeted technical pass | Minimum label source--sink cut is NP-hard with maximum path length two and, in a separate theorem, with maximum label frequency two; the bounds are not combined. | Marks repeated monitor identities as a substantive boundary. |
| McConnell et al., *Certifying Algorithms* (Computer Science Review 2011) | targeted technical pass | Separates answer production from efficiently checkable witnesses. | Guides the producer/checker trust split and rejection-oriented testing. |
| Necula, *Proof-Carrying Code*; Wetzler et al., *DRAT-trim*; exact LP certificate work | targeted technical pass | Independent evidence checking can reduce the trusted base without replacing the mathematical model. | The certificate here is application-specific: coverage potentials plus integer flow/overflow. |
| Header Space Analysis, VeriFlow, Batfish, Minesweeper, Plankton, and NetComplete | targeted technical pass | Network verification compiles finite semantics for checking or synthesis. | The present model is narrower and does not claim deployed configuration completeness. |

The closest collision is two-terminal k-hurdle optimization. The manuscript therefore does **not** claim a new hurdle algorithm, LP integrality theorem, threshold rule, or min-cost-flow dual. Its retained contribution is: (i) a linear policy-to-hurdle compiler preserving realization observations; (ii) a three-status certificate tied to the original model; (iii) a local exact-integer optimality witness; and (iv) an explicit repeated-label boundary plus a separately scoped undirected explicit-path boundary. The latter is not a hardness theorem for adding obligations to the retained directed DAG source language.

## Formulation screen

| Candidate formulation | Falsifier/resource issue | Decision |
|---|---|---|
| Explicit observation-set multicover | Binary-diamond family gives exponentially many distinct rows | Reject as main representation. |
| Parameterize a wider undirected explicit-path model only by host treewidth | Vertex cover reduces to supplied leaf--center--leaf paths on a star | Boundary for that wider interface only. |
| One observation, no loss | State-unique case reduces to ordinary cut | Baseline only. |
| Repeated monitor labels | Contains minimum label cut | Boundary. |
| Arbitrary joint obligations in the retained directed DAG language | The star construction cannot orient all triangle demands acyclically; bidirection creates two-cycles | Open/deferred; do not claim the wider reduction here. |
| Cyclic policy graph | Requires new convergence/repeated-visit semantics | Exclude. |
| Single obligation, acyclic graph, state-unique export monitors | Compiler bijection and certificate inequalities are falsifiable with exact small oracles | Retain. |
| Specification/exhaustive checker only | Correct but does not provide scalable certifying optimization | Superseded. |
| Probabilistic loss or Internet placement | Requires distributions, topology fidelity, and operational evidence unavailable here | Exclude. |

## TDSC narrative calibration: twelve concrete articles

Each row is a real TDSC research article with DOI/publisher metadata checked. The first five are also manuscript references because they directly inform the assurance or attack-graph framing. The remaining seven are writing/evidence calibration only and are not cited as support for the graph theorems.

| Article | Record and access | Pattern retained |
|---|---|---|
| Avizienis et al., *Basic Concepts and Taxonomy of Dependable and Secure Computing* (2004) | DOI `10.1109/TDSC.2004.2`; full technical pass | Define service, fault, failure, and claim boundary before mechanisms. |
| Blanchet, *A Computationally Sound Mechanized Prover for Security Protocols* (2008) | DOI `10.1109/TDSC.2007.1005`; targeted technical pass | Put abstraction and soundness scope before tool evidence. |
| K. Xu et al., *Data-Provenance Verification for Secure Hosts* (2012) | DOI `10.1109/TDSC.2011.50`; targeted technical pass | Separate evidence production, verifier, and trusted base. |
| Poolsappasit et al., *Dynamic Security Risk Management Using Bayesian Attack Graphs* (2012) | DOI `10.1109/TDSC.2011.34`; targeted technical pass | Make the model-to-decision pipeline and assumptions explicit. |
| Wang et al., *k-Zero Day Safety: A Network Security Metric for Measuring the Risk of Unknown Vulnerabilities* (2014) | DOI `10.1109/TDSC.2013.24`; targeted technical pass | Explain security meaning before formal metric and evaluation. |
| D. Xu et al., *Automated Security Test Generation with Formal Threat Models* (2012) | DOI `10.1109/TDSC.2012.24`; accessible full-text targeted pass | Tie formal threat models to executable validation and state what the generated tests do not prove. |
| Muñoz-González et al., *Exact Inference Techniques for the Analysis of Bayesian Attack Graphs* (2019) | DOI `10.1109/TDSC.2016.2627033`; full preprint targeted pass | Separate exact inference from graph fidelity and report scaling on synthetic structures. |
| Chawla et al., *VMGuard: State-Based Proactive Verification of Virtual Network Isolation With Application to NFV* (2021) | DOI `10.1109/TDSC.2020.3041430`; author/publisher full-text targeted pass | Connect a finite state model, verifier, scalability evidence, and isolation-policy scope. |
| Majumdar et al., *ProSAS: Proactive Security Auditing System for Clouds* (2022) | DOI `10.1109/TDSC.2021.3062204`; author full-text targeted pass | Keep policy audit, prevention mechanism, prototype, and cloud assumptions distinct. |
| Lakshmanan et al., *Caught-in-Translation: Detecting Cross-Level Inconsistency Attacks in NFV* (2024) | DOI `10.1109/TDSC.2023.3320811`; author-copy full-text targeted pass | State cross-layer observation boundary and distinguish detection evidence from prevention guarantees. |
| Rao et al., *Sliver: A Scalable Slicing-Based Verification for Information Flow Security* (2025) | DOI `10.1109/TDSC.2024.3403653`; publisher full-text targeted pass | Present reduction/slicing principle, consistency tests, scalability, and soundness limits separately. |
| Oqaily et al., *Cross-Level Security Verification for Network Functions Virtualization (NFV)* (2025) | DOI `10.1109/TDSC.2024.3524128`; author-copy full-text targeted pass | Keep cross-level model, verification obligations, practical system, and evaluation population explicit. |

The calibration set contains twelve named, DOI-resolved TDSC articles rather than topic placeholders. Every row was checked against an accessible complete article at least at the targeted-technical level; the two theorem-critical non-TDSC works received full technical passes. Calibration papers are not used as substitutes for mathematical evidence.

## Influential assurance exemplars

| Work | Pattern retained |
|---|---|
| Necula, proof-carrying code | Small checker and explicit evidence object. |
| McConnell et al., certifying algorithms | Producer/checker separation and rejection paths. |
| Header Space Analysis | Compile network semantics into a finite representation. |
| Batfish | Make configuration-model assumptions and data boundary visible. |
| Minesweeper | Pair expressive policy reasoning with adversarial counterexamples and explicit limits. |

## Adjacent-venue papers

| Work | Venue | Pattern retained |
|---|---|---|
| Birge-Lee et al., route-monitoring evasion | PAM | Concrete visibility gap motivates a defensive abstraction without importing an attack workflow. |
| Beckett et al., general network configuration verification | SIGCOMM | Model, property, solver, and validation appear in causal order. |
| VeriFlow | NSDI | Local invariant checking is separated from topology/configuration completeness. |
| Plankton | NSDI | State construction, reductions, and scalability boundary are explicit. |
| SICO / Bamboozling CAs | CCS / USENIX Security | Consequences remain tied to demonstrated routing behavior. |

## Writing implications

The manuscript uses eight main sections. It proceeds from the missing assurance principle to model, compiler, certificate, boundary attacks, finite implementation evidence, related work/limits, and conclusion. Quantitative figures are generated from retained rows. The bibliography is relevance-first: 58 unique entries, all cited, each mapped to a canonical source record in `docs/reference-audit.csv`; no entry is included merely to reach a number.
