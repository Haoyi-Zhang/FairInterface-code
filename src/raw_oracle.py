"""Independent bounded oracle for the *raw* input semantics.

Unlike :mod:`model`, this module does not construct justice-coloured edges.  For
``weak-service`` inputs it checks weak fairness directly on a non-empty closed
walk: every task enabled at every source state of the walk must be served by at
least one edge of the walk.  Goal deletion and true-deadlock totalisation are
implemented locally so that this oracle can expose errors in the shared input
normalisation used by the producer, checker, and coloured whole-graph oracle.

The construction is exponential in the number of tasks and is intentionally
bounded to small validation instances.
"""
from __future__ import annotations

from collections import deque


def _bounded_raw(data: dict) -> tuple[int, int, int, str, set[int], set[int], list[tuple[int, int, int, bool]]]:
    """Read the small trusted-campaign subset without importing ``model.parse``."""
    if type(data) is not dict:
        raise ValueError('raw oracle expects a model dictionary')
    n=data.get('states');k=data.get('tasks');mode=data.get('coloring')
    if type(n) is not int or type(k) is not int or not (1 <= n <= 128) or not (0 <= k <= 8):
        raise ValueError('raw oracle dimension out of range')
    if mode not in ('weak-service','justice'):
        raise ValueError('unsupported raw colouring mode')
    full=(1<<k)-1
    initial=data.get('initial');goals=data.get('goals');raw=data.get('edges')
    if not isinstance(initial,list) or not isinstance(goals,list) or not isinstance(raw,list):
        raise ValueError('raw oracle expects list-valued initial, goals, and edges')
    initials=set()
    goal_set=set()
    for value,target,name in ((initial,initials,'initial'),(goals,goal_set,'goals')):
        for item in value:
            if type(item) is not int or not 0 <= item < n:
                raise ValueError(f'raw oracle invalid {name} state')
            target.add(item)
    records=[]
    for row in raw:
        if not isinstance(row,list) or len(row)!=4 or type(row[3]) is not bool:
            raise ValueError('raw oracle invalid edge record')
        u,v,mask,change=row
        if (type(u) is not int or type(v) is not int or type(mask) is not int or
                not 0 <= u < n or not 0 <= v < n or not 0 <= mask <= full):
            raise ValueError('raw oracle edge field out of range')
        records.append((u,v,mask,change))
    return n,k,full,mode,initials,goal_set,records


def raw_fair_bad_run(data: dict, finite_changes: bool=False) -> bool:
    """Return whether the raw model has a weakly fair goal-avoiding run.

    Prefix reachability may use marked edges in both modes.  In the
    finite-change mode only the recurrent closed walk must be unmarked, exactly
    matching the paper's eventual ordinary-suffix semantics.
    """
    n,k,full,mode,initials,goals,records=_bounded_raw(data)
    # A weak-service product needs an enabled-intersection and service-union;
    # a justice input needs only the colour union.  Keep the common bound small.
    product_factor=4**k if mode=='weak-service' else 2**k
    if n*product_factor>32768:
        raise ValueError('raw-semantics oracle state budget exceeded')

    outgoing=[0]*n
    enabled=[0]*n
    for u,_,mask,_ in records:
        outgoing[u]+=1
        if mode=='weak-service':
            enabled[u]|=mask

    # Totalise only genuine raw deadlocks.  For weak-service semantics the
    # stutter serves nothing; fairness is nevertheless vacuous because no task
    # is enabled.  Justice inputs use the already-normalised all-colour stutter.
    edges=list(records)
    deadlock_mask=0 if mode=='weak-service' else full
    edges.extend((u,u,deadlock_mask,False) for u in range(n) if outgoing[u]==0)

    adj={u:[] for u in range(n) if u not in goals}
    for edge in edges:
        u,v,_,_=edge
        if u not in goals and v not in goals:
            adj[u].append(edge)

    reachable=set(initials)-goals
    todo=deque(reachable)
    while todo:
        u=todo.popleft()
        for _,v,_,_ in adj[u]:
            if v not in reachable:
                reachable.add(v);todo.append(v)

    for anchor in sorted(reachable):
        if mode=='weak-service':
            # ``always`` is the intersection of raw enabled masks at source
            # states visited by the non-empty closed walk; ``served`` is the
            # union of raw service masks on its edges.
            start=(anchor,full,0)
            todo=deque([start]);seen={start}
            while todo:
                u,always,served=todo.popleft()
                for _,v,service,change in adj[u]:
                    if finite_changes and change:
                        continue
                    new_always=always & enabled[u]
                    new_served=served | service
                    if v==anchor and (new_always & ~new_served)==0:
                        return True
                    item=(v,new_always,new_served)
                    if item not in seen:
                        seen.add(item);todo.append(item)
        else:
            start=(anchor,0)
            todo=deque([start]);seen={start}
            while todo:
                u,covered=todo.popleft()
                for _,v,colour,change in adj[u]:
                    if finite_changes and change:
                        continue
                    new_covered=covered|colour
                    if v==anchor and new_covered==full:
                        return True
                    item=(v,new_covered)
                    if item not in seen:
                        seen.add(item);todo.append(item)
    return False
