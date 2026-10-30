"""Current recording evidence for report display. Never grants repair permission."""
import array,hashlib,json,wave
from pathlib import Path
REVISION='report-classification-246'
PHYSICAL={'missing-audio','no-audible-voice','fast-generation-failed','tts-generation','generation-input','source-clock-target-missing','missing-script','reference-blocked','generation-limit','retry-budget-exhausted'}

def read(path,default):
 try:
  value=json.loads(Path(path).read_text());return value if isinstance(value,type(default)) else default
 except (OSError,ValueError):return default

class AudioEvidence:
 """Runs in the backend RPC, off the interface thread. Cache is optional telemetry."""
 def __init__(self,root,bound):
  self.path=Path(root)/'review-audio-evidence.json';self.bound=Path(bound).resolve();self.saved=read(self.path,{});self.dirty=False
 def inspect(self,path):
  if not path:return dict(state='missing')
  if not isinstance(path,(str,Path)):return dict(state='checking',reason='Invalid recording field')
  p=Path(path).resolve()
  if not p.is_relative_to(self.bound):return dict(state='checking',reason='Unmanaged recording path')
  try:st=p.stat()
  except FileNotFoundError:return dict(state='missing')
  except OSError:return dict(state='checking',reason='Recording temporarily unavailable')
  identity=[st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns];key=str(p);old=self.saved.get(key,{})
  if not isinstance(old,dict):old={}
  if old.get('identity')==identity and old.get('sha256'):return old
  result=dict(state='damaged',identity=identity)
  try:
   digest=hashlib.sha256()
   with p.open('rb') as source:
    while data:=source.read(1024*1024):digest.update(data)
   result['sha256']=digest.hexdigest()
   with wave.open(str(p)) as f:
    if f.getsampwidth()!=2:result.update(state='checking',reason='PCM format requires a separate reader')
    elif f.getnframes()<=0:result.update(state='damaged',reason='Empty recording')
    else:
     peak=0;frames=0
     while raw:=f.readframes(65536):
      samples=array.array('h',raw);peak=max(peak,max((abs(x) for x in samples),default=0));frames+=len(samples)
     result.update(state='available' if peak>32 else 'silent',peak=peak,samples=frames,seconds=f.getnframes()/f.getframerate())
   after=p.stat()
   if identity!=[after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns]:return dict(state='checking',reason='Recording changed during the read')
  except PermissionError:return dict(state='checking',reason='Recording temporarily locked')
  except (OSError,wave.Error,EOFError,ValueError,ZeroDivisionError):pass
  self.saved[key]=result;self.dirty=True;return result
 def healthy(self,path):return self.inspect(path)['state']=='available'
 def flush(self):
  if self.dirty:
   try:__import__('atomic_files').write_json(self.path,self.saved)
   except OSError:pass

