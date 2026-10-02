"""Sealed-interior weak-fairness interfaces with late-bound port closure.

Only states explicitly in ports/goals may be shared between modules. Ports are
exact states, not observations. The fixed task alphabet is shared. No action may
be added at a sealed interior. Local disabledness credit and port-deadlock
completion are deliberately deferred until all raw interfaces have been joined.
"""
from __future__ import annotations

from collections.abc import Iterable

from model import Edge, Graph, parse
from producer import summarize
from checker import reference_summary


def module_graph(data: dict) -> tuple[Graph, list[int], list[bool]]:
    """Construct the locally closed graph used to export one open module.

    Interior sources can be normalized because wiring cannot add edges there.
    Port sources retain raw service labels because global enabledness is not known
    until all modules are present.  True deadlocks are completed only for states
    that the module actually owns; unmentioned global identifiers are not claimed.
    """
    validated = parse(data)  # strict bounded schema; discard its closed labels
    if data['coloring'] != 'weak-service':
        raise ValueError('modules require explicit weak-service labels')
    enabled = [0] * validated.n
    outgoing = [False] * validated.n
    for u, v, mask, change in data['edges']:
        enabled[u] |= mask
        outgoing[u] = True
    ports = set(validated.ports)
    owned = {
        state for row in data['edges'] for state in row[:2]
    } - ports - validated.goals
    edges = [
        Edge(u, v, mask if u in ports else mask | (validated.full ^ enabled[u]), change)
        for u, v, mask, change in data['edges']
    ]
    edges += [
        Edge(u, u, validated.full)
        for u in sorted(owned)
        if not outgoing[u]
    ]
    graph = Graph(
        validated.n,
        validated.k,
        tuple(edges),
        validated.initial,
        validated.goals,
        validated.ports,
    )
    return (
        graph,
        [enabled[p] for p in graph.ports],
        [outgoing[p] for p in graph.ports],
    )


def export(data: dict, independent: bool = False) -> dict:
    """Export the raw five-field interface in canonical list order.

    The divergence field at port p only covers an ordinary infinite path whose
    first edge enters this module's interior and whose later states remain there.
    Reaching another port first is represented by a summary arc to that port.
    """
    graph, enabled, outgoing = module_graph(data)
    result = (reference_summary if independent else summarize)(graph)
    return {
        'arcs': result['arcs'],
        'divergence': result['divergence'],
        'enabled': enabled,
        'outgoing': outgoing,
    }


def validate_family(modules: list[dict]) -> Graph:
    """Validate an admissible exact-port family and return its closed raw union."""
    if not isinstance(modules, list) or not 1 <= len(modules) <= 16:
        raise ValueError('expected 1..16 modules')
    base = parse(modules[0])
    used: set[int] = set()
    edges: list[list] = []
    for data in modules:
        graph = parse(data)
        if data['coloring'] != 'weak-service' or (
            graph.n,
            graph.k,
            graph.initial,
            graph.goals,
            graph.ports,
        ) != (
            base.n,
            base.k,
            base.initial,
            base.goals,
            base.ports,
        ):
            raise ValueError('modules disagree on exact states, task alphabet or boundary')
        interiors = {
            state for row in data['edges'] for state in row[:2]
        } - set(graph.ports) - graph.goals
        if used & interiors:
            raise ValueError('shared non-port interior state')
        used |= interiors
        edges.extend(data['edges'])
    combined = {
        key: value
        for key, value in modules[0].items()
        if key not in ('description', 'role_metadata')
    }
    combined['edges'] = edges
    return parse(combined)


