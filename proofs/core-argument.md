# Exact weak-fairness boundary interfaces

This document restates the proof obligations behind the article. It is written
for auditability and does not replace the article or constitute a proof-assistant
check.

## 1. Model, normalization, and observation order

A raw model is a finite directed multigraph with exact states `V`, finite fixed
task alphabet `F`, initials `I`, goals `T`, raw service labels `S(e) subset F`,
and a change bit on each edge. A task is enabled at `v` exactly when at least one
original outgoing edge from `v` services it. Byzantine or adversarial choices are
ordinary allowed transitions and receive no implicit fairness.

Weak fairness of an infinite execution says that every task that is eventually
continuously enabled is serviced infinitely often. Label each raw edge by

`L(e) = S(e) union (F minus Enabled(source(e)))`.

For a fixed task `f`, weak fairness fails exactly when `f` is eventually always
enabled but serviced only finitely often. Its negation is that `f` is disabled
infinitely often or serviced infinitely often, exactly the condition that color
`f` occurs infinitely often in `L`. Applying this pointwise proves the
weak-fairness normalization.

The order of preprocessing is semantic. Compute enabledness on the original raw
graph, add a fully colored ordinary self-loop only at a genuine pending deadlock,
and only then delete goals. A sink exposed by goal deletion is not a deadlock: it
may represent a state whose only action must reach success. Under this order,
fair infinite paths in the normalized pending graph are exactly fair raw
executions that avoid the goal.

Edge addition is non-monotone for the liveness property. With no tasks, adding a
pending self-loop beside a mandatory goal edge destroys liveness. With one task,
a task-free self-loop is fair while the task is disabled; adding a goal edge that
services the task makes that same loop unfair and can establish liveness. This
second direction is the reason disabled-task credit cannot be finalized locally.

The property checked is universal conditional progress: every weakly fair run
reaches a goal. The finite-change interpretation restricts accepted runs to
those using finitely many marked edges, without imposing a common bound.

### Fairness-reflecting abstraction transfer

A finite graph is not automatically a sound abstraction of a protocol. Let a
concrete transition system use the same task alphabet and let `alpha` map its
states to raw-model vertices. For transfer, first totalize every true non-goal
raw deadlock in both systems by a task-free semantic self-stutter. This is not the
fully colored loop used by fairness normalization: it records an infinite blocked
behavior before colors are derived.

The article's sufficient rule then requires:

1. every concrete initial maps to an abstract initial, and an abstract goal image
   can arise only from a concrete goal;
2. every concrete semantic step, including a deadlock stutter, maps to an
   abstract semantic step between the corresponding images;
3. every task serviced by the concrete step is included in the service set of
   that abstract step;
4. every task abstractly enabled at an image state is concretely enabled at the
   source state; and
5. for finite-change transfer, an abstract marked match may be chosen only for a
   marked concrete step.

Take a fair concrete execution that avoids its goal. Deadlock totalization makes
this behavior infinite even when it becomes permanently blocked, and obligations
1--2 make its image an initial goal-avoiding abstract path. If a task is
eventually continuously enabled on the image, obligation 4 makes it eventually
continuously enabled concretely. Concrete fairness therefore services it
infinitely often, and obligation 3 records each service on the image. The image
is weakly fair, contradicting abstract liveness. Under obligation 5, finitely many
concrete marked steps yield finitely many abstract marked steps.

Both the enabledness direction and deadlock totalization are necessary for this
argument. Ordinary transition over-approximation can add an abstract outgoing
edge that enables a task absent concretely, making a concrete fair run
abstractly unfair. Likewise, if a concrete deadlock contributes no semantic
step, it could map vacuously to an abstract state whose sole edge reaches a goal;
the abstract model would be live while the concrete model stutters forever. The
proposition is a sufficient transfer rule, not full abstraction or a necessity
claim.

The repository makes the obligations executable in two ways. First, each of the
fourteen pending states of the 15-state vote-reset graph is duplicated into two
scheduler-metadata phases; the goal remains shared. Task-free phase switches map
to an abstract nonprogress loop, while vote and reset edges are duplicated. The
result has 29 states and 132 raw edges, satisfies all conditions, and preserves
the abstract nonlive unrestricted verdict and live finite-change verdict. Five
mutations separately break initial mapping, goal reflection, enabledness, service
reflection, and change reflection. A sixth regression supplies a concrete
deadlock and abstract goal-only transition and is rejected by semantic-stutter
matching.