def project(root,report,review,row,evidence,contexts):
 cfg=review.get('config',{});cues=review.get('cues',[]);active=row.get('status')=='running'
 items={(x['index'],x['language'],x['engine']):x for x in report['issues']}
 resolved={(x['index'],x['language'],x['engine']):x for x in report['resolvedIssues']}
 tracks={(x['language'],x['engine']):x for x in report['deliveryCoverage'].get('tracks',[])}
 draft=read(Path(root)/'editor-draft-studio.json',{});choices={}
 for segment in draft.get('segments',[]):
  for n in segment.get('sources',[]):
   for key,value in segment.get('reviewDecisions',{}).items():choices[(n+1,key)]=value
 languages=cfg.get('dubLanguages') or [cfg.get('targetLanguage','yue')];engines=cfg.get('selectedEngines') or [cfg.get('ttsBackend','')]
 rows=[];history=[]
 for language in languages:
  for engine in engines:
   folder,local_review=contexts.get((language,engine),(Path(root),review));timings={x['index']:x for x in read(folder/'timing.json',[]) if type(x.get('index')) is int}
   coverage=tracks.get((language,engine),{});delivered={x['index']:x for x in coverage.get('rows',[])};excluded={x['index']:x for x in coverage.get('excluded',[])}
   local_cues={c.get('reviewIndex',n)+1:c for n,c in enumerate(local_review.get('cues',[]))}
   for n,parent in enumerate(cues):
    index=parent.get('reviewIndex',n)+1;cue=local_cues.get(index,parent);key=(index,language,engine);issue=items.get(key);fixed=resolved.get(key);timing=timings.get(index,{});delivery=delivered.get(index,{})
    draft_choice=choices.get((index,language+':'+engine))
    choice=draft_choice or cue.get('editorDecisions',{}).get(language+':'+engine)
    preserved=index in excluded or (__import__('workflow_policy').original_allowed(cfg,cue) and not __import__('target_delivery').required_clock(cue)) or not cue.get('enabled',True) or bool(cue.get('opEdKind')) or bool(choice and choice.get('action')=='original')
    path=(choice or {}).get('audio') if choice and choice.get('action')=='recording' else timing.get('renderedAudio') or timing.get('audio') or delivery.get('retainedAudio')
    health=evidence.inspect(path) if not preserved else dict(state='preserved')
    expected=(choice.get('audioSHA256') or choice.get('recordingSHA256')) if choice and choice.get('action')=='recording' else timing.get('audioSHA256') or timing.get('recordingSHA256')
    if expected and health.get('sha256') and expected!=health['sha256']:health=dict(health,state='damaged',reason='Selected recording hash changed')
    available=health['state']=='available'
    if not choice and (timing.get('originalFallback') or timing.get('originalPreserved')):available=False;health=dict(health,state='missing-target')
    if not choice and timing.get('skipped'):available=False;health=dict(health,state='missing-target')
    stale_physical=bool(issue and issue.get('kind') in PHYSICAL and available and (delivery.get('available') or choice))
    # Current health disproves only an old physical absence. Keep other current
    # language, wording and timing evidence as an advisory, with history intact.
    if stale_physical:
     history.append(dict(issue));physical_evidence=[x for x in issue.get('evidence',[]) if x.get('kind',x.get('reason')) in PHYSICAL]
     others=[x for x in issue.get('evidence',[]) if x not in physical_evidence]
     if fixed:resolved[key]=fixed
     if others:
      issue=dict(issue,kind=others[-1].get('kind') or others[-1].get('reason') or 'verification-unresolved',evidence=others);items[key]=issue
     else:
      items.pop(key,None);issue=None
    if preserved:group='reportPreserved';state='preserved'
    elif health['state']=='checking' or active and not timing and not delivery:group='checking';state='checking'
    elif not available:group='reportMissing';state=health['state']
    else:
     advisory=bool(issue and issue.get('kind') not in PHYSICAL and issue.get('kind') not in ('first-audible-take-retained','target-reference-recovery','automatic-recovery','failed-voice-choice','preview-original-fallback')) or bool(cue.get('sourcePrimaryFallback') or cue.get('translationWarnings'))
     if isinstance(timing.get('renderedEnd'),(int,float)) and isinstance(cue.get('end'),(int,float)) and timing['renderedEnd']-cue['end']>2:advisory=True
     group='reportAdvisory' if advisory else 'reportAvailable';state='available'
    if issue and (cue.get('captionCovered') or cue.get('originalSpeechReason')=='subtitle-continuation'):
     history.append(dict(issue));issue=dict(issue,kind='subtitle-continuation',message='Shared subtitle content is assigned to a main spoken turn. Continuation fragments avoid repeating the same translation; this alone is not missing dubbing.',repairEligible=False,reviewLevel='advisory');items[key]=issue
    if issue:
     issue.update(reportGroup=group,deliveryState=state,recordingSHA256=health.get('sha256'))
     if available and issue.get('kind')=='first-audible-take-retained':issue['reviewLevel']='available'
    record=dict(index=index,engine=engine,language=language,captionOnly=bool(cue.get('captionOnly')),captionCovered=bool(cue.get('captionCovered')),captionCoverageOwners=cue.get('captionCoverageOwners',[]),preservationReason=cue.get('originalSpeechReason'),reportGroup=group,deliveryState=state,recordingAvailable=available,recordingSHA256=health.get('sha256'),selectedAudio=str(path) if path and available else None,processingState=row.get('status','unknown'),verificationState='inconclusive' if issue else 'not-run',hasReviewNote=group=='reportAdvisory',repaired=bool(fixed and available),userChoice=bool(choice),pendingExport=bool(draft_choice),qualityCertified=False)
    rows.append(record)
 counts={k:sum(x['reportGroup']==k for x in rows) for k in ['reportMissing','reportAdvisory','reportAvailable','reportPreserved','checking']}
 report.update(issues=list(items.values()),resolvedIssues=list(resolved.values()),reportRows=rows,reportHistory=history,reportClassificationRevision=REVISION)
 report['reviewState'].update(reportCounts=counts,pending=counts['reportMissing'],needsDubbing=counts['reportMissing'],repairEligible=sum(x.get('reportGroup')=='reportMissing' and bool(x.get('repairEligible')) for x in items.values()),advisory=counts['reportAdvisory'],available=counts['reportAvailable'],checking=counts['checking'],userChoices=sum(x['userChoice'] for x in rows),repaired=sum(x['repaired'] for x in rows),qualityCertified=False)
 evidence.flush();return report
