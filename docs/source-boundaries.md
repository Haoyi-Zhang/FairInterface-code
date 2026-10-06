# Literature calibration and source boundaries

## Review method

This file records a structured literature calibration for the internal manuscript.
It is not an independent systematic review and does not establish priority by
itself. On 2026-09-12, 2026-09-15, 2026-09-16, and 2026-09-20 for the closest-work and bibliography-audit passes, the calibration set was checked through accessible full-text versions or publisher-rendered full articles. For each paper, the pass
covered at least the abstract and introduction, the formal model or central
technical definitions, the main result and proof/evaluation architecture, the
conclusion or stated limitations, and the neighboring references relevant to
this project. This is a targeted full-text calibration, not a claim of a
line-by-line replication of every proof.

The manuscript bibliography contains 62 scholarly items. All 62 are cited in the
article; none is present only to raise the count. A separate per-key audit records
persistent identifiers, verification sources, dates, and each source's actual
manuscript role. The 22-paper matrix below is a
calibration subset of that bibliography: 12 articles in Information and
Computation, five influential foundations, and five adjacent distributed-systems
papers. The categories overlap intellectually but no paper is counted twice in
the 12+5+5 total.

## Twelve Information and Computation articles

| Paper | Problem and mechanism | Main evidence pattern | Transfer to this manuscript | Material difference |
|---|---|---|---|---|
| Vardi and Wolper, *Reasoning about Infinite Computations* (1994) | Automata-theoretic reasoning over infinite words and computations | Language-theoretic constructions and correctness proofs | Generalized-Buchi recurrence is a foundation for the closed-graph criterion | No exact-port component interface, late enabledness binding, or reconfiguration-specific boundary theorem |
| Burch et al., *Symbolic Model Checking: 10^20 States and Beyond* (1992) | Symbolic reachability and temporal verification | BDD-based global-state algorithms and case studies | Establishes that whole-graph temporal checking is mature baseline machinery | The contribution is not symbolic state-space compression and makes no scale claim |
| Costa and Stirling, *Weak and Strong Fairness in CCS* (1987) | Fairness semantics for communicating processes | Process-algebraic semantic distinctions and proof rules | Motivates keeping weak and strong fairness separate | Composition operator and observation model are substantially richer than additive exact-port wiring |
| Older, *Strong Fairness and Full Abstraction for Communicating Processes* (2000) | Full abstraction under strong fairness | Contextual semantic equivalence | Sharpens the warning that contextual power determines a sufficient abstraction | This manuscript proves neither strong-fair equivalence nor full abstraction; it gives a counterexample for its own weak interface |
| Segala, *Quiescence, Fairness, Testing, and the Notion of Implementation* (1997) | Relating receptive models and testing under quiescence/fairness | Semantic implementation relations | Supports the need to define deadlock, quiescence, and fairness before abstraction | No first-return union-capacity summary or finite-change suffix characterization |
| Rensink and Vogler, *Fair Testing* (2007) | Compositional testing that treats divergence under a fair interpretation | Testing preorder and congruence arguments | Demonstrates that fair observations can be compositional only for a declared context language | The testing operator and observations differ from sealed interiors joined by edge union |
| Henzinger, Kupferman, and Rajamani, *Fair Simulation* (2002) | Fair simulation for reducing fair-state systems | Game/simulation characterization and reduction results | Closest relational alternative to retaining complete open behavior | Retains a simulation relation rather than this finite first-return interface |
| Bustan and Grumberg, *Applicability of Fair Simulation* (2004) | When fair simulation is useful for verification | Algorithmic/semantic comparison of fair reductions | Provides an adversarial baseline against overclaiming a new fairness abstraction | Does not state the late-binding equality, field separations, or exact additive-port result |
| Kesten, Piterman, and Pnueli, *Bridging the Gap between Fair Simulation and Trace Inclusion* (2005) | Strengthening fair simulation toward trace inclusion | Refined relational constructions | Shows that missing trace correlations are a known source of imprecision | This interface deliberately forgets finite trace correlation and is exact only because recurrent visits may choose fresh excursions |
| Kupferman, Vardi, and Wolper, *Module Checking* (2001) | Verification of open systems against environments | Tree/module semantics and automata algorithms | Principal open-system baseline | Environments choose open transitions; they do not merely add edges at preserved exact states |
| Shoham and Grumberg, *Compositional Verification and 3-Valued Abstractions Join Forces* (2010) | Compositional abstraction with unknown truth values | Three-valued abstract interpretation and refinement | Illustrates a broader, reusable abstraction architecture | No task-based weak-fairness late binding or capacity lower bound |
| Lynch and Vaandrager, *Forward and Backward Simulations---Part I: Untimed Systems* (1995) | Transfer of behavior between transition systems by simulation relations | Relational preservation theorems and compositional reasoning | Supplies the broad simulation baseline for the paper's explicit abstraction-transfer obligation | The manuscript uses a narrower fairness-reflecting sufficient condition and does not claim a general simulation theory |

