"""Persisted whole-job recovery clock; AI 75%, installed native voices 25%.

In-flight inference may complete. Deadlines are checked at the NEXT item/chunk,
never by killing a shared service. A crash keeps its wall-clock anchor; pause
settles the active scope, so inactive pause time does not refund/spend allowance.
"""
import contextvars,functools,json,math,time
from pathlib import Path
_active=contextvars.ContextVar('anicanto_repair_allowance',default=None)
class RepairBudgetExceeded(RuntimeError):pass

def enabled(cfg):return __import__('delivery_policy').bounded_delivery(cfg) and not cfg.get('editorRender')
def limit(cfg):return float(cfg.get('_repairBudgetSeconds') or {'performance':60,'balanced':180,'quality':600}.get(cfg.get('workMode','balanced'),180))
def root(cfg,job):
 p=Path(cfg.get('_repairBudgetRoot') or job)
 return p.parent.parent if p.parent.name=='tracks' else p

def read(path):
 try:return json.loads(Path(path).read_text())
 except (OSError,ValueError):return {}
def remaining():
 a=_active.get();return max(0.,a['deadline']-time.monotonic()) if a else None

def check(cfg=None):
 left=remaining()
 if left is None and cfg and cfg.get('_repairDeadlineUTC') is not None:left=float(cfg['_repairDeadlineUTC'])-time.time()
 if left is not None and left<=0:raise RepairBudgetExceeded('本片本階段修復預算已用完；保留已完成錄音，繼續最後交付。')

def deadline():
 left=remaining();return time.time()+left if left is not None else None

def bounded(stage,phase='ai'):
 def decorate(fn):
  @functools.wraps(fn)
  def call(cfg,job,cues,paths,*args,**kwargs):
   if not enabled(cfg):return fn(cfg,job,cues,paths,*args,**kwargs)
   if __import__('delivery_policy').safe_capacity(cfg):return __import__('recovery_clock').run(fn,stage,phase,cfg,job,cues,paths,args,kwargs)
   if _active.get() is not None:
    check();return fn(cfg,job,cues,paths,*args,**kwargs)
   from worker import atomic_json
   folder=root(cfg,job);folder.mkdir(parents=True,exist_ok=True);marker=folder/'repair-time-budget.json';saved=read(marker)
   modern=__import__('delivery_policy').repair_first(cfg)
   if modern and not saved:
    __import__('recovery_plan').prepare(cfg,job,cues,paths);saved=read(marker)
   maximum=float(saved.get('limitSeconds',limit(cfg)))
   phase_limits=saved.get('plan',{}).get('phaseLimits')
   allowance=float(phase_limits.get(phase,0)) if phase_limits is not None else maximum*(.25 if phase=='native' else .75)
   phases=saved.setdefault('phases',{});row=phases.setdefault(phase,dict(spentSeconds=0))
   # A killed process cannot reset its uncheckpointed work. Do not charge more
   # than the remaining allowance for time when the old process may be dead.
   anchor=row.pop('activeSince',None)
   if anchor is not None:row['spentSeconds']=min(allowance,float(row.get('spentSeconds',0))+max(0,time.time()-float(anchor)));row['recoveredActiveClock']=True
   spent=float(row.get('spentSeconds',0));left=max(0,allowance-spent)
   if not math.isfinite(left) or left<=0:
    row.update(status='exhausted',limitSeconds=allowance);saved['spentSeconds']=sum(r.get('spentSeconds',0) for r in phases.values());atomic_json(marker,saved);return paths
   started=time.monotonic();row.update(activeSince=time.time(),stage=stage,status='active',limitSeconds=allowance)
   saved.update(revision='repair-time-budget-3' if phase_limits is not None else 'repair-time-budget-2',limitSeconds=maximum,mode=saved.get('mode',cfg.get('workMode','balanced')),qualityCertified=False,softDeadline=True);atomic_json(marker,saved)
   reset=_active.set(dict(deadline=started+left,root=str(folder),phase=phase));local=dict(cfg,_repairDeadlineUTC=time.time()+left)
   try:return fn(local,job,cues,paths,*args,**kwargs)
   except RepairBudgetExceeded:return paths
   finally:
    elapsed=max(0,time.monotonic()-started);row.update(spentSeconds=spent+elapsed,status='exhausted' if spent+elapsed>=allowance-.001 else 'available');row.pop('activeSince',None)
    saved['spentSeconds']=sum(r.get('spentSeconds',0) for r in phases.values());saved['status']='exhausted' if all(phases.get(p,{}).get('spentSeconds',0)>=v for p,v in (phase_limits or dict(ai=maximum*.75,native=maximum*.25)).items()) else 'available'
    saved.setdefault('stages',[]).append(dict(stage=stage,phase=phase,seconds=round(elapsed,3)))
    try:atomic_json(marker,saved)
    finally:_active.reset(reset)
  return call
 return decorate
