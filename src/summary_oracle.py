"""Independent exact first-return summary oracle for bounded finite graphs.

The implementation explores (state, accumulated-color-mask) products directly.
It imports neither producer nor checker and uses no SCC or vertex-elimination
routine.  It is intended as a finite implementation cross-check, not as the
primary asymptotic algorithm.
"""
from __future__ import annotations
from collections import deque
from model import Graph

MAX_PRODUCT_STATES = 32768


def _check_budget(g: Graph) -> None:
    if g.n * (1 << g.k) > MAX_PRODUCT_STATES:
        raise ValueError('summary-oracle product budget exceeded')


def exact_summary(g: Graph) -> dict:
    """Return the exact port summary by explicit first-return products.

    Ordinary paths stop at their first port after departure.  For each ordered
    port pair, all reachable path masks are explored and then unioned.  Hidden
    divergence requires the first edge after the source port to enter the sealed
    interior; every later state stays inside.  It is checked by explicit
    color-accumulating loops wholly inside that interior.
    """
    _check_budget(g)
    ports = set(g.ports)
    inside = set(g.remaining) - ports
    ordinary = [e for _, e in g.pending_edges() if not e.change]
    adjacency = {u: [] for u in g.remaining}
    for edge in ordinary:
        adjacency[edge.src].append(edge)

    arcs = []
    for source in g.ports:
        capacities: dict[int, int] = {}
        seen: set[tuple[int, int]] = set()
        todo: deque[tuple[int, int]] = deque()
        for edge in adjacency[source]:
            mask = edge.color
            if edge.dst in ports:
                capacities[edge.dst] = capacities.get(edge.dst, 0) | mask
            elif edge.dst in inside:
                item = (edge.dst, mask)
                if item not in seen:
                    seen.add(item)
                    todo.append(item)
        while todo:
            state, mask = todo.popleft()
            for edge in adjacency[state]:
                next_mask = mask | edge.color
                if edge.dst in ports:
                    capacities[edge.dst] = capacities.get(edge.dst, 0) | next_mask
                elif edge.dst in inside:
                    item = (edge.dst, next_mask)
                    if item not in seen:
                        seen.add(item)
                        todo.append(item)
        for target, capacity in sorted(capacities.items()):
            arcs.append([source, target, capacity, False])

    changes: dict[tuple[int, int], int] = {}
    for _, edge in g.pending_edges():
        if edge.change:
            key = (edge.src, edge.dst)
            changes[key] = changes.get(key, 0) | edge.color
    arcs.extend([[source, target, mask, True]
                 for (source, target), mask in sorted(changes.items())])
    arcs.sort(key=lambda row: (row[0], row[1], row[3]))

    divergence = []
    for port in g.ports:
        reachable: set[int] = set()
        todo_vertices: deque[int] = deque()
        for edge in adjacency[port]:
            if edge.dst in inside and edge.dst not in reachable:
                reachable.add(edge.dst)
                todo_vertices.append(edge.dst)
        while todo_vertices:
            state = todo_vertices.popleft()
            for edge in adjacency[state]:
                if edge.dst in inside and edge.dst not in reachable:
                    reachable.add(edge.dst)
                    todo_vertices.append(edge.dst)

        found = False
        for anchor in sorted(reachable):
            start = (anchor, 0)
            seen_product = {start}
            todo_product: deque[tuple[int, int]] = deque([start])
            while todo_product and not found:
                state, mask = todo_product.popleft()
                for edge in adjacency[state]:
                    if edge.dst not in inside:
                        continue
                    next_mask = mask | edge.color
                    if edge.dst == anchor and next_mask == g.full:
                        found = True
                        break
                    item = (edge.dst, next_mask)
                    if item not in seen_product:
                        seen_product.add(item)
                        todo_product.append(item)
            if found:
                break
        if found:
            divergence.append(port)

    return {'arcs': arcs, 'divergence': divergence}
