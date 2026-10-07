"""Certificate checking. Does not import producer or use its searches/SCC routine."""
from __future__ import annotations
from model import Graph


def reference_summary(g: Graph) -> dict:
    # Vertex elimination over the interior, using snapshots at every elimination.
    # The mask is a UNION over possible paths, not a jointly-realizable path mask.
    n=g.n
    reach=[[False]*n for _ in range(n)]
    color=[[0]*n for _ in range(n)]
    for u in g.remaining: reach[u][u]=True
    ordinary=[e for _,e in g.pending_edges() if not e.change]
    for e in ordinary:
        reach[e.src][e.dst]=True
        color[e.src][e.dst] |= e.color
    # Preserve positive one-edge reachability separately from reflexive closure.
    direct=[[False]*n for _ in range(n)]
    for e in ordinary: direct[e.src][e.dst]=True
    interior=sorted(set(g.remaining)-set(g.ports))
    for w in interior:
        oldr=[row[:] for row in reach]
        oldc=[row[:] for row in color]
        for u in g.remaining:
            if not oldr[u][w]: continue
            for v in g.remaining:
                if oldr[w][v]:
                    reach[u][v]=True
                    color[u][v] |= oldc[u][w] | oldc[w][w] | oldc[w][v]
    arcs=[]
    for p in g.ports:
        for q in g.ports:
            # Zero paths were used for closure; remove them from exported edges.
            positive=direct[p][q] or any(direct[p][v] and reach[v][q] for v in interior)
            if positive: arcs.append([p,q,color[p][q],False])
    changes={}
    for _,e in g.pending_edges():
        if e.change:
            changes[(e.src,e.dst)]=changes.get((e.src,e.dst),0)|e.color
    arcs += [[p,q,m,True] for (p,q),m in sorted(changes.items())]
    arcs.sort(key=lambda row:(row[0],row[1],row[3]))
    # Mutual reachability supplies equivalence classes without the producer's SCC code.
    groups=[];owner={}
    for u in interior:
        if u in owner: continue
        group={v for v in interior if reach[u][v] and reach[v][u]}
        for v in group: owner[v]=len(groups)
        groups.append(group)
    masks=[0]*len(groups);cyclic=[False]*len(groups)
    for e in ordinary:
        if e.src in owner and e.dst in owner and owner[e.src]==owner[e.dst]:
            j=owner[e.src];masks[j] |= e.color;cyclic[j]=True
    good={u for u in interior if cyclic[owner[u]] and masks[owner[u]]==g.full}
    # Require the first step after p to enter the interior, then use only
    # interior-eliminated reachability.  A route p->q->... through another port
    # is represented by the p->q summary arc plus divergence at q, not at p.
    divergence=[]
    for p in g.ports:
        entries={e.dst for e in ordinary if e.src==p and e.dst in owner}
        if any(reach[entry][v] for entry in entries for v in good):
            divergence.append(p)
    return {'arcs':arcs, 'divergence':divergence}


def check_lasso(g: Graph, witness: dict, finite: bool) -> None:
    if type(witness) is not dict or set(witness)!={'start','prefix','cycle'}:
        raise ValueError('malformed witness')
    s=witness['start']
    if type(s) is not int or s not in g.initial or s in g.goals:
        raise ValueError('witness start is not a pending initial state')
    for part in ('prefix','cycle'):
        xs=witness[part]
        if not isinstance(xs,list) or len(xs)>1_000_000:
            raise ValueError('unbounded witness sequence')
        if any(type(i) is not int or not 0<=i<len(g.edges) for i in xs):
            raise ValueError('invalid witness edge')
    if not witness['cycle']: raise ValueError('empty recurrence witness')
    u=s
    for i in witness['prefix']:
        e=g.edges[i]
        if e.src!=u or e.dst in g.goals: raise ValueError('invalid prefix')
        u=e.dst
    anchor=u
    mask=0
    for i in witness['cycle']:
        e=g.edges[i]
        if e.src!=u or e.dst in g.goals or (finite and e.change):
            raise ValueError('invalid cycle')
        mask |= e.color
        u=e.dst
    if u!=anchor or mask!=g.full: raise ValueError('cycle is not closed and fair')


def verify(g: Graph, cert: dict) -> bool:
    if type(cert) is not dict or cert.get('mode') not in ('arbitrary-changes','finite-changes'):
        raise ValueError('missing or invalid mode')
    if type(cert.get('live')) is not bool: raise ValueError('missing Boolean verdict')
    expected_keys={'mode','summary','live','blocks' if cert['live'] else 'witness'}
    if set(cert)!=expected_keys: raise ValueError('unexpected certificate fields')
    summary=cert['summary']
    if type(summary) is not dict or set(summary) != {'arcs','divergence'}:
        raise ValueError('malformed summary fields')
    if type(summary['arcs']) is not list or len(summary['arcs']) > 2*len(g.ports)**2:
        raise ValueError('unbounded arcs')
    for row in summary['arcs']:
        if (type(row) is not list or len(row)!=4 or
            any(type(x) is not int for x in row[:3]) or type(row[3]) is not bool):
            raise ValueError('malformed arc types')
    if (type(summary['divergence']) is not list or
        any(type(x) is not int for x in summary['divergence'])):
        raise ValueError('malformed divergence types')
    # Exact equality verifies both missing and spurious summary capabilities.
    if summary!=reference_summary(g): raise ValueError('summary does not match the input model')
    finite=cert['mode']=='finite-changes'
    if not cert['live']:
        check_lasso(g,cert['witness'],finite)
        return True
    ports=set(g.ports)
    reached=set(g.initial)-g.goals
    # Checker-owned, invocation-local prefix index, after exact summary replay.
    # Marked arcs remain admissible in a prefix even in finite-change mode.
    adjacency={}
    for u,v,_,_ in summary['arcs']:
        adjacency.setdefault(u,[]).append(v)
    pending=list(reached)
    while pending:
        for v in adjacency.get(pending.pop(),()):
            if v not in reached:
                reached.add(v)
                pending.append(v)
    if reached & set(summary['divergence']): raise ValueError('reachable hidden fair divergence')
    records=cert['blocks']
    if not isinstance(records,list) or len(records)>len(ports): raise ValueError('invalid blocks')
    owner={}
    ranks={}
    for j,block in enumerate(records):
        if not isinstance(block,dict): raise ValueError('malformed block')
        if set(block) not in ({'vertices','rank','empty'},{'vertices','rank','missing'}):
            raise ValueError('malformed block fields')
        xs=block['vertices']
        if not isinstance(xs,list) or not xs or len(xs)>len(ports): raise ValueError('empty/invalid block')
        if type(block['rank']) is not int or not 0<=block['rank']<=len(ports):
            raise ValueError('invalid condensation rank')
        for u in xs:
            if type(u) is not int or u not in reached or u in owner: raise ValueError('invalid block coverage')
            owner[u]=j
        ranks[j]=block['rank']
        if 'empty' in block and block['empty'] is not True: raise ValueError('invalid empty claim')
        if 'missing' in block and (type(block['missing']) is not int or not 0<=block['missing']<g.k):
            raise ValueError('invalid missing color')
    if set(owner)!=reached: raise ValueError('blocks do not cover reachable ports')
    for u,v,m,c in summary['arcs']:
        if u not in reached or (finite and c): continue
        a,b=owner[u],owner[v]
        if a!=b:
            if not ranks[a]>ranks[b]: raise ValueError('nondecreasing cross-block rank')
        else:
            block=records[a]
            if 'empty' in block: raise ValueError('edge in empty block')
            if m & (1<<block['missing']): raise ValueError('claimed missing color occurs')
    return True
