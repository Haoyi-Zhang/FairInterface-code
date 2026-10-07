"""MIT: finite reachability conformance with a test-local subset oracle.

Standalone stdlib; no private paths, producer reach helper or old checker copy.
"""
from copy import deepcopy
from itertools import product
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import model
import checker
import producer
import interfaces
import raw_oracle
import summary_oracle


def declaration(n, k, edges, ports, initial=(0,), goals=None, coloring='weak-service'):
    return dict(states=n,tasks=k,edges=[list(e) for e in edges],ports=list(ports),
                initial=list(initial),goals=[n-1] if goals is None else list(goals),coloring=coloring)


def tiny_domain():
    options=(None,(0,False),(1,False),(0,True),(1,True))
    for choices in product(options,repeat=4):
        es=[]
        for (u,v), option in zip(product(range(2),repeat=2),choices):
            if option is not None: es.append([u,v,*option])
        for goal_edges in product((False,True),repeat=2):
            rows=es+[[u,2,1,False] for u,yes in enumerate(goal_edges) if yes]
            for coloring in ('weak-service','justice'):
                yield declaration(3,1,rows,(0,1),coloring=coloring)


def closure(vertices, edges):
    # Literal Boolean matrix closure, rather than a reachability worklist.
    r={(u,v):u==v for u in vertices for v in vertices}
    for u,v,_,_ in edges:
        if u in vertices and v in vertices:r[u,v]=True
    for w in vertices:
        for u in vertices:
            for v in vertices:r[u,v]=r[u,v] or (r[u,w] and r[w,v])
    return r


def subset_bad(data, finite):
    """Independent raw admission/deadlocks and exhaustive recurrent subsets."""
    n=data['states']; full=(1<<data['tasks'])-1
    enabled=[0]*n; outgoing=[False]*n
    es=[tuple(row) for row in data['edges']]
    for u,_,m,_ in es:enabled[u]|=m;outgoing[u]=True
    es += [(u,u,0 if data['coloring']=='weak-service' else full,False)
           for u in range(n) if not outgoing[u]]
    pending=[u for u in range(n) if u not in data['goals']]
    es=[e for e in es if e[0] in pending and e[1] in pending]
    prefix=closure(pending,es)
    initials=set(data['initial'])-set(data['goals'])
    reached={v for v in pending if any(prefix[s,v] for s in initials)}
    for mask in range(1,1<<len(pending)):
        vertices=[u for i,u in enumerate(pending) if mask>>i&1]
        if not set(vertices)&reached:continue
        inside=[e for e in es if e[0] in vertices and e[1] in vertices and not (finite and e[3])]
        r=closure(vertices,inside)
        if not inside or not all(r[u,v] for u in vertices for v in vertices):continue
        served=0
        for _,_,m,_ in inside:served|=m
        if data['coloring']=='justice':
            fair=served==full
        else:
            always=full
            for u in vertices:always &= enabled[u]
            fair=always & ~served == 0
        if fair:return True
    return False


def boundary_models():
    # Both chains order their endpoint IDs differently, with disconnected ports.
    for size in (2,8,32):
        for reverse in (False,True):
            ids=list(range(size))
            if reverse:ids.reverse()
            es=[[u,v,1,bool(i%2)] for i,(u,v) in enumerate(zip(ids,ids[1:]))]
            es += [[ids[-1],size+1,1,False],[size,size,0,False]]
            yield declaration(size+2,1,es,tuple(range(size+1)),initial=(ids[0],))
    for reachable in (False,True):
        es=[[0,4,1,False],[1,2,0,False],[2,3,0,False],[3,3,0,False]]
        if reachable:es.append([0,1,0,True])
        yield declaration(5,1,es,(0,1,2))
    for k in (0,2):
        full=(1<<k)-1
        yield declaration(3,k,[],(0,1))
        yield declaration(3,k,[[0,2,full,False],[1,1,0,False]],(0,1))
        yield declaration(3,k,[[0,1,full,True],[1,0,full,True],
                               [0,2,full,False],[1,2,full,False]],(0,1))
        yield declaration(3,k,[],(),initial=())
        yield declaration(3,k,[],(),initial=(2,))


class ReachabilityRegression(unittest.TestCase):
    def test_literal_tiny_domain(self):
        for data in tiny_domain():
            graph=model.parse(data)
            for finite in (False,True):
                cert=producer.produce(graph,finite)
                self.assertEqual(cert['live'],not subset_bad(data,finite))
                self.assertTrue(checker.verify(graph,cert))
                self.assertEqual(cert['summary'],summary_oracle.exact_summary(graph))

    def test_boundaries_and_diagnostics(self):
        for data in boundary_models():
            graph=model.parse(data)
            for finite in (False,True):
                cert=producer.produce(graph,finite)
                self.assertEqual(cert['live'],not raw_oracle.raw_fair_bad_run(data,finite))
                self.assertTrue(checker.verify(graph,cert))
                self.assertEqual(cert['summary'],summary_oracle.exact_summary(graph))
                missing=deepcopy(cert)
                if missing['summary']['arcs']:
                    missing['summary']['arcs'].pop()
                    with self.assertRaisesRegex(ValueError,'^summary does not match the input model$'):
                        checker.verify(graph,missing)
        # A marked-only prefix still reaches divergence in finite-change mode.
        data=next(d for d in boundary_models() if d['states']==5 and len(d['edges'])==5)
        graph=model.parse(data)
        summary=checker.reference_summary(graph)
        bad=dict(mode='finite-changes',summary=summary,live=True,blocks=[])
        with self.assertRaisesRegex(ValueError,'^reachable hidden fair divergence$'):
            checker.verify(graph,bad)
        # Replay is earlier than positive block inspection, also with malformed blocks.
        bad['summary']=deepcopy(summary);bad['summary']['arcs'][0][2]^=1;bad['blocks']=None
        with self.assertRaisesRegex(ValueError,'^summary does not match the input model$'):
            checker.verify(graph,bad)
        large=declaration(128,8,[],tuple(range(64)))
        with self.assertRaisesRegex(ValueError,'^raw-semantics oracle state budget exceeded$'):
            raw_oracle.raw_fair_bad_run(large)

    def test_join_and_fresh_graphs(self):
        a=declaration(5,1,[[0,2,0,False],[2,1,1,False]],(0,1))
        b=declaration(5,1,[[1,3,0,False],[3,0,1,False],[0,4,1,False]],(0,1))
        for family in ([a,b],[b,a],[dict(a,edges=a['edges']+[[2,2,0,False]]),b]):
            graph,bound=interfaces.bind(family)
            self.assertEqual(bound,checker.reference_summary(graph))
            self.assertEqual(bound,summary_oracle.exact_summary(graph))
            for finite in (False,True):self.assertTrue(checker.verify(graph,producer.produce(graph,finite)))
        # Mutating a raw declaration between calls does not reuse an old index.
        d=declaration(3,1,[[0,2,1,False]],(0,1))
        self.assertTrue(producer.produce(model.parse(d))['live'])
        d['edges'].append([0,1,0,True])
        graph=model.parse(d)
        self.assertFalse(producer.produce(graph,True)['live'])
        self.assertTrue(checker.verify(graph,producer.produce(graph,True)))


if __name__=='__main__':unittest.main(verbosity=2)
