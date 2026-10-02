"""Untrusted interface and certificate synthesis using graph searches and SCCs."""
from __future__ import annotations
from collections import deque
from model import Graph


def reach(starts, adjacency):
    seen = set(starts)
    todo = list(sorted(seen))
    while todo:
        for v in adjacency.get(todo.pop(), ()):
            if v not in seen:
                seen.add(v)
                todo.append(v)
    return seen


def components(vertices, edges):
    # Iterative Kosaraju; no dependence on Python recursion limits.
    vertices = set(vertices)
    adj = {u: [] for u in vertices}
    rev = {u: [] for u in vertices}
    for u, v, *_ in edges:
        if u in vertices and v in vertices:
            adj[u].append(v)
            rev[v].append(u)
    seen, order = set(), []
    for root in sorted(vertices):
        if root in seen:
            continue
        seen.add(root)
        stack = [(root, iter(adj[root]))]
        while stack:
            u, it = stack[-1]
            v = next(it, None)
            if v is None:
                order.append(u)
                stack.pop()
            elif v not in seen:
                seen.add(v)
                stack.append((v, iter(adj[v])))
    seen, result = set(), []
    for root in reversed(order):
        if root in seen:
            continue
        block, todo = [], [root]
        seen.add(root)
        while todo:
            u = todo.pop()
            block.append(u)
            for v in rev[u]:
                if v not in seen:
                    seen.add(v)
                    todo.append(v)
        result.append(sorted(block))
    return result  # condensation order: source blocks precede target blocks


def summarize(g: Graph) -> dict:
    ports = set(g.ports)
    inside = set(g.remaining) - ports
    ordinary = [(i,e) for i,e in g.pending_edges() if not e.change]
    forward, backward = {}, {}
    ja, jr = {u: [] for u in inside}, {u: [] for u in inside}
    for _, e in ordinary:
        if e.src in inside and e.dst in inside:
            ja[e.src].append(e.dst)
            jr[e.dst].append(e.src)
    for p in g.ports:
        forward[p] = reach([e.dst for _,e in ordinary if e.src == p and e.dst in inside], ja)
        backward[p] = reach([e.src for _,e in ordinary if e.dst == p and e.src in inside], jr)
    arcs = []
    for p in g.ports:
        for q in g.ports:
            exist, mask = False, 0
            for _, e in ordinary:
                if (e.src == p or e.src in forward[p]) and (e.dst == q or e.dst in backward[q]):
                    exist = True
                    mask |= e.color
            if exist:
                arcs.append([p,q,mask,False])
    changes = {}
    for _,e in g.pending_edges():
        if e.change:
            key = (e.src,e.dst)
            changes[key] = changes.get(key,0) | e.color
    arcs += [[p,q,m,True] for (p,q),m in sorted(changes.items())]
    arcs.sort(key=lambda row:(row[0],row[1],row[3]))
    iedges = [(e.src,e.dst,e.color) for _,e in ordinary if e.src in inside and e.dst in inside]
    blocks = components(inside, iedges)
    owner = {u:j for j,block in enumerate(blocks) for u in block}
    masks = [0]*len(blocks)
    cyclic = [False]*len(blocks)
    for u,v,mask in iedges:
        if owner[u] == owner[v]:
            j=owner[u];masks[j] |= mask;cyclic[j]=True
    accepting = {u for u in inside if cyclic[owner[u]] and masks[owner[u]] == g.full}
    # Hidden divergence at p must take its first edge into the interior and
    # thereafter remain there.  forward[p] is seeded only by p->inside edges and
    # closes only over inside->inside edges, so another port can never be crossed.
    divergence = [p for p in g.ports if forward[p] & accepting]
    return {'arcs':arcs, 'divergence':divergence}


def path_edges(g: Graph, start: int, target: int, allowed=None, ordinary=False,
               first_return=False, bit=None) -> list[int]:
    """A nonempty first-return path, or ordinary possibly empty reachability path."""
    allowed = set(g.remaining) if allowed is None else set(allowed)
    adj = {}
    for i,e in g.pending_edges():
        if e.src in allowed and e.dst in allowed and not (ordinary and e.change):
            adj.setdefault(e.src,[]).append((i,e))
    need = bit is not None
    initial = (start, False)
    todo, pred = deque([initial]), {initial:None}
    if start == target and not need and not first_return:
        return []
    end = None
    while todo and end is None:
        node, seenbit = todo.popleft()
        for i,e in adj.get(node,[]):
            yes = seenbit or (need and bool(e.color & (1 << bit)))
            state = (e.dst, bool(yes))
            if e.dst == target and (not need or yes):
                # Closing path can return to the initial BFS state.
                trail, cur = [i], (node,seenbit)
                while pred[cur] is not None:
                    prev, edgeid = pred[cur]
                    trail.append(edgeid)
                    cur = prev
                return list(reversed(trail))
            if first_return and e.dst in g.ports:
                continue
            if state not in pred:
                pred[state] = ((node,seenbit),i)
                todo.append(state)
    raise ValueError('requested path does not exist')


