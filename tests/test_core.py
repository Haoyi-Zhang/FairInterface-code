from __future__ import annotations
import copy,csv,itertools,json,shutil,sys,tempfile,unittest
from pathlib import Path
ARTIFACT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ARTIFACT))
sys.path.insert(0,str(ARTIFACT/'src'))
from model import Graph,Edge,parse,strict_json
from producer import produce,summarize
from checker import verify,reference_summary
from oracle import fair_bad_run,strong_bad_run
from raw_oracle import raw_fair_bad_run
from summary_oracle import exact_summary
from interfaces import bind,close_join,export,join_exports,module_graph,validate_family
from refinement import check_refinement
import reproduce as reproduction
from fixtures import (named,model,strong_modules,random_families,quorum_obligations,
                      expanded_role_model)

class ContractTests(unittest.TestCase):
    def test_named(self):
        expected={'goal-enabled':(True,True),'true-deadlock':(False,False),
          'goal-only-sink':(True,True),'hidden-divergence':(False,False),
          'no-fair-path':(True,True),'zero-task-cycle':(False,False),
          'goal-initial':(True,True),'empty-initial':(True,True),
          'nonjoint-capacity':(False,False),'one-shot-ports':(True,True),
          'change-only-cycle':(False,True),'role-reset':(False,True),
          'role-static':(True,True)}
        for name,data in named().items():
            for finite in (False,True):
                with self.subTest(name=name,finite=finite):
                    g=parse(data);c=produce(g,finite)
                    self.assertEqual(c['live'],expected[name][int(finite)])
                    self.assertEqual(c['live'],not fair_bad_run(g,finite))
                    self.assertTrue(verify(g,c))
                    self.assertEqual(c['summary'],exact_summary(g))
    def test_raw_semantics_oracle(self):
        # This path bypasses model.parse and therefore checks enabledness,
        # goal deletion, and true-deadlock totalisation independently.
        for name,data in named().items():
            for finite in (False,True):
                with self.subTest(name=name,finite=finite):
                    self.assertEqual(produce(parse(data),finite)['live'],
                                     not raw_fair_bad_run(data,finite))
        justice=model(2,1,[(0,0,1,False)],ports=(0,),goals=(1,),mode='justice')
        self.assertTrue(raw_fair_bad_run(justice))
        justice['edges'][0][2]=0
        self.assertFalse(raw_fair_bad_run(justice))

    def test_reference_audit_inventory(self):
        path=Path(__file__).resolve().parents[1]/'reference_audit.csv'
        with path.open(newline='') as handle:
            rows=list(csv.DictReader(handle))
        self.assertGreaterEqual(len(rows),55)
        keys=[row['bibkey'] for row in rows]
        self.assertEqual(len(keys),len(set(keys)))
        required={'bibkey','title','authors','year','entry_type','venue_or_series',
                  'persistent_identifier_or_record','verification_source','checked_on',
                  'verification_basis','manuscript_role','status'}
        self.assertTrue(required <= set(rows[0]))
        for row in rows:
            with self.subTest(bibkey=row['bibkey']):
                self.assertTrue(row['title'] and row['authors'] and row['year'])
                self.assertTrue(row['persistent_identifier_or_record'])
                self.assertTrue(row['verification_source'].startswith('https://'))
                self.assertEqual(row['status'],'verified')

    def test_enabled_before_goal_deletion(self):
        g=parse(named()['goal-enabled'])
        self.assertEqual(g.edges[0].color,0)
        self.assertEqual(len(parse(named()['goal-only-sink']).pending_edges()),0)
        self.assertFalse(raw_fair_bad_run(named()['goal-enabled']))
        self.assertFalse(raw_fair_bad_run(named()['goal-only-sink']))
        self.assertTrue(raw_fair_bad_run(named()['true-deadlock']))
    def test_quorums(self):
        self.assertEqual(quorum_obligations(named()['role-reset']),
          [{'honest_quorum_available':True,'min_honest_intersection':1}]*2)
    def test_late_enabledness(self):
        a=model(2,1,[(0,0,0,False)])
        b=model(2,1,[(0,1,1,False)])
        g,s=bind([a,b]);self.assertEqual(s,summarize(g));self.assertEqual(s,reference_summary(g))
        self.assertTrue(produce(g)['live'])
        # Premature local closure would permanently label the self-loop with f.
        self.assertEqual(produce(parse(a))['summary']['arcs'][0][2],1)
    def test_late_deadlock_completion(self):
        a=model(2,1,[]);b=model(2,1,[(0,1,0,False)])
        g,s=bind([a,b]);self.assertEqual(s,{'arcs':[],'divergence':[]})
        self.assertTrue(produce(g)['live'])
    def test_strong_fairness_separation(self):
        a,b,c=strong_modules();self.assertEqual(export(a),export(b))
        da={**a,'edges':a['edges']+c['edges']}
        db={**b,'edges':b['edges']+c['edges']}
        self.assertFalse(strong_bad_run(da));self.assertTrue(strong_bad_run(db))
        self.assertFalse(produce(parse(da))['live']);self.assertFalse(produce(parse(db))['live'])
    def test_module_sealing(self):
        a=model(4,1,[(0,1,0,False)])
        b=model(4,1,[(1,3,1,False)])
        with self.assertRaises(ValueError):bind([a,b])
    def test_rename_tasks(self):
        data=named()['nonjoint-capacity'];g=parse(data)
        swapped=Graph(g.n,g.k,tuple(Edge(e.src,e.dst,((e.color&1)<<1)|((e.color&2)>>1),e.change) for e in g.edges),g.initial,g.goals,g.ports)
        self.assertEqual(produce(g)['live'],produce(swapped)['live'])
    def test_cannot_use_zero_path_as_loop(self):
        g=Graph(1,0,(),(0,),frozenset(),(0,))
        self.assertEqual(summarize(g),{'arcs':[],'divergence':[]})
        self.assertTrue(produce(g)['live'])  # direct colored graph; no deadlock normalization
    def test_bad_json_and_schema(self):
        for raw in ('{"states":2,"states":3}','{"x":NaN}'):
            with self.assertRaises(ValueError):strict_json(raw)
        base=named()['goal-enabled']
        for patch in ({'states':True},{'tasks':9},{'states':129},{'ports':[]},
                      {'edges':[[0,0,-1,False]]},{'edges':[[0,0,0,0]]}):
            with self.assertRaises(ValueError):parse({**base,**patch})

        # The verified POSIX path succeeds, while a platform without the
        # resource API is rejected before any child process starts.
        reproduction._require_supported_environment()
        saved_resource=reproduction.resource
        try:
            reproduction.resource=None
            with self.assertRaisesRegex(RuntimeError,'Native Windows is not supported'):
                reproduction._require_supported_environment()
        finally:
            reproduction.resource=saved_resource

        # Resume planning distinguishes actual execution from validated reuse.
        # The retained bundles supply deterministic fixtures; no campaign is run
        # by this unit test.  Zero, one, and all completed chunks must all lead
        # to the same frozen scientific totals after pending chunks are supplied.
        jobs=reproduction._jobs();source=ARTIFACT/'results'
        def copy_bundle(destination,job):
            for item in reproduction._required_suite_paths(source,job):
                shutil.copy2(item,destination/item.name)
        def validate_generated_summary(destination,reused,pending,invalid,suites):
            # Isolated unit fixture: these receipts model which runner calls would
            # occur; production summaries receive receipts only from subprocesses
            # that actually ran.  This catches the former fixed-20-command bug.
            shutil.copy2(source/'tests.stderr.txt',destination/'tests.stderr.txt')
            result=reproduction._aggregate_suites(suites)
            result.update({
                'execution_mode':'resume',
                'commands_executed_this_run':[
                    {'tag':'tests','exit_code':0},
                    *({'tag':reproduction._job_tag(job),'exit_code':0} for job in pending),
                ],
                'results_reused_after_validation':[
                    {key:value for key,value in item.items() if key!='result'}
                    for item in reused
                ],
                'invalid_resume_records_recomputed':invalid,
            })
            reproduction._validate_result(result,destination,jobs)
            path=destination/'summary.json'
            path.write_text(json.dumps(result,indent=2)+'\n')
            return json.loads(path.read_text())
        for completed in (0,1,len(jobs)):
            with self.subTest(resume_completed=completed), tempfile.TemporaryDirectory() as rawdir:
                destination=Path(rawdir)
                for job in jobs[:completed]:copy_bundle(destination,job)
                reused,pending,invalid=reproduction._classify_resume(destination,jobs)
                self.assertEqual((len(reused),len(pending),len(invalid)),
                                 (completed,len(jobs)-completed,0))
                for job in pending:copy_bundle(destination,job)
                suites=[reproduction._validate_suite_bundle(destination,job) for job in jobs]
                summary=validate_generated_summary(destination,reused,pending,invalid,suites)
                for key,value in reproduction.EXPECTED_TOTALS.items():
                    self.assertEqual(summary[key],value)
                transfer=next(item for item in suites if item['suite']=='transfer')
                self.assertEqual((transfer['verdict_cases'],transfer['nonlive']),(2038,1216))

        # A partial marker is not trusted. Missing logs and damaged JSON are
        # classified for recomputation, then the complete bundle revalidates.
        damages=(('missing-log','named'),('corrupt-json','raw'),
                 ('nonempty-stderr','scaling'),('wrong-core-range','core-3-0-2000'))
        for damage,target in damages:
            with self.subTest(resume_damage=damage), tempfile.TemporaryDirectory() as rawdir:
                destination=Path(rawdir)
                for job in jobs:copy_bundle(destination,job)
                if damage=='missing-log':
                    (destination/'named.stderr.txt').unlink()
                elif damage=='corrupt-json':
                    (destination/'raw.json').write_text('{broken')
                elif damage=='nonempty-stderr':
                    (destination/'scaling.stderr.txt').write_text('unexpected warning\n')
                else:
                    path=destination/'core-3-0-2000.csv'
                    rows=path.read_text().splitlines()
                    fields=rows[1].split(',');fields[0]='9999';rows[1]=','.join(fields)
                    path.write_text('\n'.join(rows)+'\n')
                reused,pending,invalid=reproduction._classify_resume(destination,jobs)
                self.assertEqual([reproduction._job_tag(job) for job in pending],[target])
                self.assertEqual(len(reused),len(jobs)-1);self.assertEqual(len(invalid),1)
                copy_bundle(destination,pending[0])
                suites=[reproduction._validate_suite_bundle(destination,job) for job in jobs]
                summary=validate_generated_summary(destination,reused,pending,invalid,suites)
                for key,value in reproduction.EXPECTED_TOTALS.items():
                    self.assertEqual(summary[key],value)
    def test_certificate_mutations(self):
        cases=named();mutants=[]
        g=parse(cases['nonjoint-capacity']);c=produce(g)
        x=copy.deepcopy(c);x['summary']['arcs'][0][2]=0;mutants.append((g,x))
        x=copy.deepcopy(c);x['summary']['arcs'].pop();mutants.append((g,x))
        x=copy.deepcopy(c);x['witness']['cycle']=[];mutants.append((g,x))
        x=copy.deepcopy(c);x['witness']['cycle'][0]=999999;mutants.append((g,x))
        x=copy.deepcopy(c);x['witness']['start']=True;mutants.append((g,x))
        g2=parse(cases['hidden-divergence']);x=produce(g2);x['summary']['divergence']=[];mutants.append((g2,x))
        g3=parse(cases['role-reset']);x=produce(g3);x['mode']='finite-changes';mutants.append((g3,x))
        g4=parse(cases['one-shot-ports']);x=produce(g4)
        for block in x['blocks']:block['rank']=0
        mutants.append((g4,x))
        g5=parse(cases['goal-enabled']);x=produce(g5);x['blocks'][0]['missing']=1;mutants.append((g5,x))
        g6=parse(cases['zero-task-cycle']);x=produce(g6);x['summary']['arcs'][0][0]=False;mutants.append((g6,x))
        for j,(model_,mutant) in enumerate(mutants):
            with self.subTest(mutant=j):
                with self.assertRaises(ValueError):verify(model_,mutant)
    def test_interface_component_separations(self):
        # Excursion existence: k=0, same port flags and no divergence.
        with_arc=model(3,0,[(0,1,0,False),(0,2,0,False)],ports=(0,1))
        without_arc=model(3,0,[(0,2,0,False)],ports=(0,1))
        context=model(3,0,[(1,0,0,False)],ports=(0,1))
        ia,ib=export(with_arc),export(without_arc)
        self.assertEqual((ia['divergence'],ia['enabled'],ia['outgoing']),
                         (ib['divergence'],ib['enabled'],ib['outgoing']))
        self.assertFalse(produce(bind([with_arc,context])[0])['live'])
        self.assertTrue(produce(bind([without_arc,context])[0])['live'])

        # Hidden divergence: all other interface fields agree.
        diverge=model(4,1,[(0,1,0,False),(0,3,1,False),(1,1,0,False)])
        terminate=model(4,1,[(0,1,0,False),(0,3,1,False),(1,3,0,False)])
        ia,ib=export(diverge),export(terminate)
        self.assertEqual((ia['arcs'],ia['enabled'],ia['outgoing']),
                         (ib['arcs'],ib['enabled'],ib['outgoing']))
        self.assertNotEqual(ia['divergence'],ib['divergence'])
        self.assertFalse(produce(bind([diverge])[0])['live'])
        self.assertTrue(produce(bind([terminate])[0])['live'])

        # D(p) may not cross another port before entering a hidden loop.  With
        # F empty, p->q followed by q->u,u->u gives D(p)=false and D(q)=true;
        # p is nevertheless nonlive because q is reachable.  Direct p->u is the
        # positive control.  Both change interpretations agree because all edges
        # here are ordinary.
        via_port_1=model(4,0,[(0,1,0,False)],ports=(0,1),goals=(3,))
        via_port_2=model(4,0,[(1,2,0,False),(2,2,0,False)],ports=(0,1),goals=(3,))
        self.assertEqual(export(via_port_1)['divergence'],[])
        self.assertEqual(export(via_port_2)['divergence'],[1])
        graph,bound=bind([via_port_1,via_port_2])
        self.assertEqual(bound['arcs'],[[0,1,0,False]])
        self.assertEqual(bound['divergence'],[1])
        self.assertEqual(bound,summarize(graph));self.assertEqual(bound,reference_summary(graph))
        self.assertEqual(bound,exact_summary(graph))
        for finite in (False,True):
            certificate=produce(graph,finite)
            self.assertFalse(certificate['live']);self.assertTrue(verify(graph,certificate))

        direct=model(4,0,[(0,2,0,False),(2,2,0,False)],ports=(0,1),goals=(3,))
        direct_graph,direct_bound=bind([direct])
        self.assertEqual(export(direct)['divergence'],[0])
        # The unused exact port q is a true port deadlock and is completed
        # only at global closure; there is still no ordinary arc out of p.
        self.assertEqual(direct_bound['arcs'],[[1,1,0,False]])
        self.assertEqual(direct_bound['divergence'],[0])
        self.assertEqual(direct_bound,summarize(direct_graph))
        self.assertEqual(direct_bound,reference_summary(direct_graph))
        self.assertEqual(direct_bound,exact_summary(direct_graph))
        for finite in (False,True):
            certificate=produce(direct_graph,finite)
            self.assertFalse(certificate['live']);self.assertTrue(verify(direct_graph,certificate))

        # Enabledness: same loop, divergence and outgoing flag; a goal edge enables f.
        loop=model(2,1,[(0,0,0,False)])
        loop_goal=model(2,1,[(0,0,0,False),(0,1,1,False)])
        ia,ib=export(loop),export(loop_goal)
        self.assertEqual((ia['arcs'],ia['divergence'],ia['outgoing']),
                         (ib['arcs'],ib['divergence'],ib['outgoing']))
        self.assertNotEqual(ia['enabled'],ib['enabled'])
        self.assertFalse(produce(bind([loop])[0])['live'])
        self.assertTrue(produce(bind([loop_goal])[0])['live'])

        # Outgoing: a true port deadlock differs from a goal-only unserviced edge.
        dead=model(2,1,[])
        goal_only=model(2,1,[(0,1,0,False)])
        ia,ib=export(dead),export(goal_only)
        self.assertEqual((ia['arcs'],ia['divergence'],ia['enabled']),
                         (ib['arcs'],ib['divergence'],ib['enabled']))
        self.assertNotEqual(ia['outgoing'],ib['outgoing'])
        self.assertFalse(produce(bind([dead])[0])['live'])
        self.assertTrue(produce(bind([goal_only])[0])['live'])

    def test_capacity_information_separation(self):
        # Common initial entry r=0; inputs 1,2; outputs 3,4; goal 5.
        # Contexts select a pair by an entry edge, never by changing initial states.
        for matrix in range(16):
            es=[[1+i,3+j,(matrix>>(2*i+j))&1,False] for i in range(2) for j in range(2)]
            es += [[v,5,1,False] for v in range(5)]
            base=model(6,1,es,ports=(0,1,2,3,4),initial=(0,))
            item=export(base)
            self.assertEqual(item['enabled'],[1]*5)
            self.assertEqual(item['outgoing'],[True]*5)
            self.assertEqual(item['divergence'],[])
            for i in range(2):
                for j in range(2):
                    context=model(6,1,[[0,1+i,0,False],[3+j,1+i,0,False]],ports=(0,1,2,3,4),initial=(0,))
                    graph,bound=bind([base,context])
                    self.assertEqual(bound,reference_summary(graph))
                    self.assertEqual(fair_bad_run(graph),bool((matrix>>(2*i+j))&1))
    def test_grouping_retains_exact_ports(self):
        for family in random_families(24):
            merged={**family[0],'edges':family[0]['edges']+family[1]['edges']}
            _,a=bind(family)
            _,b=bind([merged]+family[2:])
            _,c=bind(list(reversed(family)))
            self.assertEqual(a,b)
            self.assertEqual(a,c)
    def test_raw_interface_join_algebra(self):
        # The raw join is the algebraic operation exposed by the theorem.  It
        # must be order/grouping independent and must not perform closure early.
        for family in random_families(8):
            items=[export(module) for module in family]
            port_count=len(family[0]['ports'])
            canonical=join_exports(items,port_count)
            for order in itertools.permutations(items):
                self.assertEqual(join_exports(order,port_count),canonical)
            left=join_exports([join_exports(items[:2],port_count),*items[2:]],port_count)
            self.assertEqual(left,canonical)
            for item in items:
                self.assertEqual(join_exports([item,item],port_count),item)
            graph=validate_family(family)
            self.assertEqual(close_join(graph,canonical),summarize(graph))

    def test_random_module_pilot(self):
        for family in random_families(24):
            g,s=bind(family);_,s2=bind(family,independent=True)
            self.assertEqual(s,s2);self.assertEqual(s,summarize(g))
            self.assertEqual(s,reference_summary(g));self.assertEqual(s,exact_summary(g))

    def test_unmentioned_states_are_not_claimed(self):
        data=model(5,1,[(0,2,0,False)],ports=(0,1))
        graph,_,_=module_graph(data)
        self.assertIn(Edge(2,2,graph.full,False),graph.edges)
        self.assertNotIn(Edge(3,3,graph.full,False),graph.edges)

    def test_refinement_fixture(self):
        concrete,abstract,mapping=expanded_role_model()
        report=check_refinement(concrete,abstract,mapping)
        self.assertTrue(report['valid'])
        self.assertEqual((report['concrete_states'],report['abstract_states']),(29,15))
        for finite,expected in ((False,False),(True,True)):
            graph=parse(concrete);certificate=produce(graph,finite)
            self.assertEqual(certificate['live'],expected)
            self.assertTrue(verify(graph,certificate))
            self.assertEqual(certificate['summary'],exact_summary(graph))

    def test_refinement_deadlock_totalization(self):
        # Both raw models deadlock: their semantic task-free stutters match.
        concrete=model(2,1,[],ports=(0,),initial=(0,),goals=(1,))
        abstract=model(2,1,[],ports=(0,),initial=(0,),goals=(1,))
        report=check_refinement(concrete,abstract,[0,1])
        self.assertEqual(report['concrete_deadlock_stutters'],1)
        self.assertEqual(report['abstract_deadlock_stutters'],1)

        # Unsound without semantic totalization: the abstract model can only
        # reach its goal, whereas the concrete model can stutter forever.
        abstract_goal_only=model(2,1,[(0,1,0,False)],ports=(0,),initial=(0,),goals=(1,))
        self.assertTrue(produce(parse(abstract_goal_only))['live'])
        self.assertFalse(produce(parse(concrete))['live'])
        with self.assertRaises(ValueError):
            check_refinement(concrete,abstract_goal_only,[0,1])

    def test_refinement_mutations(self):
        concrete,abstract,mapping=expanded_role_model()
        bad_maps=[]
        changed=mapping[:];changed[0]=1;bad_maps.append((concrete,changed))
        changed=mapping[:];changed[1]=abstract['goals'][0];bad_maps.append((concrete,changed))
        for candidate,bad_mapping in bad_maps:
            with self.assertRaises(ValueError):check_refinement(candidate,abstract,bad_mapping)

        missing=copy.deepcopy(concrete)
        missing['edges']=[row for row in missing['edges']
                          if not (row[0]==0 and row[2]&1)]
        with self.assertRaises(ValueError):check_refinement(missing,abstract,mapping)

        invented=copy.deepcopy(concrete)
        invented['edges'].append([0,0,16,False])
        with self.assertRaises(ValueError):check_refinement(invented,abstract,mapping)

        unmarked=copy.deepcopy(concrete)
        index=next(i for i,row in enumerate(unmarked['edges']) if row[3])
        unmarked['edges'][index][3]=False
        with self.assertRaises(ValueError):check_refinement(unmarked,abstract,mapping)

if __name__=='__main__':unittest.main(verbosity=2)
