# Theorem-to-artifact map

This map identifies the executable evidence associated with each mathematical
claim. It does not replace the proof in the article or
`proofs/core-argument.md`, and agreement among programs is not a
proof-assistant derivation. Paths are relative to the standalone artifact root.

## Semantic layer

| Article claim | Mathematical obligation | Primary implementation | Independent checks | Retained evidence |
|---|---|---|---|---|
| Lemma `lem:normalization` | Weak service fairness equals generalized-Buchi color recurrence; true deadlocks are observed before goal deletion | `src/model.py:parse` | `src/raw_oracle.py:raw_fair_bad_run` does not import the parser or construct justice colors | `results/raw.csv`, `results/named.csv`, `results/tests.stderr.txt` |
| Proposition `prop:nonmonotone` | Adding an edge may either create a fair bad run or make an old run unfair | `src/interfaces.py`, `src/producer.py` | `test_late_enabledness`, `test_late_deadlock_completion` | `results/tests.stderr.txt` |
| Proposition `prop:transfer` | Initial/goal, step, service, enabledness, deadlock-stutter, and marked-edge reflection transfer abstract liveness | `src/refinement.py:check_refinement` | Accepted scheduler expansion, five obligation mutations, deadlock-stutter regression, and tiny relation enumeration | `results/refinement.json`, `results/transfer.csv`, `results/tests.stderr.txt` |

## Closed summary layer

| Article claim | Mathematical obligation | Primary implementation | Independent checks | Retained evidence |
|---|---|---|---|---|
| Lemma `lem:recurrence` and Theorem `thm:boundary` | A fair pending run is either divergence whose first step leaves its source port for the interior and never returns to any port, or a reachable color-complete recurrent port component | `src/producer.py:summarize`, `produce` | `src/checker.py:reference_summary`, `src/summary_oracle.py:exact_summary`, interface-free `src/oracle.py:fair_bad_run`, and the `p -> q -> u -> u` locality regression | `results/summary.json`; targeted `results/tests.stderr.txt`; suite CSVs except that transfer verdict/nonlive counts are aggregate-only |
| Corollary `cor:finite` | Prefixes may use marked connectors; the recurrent suffix is ordinary | mode-specific filtering in `src/producer.py` and `src/checker.py` | whole-graph and raw-semantics oracles independently filter recurrent marked edges | `results/named.csv`, `results/raw.csv`, `results/transfer.csv` |
| Lemma `lem:elimination` | Snapshot vertex elimination preserves first-return existence and union capacity | `src/checker.py:reference_summary` | graph-search producer and mask-product summary oracle | 310,463 comparisons recorded in `results/summary.json` |

## Open-interface layer

| Article claim | Mathematical obligation | Primary implementation | Independent checks | Retained evidence |
|---|---|---|---|---|
| Definition `def:family` | Exact shared ports/goals, disjoint sealed interiors, additive edge union | `src/interfaces.py:validate_family`, `module_graph` | overlap rejection and unmentioned-state ownership tests | `results/tests.stderr.txt` |
| Raw join algebra | Componentwise union/OR is associative, commutative, and idempotent before closure | `src/interfaces.py:join_exports` | `test_raw_interface_join_algebra` checks permutations, grouping, and idempotence | `results/tests.stderr.txt` |
| Theorem `thm:binding` | `Summary(union modules) = close(join(exports))`, including exact union of local divergence under the first-step-interior definition | `src/interfaces.py:export`, `join_exports`, `close_join`, `bind` | elimination export, direct summary oracle, three exhaustive binding families, and the cross-port/direct-entry divergence controls in `test_interface_component_separations` | `results/modules.csv`, `results/binding.csv`, targeted `results/tests.stderr.txt` |
| Theorem `thm:fields` | Removing reachability/capacity, divergence, enabledness, or outgoing existence loses exactness | exported-field comparison and closed verdicts | same-context field-separation tests and 64 fixed-entry capacity contexts | `results/tests.stderr.txt` |

## Certificate and information layer

| Article claim | Mathematical obligation | Primary implementation | Independent checks | Retained evidence |
|---|---|---|---|---|
| Theorem `thm:certificates` | Positive blocks/ranks are sound and complete; negative concrete lassos witness nonliveness | `src/producer.py:produce`, `src/checker.py:verify` | certificate mutation tests plus whole-graph oracle verdicts | `results/cases/*.certificate.json`, `results/tests.stderr.txt` |
| Lemma `lem:witness-size` | A bounded lasso exists for every fair bad run | constructive proof; producer emits concrete lassos | checker validates every emitted prefix and cycle | `results/cases/*.certificate.json` |
| Theorem `thm:lower` and Corollary `cor:information` | Capacity bits need worst-case `Omega(k|P|^2)` information; the displayed dense encoding uses `O(k|P|^2)` | proof family in `proofs/core-argument.md` | 64 fixed-entry selecting contexts in `test_capacity_information_separation` | `results/tests.stderr.txt` |
| Proposition `prop:strong` | The weak interface is insufficient for task-based strong fairness | `src/oracle.py:strong_bad_run` | equal-export modules and distinguishing context | `results/tests.stderr.txt` |

## Validation inventory and trust boundary

A clean controller invocation in `reproduce.py` executes 22 unit tests and 19
bounded campaign chunks sequentially. A resumed invocation always reruns the
current tests, validates each reused suite's JSON, exact CSV header/content range,
stdout receipt, empty stderr, suite tag, frozen case count, source parameters, and
record-by-record generated JSONL inputs, and records reuse separately from commands
actually executed. Missing or damaged bundles are recomputed. Unit fixtures cover
zero/one/all completed inventories and four damage classes; retained targeted runs
cover all-reuse and actual single-suite recomputation. It fails on suite-count drift,
result-count drift, nonzero exits,
oracle disagreement, certificate rejection, or an incomplete execution/reuse
partition. The five decision
paths intentionally share the declared mathematical semantics but separate major
implementation choices:

1. graph-search production and concrete witness construction;
2. snapshot vertex-elimination checking;
3. direct first-return state/mask products;
4. an interface-free whole-graph state/mask product; and
5. a parser-independent raw weak-service oracle.

The trusted boundary still includes the finite input model, task naming, the
admissibility/refinement arguments supplied by a protocol user, Python's runtime,
and the hand proofs. The artifact does not certify a source-to-model extraction,
a quorum-safety argument, cryptography, or a scheduler assumption.
