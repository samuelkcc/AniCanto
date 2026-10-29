"""Per-cue operation counts, retained across phases, new text and resume."""
from pathlib import Path
from repair_limits import read,check

def reserve(job,stage,index,maximum):
 from worker import atomic_json
 check();file=Path(job)/'recovery-operation-counts.json';saved=read(file);key=stage+':'+str(index);used=int(saved.get(key,0))
 if used>=maximum:return False
 saved[key]=used+1;atomic_json(file,saved);return True
