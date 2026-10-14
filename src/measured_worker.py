"""Run an owned script and retain native self peak before the process exits."""
import json
from pathlib import Path
import runpy
import sys
import time
from process_metrics import self_peak_kib

receipt=Path(sys.argv[1])
target=sys.argv[2]
sys.argv=sys.argv[2:]
try:
    runpy.run_path(target,run_name='__main__')
finally:
    receipt.write_text(json.dumps({'self_cpu_seconds_before_exit':time.process_time(),
                                   'peak_rss_kib':self_peak_kib(),
                                   'optimize':sys.flags.optimize,
                                   'dont_write_bytecode':sys.dont_write_bytecode},indent=2)+'\n')
