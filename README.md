# Late-Bound Fairness Interfaces for Finite-State Reconfiguration

This directory is a standalone, standard-library-only artifact for the paper. It
checks task-based weakly fair termination in declared finite transition systems,
constructs open and closed boundary summaries, emits positive or negative
certificates, and validates the implementation through structurally different
summary, whole-graph, raw-semantics, and transfer checks.

The artifact is not a Byzantine protocol implementation, deployment benchmark,
proof-assistant development, or source-code model extractor. Its guarantees apply
only to the supplied finite JSON semantics: fixed task identities, exact ports,
sealed interiors, additive port wiring, and weak fairness. A synthetic refinement
fixture and a tiny-model family exercise the paper's sufficient transfer rule;
neither is a refinement of a real protocol.

## Supported execution environment

The reproduction entry point uses POSIX process groups and Python's `resource`
module to enforce child timeouts and report process resource use. The verified
path for the current targeted validation was:

- Linux on x86-64;
- CPython 3.13.5;
- the Python standard library only;
- one scientific child process at a time.

Native Windows does not provide the required `resource` and process-group APIs,
so `reproduce.py` exits with a clear unsupported-platform message rather than
failing during import; the unit suite simulates the missing-resource path. A
Linux environment is the documented runnable path.
macOS has an explicit `ru_maxrss` bytes-to-KiB conversion in the controller but
was not tested here; WSL was also not tested.

Every new `summary.json` records the operating system, machine, Python
implementation/version, interpreter basename, process-group mechanism, the
native `ru_maxrss` unit, and the reported RSS unit. Reported peak RSS is normalized
to KiB. The retained historical clean campaign predates this environment capture:
its OS and interpreter are therefore recorded as unknown rather than reconstructed.
Its already reported RSS figures remain labeled as KiB because that is how the
historical record stored them.

## One-command reproduction

From this directory:

```bash
python3 reproduce.py --output reproduced
```

A clean run requires a new output directory and executes 22 unit-test methods plus
19 bounded campaign chunks sequentially. It writes retained inputs, CSV/JSON
results, certificates, per-command logs, and `summary.json`. Before accepting the
run, the controller checks the exact suite inventory, deterministic totals,
command exits, and the 22-test receipt. Expected deterministic totals are:

- 244,828 producer/checker verdict cases;
- 310,463 direct summary-oracle comparisons;
- 65,635 exhaustive two-module binding cases within that summary total;
- 244,824 complete whole-graph product-oracle comparisons and four declared
  budget exclusions;
- 2,500 parser-independent raw-semantics comparisons;
- 22,186 tiny concrete/abstract relation candidates, of which 1,358 satisfy the
  transfer checker and induce 2,116 checked liveness implications;
- one accepted 29-state-to-15-state refinement-condition instance, five rejected
  obligation mutations, and one rejected deadlock-totalization regression;
- 210,088 nonlive verdicts, a fixture count rather than a population estimate;
- zero summary, verdict, certificate, transfer, normalization, or oracle
  mismatches.

The transfer suite's 2,038 model-verdict and 1,216 nonlive counts are retained
aggregate fields in `results/transfer.json` and `results/transfer.stdout.txt`.
`results/transfer.csv` contains two family summaries, not one row per model. Those
two aggregate counts are recomputed by the transfer campaign; the CSV is not
an independent per-model receipt.

The named-case test also exercises five empty-task boundaries in both change
modes: true blocking, a sole goal edge, port recurrence, hidden recurrence, and
a marked-only cycle. Every negative certificate must contain a nonempty cycle.
The quorum test includes identical quorums, whose intersection has three members;
the stated two-member intersection is a lower bound.

The retained historical clean run reports 66.095382 seconds wall time, 75.520377
child CPU seconds, 1.277129 controller CPU seconds, 103,084 KiB peak child RSS,
and 92,960 KiB peak controller RSS. The two RSS values are separate process
maxima, not a simultaneous sum. The run's OS and interpreter were not captured.

## Resume contract

Resume is explicit:

```bash
python3 reproduce.py --output reproduced --resume
```

A `.json` marker alone is never trusted. Before a campaign chunk is skipped, the
controller validates all of the following:

- result JSON, CSV, stdout log, and stderr log are present and readable, and a
  completed suite's stderr log is empty;
- the suite name matches the expected campaign parameters (`n`, `start`, and
  `stop` are encoded in each core-suite name);
