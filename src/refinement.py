"""Finite checker for the sufficient abstraction-transfer conditions.

This checks a supplied total state map between two raw weak-service models.  It
is deliberately narrower than a general simulation framework and establishes
only the conditions stated by Proposition 2.4 of the accompanying paper.

A true non-goal deadlock denotes an infinite task-free stutter in the raw
semantics.  The checker therefore totalizes such states before matching steps.
Ignoring that semantic step would be unsound: a deadlocked concrete state could
otherwise be related to an abstract state whose only transition reaches a goal.
"""
from __future__ import annotations
from model import parse


def _raw_edges(data: dict) -> list[tuple[int, int, int, bool]]:
    graph = parse(data)  # strict schema, bounds, endpoints, and marked-port discipline
    if data['coloring'] != 'weak-service':
        raise ValueError('refinement inputs must use raw weak-service labels')
    return [tuple(row) for row in data['edges']]


def _semantic_steps(data: dict) -> tuple[list[tuple[int, int, int, bool, bool]], int]:
    """Return raw steps plus task-free stutters at true pending deadlocks.

    The final Boolean marks a synthesized deadlock stutter.  Its service set is
    empty: weak fairness regards the continuation as fair because no task is
    enabled, not because the stutter performs every task.  Goal states need no
    continuation for a goal-avoidance transfer argument.
    """
    graph = parse(data)
    raw = _raw_edges(data)
    outgoing = [False] * graph.n
    for source, _, _, _ in raw:
        outgoing[source] = True
    steps = [(source, target, services, change, False)
             for source, target, services, change in raw]
    synthesized = 0
    for state in range(graph.n):
        if state not in graph.goals and not outgoing[state]:
            steps.append((state, state, 0, False, True))
            synthesized += 1
    return steps, synthesized


def check_refinement(concrete: dict, abstract: dict, mapping: list[int]) -> dict:
    """Check the finite sufficient conditions and return an auditable report.

    Services are reflected from concrete to abstract (X subseteq Y), abstract
    enabledness is reflected back to each concrete state, abstract goals reflect
    concrete goals, and an abstract marked match is permitted only for a marked
    concrete step.  True pending deadlocks are matched as task-free stutters.
    Therefore a fair concrete goal-avoiding run maps to a fair abstract
    goal-avoiding run; finite concrete change implies finite abstract change.
    """
    cg = parse(concrete)
    ag = parse(abstract)
    cedges = _raw_edges(concrete)
    aedges = _raw_edges(abstract)
    csteps, cdeadlocks = _semantic_steps(concrete)
    asteps, adeadlocks = _semantic_steps(abstract)
    if cg.k != ag.k:
        raise ValueError('task alphabets disagree')
    if not isinstance(mapping, list) or len(mapping) != cg.n:
        raise ValueError('mapping must give one abstract state per concrete state')
    if any(type(value) is not int or not 0 <= value < ag.n for value in mapping):
        raise ValueError('mapping contains an invalid abstract state')

    abstract_initials = set(ag.initial)
    bad_initials = [state for state in cg.initial if mapping[state] not in abstract_initials]
    if bad_initials:
        raise ValueError('a concrete initial does not map to an abstract initial')

    bad_goals = [state for state in range(cg.n)
                 if mapping[state] in ag.goals and state not in cg.goals]
    if bad_goals:
        raise ValueError('abstract goal does not reflect a concrete goal')

    # Enabledness is computed from raw service edges.  Synthesized deadlock
    # stutters perform no task and therefore do not enable one.
    enabled_c = [0] * cg.n
    enabled_a = [0] * ag.n
    for source, _, services, _ in cedges:
        enabled_c[source] |= services
    for source, _, services, _ in aedges:
        enabled_a[source] |= services
    bad_enabled = [state for state in range(cg.n)
                   if enabled_a[mapping[state]] & ~enabled_c[state]]
    if bad_enabled:
        raise ValueError('abstract enabledness is not contained in concrete enabledness')

    matches = []
    for index, (source, target, services, change, synthetic) in enumerate(csteps):
        image_source = mapping[source]
        image_target = mapping[target]
        candidates = []
        for aindex, (asource, atarget, aservices, achange, asynthetic) in enumerate(asteps):
            if (asource == image_source and atarget == image_target and
                    services & ~aservices == 0 and (not achange or change)):
                candidates.append(aindex)
        if not candidates:
            kind = 'deadlock stutter' if synthetic else 'edge'
            raise ValueError(f'concrete {kind} {index} has no preserving abstract match')
        matches.append(candidates[0])

    return {
        'valid': True,
        'concrete_states': cg.n,
        'abstract_states': ag.n,
        'concrete_edges': len(cedges),
        'abstract_edges': len(aedges),
        'concrete_semantic_steps': len(csteps),
        'abstract_semantic_steps': len(asteps),
        'concrete_deadlock_stutters': cdeadlocks,
        'abstract_deadlock_stutters': adeadlocks,
        'tasks': cg.k,
        'mapping': mapping,
        'initial_images': sorted({mapping[state] for state in cg.initial}),
        'matched_abstract_step': matches,
        'conditions': {
            'initial_mapping': True,
            'goal_reflection': True,
            'semantic_step_and_service_reflection': True,
            'true_deadlock_totalization': True,
            'enabledness_reflection': True,
            'finite_change_reflection': True,
        },
    }
