"""Fresh bounded repair of reported lines; immutable donors and retained best takes.

The original ASR, translation, actor references and delivered good recordings
are reused. A new version resets only the reported lines' generation/recovery
budget. Nothing edits or deletes the previous movie or its repair evidence.
"""
import copy,hashlib,json,shutil,time,uuid
from pathlib import Path

REVISION='reported-lines-retry-1'

def read(path,default):
 try:return json.loads(Path(path).read_text())
 except (OSError,ValueError):return default

def fingerprint(review):return hashlib.sha256(json.dumps(review,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def submission(root,review_path,snapshot,mode='pending',saved_draft=None):
 root=Path(root).resolve();path=Path(review_path).resolve()
 if not path.is_relative_to(root/'jobs') or not path.is_file():raise ValueError('The saved review is unavailable.')
 review=read(path,{})
 if review.get('config',{}).get('productionMode')!='normal' and not __import__('basic_flow').enabled(review.get('config',{})):raise ValueError('Automatic review retry requires Normal mode.')
 if mode not in ('pending','all'):raise ValueError('Unknown review retry mode.')
 targets={}
 for issue in snapshot.get('issues',[]):
  if mode=='pending' and issue.get('repairEligible') is False:continue
  if mode=='pending' and issue.get('reportGroup') not in (None,'reportMissing'):continue
  if issue.get('kind')=='name-term-mismatch':continue
  if issue.get('status')=='user-choice-saved' or (mode=='pending' and issue.get('triage') in ('checked','deferred')):continue
  if type(issue.get('index')) is int:targets.setdefault(issue.get('language','yue')+':'+issue.get('engine',''),[]).append(issue['index'])
 for stale in snapshot.get('staleRecordings',[]):
  if not stale.get('protected'):targets.setdefault(stale['language']+':'+stale['engine'],[]).append(stale['index'])
 from multitrack import saved_track_reports
 donors={}
 for row in saved_track_reports(path):
  folder=Path(row['report']).resolve().parent
  if folder.is_relative_to(path.parent) and (folder/'timing.json').is_file():donors[row.get('language','yue')+':'+row['engine']]=str(folder)
 if not donors:raise ValueError('Saved recordings are missing; run conversion first.')
 if mode=='all':targets={key:list(range(1,len(review['cues'])+1)) for key in donors}
 if set(targets)-set(donors):raise ValueError('A reported track has no saved recordings.')
 cues=copy.deepcopy(review['cues'])
 if saved_draft:
  from project_edit import materialize
  from desktop_state import review_fingerprint
  if Path(saved_draft.get('review','/nonexistent')).resolve()!=path or saved_draft.get('baseFingerprint')!=review_fingerprint(review):raise ValueError('Saved edits are out of date. Refresh the review before repairing.')
  edited=materialize(review,saved_draft)
  # Donor recordings are indexed against the original dialogue. Splits, merges
  # and reordered lines need the full editorial render, not a targeted retry.
  if len(edited)!=len(cues) or any(c.get('editorSources')!=[i] for i,c in enumerate(edited)):
   raise ValueError('Split, merged or reordered dialogue needs Produce a new version.')
  fields=('start','end','cantonese','mandarin','english','speakerId','enabled','subtitleStart','subtitleEnd','captionText','preserveOriginalSpeech')
  for i,(old,new) in enumerate(zip(cues,edited),1):
   decisions=new.get('editorDecisions',{})
   defaults=dict(english='',mandarin='',speakerId='',enabled=True,subtitleStart=old['start'],subtitleEnd=old['end'],captionText=old.get('cantonese',''),preserveOriginalSpeech=False)
   changed=any(new.get(k,defaults.get(k))!=old.get(k,defaults.get(k)) for k in fields)
   if changed:
    for key in donors:targets.setdefault(key,[]).append(i)
   for key in decisions:
    if key in donors:targets[key]=[n for n in targets.get(key,[]) if n!=i]
  cues=edited
 if mode=='pending' and not any(targets.values()) and not any(c.get('editorDecisions') for c in cues):raise ValueError('There are no reported lines or saved changes to repair.')
 settings=copy.deepcopy(review['config'])
 # An explicit new repair version can use the corrected target gate; the old request stays frozen.
 settings['targetDeliveryRevision']=__import__('target_delivery').REVISION
 if saved_draft and 'voiceProfiles' in saved_draft.get('settings',{}):settings['voiceProfiles']=copy.deepcopy(saved_draft['settings']['voiceProfiles'])
 return dict(id=uuid.uuid4().hex,review=str(path),settings=settings,automaticReviewRetry=dict(revision=REVISION,mode=mode,fingerprint=fingerprint(review),targets={k:sorted(set(v)) for k,v in targets.items()},donors=donors,submittedCues=cues))

def render(w,request,draft):
 source=Path(draft['review']).resolve();base=source.parent;review=read(source,{})
 spec=draft['automaticReviewRetry'];root=Path(request['storage']).resolve()
 if not source.is_relative_to(root/'jobs') or fingerprint(review)!=spec['fingerprint']:raise ValueError('The source review changed. Refresh before retrying.')
 ident=draft['id']
 if not isinstance(ident,str) or len(ident)!=32 or not all(c in '0123456789abcdef' for c in ident):raise ValueError('Invalid automatic repair version.')
 folder=base/'versions'/ident
 folder.mkdir(parents=True,exist_ok=False)
 cfg=dict(copy.deepcopy(review['config']),**draft.get('settings',{}));cfg.update({k:request[k] for k in ('storage','port','executable','ffmpeg','ffprobe') if k in request})
 cfg.pop('_trackControl',None);cfg.pop('editorCache',None);cfg.pop('_generationGuardRoot',None);cfg.pop('_explicitRetakeToken',None)
 cfg.update(productionMode='normal',editorRender=False,scriptLocked=True,automaticDurationRewrite=bool(cfg.get('limitSpeechDuration')) if __import__('basic_flow').enabled(cfg) else True,exportFolder=review['config'].get('exportFolder',''),_reviewRetry=spec,_reviewRetryToken=ident)
 for name in ('cues.json','japanese-analysis.json','japanese-original.wav','source.srt','subtitle-context.json','subtitle-context-meta.json','natural-scene-boundaries.json','nonverbal-classification-v2.json'):
  p=base/name
  if p.is_file():shutil.copy2(p,folder/name)
 cfg['_editorSourceRoot']=str(base)
 submitted=copy.deepcopy(spec.get('submittedCues',review['cues']))
 w.atomic_json(folder/'cues.json',submitted);w.atomic_json(folder/'review.json',dict(review,config=cfg,cues=submitted,status='pending'))
 version=dict(id=ident,created=time.time(),status='running',sourceReview=str(source),automaticReviewRetry=spec)
 w.atomic_json(folder/'version.json',version)
 original=w.emit
 def relay(stage,message,progress=None,**extra):original(stage,message,progress,job=str(folder),**{k:v for k,v in extra.items() if k!='job'})
 w.emit=relay
 try:
  relay('再次 AI 修復','只重新生成同核對已報告嘅對白；沿用原聲辨識、翻譯稿及成功錄音，舊成品保留。',.55)
  w.render_review(dict(review=str(folder/'review.json'),cues=submitted,fastPrepared=True,lockScript=True))
  report=read(folder/'report.json',{});version.update(status='complete',output=report.get('exportedOutput') or report.get('output'),report=str(folder/'report.json'))
  w.atomic_json(folder/'version.json',version)
 finally:w.emit=original

def track_cues(cfg,cues,engine,language):
 spec=cfg.get('_reviewRetry')
 if not spec:return cues
 key=language+':'+engine;source=Path(spec['donors'][key]).resolve();pending=set(spec['targets'].get(key,[]));timing={r['index']:r for r in read(source/'timing.json',[])}
 result=copy.deepcopy(cues)
 for n,cue in enumerate(result):
  index=cue.get('reviewIndex',n)+1
  if index in pending:__import__('target_delivery').prepare(cfg,[cue])
  # Explicit saved choices/manual audio remain protected even when reported.
  if cue.get('editorAudio') or cue.get('preserveOriginalSpeech'):continue
  if index in pending:
   cue['_seed']=(int(cfg['_reviewRetryToken'][:8],16)+index)%2147483647
   continue
  row=timing.get(index,{});audio=Path(row.get('renderedAudio','')).resolve()
  if row.get('skipped') or row.get('originalFallback') or not audio.is_relative_to(source) or not audio.is_file():raise ValueError('A retained line has no verified delivered recording; it was not silently dropped.')
  cue.update(editorAudio=str(audio),editorAudioBackend=engine,editorAudioLanguage=language,_retryRetained=dict(start=row['renderedStart'],end=row['renderedEnd'],audioSHA256=hashlib.sha256(audio.read_bytes()).hexdigest()))
 return result

def keep_better_baselines(cfg,job,cues,paths,placement,run,emit):
 spec=cfg.get('_reviewRetry')
 if not spec:return paths,placement
 from normal_recovery import clear_confirmed,verified_check
 from worker import atomic_json
 from natural_schedule import plan
 from natural_delivery import seconds
 from audio_fallback import healthy
 key=cfg.get('targetLanguage','yue')+':'+cfg['ttsBackend'];source=Path(spec['donors'][key]);pending=set(spec['targets'].get(key,[]));checks=read(Path(job)/'normal-checks.json',{});unresolved=set(checks.get('unresolved',[]))
 old=[v for v in read(source/'target-reference-recovery.json',{}).values() if v.get('status')=='adopted'];timing={v['index']:v for v in read(source/'timing.json',[])}
 current_bank=[v for v in read(Path(job)/'target-reference-recovery.json',{}).values() if v.get('status')=='adopted']
 current_checks=checks.get('checks',{})
 selected=list(paths);lengths=[v.get('seconds') for v in placement];ledger=read(Path(job)/'target-reference-recovery.json',{});confirmed=set()
 for i,cue in enumerate(cues):
  index=cue.get('reviewIndex',i)+1
  if index not in pending:continue
  current_proof=current_checks.get(str(index),current_checks.get(index,{}))
  current_verified=verified_check(current_proof,cue.get('cantonese',''),cfg.get('targetLanguage','yue')) or any(v.get('index')==index and v.get('text')==cue.get('cantonese') and verified_check(v.get('check',{}),cue.get('cantonese',''),cfg.get('targetLanguage','yue')) and Path(v.get('selectedAudio') or v.get('audio','')).resolve()==Path(paths[i]).resolve() for v in current_bank)
  if index not in unresolved and healthy(paths[i]) and placement[i]['fit'] and current_verified:continue
  row=timing.get(index,{});record=next((v for v in old if v.get('index')==index and v.get('text')==cue.get('cantonese') and verified_check(v.get('check',{}),cue.get('cantonese',''),cfg.get('targetLanguage','yue'))),None)
  path=Path(row.get('renderedAudio','')).resolve()
  if not record or row.get('skipped') or row.get('originalFallback') or not path.is_relative_to(source) or not healthy(path):continue
  trial=list(lengths);trial[i]=seconds(path,cfg,run);proposed=plan(cfg,cues,trial)
  if not proposed[i]['fit'] or any(p['fit'] and not proposed[n]['fit'] for n,p in enumerate(placement)):continue
  output=Path(job)/'retained-best'/f'{index}.wav';output.parent.mkdir(exist_ok=True);shutil.copy2(path,output)
  selected[i]=output;lengths=trial;placement=proposed;confirmed.add(index)
  digest=hashlib.sha256(output.read_bytes()).hexdigest();ledger['retained-'+str(index)]=dict(record,audio=str(output),selectedAudio=str(output),audioSHA256=digest,selectedAudioSHA256=digest,status='adopted',retainedFromPreviousVersion=True)
 if confirmed:
  atomic_json(Path(job)/'target-reference-recovery.json',ledger);clear_confirmed(cfg,Path(job),confirmed,atomic_json)
  emit('保留較佳錄音',f'新試錄未優於已確認錄音；保留 {len(confirmed)} 句原有目標語言版本，聲線差異提示仍保留。',.90)
 return selected,placement