Second, the `transfer` campaign exhausts 22,186 tiny concrete/abstract relation
candidates. It accepts 1,358 relations and checks 2,116 arbitrary- or
finite-change implications, with no counterexample to `abstract live => concrete
live`. These checks exercise the finite contract but do not create a source-level
protocol refinement.

### Protocol-instantiation obligations

Applying the finite theorem to a protocol requires evidence outside the checker.
Five obligations must be kept separate.

1. **State extraction and ownership.** Exact ports must retain all
   progress-relevant epoch, role, quorum, vote, and message history, and every
   hidden step must stay in one owning module until the next exact port.
2. **Tasks and scheduler premise.** Fixed task/service names must denote concrete
   scheduling or communication opportunities. Continuous enabledness in the
   finite model must imply concrete enabledness, and the external system must
   justify the assumed weak fairness.
3. **Change semantics.** Every marked edge must preserve the history represented
   at its target. The finite-change result additionally needs a reason that the
   concrete execution has a last marked change; the theorem does not create one.
4. **Safety and quorum reasoning.** Authentication, agreement, state transfer,
   and same- or cross-configuration quorum invariants are separate assumptions or
   proofs. Restricting the graph by such invariants does not make the liveness
   checker prove them.
5. **Evidence direction.** The forward simulation above transfers a positive
   abstract liveness verdict. An abstract negative lasso is a concrete
   counterexample only when every edge of the lasso has a compatible concrete
   realization and those realizations can be concatenated indefinitely.

The scheduler-expanded vote-reset fixture exercises the forward transfer
conditions on a synthetic relation. It is not automatic code extraction, a
Byzantine-protocol refinement, or a proof of the five obligations for a deployed
system.

## 2. Ports and closed summaries

Ports contain every pending initial and both pending endpoints of each marked
edge. Every other pending state is interior. Thus every pending marked edge is a
direct port connector and every suffix trapped inside one interior is ordinary.
Ports are exact states; quotienting votes, epochs, memberships, or message
histories needs a separate correctness argument.

A first-return excursion is a nonempty goal-avoiding path from port `p` to port
`q` with no internal port. An ordinary excursion uses no marked edge. Marked
connectors are direct port edges. The closed summary records:

- `R_z(p,q)`: existence of a first-return arc of kind `z` (ordinary or marked);
- `C_z(p,q)`: union of all fairness colors occurring on all such excursions;
- `D(p)`: existence of a fair infinite ordinary run `p,e0,v1,e1,...` with
  `vi` interior for every `i >= 1`.  Thus the first edge enters the interior and
  the run never crosses another port before the hidden recurrence.

A capacity is a union over possible witnesses. It is not asserted that one
excursion realizes all stored colors.

### Excursion-membership lemma

For an ordinary concrete edge `u -> v`, the edge lies on a `p`-to-`q`
first-return excursion exactly when its source is `p` or interior-reachable from
`p`, and its destination is `q` or can interior-reach `q`. Necessity follows by
cutting a witness path at the edge. Sufficiency follows by concatenating a
prefix, the edge, and a suffix. Repeated interior vertices are allowed. This
proves the graph-search producer's edge-selection rule.

### Elimination invariant

The checker instead eliminates interior vertices. With eliminated set `W`,
`R_xy` means that there is an `x`-to-`y` path whose internal vertices are in `W`,
and `U_xy` is the union of colors on all such paths. When eliminating `w`, old
matrices are snapshotted. If `R_xw` and `R_wy` hold, reachability is added and
`U_xw union U_ww union U_wy` contributes to `U_xy`.

Any newly admitted path decomposes at its first and last visit to `w` into a
prefix, zero or more `w`-loops, and a suffix. Conversely, every contributed color
has a concrete witness after arbitrary realizing paths are attached for the
other factors. Because `U` is a union over paths, distinct colors may use
distinct witnesses. Snapshotting preserves the induction even when indices equal
`w`. After all interiors are eliminated, requiring an explicit first edge
removes zero-length port paths. This proves the matrix summary independently of
the producer's search decomposition.

### Recurrence lemma

A finite colored graph has a fair infinite path from an initial state exactly
when a reachable cyclic strongly connected component has every color on its
internal edges. One direction takes the recurrent support of a fair path. For
the other, choose one internal edge for each color, connect the chosen edges by
paths within the SCC, and repeat the resulting closed walk. With no colors, any
nonempty cycle suffices. A singleton without a self-loop is not cyclic.