def join_exports(items: Iterable[dict], port_count: int) -> dict:
    """Join raw interfaces before installing global fairness credit.

    The operation is componentwise union/OR and is therefore associative,
    commutative, and idempotent on canonical exports.  It intentionally performs
    no disabled-task closure and no port-deadlock completion.
    """
    if type(port_count) is not int or port_count < 0:
        raise ValueError('invalid port count')
    sequence = list(items)
    if not sequence:
        raise ValueError('cannot join an empty interface family')

    enabled = [0] * port_count
    outgoing = [False] * port_count
    capacities: dict[tuple[int, int, bool], int] = {}
    divergences: set[int] = set()
    for item in sequence:
        if type(item) is not dict or set(item) != {
            'arcs', 'divergence', 'enabled', 'outgoing'
        }:
            raise ValueError('malformed raw interface')
        if (
            not isinstance(item['enabled'], list)
            or not isinstance(item['outgoing'], list)
            or len(item['enabled']) != port_count
            or len(item['outgoing']) != port_count
        ):
            raise ValueError('raw interface boundary length mismatch')
        for index in range(port_count):
            mask = item['enabled'][index]
            flag = item['outgoing'][index]
            if type(mask) is not int or type(flag) is not bool:
                raise ValueError('malformed port field')
            enabled[index] |= mask
            outgoing[index] |= flag
        if not isinstance(item['divergence'], list) or any(
            type(port) is not int for port in item['divergence']
        ):
            raise ValueError('malformed divergence field')
        divergences.update(item['divergence'])
        if not isinstance(item['arcs'], list):
            raise ValueError('malformed arc field')
        for row in item['arcs']:
            if (
                not isinstance(row, list)
                or len(row) != 4
                or type(row[0]) is not int
                or type(row[1]) is not int
                or type(row[2]) is not int
                or type(row[3]) is not bool
            ):
                raise ValueError('malformed raw interface arc')
            key = (row[0], row[1], row[3])
            capacities[key] = capacities.get(key, 0) | row[2]

    arcs = [
        [source, target, mask, change]
        for (source, target, change), mask in sorted(capacities.items())
    ]
    return {
        'arcs': arcs,
        'divergence': sorted(divergences),
        'enabled': enabled,
        'outgoing': outgoing,
    }


def close_join(graph: Graph, joined: dict) -> dict:
    """Install global disabledness credit and genuine port-deadlock loops."""
    if type(joined) is not dict or set(joined) != {
        'arcs', 'divergence', 'enabled', 'outgoing'
    }:
        raise ValueError('malformed joined interface')
    ports = list(graph.ports)
    if len(joined['enabled']) != len(ports) or len(joined['outgoing']) != len(ports):
        raise ValueError('joined interface boundary length mismatch')
    position = {port: index for index, port in enumerate(ports)}
    if set(joined['divergence']) - set(ports):
        raise ValueError('divergence outside the exact boundary')

    capacities: dict[tuple[int, int, bool], int] = {}
    for source, target, mask, change in joined['arcs']:
        if source not in position or target not in position:
            raise ValueError('summary arc outside the exact boundary')
        if mask < 0 or mask > graph.full:
            raise ValueError('summary capacity outside the task alphabet')
        key = (source, target, change)
        capacities[key] = capacities.get(key, 0) | mask

    for index, port in enumerate(ports):
        mask = joined['enabled'][index]
        flag = joined['outgoing'][index]
        if type(mask) is not int or not 0 <= mask <= graph.full or type(flag) is not bool:
            raise ValueError('invalid joined port field')
        if not flag:
            capacities[(port, port, False)] = graph.full

    arcs = []
    for (source, target, change), mask in sorted(capacities.items()):
        disabled = graph.full ^ joined['enabled'][position[source]]
        arcs.append([source, target, mask | disabled, change])
    return {'arcs': arcs, 'divergence': sorted(joined['divergence'])}


def bind(modules: list[dict], independent: bool = False) -> tuple[Graph, dict]:
    """Join exact-port interfaces and then perform the single global closure."""
    graph = validate_family(modules)
    joined = join_exports(
        (export(data, independent) for data in modules), len(graph.ports)
    )
    return graph, close_join(graph, joined)
