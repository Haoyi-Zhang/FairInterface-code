"""Deterministic, benign finite models. No external inputs or protocol execution."""
from __future__ import annotations
from itertools import combinations


def model(n,k,edges,ports=(0,),initial=(0,),goals=None,mode='weak-service',description=''):
    return {'states':n,'tasks':k,'coloring':mode,'edges':[list(e) for e in edges],
            'initial':list(initial),'goals':[n-1] if goals is None else list(goals),
            'ports':list(ports),'description':description}


def role_model(reset=True):
    # Honest vote sets differ with configuration, not merely the leader name.
    roles=[{'members':[0,1,2,3],'faults':[3],'honest':[0,1,2]},
           {'members':[1,2,3,4],'faults':[4],'honest':[1,2,3]}]
    states=[(r,mask) for r in range(2) for mask in range(8) if mask!=7]
    index={s:i for i,s in enumerate(states)};goal=len(states);es=[]
    for (r,mask),u in index.items():
        hs=roles[r]['honest']
        for pos,task in enumerate(hs):
            if not (mask>>pos)&1:
                newer=mask|(1<<pos)
                es.append([u,goal if newer==7 else index[(r,newer)],1<<task,False])
        es.append([u,u,0,False])  # arbitrary modeled non-progress action
        if reset:
            es.append([u,index[(1-r,0)],0,True])
    ports=tuple(range(goal)) if reset else (index[(0,0)],index[(1,0)])
    d=model(goal+1,5,es,ports,initial=(0,),description='Two 3-of-4 configurations, one Byzantine member each; honest votes only; reset on change.')
    d['role_metadata']={'roles':roles,'threshold':3,'states':[[r,m] for r,m in states],
        'interpretation':'finite vote collector; no agreement, authentication or deployed protocol claim'}
    return d



def expanded_role_model():
    """Scheduler-expanded finite refinement of the 15-state vote-reset fixture.

    Every pending abstract state has two concrete scheduler phases.  Abstract
    steps are duplicated in both phases, and a task-free phase-toggle step maps
    to the abstract task-free self-loop already present at each pending state.
    This is a synthetic refinement fixture, not a protocol implementation.
    """
    abstract = role_model(True)
    abstract_goal = abstract['goals'][0]
    concrete_goal = 2 * abstract_goal
    edges = []
    for source, target, services, change in abstract['edges']:
        for phase in (0, 1):
            csource = 2 * source + phase
            ctarget = concrete_goal if target == abstract_goal else 2 * target + phase
            edges.append([csource, ctarget, services, change])
    for state in range(abstract_goal):
        edges.append([2 * state, 2 * state + 1, 0, False])
        edges.append([2 * state + 1, 2 * state, 0, False])
    concrete = model(concrete_goal + 1, abstract['tasks'], edges,
                     ports=tuple(range(concrete_goal)), initial=(0,),
                     goals=(concrete_goal,),
                     description=('Scheduler-expanded refinement of role-reset; '
                                  'two metadata phases per pending state.'))
    concrete['role_metadata'] = {
        'source_fixture': 'role-reset',
        'scheduler_phases': 2,
        'interpretation': ('synthetic finite refinement witness only; no code, '
                           'network, authentication, or deployed protocol claim'),
    }
    mapping = [state // 2 for state in range(concrete_goal)] + [abstract_goal]
    return concrete, abstract, mapping


def named():
    cases={
      'goal-enabled':model(2,1,[(0,0,0,False),(0,1,1,False)]),
      'true-deadlock':model(2,1,[]),
      'goal-only-sink':model(2,1,[(0,1,1,False)]),
      'hidden-divergence':model(3,1,[(0,1,0,False),(0,2,1,False),(1,1,0,False)]),
      'no-fair-path':model(2,1,[(0,0,0,False)],goals=(1,),mode='justice'),
      'zero-task-cycle':model(2,0,[(0,0,0,False)]),
      'goal-initial':model(2,1,[(0,1,1,False)],ports=(),initial=(1,)),
      'empty-initial':model(2,1,[],ports=(),initial=()),
      'nonjoint-capacity':model(5,2,[(0,1,1,False),(1,3,0,False),(0,2,2,False),(2,3,0,False),(3,0,0,False)],ports=(0,3),mode='justice'),
      'one-shot-ports':model(3,1,[(0,1,1,False),(1,2,1,False)],ports=(0,1),mode='justice'),
      'change-only-cycle':model(3,1,[(0,1,1,True),(1,0,1,True),(0,2,1,False),(1,2,1,False)],ports=(0,1),mode='justice'),
      'role-reset':role_model(True),
      'role-static':role_model(False),
    }
    return cases


def strong_modules():
    # Ports p=0,q=1; interior w=2,u=3,v=4; goal=5.
    base=model(6,1,[(0,2,0,False),(2,3,0,False),(3,1,0,False),(3,5,1,False)],ports=(0,1))
    bypass={**base,'edges':base['edges']+[[2,4,0,False],[4,1,0,False]]}
    context=model(6,1,[(1,0,0,False)],ports=(0,1))
    return base,bypass,context


class Stream:
    """Specified 64-bit LCG, used only for structural variety, not sampling claims."""
    def __init__(self,seed): self.state=seed
    def take(self,n):
        self.state=(6364136223846793005*self.state+1442695040888963407)&((1<<64)-1)
        return (self.state>>32)%n


def random_closed(count=512,seed=12648430):
    rng=Stream(seed)
    for _ in range(count):
        n=4+rng.take(9);k=rng.take(5);es=[];ports={0}
        for u in range(n-1):
            for v in range(n):
                if rng.take(5)==0:
                    c=(v!=n-1 and rng.take(5)==0)
                    if c: ports.update((u,v))
                    es.append([u,v,rng.take(1<<k),c])
        yield model(n,k,es,tuple(sorted(ports)))


def random_families(count=256,seed=195936478):
    rng=Stream(seed)
    for _ in range(count):
        m=2+rng.take(2);n=2+2*m+1;k=rng.take(4);family=[]
        for j in range(m):
            vertices=(0,1,2+2*j,3+2*j);es=[]
            for u in vertices:
                for v in (*vertices,n-1):
                    if rng.take(3)==0:
                        c=u<2 and v<2 and rng.take(4)==0
                        es.append([u,v,rng.take(1<<k),c])
            family.append(model(n,k,es,ports=(0,1)))
        yield family


def quorum_obligations(data):
    meta=data['role_metadata'];answer=[]
    for r in meta['roles']:
        qs=[set(x) for x in combinations(r['members'],meta['threshold'])]
        honest=set(r['members'])-set(r['faults'])
        answer.append({'honest_quorum_available':any(q<=honest for q in qs),
            'min_honest_intersection':min(len(a&b&honest) for a in qs for b in qs)})
    return answer
