"""Authoritative production milestones, independent of child-model percentages.

Durations count time while this worker is alive, including loading and retries.
Saved phase totals survive resume; time between worker runs is never added.
"""
import math
import functools
import threading
import json
import time
from pathlib import Path
from atomic_files import write_json

PHASES=('prepare','recognition','roles','translation','voice','repair','export')
ANCHORS=(0,.10,.22,.34,.50,.82,.94,1)
_active=None
_lock=threading.RLock()
def locked(fn):
    @functools.wraps(fn)
    def call(*a,**kw):
        with _lock:return fn(*a,**kw)
    return call

class Journey:
    def __init__(self,job,clock=time.monotonic):
        self.job=Path(job);self.clock=clock;self.last=clock();self.current=None;self.done=False;self.quality_status=None
        try:prior=json.loads((self.job/'production-progress.json').read_text())
        except (OSError,ValueError):prior={}
        if not isinstance(prior,dict):prior={}
        previous=prior.get('milestones',[])
        if not isinstance(previous,list):previous=[]
        def seconds(value):
            try:value=float(value)
            except (ValueError,TypeError):return 0
            return max(0,value) if math.isfinite(value) else 0
        self.rows=[]
        for key in PHASES:
            old=next((r for r in previous if isinstance(r,dict) and r.get('id')==key),{})
            state=old.get('state')
            self.rows.append(dict(id=key,state=state if state in ('complete','prepared','skipped','saved') else 'pending',seconds=seconds(old.get('seconds',0))))
        self.value=min(.94,seconds(prior.get('progress',0)))
        # Migrate an older running job without inventing a previous percentage.
        # Existing track reports prove it reached dubbing, not that QA passed.
        if any((self.job/'tracks').glob('*/report.json')):
            self.value=max(self.value,ANCHORS[4])
            if self.rows[4]['state']=='pending':self.rows[4]['state']='saved'
        self.resumed=bool(previous or self.value)

    def tick(self):
        now=self.clock()
        if self.current is not None:self.rows[self.current]['seconds']+=max(0,now-self.last)
        self.last=now
    def enter(self,key,skipped=False,cached=False):
        if self.done:return
        i=PHASES.index(key);self.tick()
        # Work inside a later phase (e.g. one repaired take) cannot rewind the journey.
        if self.current is not None and i<self.current:return
        if self.current is not None and i!=self.current and self.rows[self.current]['state']!='prepared':self.rows[self.current]['state']='complete'
        self.current=i;self.rows[i]['state']='skipped' if skipped else 'prepared' if cached else 'running'
        if skipped:self.current=None
        self.value=max(self.value,ANCHORS[i+1] if skipped else ANCHORS[i])
    def prepared(self):
        for i in range(4):
            if self.rows[i]['state']=='pending':self.rows[i]['state']='prepared'
        self.value=max(self.value,ANCHORS[4])
    def finish(self,partial=False,exported=False):
        if self.done:return
        self.tick()
        completed=exported or not partial
        if self.current is not None:self.rows[self.current]['state']='complete' if completed else 'incomplete'
        if exported:self.rows[-1]['state']='complete'
        self.current=None;self.done=completed
        self.quality_status='needs-review' if partial else 'complete'
        if completed:self.value=1
    def advance(self,phase,fraction):
        if phase not in PHASES:return
        i=PHASES.index(phase)
        if self.current!=i:return
        try:fraction=float(fraction)
        except (ValueError,TypeError):return
        if not math.isfinite(fraction):return
        # Reserve the last 10% of a phase for preparation/alignment/reporting.
        bounded=min(.9,max(0,fraction)*.9)
        self.value=max(self.value,ANCHORS[i]+(ANCHORS[i+1]-ANCHORS[i])*bounded)
    def snapshot(self):
        self.tick()
        return dict(version=1,job=str(self.job),progress=self.value,milestones=self.rows,complete=self.done,resumed=self.resumed,qualityStatus=self.quality_status)
    def save(self):
        data=self.snapshot();path=self.job/'production-progress.json'
        try:write_json(path,data)
        except OSError:pass # Progress persistence must never abort encoding.
        return data

@locked
def reset():
    global _active
    _active=None

@locked
def begin(job,prepared=False):
    global _active
    if _active is None or _active.job!=Path(job):_active=Journey(job)
    if prepared:_active.prepared()
    return _active

@locked
def phase(job,key,skipped=False,prepared=False,cached=False):
    journey=begin(job,prepared);journey.enter(key,skipped,cached);return journey.save()

@locked
def finish(partial=False,exported=False):
    if _active is not None:_active.finish(partial,exported=exported);_active.save()

@locked
def advance(phase,fraction):
    if _active is not None:_active.advance(phase,fraction)

@locked
def snapshot():
    global _active
    if _active is not None and not _active.job.is_dir():_active=None
    return _active.save() if _active is not None else None
