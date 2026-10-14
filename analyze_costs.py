"""Reconcile paired SCC evidence, unchanged historical verdicts and real costs.

No scientific inputs are generated here. Full command costs are kept distinct
from paired already-normalized-input solver intervals. Optimized runs are
repeat validation of the same population, never additional scientific cases.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('normal',type=Path)
parser.add_argument('optimized',type=Path)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--paper-table',type=Path)
args=parser.parse_args()
summaries=[json.loads((directory/'summary.json').read_text())
           for directory in (args.normal,args.optimized)]
historical=ROOT/'results'
rows=[]
inputs=[]
normal_bindings={}
for index,(directory,summary) in enumerate(zip((args.normal,args.optimized),summaries)):
    if summary['total_monolithic_checks']!=244828 or summary['mismatches']!=0:
        raise ValueError('incomplete SCC evidence')
    if summary['environment']['optimize']!=index:
        raise ValueError('interpreter optimization receipt mismatch')
    if len(summary['commands_executed_this_run'])!=20 or summary['results_reused_after_validation']:
        raise ValueError('evidence must be an actual clean full run')
    if any(command['optimize']!=index or not command['dont_write_bytecode']
           for command in summary['commands_executed_this_run']):
        raise ValueError('child mode/bytecode receipt mismatch')
    totals=[0,0,0]
    count=0
    for suite in summary['suites']:
        tag=suite['suite']
        source=directory/f'{tag}.csv'
        with source.open(newline='') as handle, (historical/source.name).open(newline='') as old:
            observed=list(csv.reader(handle));retained=list(csv.reader(old))
        # Scaling retains a timing column, not a scientific outcome. All other
        # cells must remain literally identical, including negative verdicts.
        if tag=='scaling':
            position=observed[0].index('wall_seconds')
            observed=[row[:position]+row[position+1:] for row in observed]
            retained=[row[:position]+row[position+1:] for row in retained]
        if observed!=retained:
            raise ValueError(f'historical outcome drift: {tag}')
        cost=directory/f'{tag}-costs.csv'
        sums=[0,0,0];suite_count=0
        bindings=[]
        with cost.open(newline='') as handle:
            for record in csv.DictReader(handle):
                if int(record['evaluation'])!=suite_count:raise ValueError('evaluation order drift')
                for j,key in enumerate(('producer_ns','checker_ns','monolithic_ns')):
                    sums[j]+=int(record[key])
                bindings.append(tuple(record[key] for key in (
                    'evaluation','normalized_graph_sha256','states','tasks',
                    'normalized_edges','ports','finite_changes','live')))
                suite_count+=1
        if index==0:normal_bindings[tag]=bindings
        elif bindings!=normal_bindings[tag]:raise ValueError('normal/optimized source binding drift')
        if suite_count!=suite['verdict_cases'] or sums!=[
            suite[key] for key in ('producer_ns','checker_ns','monolithic_ns')]:
            raise ValueError('raw cost aggregate mismatch')
        rows.append([index,tag,suite_count,*sums])
        totals=[a+b for a,b in zip(totals,sums)]
        count+=suite_count
        inputs.append({'mode':index,'file':str(cost.resolve()),'bytes':cost.stat().st_size,
                       'sha256':hashlib.sha256(cost.read_bytes()).hexdigest()})
    self_cpu=sum(suite['cpu_seconds'] for suite in summary['suites'])
    if summary['measured_child_cpu_seconds']+.1<self_cpu:
        raise ValueError('process accounting omits worker CPU')
    summary['paired_costs']={'verdict_evaluations':count,'producer_ns':totals[0],
                             'checker_ns':totals[1],'monolithic_ns':totals[2],
                             'summed_scientific_self_cpu_seconds':self_cpu}
args.output.mkdir(parents=True,exist_ok=False)
with (args.output/'suite-costs.csv').open('w',newline='') as handle:
    writer=csv.writer(handle)
    writer.writerow(['optimize','suite','evaluations','producer_ns','checker_ns','monolithic_ns'])
    writer.writerows(rows)
result={'unique_verdict_population':244828,'repeated_validation_modes':[0,1],
        'historical_scientific_rows_unchanged':True,
        'normal_optimized_normalized_graph_bindings_identical':True,
        'normal':{key:summaries[0][key] for key in ('paired_costs','wall_seconds',
                    'measured_child_cpu_seconds','parent_cpu_seconds','peak_child_rss_kib',
                    'peak_parent_rss_kib','environment')},
        'optimized':{key:summaries[1][key] for key in ('paired_costs','wall_seconds',
                    'measured_child_cpu_seconds','parent_cpu_seconds','peak_child_rss_kib',
                    'peak_parent_rss_kib','environment')},
        'measurement_scope':'Paired stages share already-normalized input; fixed producer/checker/SCC order. Full campaign cost includes input generation, module exports/join, all oracles, serialization, IO, tests, process startup and controller validation. No isolated baseline end-to-end, incremental maintenance, confidence interval, or speedup claim.',
        'source_files':inputs}
# Normalize public bindings to result-directory names, not private machine paths.
for record in inputs:
    record['file']=f"{'normal' if record['mode']==0 else 'optimized'}/{Path(record['file']).name}"
(args.output/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
if args.paper_table:
    cost=summaries[0]['paired_costs']
    text=('\\begin{tabular}{lr}\n\\toprule\nOperation & Seconds \\\\\n\\midrule\n'
          f"Ordinary SCC decision & {cost['monolithic_ns']/1e9:.3f} \\\\\n"
          f"Summary and certificate production & {cost['producer_ns']/1e9:.3f} \\\\\n"
          f"Independent certificate checking & {cost['checker_ns']/1e9:.3f} \\\\\n"
          '\\bottomrule\n\\end{tabular}\n')
    args.paper_table.write_text(text)
print(json.dumps({key:value for key,value in result.items() if key!='source_files'},indent=2))
