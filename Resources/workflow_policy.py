"""Persistent bounded recovery, shared by generation and scene translation."""
import hashlib,json,time
from pathlib import Path

def reserve(folder,namespace,identity,limit=4):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    path=folder/(namespace+'-budget.json')
    rows=json.loads(path.read_text()) if path.exists() else {}
    key=hashlib.sha256(json.dumps(identity,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    row=rows.get(key,dict(attempts=0))
    if row['attempts']>=limit:return False
    row.update(attempts=row['attempts']+1,updated=time.time());rows[key]=row
    from worker import atomic_json
    atomic_json(path,rows)
    return True

def original_allowed(cfg,cue):
    # Only deliberate source preservation/nonverbal performance is permitted.
    return bool(cue.get('preserveOriginalSpeech') and cue.get('originalSpeechReason') not in ('missing-script','unresolved-overlap'))

def cross_engine_allowed(cfg):
    return bool(cfg.get('allowCrossEngineRepair',False))