def concrete_lasso(g: Graph, summary: dict, reached: set[int], finite_changes: bool) -> dict:
    """Construct a concrete lasso; no shortest-witness claim is made."""
    ordinary = [(i,e) for i,e in g.pending_edges() if not e.change]
    inside = set(g.remaining) - set(g.ports)
    iadj = {u:[] for u in inside}
    for _,e in ordinary:
        if e.src in inside and e.dst in inside:
            iadj[e.src].append(e.dst)
    fulladj = {u:[] for u in g.remaining}
    for _,e in g.pending_edges():
        fulladj[e.src].append(e.dst)
    original_reach = reach([i for i in g.initial if i not in g.goals],fulladj)
    iedges = [(e.src,e.dst,e.color) for _,e in ordinary if e.src in inside and e.dst in inside]
    internal_good = None
    for block in components(inside,iedges):
        b = set(block)
        es = [(i,e) for i,e in ordinary if e.src in b and e.dst in b]
        mask=0
        for _,e in es: mask |= e.color
        if es and mask == g.full and b & original_reach:
            internal_good=(b,es)
            break
    if internal_good:
        block,es=internal_good
        anchor=min(block)
        selected=[]
        if g.k:
            for f in range(g.k): selected.append(next((i,e) for i,e in es if e.color & (1<<f)))
        else: selected=[es[0]]
        loop=[]
        for i,e in selected:
            loop += path_edges(g,anchor,e.src,block,ordinary=True)
            loop += [i]
            loop += path_edges(g,e.dst,anchor,block,ordinary=True)
    else:
        arcs=[a for a in summary['arcs'] if a[0] in reached and a[1] in reached
              and not (finite_changes and a[3])]
        chosen=None
        for block in components(reached,arcs):
            b=set(block)
            es=[a for a in arcs if a[0] in b and a[1] in b]
            mask=0
            for a in es: mask |= a[2]
            if es and mask == g.full:
                chosen=(b,es)
                break
        if chosen is None: raise ValueError('no negative lasso')
        block,es=chosen
        anchor=min(block)
        def route(s,t):
            if s == t: return []
            todo=deque([s]); pred={s:None}
            while todo:
                u=todo.popleft()
                for a in es:
                    if a[0] == u and a[1] not in pred:
                        pred[a[1]]=(u,a)
                        if a[1] == t:
                            result=[]; cur=t
                            while pred[cur] is not None:
                                prev,arc=pred[cur]; result.append(arc); cur=prev
                            return list(reversed(result))
                        todo.append(a[1])
            raise ValueError('component route absent')
        def expand(a,f=None):
            if a[3]:
                return [next(i for i,e in g.pending_edges() if e.change and e.src==a[0]
                             and e.dst==a[1] and (f is None or e.color & (1<<f)))]
            return path_edges(g,a[0],a[1],ordinary=True,first_return=True,bit=f)
        loop=[]
        selected=[(next(a for a in es if a[2] & (1<<f)),f) for f in range(g.k)] if g.k else [(es[0],None)]
        for a,f in selected:
            for b in route(anchor,a[0]): loop += expand(b)
            loop += expand(a,f)
            for b in route(a[1],anchor): loop += expand(b)
    prefix=None
    start=None
    for s in g.initial:
        if s in g.goals: continue
        try:
            prefix=path_edges(g,s,anchor)
            start=s
            break
        except ValueError: pass
    if prefix is None: raise ValueError('lasso unreachable')
    return {'start':start,'prefix':prefix,'cycle':loop}


def produce(g: Graph, finite_changes=False) -> dict:
    summary=summarize(g)
    adjacency={p:[] for p in g.ports}
    for u,v,_,_ in summary['arcs']: adjacency[u].append(v)
    reached=reach([s for s in g.initial if s not in g.goals],adjacency)
    suffix=[a for a in summary['arcs'] if a[0] in reached and a[1] in reached
            and not (finite_changes and a[3])]
    blocks=components(reached,suffix)
    records=[]
    bad=bool(reached & set(summary['divergence']))
    for idx,block in enumerate(blocks):
        b=set(block)
        es=[a for a in suffix if a[0] in b and a[1] in b]
        mask=0
        for a in es: mask |= a[2]
        if es and mask == g.full: bad=True
        if not es:
            records.append({'vertices':block,'rank':len(blocks)-idx,'empty':True})
        elif mask != g.full:
            missing=next(f for f in range(g.k) if not mask & (1<<f))
            records.append({'vertices':block,'rank':len(blocks)-idx,'missing':missing})
    answer={'mode':'finite-changes' if finite_changes else 'arbitrary-changes',
            'summary':summary,'live':not bad}
    if bad: answer['witness']=concrete_lasso(g,summary,reached,finite_changes)
    else: answer['blocks']=records
    return answer