### Boundary theorem

A closed normalized model has a fair goal-avoiding run exactly when either:

1. a reachable port has `D`, or
2. a reachable cyclic SCC of the summary graph has capacity union equal to `F`.

For necessity, split by the number of port visits. With finitely many visits,
let `p` be the last port: the suffix beginning at `p` takes its first edge into
the interior and every later state is interior, hence witnesses `D(p)`.
Infinitely many visits yield recurrent macroarcs; every infinitely recurring
concrete color lies on one of those arcs, so their recurrent support is an
accepting summary SCC.

For sufficiency, `D` directly supplies an interior suffix. In an accepting
summary SCC, choose for each task a macroarc whose capacity contains it and a
concrete excursion witnessing that occurrence. Connect those chosen macroarcs by
realizable summary paths and repeat. Different visits to the same macroarc may
choose different excursions. That freedom is why union capacities are exact for
weak-fair recurrence without storing an exponential family of joint masks.

For finite-change liveness, use all arc kinds for prefix reachability but only
ordinary arcs for the recurrent SCC. Any accepted run has an ordinary suffix
after its last marked edge. The hidden-divergence field needs no marked variant:
marked pending edges are port connectors and cannot occur in an interior suffix.
Conversely, any reachable ordinary fair loop has a finite prefix and therefore
uses only finitely many marked edges.

## 3. Sealed modules and exact late binding

An admissible family shares exact ports, goals, tasks, and initials. Each module
owns a private interior, private interiors are pairwise disjoint, and every edge
incident to a private interior belongs to its owner. Outside an interior, modules
may contribute port edges and goal edges. Wiring is multigraph edge union; it may
add edges at ports but cannot delete an edge, modify an existing private
interior, synchronize actions, or identify states. Goal edges are retained while
port enabledness and outgoing-edge existence are computed.

Each module exports the raw interface `(R, U, D, A, O)`:

- `R` and raw union capacity `U` for ordinary excursions and marked connectors;
- `D` for hidden fair ordinary divergence, using the same first-step condition:
  after leaving source port `p`, every state is in that module's private interior;
- `A(p)`, the union of raw services on all module edges leaving `p`, including
  edges to goals;
- `O(p)`, whether any raw module edge leaves `p`.

For an excursion, the first edge leaves a port and is represented with raw
services only. Interior-source edges already use closed weak-fair colors because
wiring cannot alter their enabledness. True interior deadlocks are completed
locally; port deadlocks are not.

Define raw-interface join `X sqcup Y` componentwise: disjoin `R` and `O`, union
present-arc capacities `U`, divergence `D`, and enabledness masks `A`, while
keeping ordinary and marked arc kinds separate. Bitwise/set union and Boolean OR
make this operation associative, commutative, and idempotent. It performs no
fairness closure. For a joined interface `X`, the closure map `B` turns every
present `p`-source capacity into

`B(X).C_z(p,q) = X.U_z(p,q) union (F minus X.A(p))`

and adds a fully colored ordinary `p` self-loop exactly when `X.O(p)` is false;
divergence is unchanged.

Every first-return excursion belongs to one module because interiors are sealed;
its unique port-source edge receives exactly the common post-wiring disabled-task
credit. Union over concrete witnesses commutes with adding that common credit.
Interior labels are unchanged. For divergence, a global `D(p)` witness enters
one private interior on its first edge and remains there forever. Every edge
incident to that interior belongs to its owner, so the whole witness is a local
`D_i(p)` witness; the converse inclusion is immediate. Hence global `D` is the
union of local `D_i`. A path `p -> q -> u -> u` with ports `p,q` and interior
`u` therefore has `D(p)=false` and `D(q)=true`: nonliveness from `p` is represented
by the summary arc `p -> q` followed by reachable `D(q)`. In the direct control
`p -> u -> u`, `D(p)=true`. This argument is unchanged in finite-change mode
because all hidden edges are ordinary. A port is a genuine global deadlock
exactly when every outgoing flag is false. Goal edges affect `A` and `O` but do
not create pending excursions. These observations prove the fieldwise equality

`Summary(union_i M_i) = B(sqcup_i Interface(M_i))`

and therefore exact substitution for both change modes in contexts admissible
with both compared modules.

