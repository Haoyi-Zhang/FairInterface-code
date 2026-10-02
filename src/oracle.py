"""Small exact oracle: exhaustive reachable (vertex, accumulated-mask) loops.

This deliberately does not import producer/checker and does not use SCCs or
boundary summaries. It is exponential in task count, bounded to tiny instances.
"""
from collections import deque
from model import Graph


def fair_bad_run(g: Graph, finite_changes=False) -> bool:
    if g.n*(1<<g.k)>8192:
        raise ValueError('small-oracle state budget exceeded')
    todo=deque(s for s in g.initial if s not in g.goals)
    reachable=set(todo)
    pending=g.pending_edges()
    adj={u:[] for u in g.remaining}
    for _,e in pending: adj[e.src].append(e)
    while todo:
        u=todo.popleft()
        for e in adj[u]:
            if e.dst not in reachable:
                reachable.add(e.dst); todo.append(e.dst)
    for anchor in sorted(reachable):
        todo=deque([(anchor,0)])
        seen={(anchor,0)}
        while todo:
            u,mask=todo.popleft()
            for e in adj[u]:
                if finite_changes and e.change: continue
                newmask=mask|e.color
                if e.dst==anchor and newmask==g.full: return True
                item=(e.dst,newmask)
                if item not in seen:
                    seen.add(item); todo.append(item)
    return False


def strong_bad_run(data: dict) -> bool:
    """Tiny raw-service Streett oracle used ONLY for the boundary counterexample."""
    n,k=data['states'],data['tasks']
    if n*(4**k)>8192: raise ValueError('Streett test budget exceeded')
    enabled=[0]*n; outgoing=[0]*n
    for u,v,m,c in data['edges']:
        enabled[u] |= m; outgoing[u]+=1
    es=[tuple(row) for row in data['edges']]
    es += [(u,u,0,False) for u in range(n) if outgoing[u]==0]
    goals=set(data['goals'])
    adj={u:[] for u in range(n) if u not in goals}
    for u,v,m,c in es:
        if u not in goals and v not in goals: adj[u].append((v,m))
    reached=set(data['initial'])-goals; todo=list(reached)
    while todo:
        for v,m in adj[todo.pop()]:
            if v not in reached: reached.add(v);todo.append(v)
    for anchor in sorted(reached):
        todo=deque([(anchor,0,0)]);seen=set(todo)
        while todo:
            u,en,sv=todo.popleft()
            for v,m in adj[u]:
                newen=en|enabled[u];newsv=sv|m
                if v==anchor and (newen & ~newsv)==0: return True
                item=(v,newen,newsv)
                if item not in seen: seen.add(item);todo.append(item)
    return False
