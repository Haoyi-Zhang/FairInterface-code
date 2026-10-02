# Finite input contract

An input is a JSON object with `states`, `tasks`, `coloring`, `edges`, `initial`,
`goals`, and `ports`. Only `description` and `role_metadata` are additionally
accepted annotation fields; they do not affect the semantics. State IDs are
integers from zero to `states - 1`. A task mask is an integer in
`[0, 2**tasks)`. An edge is `[source, destination, mask, change]`, where `change`
is exactly a JSON Boolean. State and task counts must not be Booleans.

`weak-service` masks mean raw service events. For each task, enabledness is the
existence of an original outgoing service edge, **including edges to goals**.
The normalized mask is raw service union tasks not enabled at the source.
`justice` masks directly specify recurrence colors. For raw input in either
mode, original deadlocks receive a fully colored ordinary self-loop before goal
vertices are deleted. New sinks created by goal deletion receive no new loop.
The direct colored-graph enumeration intentionally bypasses that raw normalization
and tests infinite-path graph semantics without deadlock completion.

The initial, goal and port collections contain distinct bounded integer IDs.
Every pending initial state and each endpoint of a pending marked edge must be a
port. Goals and ports are disjoint. The goal is reachability at least once;
only prefixes that have not yet reached it matter. Empty initials are valid and
produce vacuous liveness. A goal initial is already successful. A one-vertex
component with no self-loop is not a cycle, even with no tasks.

Bounds: 1..128 states, 0..8 tasks, at most 4,096 raw edges and 64 ports; model or
module-family file at most 1 MiB, certificate at most 4 MiB. JSON duplicate keys,
NaN/Infinity and unknown top-level fields are rejected. A module family contains
1..16 weak-service modules with identical global state universe, task count,
initials, goals and exact ports. Their incident private interiors must be disjoint;
combined raw edges still obey the 4,096-edge cap. An unused global ID can occur
in every file without becoming a shared reachable interior.

The finite-change mode admits any finite number of marked edges, without an
instance-wide numerical bound. Prefix reachability uses all edges, but an
accepting recurrent suffix must use only ordinary edges. A change label is not
a service event by itself. Actions of Byzantine participants are not scheduled
fairly unless explicitly selected into the task set. This is a declarative
finite transition system, not an automatic extraction from a distributed program.

Open summaries preserve ordinary/change arc kind, reachability, union capacity,
hidden fair divergence, raw port enabling masks and outgoing flags. Hidden
divergence at port `p` requires an ordinary infinite path whose first edge enters
the private interior and whose every later state remains interior; a path that
first reaches another port is represented by a summary arc to that port. Raw exports
are joined componentwise by union/OR; `src/interfaces.py` exposes this operation
separately from the one global closure that adds disabled-task credit and genuine
port-deadlock loops. Binding may add transitions at exact shared ports but may not
remove edges, synchronize a product, change an interior, hide a port, or merge
observationally similar states.
The accepted certificate structure is defined by the strict checker; positive
blocks use bounded ranks and missing colors, while negative witnesses refer to
normalized concrete edge indices. These indices are not external protocol IDs.

## Independent finite cross-checks

The direct summary oracle explores `(state, seen_mask)` products separately from
each source port. It stops a path at its first returned port, records every reached
mask for the corresponding ordinary or marked arc, unions those masks into the
capacity, and searches for color-complete infinite behavior wholly inside the
sealed interior. It does not call the producer's graph-search summary, the
checker's elimination summary, or either implementation's SCC helper. Its guard
is `states * 2**tasks <= 32768`; every retained campaign input satisfies it.

The whole-graph oracle ignores ports and summaries. For each reachable pending
anchor, it searches a complete `(state, seen_mask)` product for a nonempty return
covering every color. In finite-change mode its recurrent search excludes marked
edges. Its smaller guard is `states * 2**tasks <= 8192`; four declared scaling
fixtures exceed this guard and are reported as exclusions rather than agreements.

The raw-semantics oracle does not import `model.parse` and does not construct
justice-colored edges for `weak-service` inputs. It totalizes only genuine raw
non-goal deadlocks, removes goals locally, and searches nonempty closed walks while
tracking the intersection of task-enabled masks over source states and the union
of raw service masks over traversed edges. A repeated walk is weakly fair exactly
when every task in that enabled intersection occurs in the service union. In
finite-change mode, prefix reachability may use marked edges but the recurrent
walk may not. Its guard is `states * 4**tasks <= 32768` for weak-service inputs
and `states * 2**tasks <= 32768` for direct justice inputs.

## Refinement-condition report

`src/refinement.py` checks a supplied total state map from one finite concrete
model to one finite abstract model. Both inputs must use raw `weak-service`
labels. Before matching steps, the checker adds a **task-free semantic
self-stutter** at every true non-goal raw deadlock in each model. This represents
an execution that remains blocked forever. It is deliberately different from the
fully colored loop used later by weak-fairness normalization: the raw stutter
performs no service, and fairness regards it as fair because no task is enabled.

The transfer contract requires:

1. every concrete initial maps to an abstract initial;
2. any concrete state mapped to an abstract goal is itself a concrete goal;
3. every concrete semantic step, including a synthesized deadlock stutter, maps
   to an abstract semantic step between the corresponding images;
4. the abstract step's raw service mask contains the concrete service mask;
5. every task enabled at an abstract image is enabled at the concrete source;
6. a mapped abstract step may be marked only when its concrete step is marked.

The checker returns a structured report naming the first failed obligation and,
on success, the semantic-step counts and chosen matches. Acceptance proves only
that the supplied finite relation satisfies these sufficient conditions. It
neither discovers the map nor establishes correspondence between program code
and either graph.

The retained fixture maps a 29-state, 132-raw-edge scheduler expansion to the
15-state vote-reset model. Five mutation classes break initial mapping, goal
reflection, enabledness, service reflection, or change reflection. A sixth
regression maps a truly deadlocked concrete initial to an abstract state whose
only edge reaches a goal; it is rejected specifically because the concrete
semantic stutter has no match. The separate `transfer` campaign's retained summary records 22,186 tiny
relation candidates, 1,358 accepted relations, 2,116 unrestricted or
finite-change implications, 2,038 model verdicts, and 1,216 nonlive verdicts.
The last two counts are aggregate fields in `results/transfer.json` and its stdout
receipt; `results/transfer.csv` contains two family summaries rather than
per-model rows. They were not recomputed by the targeted definition/resume repair.
These are finite model-level checks, not a source-level protocol refinement.