Raw joins may be reordered or grouped while all exact ports remain visible. The
closure map is intentionally not a homomorphism that may be applied to an early
subfamily. With one task `f`, let raw export `X` contain a task-free ordinary
self-loop at `p`, and let raw export `Y` contain only an `f`-serving edge from `p`
to a goal. `B(X)` colors the loop with `f` because `f` is disabled in `X`, whereas
`B(X sqcup Y)` leaves it uncolored because `Y` enables `f`. Preserving the color
from `B(X)` therefore gives the wrong closed union. The outgoing flag yields the
same obstruction for an early synthetic deadlock loop. The late-enabledness and
late-deadlock tests exercise both failures. Hiding or merging a port, reopening a
closed result as if it were raw, synchronizing actions, or deleting transitions
is outside the theorem.

## 4. Necessity of the exported components

Each separation below uses only ordinary edges and keeps the initial port fixed.
In each pair, every field except the named one agrees.

- **Reachability `R`.** With no tasks, compare a module with `p -> q` and
  `p -> goal` against one with only `p -> goal`. Context edge `q -> p` creates a
  pending cycle only in the first.
- **Capacity `U`.** In the fixed-entry family below, change one task bit on one
  input-output excursion while preserving the complete reachability relation.
  A selecting return context makes the liveness verdict depend on that bit.
- **Divergence `D`.** Compare `p` entering an interior task-free self-loop with
  `p` entering an equally labeled finite path to goal; keep task enabledness at
  `p` identical with the same goal edge. Only the first has hidden divergence.
- **Enabledness `A`.** Compare a task-free self-loop at `p` with the same loop
  plus an `f`-serving edge to goal. The loop changes from fair to unfair solely
  because the context-visible enabledness changes.
- **Outgoing existence `O`.** Compare a deadlocked port with a port whose only
  task-free edge reaches the goal. Raw service union is empty in both, but only
  the deadlock receives a fair completion loop.

Thus simply deleting a displayed component loses exactness in the same context
class as the substitution theorem. This does not prove that the tuple is a
unique encoding, that fields cannot be jointly recoded, or that it induces a
coarsest equivalence for another composition language.

## 5. Complete two-sided certificates

Let `Q` be the summary ports reachable with all arc kinds. For unrestricted
liveness, suffix edges include both kinds; for finite-change liveness, suffix
edges are ordinary.

A positive certificate partitions `Q` into nonempty blocks. Every block has a
nonnegative rank and either no internal suffix edge or a named task absent from
all internal capacities. Every cross-block suffix edge strictly decreases rank,
and no reached port may satisfy `D`.

Soundness follows because an infinite suffix can decrease rank only finitely
many times and must eventually remain in one block, where it either has no edge
or permanently misses the named color. For completeness, take suffix SCCs as
blocks, assign reverse-topological ranks, name a missing color in every cyclic
SCC, and treat an acyclic singleton as having no internal edge. Ranks at most the
number of ports suffice.

A negative certificate is a concrete pending prefix followed by a nonempty
closed walk that covers every color; the walk contains no marked edge in
finite-change mode. Repetition is a fair counterexample. The recurrence lemma
makes such lassos complete. The checker validates identifiers, adjacency,
closure, goal avoidance, labels, mode, and the independently recomputed complete
summary. Witnesses are not claimed shortest.

A fair bad execution has a lasso with a prefix of at most `n-1` edges and a cycle
of at most `max(1,k)(2n-1)` edges: choose an accepting SCC and anchor, use a
shortest prefix, and for each color connect the anchor to an edge carrying that
color and back by shortest internal paths. This is an existence bound, not a
bound attained by every producer output.

## 6. Capacity-information lower bound

Fix `a >= 1` input ports, `b >= 1` output ports, a separate common initial port
`r`, and `k >= 1` tasks. For each input-output pair independently choose a subset
`X_ij` of tasks. Include one raw edge from input `i` to output `j` serving
`X_ij`, and from every port include a goal edge serving every task. All tasks are
therefore enabled at ports in every module. The modules share reachability,
divergence, enabledness, outgoing flags, and initial state; only the `kab`
capacity bits vary.

For a differing bit `f` of pair `(i,j)`, a context adds a task-free edge `r -> i`
and a return `j -> i` serving `F minus {f}`. Other outputs have only goal edges
and cannot recur. A fair pending loop exists exactly when `f` belongs to
`X_ij`. Hence all `2^(kab)` matrices are pairwise distinguishable with the same
entry state. Any fixed-length exact binary summary needs at least `kab` bits; the
same worst-case maximum follows for variable-length strings because fewer than
`2^(kab)` strings are shorter than `kab` bits. Since `|P| = a+b+1`, balanced
`a,b` yield an `Omega(k |P|^2)` worst-case order.

