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

The controller retains POSIX process groups/`resource` and adds a native Windows
path using standard-library `ctypes`: kill-on-close jobs, total job CPU (kernel
plus user, including completed descendants), and worker peak working sets.
A virtual environment's direct `python.exe` handle can be only a launcher; its
CPU is not full worker cost. Owned benign parent/grandchild termination and an
arithmetic worker check this distinction. The clean runs in `results/owned-scc/`
used Windows 11 build 28000, Intel Core i7-12700KF (12 cores/20 logical processors),
CPython 3.12.14, no third-party Python dependencies and one scientific worker at
a time. Fixed limits remain 20 wall seconds per child and 180 per campaign, not
CPU/memory OS quotas. Worker peak working set is not simultaneous process-tree
memory. The modified POSIX wrapper path, macOS and WSL were not executed here;
earlier Linux results remain historical.

Every new `summary.json` records the operating system, machine, Python
implementation/version, interpreter basename, process-group mechanism, the
native `ru_maxrss` unit, and the reported RSS unit. Reported peak RSS is normalized
to KiB. The retained historical clean campaign predates this environment capture:
its OS and interpreter are therefore recorded as unknown rather than reconstructed.
Its already reported RSS figures remain labeled as KiB because that is how the
historical record stored them.

## One-command reproduction

From this directory, choose a fresh external output parent as `OWNED_OUTPUT`:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B reproduce.py --output "$OWNED_OUTPUT/reproduced"
# Repeat the same inputs; do not add the counts:
PYTHONDONTWRITEBYTECODE=1 python3 -B -O reproduce.py --output "$OWNED_OUTPUT/reproduced-optimized"
```

A clean run requires a new output directory and executes 25 unit-test methods plus
19 bounded campaign chunks sequentially. It writes retained inputs, CSV/JSON
results, certificates, per-command logs, and `summary.json`. Before accepting the
run, the controller checks the exact suite inventory, deterministic totals,
command exits, and the 25-test receipt. Expected deterministic totals are:

- 244,828 producer/checker verdict cases;
- 244,828 paired ordinary SCC decisions on the same normalized inputs, with no
  product exclusions (not additional scientific cases);
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
an independent per-model receipt. Current `transfer-costs.csv` additionally binds
all 2,038 model evaluations to normalized-graph digests, evaluation order, mode,
and verdict; deterministic source construction remains in `src/campaign.py`.

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
python3 reproduce.py --output "$OWNED_OUTPUT/reproduced" --resume
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

Create the external `OWNED_OUTPUT` directory before running the CLI examples.
The CLI does not create parent directories and refuses existing output files;
use a fresh directory for each smoke run. Campaign outputs below also stay under
that parent.

```bash
python3 tests/test_core.py
python3 src/cli.py synthesize inputs/role-reset.json "$OWNED_OUTPUT/role-reset.cert.json"
python3 src/cli.py check inputs/role-reset.json "$OWNED_OUTPUT/role-reset.cert.json"
python3 src/cli.py synthesize inputs/role-reset.json "$OWNED_OUTPUT/role-reset-finite.cert.json" --finite-changes
python3 src/cli.py bind inputs/late-binding-family.json "$OWNED_OUTPUT/bound-interface.json"
python3 src/campaign.py binding --out "$OWNED_OUTPUT/binding-check"
python3 src/campaign.py refinement --out "$OWNED_OUTPUT/refinement-check"
python3 src/campaign.py transfer --out "$OWNED_OUTPUT/transfer-check"
python3 src/campaign.py raw --out "$OWNED_OUTPUT/raw-check"
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
- `src/monolithic.py`: ordinary whole-graph SCC decision baseline, without an
  interface, mask product, producer/checker helper, or certificate.
- `src/process_metrics.py`, `src/measured_worker.py`: native owned-worker
  measurements and receipts; job CPU includes interpreter descendants.
- `analyze_costs.py`: historical-outcome reconciliation and paired-cost analysis.
- `tests/test_core.py`: 25 contract, algebra, separation, reference, refinement,
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

Positive verification uses an invocation-local checker-owned adjacency/worklist
after the unchanged exact summary reconstruction and comparison. Both arc kinds
remain available to prefix reachability in both change modes; only recurrent
checks filter marked arcs. `python -B tests/reachability_regression.py` provides
a portable independent finite regression and runs explicitly in CI before the
25-test/full-campaign receipt. It does not establish a speedup or protocol
guarantee. The scientific workflow runs this regression before the full campaign;
exact-head run results are available in the repository's Actions tab.

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

## Paired-cost interpretation

`results/owned-scc/` retains both clean full runs, generated-input JSONL,
scientific CSV/JSON, worker mode/bytecode/peak-memory receipts and timing rows.
The comparison is regenerated by:

```bash
python3 -B analyze_costs.py results/owned-scc/normal results/owned-scc/optimized --output cost-check
```

The fixed order is producer, independent checker, then SCC decision. Each sees
the same already-normalized graph and change mode. Full process-tree CPU and
campaign wall time additionally cover input generation/normalization, module
export/join, all oracles, source binding, serialization, IO, tests, process startup
and controller validation. The baseline has the same Boolean semantics, but
does not emit a consumer-checkable certificate. No standalone end-to-end solver
comparison, incremental maintenance gain, confidence interval, speedup, native
protocol deployment or novel SCC criterion is established. The two modes repeat
the same population; all historical negative outcomes and files are retained.
