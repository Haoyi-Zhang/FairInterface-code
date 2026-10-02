"""Finite closed models. No network, protocol implementation, or symbolic input."""
from __future__ import annotations
from dataclasses import dataclass
import json
from pathlib import Path

MAX_BYTES = 1_048_576
MAX_STATES, MAX_TASKS, MAX_EDGES, MAX_PORTS = 128, 8, 4096, 64

@dataclass(frozen=True)
class Edge:
    src: int
    dst: int
    color: int
    change: bool = False

@dataclass(frozen=True)
class Graph:
    n: int
    k: int
    edges: tuple[Edge, ...]
    initial: tuple[int, ...]
    goals: frozenset[int]
    ports: tuple[int, ...]

    @property
    def full(self) -> int:
        return (1 << self.k) - 1

    @property
    def remaining(self) -> frozenset[int]:
        return frozenset(range(self.n)) - self.goals

    def pending_edges(self) -> tuple[tuple[int, Edge], ...]:
        return tuple((i, e) for i, e in enumerate(self.edges)
                     if e.src not in self.goals and e.dst not in self.goals)


def _integer(x: object, lo: int, hi: int, field: str) -> int:
    if type(x) is not int or not lo <= x <= hi:
        raise ValueError(f'{field}: expected integer in [{lo},{hi}]')
    return x


def _ids(xs: object, n: int, field: str) -> tuple[int, ...]:
    if not isinstance(xs, list):
        raise ValueError(f'{field}: expected list')
    ys = tuple(_integer(x, 0, n - 1, field) for x in xs)
    if len(set(ys)) != len(ys):
        raise ValueError(f'{field}: repeated state')
    return tuple(sorted(ys))


def parse(data: dict) -> Graph:
    required = {'states', 'tasks', 'coloring', 'edges', 'initial', 'goals', 'ports'}
    if type(data) is not dict or not required <= data.keys():
        raise ValueError('missing model fields')
    if data.keys() - required - {'description', 'role_metadata'}:
        raise ValueError('unknown model fields')
    n = _integer(data['states'], 1, MAX_STATES, 'states')
    k = _integer(data['tasks'], 0, MAX_TASKS, 'tasks')
    full = (1 << k) - 1
    mode = data['coloring']
    if mode not in ('justice', 'weak-service'):
        raise ValueError('coloring must be justice or weak-service')
    initial = _ids(data['initial'], n, 'initial')
    goals = frozenset(_ids(data['goals'], n, 'goals'))
    ports = _ids(data['ports'], n, 'ports')
    if len(ports) > MAX_PORTS or not set(initial).difference(goals) <= set(ports):
        raise ValueError('ports exceed bound or omit a pending initial state')
    if goals.intersection(ports):
        raise ValueError('goal states cannot be ports')
    raw = data['edges']
    if not isinstance(raw, list) or len(raw) > MAX_EDGES:
        raise ValueError('edges must be a bounded list')
    out = [0] * n
    enabled = [0] * n
    records = []
    for row in raw:
        if not isinstance(row, list) or len(row) != 4 or type(row[3]) is not bool:
            raise ValueError('edge must be [source,target,mask,change_boolean]')
        u = _integer(row[0], 0, n-1, 'source')
        v = _integer(row[1], 0, n-1, 'target')
        mask = _integer(row[2], 0, full, 'mask')
        change = row[3]
        if change and u not in goals and v not in goals and not {u,v} <= set(ports):
            raise ValueError('every pending change endpoint must be a port')
        out[u] += 1
        enabled[u] |= mask
        records.append((u, v, mask, change))
    # Enabledness includes edges into the goal. It is never recomputed after deletion.
    edges = [Edge(u, v, mask if mode == 'justice' else mask | (full ^ enabled[u]), c)
             for u, v, mask, c in records]
    # Totalize only true deadlocks of the original model, never goal-deletion sinks.
    for u in range(n):
        if out[u] == 0:
            edges.append(Edge(u, u, full, False))
    return Graph(n, k, tuple(edges), initial, goals, ports)


def strict_json(raw: bytes | str) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    def constant(value):
        raise ValueError('non-finite JSON number')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def load(path: str | Path) -> Graph:
    with Path(path).open('rb') as handle:
        raw = handle.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('input exceeds byte limit')
    return parse(strict_json(raw))
