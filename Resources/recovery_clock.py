"""v4 persisted phase clocks, including safely suspended nested endpoint checks.

No clock refunds on resume. Endpoint ASR cannot spend AI/native repair time.
Only the owned ASR process may time out; this never stops shared model servers.
"""
import math,time
from pathlib import Path

def run(fn,stage,phase,cfg,job,cues,paths,args,kwargs):
 import repair_limits as limits
 from worker import atomic_json
 folder=limits.root(cfg,job);folder.mkdir(parents=True,exist_ok=True)
 marker=folder/'repair-time-budget.json'
 parent=limits._active.get()
 if parent and parent.get('phase')==phase:
  limits.check();return fn(cfg,job,cues,paths,*args,**kwargs)
 def persist(scope,status,active=False):
  saved=limits.read(marker);phases=saved.setdefault('phases',{});row=phases.setdefault(scope['phase'],{})
  now=time.monotonic()
  if scope.get('running'):
   elapsed=max(0.,now-scope['last']);scope['spent']+=elapsed;scope['used']+=elapsed
  scope['last']=now;scope['running']=active
  row.update(spentSeconds=scope['spent'],limitSeconds=scope['allowance'],stage=scope['stage'],status=status)
  if active:row['activeSince']=time.time()
  else:row.pop('activeSince',None)
  saved.update(revision='repair-time-budget-4',spentSeconds=sum(r.get('spentSeconds',0) for r in phases.values()),qualityCertified=False,softDeadline=True)
  saved['status']='exhausted' if all(phases.get(p,{}).get('spentSeconds',0)>=value for p,value in saved.get('plan',{}).get('phaseLimits',{}).items()) else 'available'
  if status in ('available','exhausted'):
   saved.setdefault('stages',[]).append(dict(stage=scope['stage'],phase=scope['phase'],seconds=round(scope['used'],4)))
  atomic_json(marker,saved)
 def activate(scope):
  left=max(0.,scope['allowance']-scope['spent']);scope['deadline']=time.monotonic()+left;scope['cfg']['_repairDeadlineUTC']=time.time()+left
  persist(scope,'active',True)
 pause=None;token=None
 if parent:
  if parent.get('root')!=str(folder):raise ValueError('Cannot nest recovery clocks from different films')
  persist(parent,'suspended');pause=limits._active.set(None)
 try:
  __import__('recovery_plan').prepare(cfg,job,cues,paths)
  saved=limits.read(marker);phases=saved.setdefault('phases',{});row=phases.setdefault(phase,dict(spentSeconds=0))
  allowance=float(saved.get('plan',{}).get('phaseLimits',{}).get(phase,0))
  if not math.isfinite(allowance) or allowance<0:raise ValueError('Invalid recovery phase allowance')
  anchor=row.pop('activeSince',None)
  if anchor is not None:
   row['spentSeconds']=min(allowance,float(row.get('spentSeconds',0))+max(0.,time.time()-float(anchor)));row['recoveredActiveClock']=True
  spent=float(row.get('spentSeconds',0));left=max(0.,allowance-spent)
  if not math.isfinite(left) or left<=0:
   row.update(status='exhausted',limitSeconds=allowance);atomic_json(marker,saved);return paths
  atomic_json(marker,saved)
  local=dict(cfg);scope=dict(phase=phase,root=str(folder),stage=stage,spent=spent,used=0.,last=time.monotonic(),running=False,allowance=allowance,cfg=local)
  activate(scope);token=limits._active.set(scope)
  try:return fn(local,job,cues,paths,*args,**kwargs)
  except limits.RepairBudgetExceeded:return paths
  finally:
   persist(scope,'exhausted' if scope['spent']+max(0,time.monotonic()-scope['last'])>=allowance-.001 else 'available')
   limits._active.reset(token)
 finally:
  if parent:
   limits._active.reset(pause);activate(parent)
