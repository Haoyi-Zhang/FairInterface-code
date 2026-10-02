"""Bounded certificate CLI: synthesize, check, or bind a module family."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from model import load,strict_json,MAX_BYTES
from producer import produce
from checker import verify,reference_summary
from interfaces import bind

CERT_BYTES=4*1024*1024

def read_json(path,limit):
    with Path(path).open('rb') as f:raw=f.read(limit+1)
    if len(raw)>limit:raise ValueError('JSON input exceeds byte limit')
    return strict_json(raw)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sp=p.add_subparsers(dest='command',required=True)
    for action in ('synthesize','check'):
        s=sp.add_parser(action);s.add_argument('model');s.add_argument('certificate')
        if action=='synthesize':s.add_argument('--finite-changes',action='store_true')
    s=sp.add_parser('bind');s.add_argument('family');s.add_argument('output')
    a=p.parse_args()
    if a.command=='check':
        verify(load(a.model),read_json(a.certificate,CERT_BYTES))
        print('VALID');return
    if a.command=='synthesize':
        g=load(a.model);data=produce(g,a.finite_changes);verify(g,data);path=Path(a.certificate)
    else:
        family=read_json(a.family,MAX_BYTES)
        g,data=bind(family);_,independent=bind(family,independent=True)
        if data!=independent or data!=reference_summary(g):raise ValueError('independent interface mismatch')
        path=Path(a.output)
    encoded=(json.dumps(data,indent=2,sort_keys=True)+'\n').encode()
    if len(encoded)>CERT_BYTES:raise ValueError('output exceeds byte limit')
    # Parent is explicit: no implicit directories or network paths are chosen.
    with path.open('xb') as f:f.write(encoded)
    print(str(path))

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,TypeError,KeyError,RecursionError) as e:
        print(f'ERROR: {e}',file=sys.stderr);sys.exit(2)