- the frozen case count, exact CSV header, and CSV row count match the suite;
- every core CSV row lies in its named encoding range and covers each permitted
  port-set/initial combination exactly once;
- the stdout JSON receipt equals the result JSON, and the two transfer-family CSV
  aggregates agree with the transfer JSON fields;
- generated-input JSONL files for the closed and module suites parse record by
  record, have the expected top-level types, and have the expected line counts.

Missing or damaged bundles are recomputed. Unit tests are always rerun against the
current source. `commands_executed_this_run` contains only commands really run in
the current invocation. Validated skips appear separately under
`results_reused_after_validation`, with their source parameters and checked files;
no command receipt is invented for reuse. Unit tests cover zero, one, and all
chunks already complete, plus a missing log, corrupt JSON, nonempty stderr, and a
core CSV outside its named source range; each repaired plan preserves the frozen
scientific totals. The actual all-completed resume receipt is retained under
`results/resume-validation/summary.json`; it executed only the current tests and
validated/reused all 19 campaign bundles. A second targeted run deliberately made
`named.stderr.txt` nonempty, reran only tests and `named`, reused the other 18
bundles, and is recorded in `results/resume-validation/damaged-named-summary.json`.

## Focused commands

```bash
python3 tests/test_core.py
python3 src/cli.py synthesize inputs/role-reset.json role-reset.cert.json
python3 src/cli.py check inputs/role-reset.json role-reset.cert.json
python3 src/cli.py synthesize inputs/role-reset.json role-reset-finite.cert.json --finite-changes
python3 src/cli.py bind inputs/late-binding-family.json bound-interface.json
python3 src/campaign.py binding --out binding-check
python3 src/campaign.py refinement --out refinement-check
python3 src/campaign.py transfer --out transfer-check
python3 src/campaign.py raw --out raw-check
```

`VALID` means that the checker recomputed the normalized graph and boundary
summary and validated the supplied certificate. It does not establish that an
external protocol was abstracted faithfully.

## Directory guide

- `src/model.py`: strict schema, normalization, enabledness, and deadlock order.
- `src/producer.py`: graph-search summary and certificate synthesis.
- `src/checker.py`: snapshot-elimination summary and certificate validation.
- `src/interfaces.py`: open module export, ownership checks, associative raw
  interface join, and one-shot post-wiring closure.
- `src/summary_oracle.py`: direct first-return mask-product summary construction,
  independent of the search and elimination implementations.
- `src/oracle.py`: bounded whole-graph state-by-color-mask oracle and the
  strong-fairness negative control.
- `src/raw_oracle.py`: bounded raw weak-service/justice oracle that bypasses
  `model.parse` and justice-color normalization.
- `src/refinement.py`: finite checker for abstraction-transfer obligations,
  including semantic stutters at true non-goal deadlocks.
- `src/fixtures.py`: named fixtures, including the scheduler-expanded refinement.
- `src/campaign.py`: deterministic exhaustive/generated campaigns.
- `tests/test_core.py`: 22 contract, algebra, separation, reference, refinement,
  resume, and corruption tests.
- `inputs/`: named scientific fixtures.
- `results/`: retained scientific inputs/results plus targeted validation records.
- `proofs/core-argument.md`: proof obligations and declared boundaries.
- `docs/model-format.md`: input, output, interface-algebra, oracle, and refinement
  contracts.
- `docs/theorem-code-map.md`: theorem-to-code, test, result, and trust-boundary
  crosswalk.
- `docs/source-boundaries.md`: 12+5+5 literature calibration and closest-work delta.
- `reference_audit.csv`: one verified bibliographic record per cited BibTeX key.
- `claim_evidence_ledger.csv`: claim-to-proof/check mapping.
- `external_resources.csv`: scholarly and publisher source inventory.

## Trust boundary

The producer and checker implement different summary algorithms but share the
finite model semantics and parser. The direct summary oracle reconstructs
first-return masks without importing either summary implementation. The
whole-graph oracle avoids ports and summaries but shares normalization. The raw
oracle independently reads the bounded model dictionary and evaluates weak
fairness through enabled-set intersection and service-set union, so the 2,500-case
raw campaign also tests parsing/normalization-sensitive verdicts. All paths still
implement the same mathematical specification and are not independent human
proofs.

The refinement checker validates a supplied finite relation and the retained
transfer campaign covers a small family; neither derives an abstraction from
source code. Agreement is strong finite implementation evidence, not a
machine-checked general theorem, independent review, or evidence about an
unprovided protocol.