## Five influential foundations

These papers were selected as field-shaping technical foundations, not as an
award list. No award status is asserted.

| Paper | Role in the calibration | Boundary retained here |
|---|---|---|
| Alpern and Schneider, *Defining Liveness* (1985) | Canonical safety/liveness topological distinction | The paper studies one conditional liveness property, not a new general definition of liveness |
| Vardi and Wolper, *An Automata-Theoretic Approach to Automatic Program Verification* (1986) | Automata-theoretic temporal verification | Generalized-Buchi emptiness remains a baseline, not a claimed contribution |
| de Alfaro and Henzinger, *Interface Automata* (2001) | Explicit component/environment compatibility | This manuscript's context class is intentionally narrower and lacks action synchronization or optimistic compatibility |
| Fischer, Lynch, and Paterson, *Impossibility of Distributed Consensus with One Faulty Process* (1985) | Separates termination assumptions from safety in asynchronous distributed systems | The finite graph checker does not prove consensus or bypass impossibility assumptions |
| Castro and Liskov, *Practical Byzantine Fault Tolerance* (1999) | Concrete Byzantine replication and liveness motivation | Quorums, authentication, synchrony, and implementation refinement must be supplied separately |

## Five adjacent distributed-systems papers

| Paper | Reconfiguration/liveness mechanism | Comparison outcome |
|---|---|---|
| Lamport, Malkhi, and Zhou, *Vertical Paxos and Primary-Backup Replication* (2009) | External configuration master and quorum selection across configurations | Concrete configuration safety/progress mechanism; not an exact finite port-summary theorem |
| Lynch and Shvartsman, *RAMBO* (2002) | Reconfigurable atomic memory with explicit configuration management | Rich protocol and dynamic-network setting beyond the declared graph abstraction |
| Aguilera et al., *Dynamic Atomic Storage without Consensus* (2011) | Dynamic storage and reconfiguration without consensus | Establishes concrete state-transfer/quorum obligations absent from the abstract checker |
| Spiegelman and Keidar, *On Liveness of Dynamic Storage* (2017) | Impossibility/possibility boundaries under ongoing reconfiguration | Already shows that infinite churn can obstruct progress; the vote-reset example is not presented as a new general impossibility theorem |
| Leung, Zeldovich, and Kaashoek, *Shipwright* (2025) | Modular liveness proofs for Byzantine participants, cryptographic signatures, and executable PBFT prototype | Broader proof framework and protocol connection; this project neither reuses its proof/code nor claims an implementation refinement |

## Closest-work adversarial addendum

A second pass targeted work most likely to subsume the claimed contribution,
rather than adding more general background.

