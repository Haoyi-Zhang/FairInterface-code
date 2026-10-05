"""One bounded deterministic campaign chunk; all experiment data are generated."""
from __future__ import annotations
import argparse,csv,itertools,json,resource,sys,time
from pathlib import Path
from model import Graph,Edge,parse
from producer import produce,summarize
from checker import verify,reference_summary
from oracle import fair_bad_run
from raw_oracle import raw_fair_bad_run
from summary_oracle import exact_summary
from interfaces import bind
from refinement import check_refinement
from fixtures import (named,random_closed,random_families,model,
                      quorum_obligations,expanded_role_model)


def evaluate(g,finite=False,oracle=True):
    certificate=produce(g,finite)
    verify(g,certificate)
    if certificate['summary'] != exact_summary(g):
        raise AssertionError('exact summary-oracle disagreement')
    product_used=False
    if oracle:
        product_used=True
        if certificate['live']==fair_bad_run(g,finite):
            raise AssertionError('whole-graph product-oracle disagreement')
    return certificate,product_used


def decode_edges(code, templates):
    """Three-way absent/service-0/service-1 ordinary edge encoding."""
    edges=[]
    for source,target in templates:
        option=code%3;code//=3
        if option:
            edges.append([source,target,option-1,False])
    return edges


def decode_mixed_edges(code, templates):
    """Five-way absent/ordinary-or-marked service-0-or-service-1 encoding."""
    options=(None,(0,False),(1,False),(0,True),(1,True))
    edges=[]
    for source,target in templates:
        option=options[code%5];code//=5
        if option is not None:
            services,change=option
            edges.append([source,target,services,change])
    return edges


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('kind',choices=['core','closed','modules','binding','refinement','transfer','raw','named','scaling'])
    ap.add_argument('--n',type=int,default=3);ap.add_argument('--start',type=int,default=0)
    ap.add_argument('--stop',type=int,default=19683);ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    tag=f'core-{args.n}-{args.start}-{args.stop}' if args.kind=='core' else args.kind
    began=time.perf_counter();cpu=time.process_time()
    count=0;verdicts=0;summary_cases=0;negative=0;product_checks=0;raw_checks=0
    rows=[];header=[];extra={}

    if args.kind=='core':
        n=args.n
        if n not in (2,3):raise ValueError('core dimension not in frozen campaign')
        k=2 if n==2 else 1;base=(1<<k)+1;limit=base**(n*n)
        if not 0<=args.start<=args.stop<=limit:raise ValueError('invalid enumeration range')
        for code in range(args.start,args.stop):
            rest=code;edges=[]
            for source,target in itertools.product(range(n),repeat=2):
                value=rest%base;rest//=base
                if value:edges.append(Edge(source,target,value-1))
            for port_mask in range(1,1<<n):
                ports=tuple(i for i in range(n) if port_mask&(1<<i))
                for initial in ports:
                    graph=Graph(n,k,tuple(edges),(initial,),frozenset(),ports)
                    certificate,used=evaluate(graph)
                    count+=1;verdicts+=1;summary_cases+=1;product_checks+=used
                    negative+=not certificate['live']
                    rows.append([code,port_mask,initial,int(certificate['live'])])
        header=['edge_encoding','port_bits','initial','live']

    elif args.kind in ('closed','modules'):
        models=random_closed() if args.kind=='closed' else random_families()
        with (args.out/(tag+'-inputs.jsonl')).open('w') as inputs:
            for index,data in enumerate(models):
                inputs.write(json.dumps(data,separators=(',',':'))+'\n')
                if args.kind=='closed':
                    graph=parse(data)
                else:
                    graph,bound=bind(data);_,independent=bind(data,independent=True)
                    exact=exact_summary(graph)
                    if bound!=independent or bound!=summarize(graph) or bound!=reference_summary(graph) or bound!=exact:
                        raise AssertionError('module composition mismatch')
                for finite in (False,True):
                    certificate,used=evaluate(graph,finite)
                    count+=1;verdicts+=1;summary_cases+=1;product_checks+=used
                    negative+=not certificate['live']
                    rows.append([index,graph.n,graph.k,len(graph.edges),len(graph.ports),
                                 int(finite),int(certificate['live'])])
        header=['case','states','tasks','normalized_edges','ports','finite_changes','live']

    elif args.kind=='binding':
        # Two private one-state interiors (2 and 3), exact ports 0 and 1, goal 4.
        # Each of ten template edges is absent, task-free, or task-serving.
        templates_a=[(0,2),(2,1),(2,2),(0,4),(1,0)]
        templates_b=[(0,3),(3,1),(3,3),(0,4),(1,0)]
        size=3**5
        for code_a in range(size):
            module_a=model(5,1,decode_edges(code_a,templates_a),ports=(0,1))
            for code_b in range(size):
                module_b=model(5,1,decode_edges(code_b,templates_b),ports=(0,1))
                graph,bound=bind([module_a,module_b])
                independent=reference_summary(graph)
                exact=exact_summary(graph)
                if bound!=summarize(graph) or bound!=independent or bound!=exact:
                    raise AssertionError('exhaustive late-binding mismatch')
                rows.append(['ordinary',code_a,code_b,len(bound['arcs']),len(bound['divergence'])])
                count+=1;summary_cases+=1
        # A second complete family puts goal edges behind private interiors and
        # uses opposite return directions.  It exercises first-return stopping,
        # hidden divergence, and goal observation at interior sources.
        goal_templates_a=[(0,2),(2,1),(2,2),(2,4)]
        goal_templates_b=[(1,3),(3,0),(3,3),(3,4)]
        goal_size=3**4
        for code_a in range(goal_size):
            module_a=model(5,1,decode_edges(code_a,goal_templates_a),ports=(0,1))
            for code_b in range(goal_size):
                module_b=model(5,1,decode_edges(code_b,goal_templates_b),ports=(0,1))
                graph,bound=bind([module_a,module_b])
                independent=reference_summary(graph)
                exact=exact_summary(graph)
                if bound!=summarize(graph) or bound!=independent or bound!=exact:
                    raise AssertionError('interior-goal late-binding mismatch')
                rows.append(['interior-goal',code_a,code_b,len(bound['arcs']),len(bound['divergence'])])
                count+=1;summary_cases+=1

        # A small complete cross-product adds marked/ordinary port connectors.
        connector_options=[None,(0,False),(1,False),(0,True),(1,True)]
        for index_a,option_a in enumerate(connector_options):
            for index_b,option_b in enumerate(connector_options):
                edge_a=[] if option_a is None else [[0,1,option_a[0],option_a[1]]]
                edge_b=[] if option_b is None else [[1,0,option_b[0],option_b[1]]]
                module_a=model(3,1,edge_a,ports=(0,1))
                module_b=model(3,1,edge_b,ports=(0,1))
                graph,bound=bind([module_a,module_b])
                if bound!=summarize(graph) or bound!=reference_summary(graph) or bound!=exact_summary(graph):
                    raise AssertionError('marked connector late-binding mismatch')
                rows.append(['connectors',index_a,index_b,len(bound['arcs']),len(bound['divergence'])])
                count+=1;summary_cases+=1
        header=['family','encoding_a','encoding_b','summary_arcs','divergence_ports']
        extra={'ordinary_template_cases':size*size,'interior_goal_cases':goal_size*goal_size,'marked_connector_cases':25}

    elif args.kind=='refinement':
        concrete,abstract,mapping=expanded_role_model()
        report=check_refinement(concrete,abstract,mapping)
        (args.out/'role-reset-expanded.json').write_text(json.dumps(concrete,indent=2)+'\n')
        (args.out/'role-reset-abstraction.json').write_text(json.dumps(abstract,indent=2)+'\n')
        (args.out/'role-reset-refinement.json').write_text(json.dumps(report,indent=2)+'\n')
        expected={False:False,True:True}
        for finite in (False,True):
            graph=parse(concrete);certificate,used=evaluate(graph,finite)
            if certificate['live']!=expected[finite]:
                raise AssertionError('expanded refinement fixture verdict changed')
            count+=1;verdicts+=1;summary_cases+=1;product_checks+=used
            negative+=not certificate['live']
            rows.append(['role-reset-expanded',graph.n,graph.k,len(graph.edges),
                         len(graph.ports),int(finite),int(certificate['live'])])
        header=['case','states','tasks','normalized_edges','ports','finite_changes','live']
        extra={'refinement_checks':1,'concrete_states':report['concrete_states'],
               'abstract_states':report['abstract_states'],
               'concrete_raw_edges':report['concrete_edges']}

    elif args.kind=='transfer':
        # Exhaustive tiny-model check of the executable transfer contract.
        # Ordinary family: two concrete pending phases map to one abstract
        # pending state.  Every listed edge is absent, task-free, or serving.
        ordinary_abstract_templates=[(0,0),(0,1)]
        ordinary_concrete_templates=[(0,0),(0,1),(0,2),(1,0),(1,1),(1,2)]
        ordinary_abstract=[]
        for code in range(3**len(ordinary_abstract_templates)):
            data=model(2,1,decode_edges(code,ordinary_abstract_templates),ports=(0,),goals=(1,))
            graph=parse(data);certificate,used=evaluate(graph,False)
            count+=0;verdicts+=1;summary_cases+=1;product_checks+=used
            negative+=not certificate['live']
            ordinary_abstract.append((data,certificate['live']))
        ordinary_concrete=[]
        for code in range(3**len(ordinary_concrete_templates)):
            data=model(3,1,decode_edges(code,ordinary_concrete_templates),ports=(0,1),goals=(2,))
            graph=parse(data);certificate,used=evaluate(graph,False)
            verdicts+=1;summary_cases+=1;product_checks+=used
            negative+=not certificate['live']
            ordinary_concrete.append((data,certificate['live']))
        ordinary_candidates=0;ordinary_accepted=0;ordinary_implications=0
        mapping=[0,0,1]
        for abstract_data,abstract_live in ordinary_abstract:
            for concrete_data,concrete_live in ordinary_concrete:
                ordinary_candidates+=1
                try:
                    check_refinement(concrete_data,abstract_data,mapping)
                except ValueError:
                    continue
                ordinary_accepted+=1;ordinary_implications+=1
                if abstract_live and not concrete_live:
                    raise AssertionError('ordinary transfer implication failed')

        # Marked family: cross-phase and goal edges independently choose absent,
        # ordinary/marked, and task-free/serving labels.  Both arbitrary- and
        # finite-change implications are checked for every accepted relation.
        mixed_abstract_templates=[(0,0),(0,1)]
        mixed_concrete_templates=[(0,1),(1,0),(0,2),(1,2)]
        mixed_abstract=[]
        for code in range(5**len(mixed_abstract_templates)):
            data=model(2,1,decode_mixed_edges(code,mixed_abstract_templates),ports=(0,),goals=(1,))
            lives=[]
            for finite in (False,True):
                graph=parse(data);certificate,used=evaluate(graph,finite)
                verdicts+=1;summary_cases+=1;product_checks+=used
                negative+=not certificate['live'];lives.append(certificate['live'])
            mixed_abstract.append((data,tuple(lives)))
        mixed_concrete=[]
        for code in range(5**len(mixed_concrete_templates)):
            data=model(3,1,decode_mixed_edges(code,mixed_concrete_templates),ports=(0,1),goals=(2,))
            lives=[]
            for finite in (False,True):
                graph=parse(data);certificate,used=evaluate(graph,finite)
                verdicts+=1;summary_cases+=1;product_checks+=used
                negative+=not certificate['live'];lives.append(certificate['live'])
            mixed_concrete.append((data,tuple(lives)))
        mixed_candidates=0;mixed_accepted=0;mixed_implications=0
        for abstract_data,abstract_lives in mixed_abstract:
            for concrete_data,concrete_lives in mixed_concrete:
                mixed_candidates+=1
                try:
                    check_refinement(concrete_data,abstract_data,mapping)
                except ValueError:
                    continue
                mixed_accepted+=1
                for index in (0,1):
                    mixed_implications+=1
                    if abstract_lives[index] and not concrete_lives[index]:
                        raise AssertionError('marked transfer implication failed')

        count=ordinary_candidates+mixed_candidates
        rows=[['ordinary',ordinary_candidates,ordinary_accepted,ordinary_implications],
              ['marked',mixed_candidates,mixed_accepted,mixed_implications]]
        header=['family','relation_candidates','accepted_relations','implication_checks']
        extra={'transfer_relation_candidates':count,
               'accepted_transfer_relations':ordinary_accepted+mixed_accepted,
               'transfer_implication_checks':ordinary_implications+mixed_implications,
               'ordinary_transfer_candidates':ordinary_candidates,
               'marked_transfer_candidates':mixed_candidates}

    elif args.kind=='raw':
        # Exhaustive two-state raw-input families.  This oracle bypasses
        # model.parse, so it independently exercises enabledness-before-goal-
        # deletion, true-deadlock totalisation, and marked-cycle filtering.
        templates=list(itertools.product(range(2),repeat=2))
        families=(('goal',[1],(0,)),('no-goal',[],(0,1)))
        for family,goals,ports in families:
            for code in range(5**len(templates)):
                data=model(2,1,decode_mixed_edges(code,templates),ports=ports,
                           initial=(0,),goals=goals,mode='weak-service')
                graph=parse(data)
                for finite in (False,True):
                    certificate,used=evaluate(graph,finite)
                    raw_bad=raw_fair_bad_run(data,finite)
                    if certificate['live']==raw_bad:
                        raise AssertionError('raw-semantics oracle disagreement')
                    count+=1;verdicts+=1;summary_cases+=1;product_checks+=used;raw_checks+=1
                    negative+=not certificate['live']
                    rows.append([family,code,int(finite),int(certificate['live'])])
        header=['family','edge_encoding','finite_changes','live']
        extra={'raw_semantics_oracle_checks':raw_checks,
               'raw_goal_family_cases':5**len(templates)*2,
               'raw_no_goal_family_cases':5**len(templates)*2}

    elif args.kind=='named':
        cases=args.out/'cases';cases.mkdir(exist_ok=True)
        for name,data in named().items():
            (cases/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')
            graph=parse(data)
            for finite in (False,True):
                certificate,used=evaluate(graph,finite)
                count+=1;verdicts+=1;summary_cases+=1;product_checks+=used
                negative+=not certificate['live']
                (cases/(name+('-finite' if finite else '-arbitrary')+'.certificate.json')).write_text(json.dumps(certificate,indent=2)+'\n')
                rows.append([name,graph.n,graph.k,len(graph.edges),len(graph.ports),
                             int(finite),int(certificate['live'])])
        (args.out/'quorum-obligations.json').write_text(
            json.dumps(quorum_obligations(named()['role-reset']),indent=2)+'\n')
        header=['case','states','tasks','normalized_edges','ports','finite_changes','live']

    else:
        for n in (8,16,32,64,128):
            for k in (1,4,8):
                for ring in (False,True):
                    edges=[(i,i+1,(1<<k)-1,False) for i in range(n-1)]
                    if ring:edges.append((n-2,0,0,False))
                    data=model(n,k,edges,ports=(0,),mode='justice');graph=parse(data)
                    use_product=n*(1<<k)<=8192
                    start_case=time.perf_counter();certificate,used=evaluate(graph,oracle=use_product)
                    elapsed=time.perf_counter()-start_case
                    count+=1;verdicts+=1;summary_cases+=1;product_checks+=used
                    negative+=not certificate['live']
                    rows.append([n,k,int(ring),len(graph.edges),len(certificate['summary']['arcs']),
                                 int(certificate['live']),elapsed,int(use_product)])
        header=['states','tasks','returning_ring','normalized_edges','summary_arcs',
                'live','wall_seconds','whole_graph_oracle_used']

    with (args.out/(tag+'.csv')).open('w',newline='') as handle:
        writer=csv.writer(handle);writer.writerow(header);writer.writerows(rows)
    stats={'suite':tag,'cases':count,'verdict_cases':verdicts,
           'summary_oracle_checks':summary_cases,
           'whole_graph_oracle_checks':product_checks,
           'whole_graph_oracle_exclusions':verdicts-product_checks,
           'raw_semantics_oracle_checks':raw_checks,
           'nonlive':negative,'mismatches':0,
           'wall_seconds':time.perf_counter()-began,
           'cpu_seconds':time.process_time()-cpu,
           'peak_rss_kib':int((resource.getrusage(resource.RUSAGE_SELF).ru_maxrss+1023)//1024)
                          if sys.platform=='darwin'
                          else int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
           'workers':1,**extra}
    # Completion marker written last; failed chunks are never mistaken for success.
    (args.out/(tag+'.json')).write_text(json.dumps(stats,indent=2)+'\n')
    print(json.dumps(stats))

if __name__=='__main__':main()