The displayed interface also has a direct matching upper order. With `b=|P|`,
two arc kinds need `O(b^2)` reachability bits and `O(k b^2)` capacity bits;
divergence and outgoing flags need `O(b)`, and enabledness needs `O(kb)`. Hence
the capacity-dominated dense representation has worst-case `Theta(k b^2)`
information order. This is not a unique-minimum-format theorem, an average-case
compression bound, a serialization-optimality result, or a statement about a
sparse instance.

## 7. Boundaries: strong fairness and merged states

Strong fairness requires a task serviced infinitely often whenever it is enabled
infinitely often, not only continuously. Consider a unique `p`-to-`q` excursion
through a state `u` where an `f`-service goal edge is enabled; add a task-free
return `q -> p`. In one module, every loop visits `u`; in another, an optional
bypass avoids every state enabling `f`. The two modules have equal
`(R,U,D,A,O)` under the weak interface, but only the bypass module has a strongly
fair pending loop. Union capacities forget whether enable events are avoidable.
The result only refutes reuse of this interface for strong fairness; a richer
strong-fair interface may exist.

Likewise, merging exact ports can invent recurrence. Quotienting a one-shot path
`p0 -> p1 -> goal` into one state turns its transition into a self-loop. Retaining
membership while discarding vote or epoch history is therefore outside the
proved substitution theorem unless a separate quotient proof is supplied.

## 8. Independent finite constructions and retained evidence

The direct summary oracle is independent of both summary implementations. For
each source port it explores the complete product of an interior path state and a
seen-color mask, stops at the first returned port, records every reached mask by
arc kind, and unions those masks into the corresponding capacity. A separate
product search detects a color-complete infinite suffix wholly inside the sealed
interior. It imports neither the producer's first-return reachability logic nor
the checker's elimination matrices or SCC routine. Exhausting the product is
exact because every recorded product path is a concrete first-return witness, and
every such witness induces a reached product state; the same two directions hold
for an interior loop.

The whole-graph oracle constructs the complete product of normalized state `v`
and seen-color mask `M` when `n 2^k <= 8192`. For each reachable anchor, it
searches for a nonempty return with mask `F`; recurrent search omits marked edges
in finite-change mode. Such a return is a repeatable fair walk. Conversely, the
recurrence lemma supplies a closed walk covering all colors, which reaches an
accepting product state at any anchor. Thus this oracle is an exact decision path
within its declared budget and does not use ports or summaries.

The retained clean campaign reports:

- 244,828 producer/checker verdicts, all agreeing and with every synthesized
  certificate accepted by the checker;
- 310,463 direct summary-oracle comparisons, all agreeing with both summary
  implementations;
- within that total, 65,635 exhaustive two-module binding cases: all `3^10`
  ordinary assignments, `3^8` private-interior goal assignments, and 25 marked
  connector combinations;
- 244,824 in-budget whole-graph oracle verdicts, all agreeing, with four larger
  chain/ring cases explicitly excluded by that oracle's smaller budget;
- 2,500 raw-semantics comparisons that bypass `model.parse` and justice-color
  normalization while checking enabledness intersections and service unions;
- one accepted 29-state-to-15-state refinement relation, five deliberately broken
  obligation classes, and one deadlock-totalization regression;
- 22,186 tiny transfer relation candidates, 1,358 accepted relations, and 2,116
  checked unrestricted or finite-change implications; and
- 22 unit-test methods covering normalization order, the raw oracle, reference
  inventory, schema rejection, certificate corruption, raw-interface algebra,
  regrouping, component separations (including the `p -> q` hidden-divergence
  locality regression), fixed-entry lower-bound contexts, ownership, strong
  fairness, refinement failures, deadlock semantics, and resume-record validation.

These checks validate implementations over a finite deterministic campaign. The
producer and checker share the parser and mathematical specification; the direct
summary and whole-graph oracles share normalization. The raw oracle removes that
shared parsing/normalization path on its bounded family, but all programs still
implement the same mathematical specification. A common definition error, an
invalid source-to-model abstraction, or a flaw in the hand proof could survive.
No independent human or proof-assistant verification is claimed.