| Work | Strongest overlapping result | Why it does not establish the paper's theorem | Consequence for wording |
|---|---|---|---|
| Wang et al., *Compositional SCC Analysis for Language Emptiness* (2006) | Successive SCC refinement over over-approximations, with monotonic weakening under composition and experimental LTL model-checking evidence | It incrementally refines whole-system fair-cycle candidates; it does not export an exact first-return component interface whose disabled-task colors and deadlock completion are bound after additive exact-port wiring | The paper treats SCC recurrence and compositional fair-cycle search as prior art and claims only the exact boundary/order-of-operations result |
| Lang and Mateescu, *Partial Model Checking Using Networks of Labelled Transition Systems and Boolean Equation Systems* (2013) | Compositional quotienting of temporal formulas through networks that support broad synchronization operators, with formula-graph reductions and CADP experiments | The retained object is a quotient formula/Boolean-equation representation, not the five-field graph interface; its operator language is broader and its result does not state the late-enabledness equality, field separations, or capacity lower bound | The manuscript explicitly describes partial model checking as a more general compositional route rather than implying that compositional verification itself is new |
| Mennicke and Prehn, *Keep It Fair: Equivalence and Composition* (2019) | Analysis of how fairness-sensitive equivalences interact with composition and which operators preserve fair behavior | It studies equivalence spectra for process composition, not exact-state edge-union contexts or a first-return capacity summary; conversely, this manuscript does not prove a coarsest equivalence or full abstraction | The introduction and limits now say that fairness equivalences need not survive arbitrary composition and restrict every substitution claim to the declared operator |
| Correnson, Kuhn, and Finkbeiner, *Almost Fair Simulations* (2025) | Sound mechanized simulation rules for fair trace inclusion under Buchi fairness, with examples in Rocq | It retains a relational proof object for trace inclusion, while this work exports a coarser exact summary only for repeated weak-fair recurrence under sealed additive wiring | The source is cited as a stronger relational alternative; its bibliographic record was corrected to PACMPL 9 (ICFP), 222--245, DOI 10.1145/3747512 |
| Correnson, Kuhn, and Finkbeiner, *Completing Almost Fair Simulations* (2026) | A sound and complete deductive system for fair similarity between B\"uchi automata, with soundness and completeness mechanized in Rocq | It proves relational language-inclusion rules and keeps pairwise simulation structure; it does not derive the exact five-field additive-port quotient or late enabledness/deadlock closure | The manuscript treats this newest result as a stronger mechanized relational alternative and confines its own novelty to the restricted boundary equality and information result |
| Zhao et al., *Compositional Verification of Composite Byzantine Protocols* (Bythos, 2024) | Mechanized safety and liveness reasoning for sequential and horizontal compositions of Byzantine protocols | It proves protocol-level composition results with richer assumptions and proof infrastructure, not an exact five-field summary for additive exact-state wiring | The manuscript treats Bythos as a stronger protocol connection and narrows its own claim to the finite-graph boundary theorem |
| Qiu et al., *LiDO: Linearizable Byzantine Distributed Objects with Refinement-Based Liveness Proofs* (2024) | Refinement-based safety and liveness proofs for Byzantine distributed objects | It connects abstract objects to protocol implementations through refinement rather than exporting the present first-return interface | The manuscript explicitly says that a concrete use of its checker still needs an external refinement of the LiDO/Shipwright kind |
| Honoré et al., *Adore* (2022), and Schultz et al., *Formal Verification of a Distributed Dynamic Reconfiguration Protocol* (2022) | Certified or machine-checked protocol-level reconfiguration safety | These works address concrete reconfiguration algorithms and invariants; they do not state the weak-fair late-binding equality or two change-mode recurrence theorem | The paper separates its liveness certificate from protocol safety and quorum proof obligations |
| Froleyks et al., *Liveness Proofs for Hardware Model Checking* (2026) | A generic propositional certificate format and checking architecture for liveness model checking | Its symbolic hardware setting and certificate language differ from the finite first-return ranks and lassos here | The manuscript presents its certificates as finite-graph witnesses, not a new generic certifying model-checker architecture |
| Zhu et al., *A Fairness-Based Refinement Strategy to Transform Liveness Properties in Event-B Models* (2023) | Explicit proof obligations for carrying liveness and fairness through refinement | It addresses refinement of Event-B models rather than exact additive-port summaries; this project checks only a sufficient finite relation supplied by the user | The paper presents fairness-aware refinement as a broader obligation framework and does not treat transition simulation alone as sufficient |
| Bravo, Chockler, and Gotsman, *Liveness and Latency of Byzantine State-Machine Replication* (2022) | Separates synchronizer behavior, liveness, and latency in partially synchronous Byzantine replication | It studies protocol-level liveness and latency under timing/synchronizer assumptions, not the finite weak-fair interface theorem | The manuscript uses it to delimit the missing scheduler, timing, and protocol-refinement obligations rather than to claim deployment relevance |

These comparisons narrow the defensible novelty statement. The result is not a
new generalized-Buchi algorithm, a general compositional model checker, or a
new fairness-preserving equivalence. It is an exact commutation theorem and
certificate boundary for one deliberately restricted wiring operator, plus
separations and an information lower bound inside that restriction.

## Synthesis and closest-work delta

The calibration supports four conservative conclusions.

1. Generalized-Buchi recurrence, task fairness, fair simulation, open-system
   verification, assume-guarantee reasoning, certificates, and concrete
   reconfiguration mechanisms are established foundations. The manuscript does
   not claim those ingredients as new.
2. The retained technical delta is the order-of-operations result for one
   declared context class: export first-return reachability/capacity, hidden
   divergence, raw port enabledness, and outgoing-edge existence; union module
   interfaces; then bind weak-fairness colors and deadlock completion. The paper
   proves equality with closing the union first for both unrestricted and
   finite-change interpretations.
3. The field-separation theorem and the fixed-entry capacity family delimit the
   representation claim. They show that deleting a displayed field loses
   exactness and that capacity information has a worst-case quadratic order.
   They do not prove a unique encoding, a coarsest precongruence, or full
   abstraction for a larger language.
4. No calibrated paper located in this pass states the same combination of
   exact additive-port late binding, arbitrary/finite-change recurrence,
   per-field contextual separations, complete two-sided certificates, and the
   fixed-entry capacity lower bound. This is a literature-search delta, not a
   formal proof of priority. A human domain expert should still challenge the
   novelty and significance before external use.

## Source and reuse limits

Only bibliographic facts and technical ideas needed for comparison are reused by
citation and paraphrase. No external paper text, figure, code, benchmark, or PDF
bytes are redistributed. The artifact's executable evidence is locally generated
from declared finite models. Citation does not imply collaboration, author
approval, theorem endorsement, or inheritance of any proof. The full source
inventory and stable scholarly links are in `external_resources.csv`.
