"""Opt-in, one-operation audible overlap repair. Unknown speech stays unchanged."""
import hashlib,json,math,os,subprocess,sys,wave
from pathlib import Path
REVISION='optional-audible-overlap-repair-1'
THRESHOLD=2.
def read(path):
 try:return json.loads(Path(path).read_text())
 except (OSError,ValueError):return {}
def union(spans):
 result=[]
 for a,b in sorted(spans):
  if b<=a:continue
  if result and a<=result[-1][1]:result[-1][1]=max(result[-1][1],b)
  else:result.append([a,b])
 return result

def overlap_seconds(cues,spans,index):
 own=cues[index];start=float(own.get('speechStart',own['start']))
 later=[(float(c.get('speechStart',c['start']))+a,float(c.get('speechStart',c['start']))+b) for j,c in enumerate(cues) if j!=index and float(c.get('speechStart',c['start']))>start and not c.get('preserveOriginalSpeech') for a,b in spans.get(j,[])]
 intersections=[(max(start+a,x),min(start+b,y)) for a,b in spans.get(index,[]) for x,y in later if min(start+b,y)>max(start+a,x)]
 return sum(b-a for a,b in union(intersections))

def detect(cfg,job,cues,paths,run):
 """A local VAD supplies speech evidence; amplitude alone never grants a retake."""
 from runtime_paths import python_for
 from worker import atomic_json
 folder=Path(job)/'audible-overlap';folder.mkdir(exist_ok=True)
 rows=[]
 for i,(cue,path) in enumerate(zip(cues,paths)):
  if cue.get('preserveOriginalSpeech') or not cue.get('enabled',True) or not Path(path).is_file() or Path(path).name.startswith('skipped-'):continue
  key=hashlib.sha256(Path(path).read_bytes()).hexdigest()[:24];cache=folder/(key+'.json')
  if not cache.exists():
   req=folder/(key+'-request.json');atomic_json(req,dict(audio=str(path),ffmpeg=cfg['ffmpeg']))
   runtime=None
   for candidate in dict.fromkeys([python_for(cfg['storage'],'asr-runtime'),python_for(cfg['storage'],'runtime')]):
    if candidate.is_file():
     probe=subprocess.run([candidate,'-B','-c',"import importlib.util;raise SystemExit(0 if importlib.util.find_spec('faster_whisper') else 2)"],capture_output=True,timeout=10)
     if probe.returncode==0:runtime=candidate;break
   if runtime is None:raise ValueError('Installed local VAD runtime unavailable; no download requested')
   result=subprocess.run([runtime,'-B',str(Path(__file__).resolve()),str(req)],capture_output=True,text=True,timeout=120,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
   if result.returncode:raise ValueError(result.stderr[-500:] or 'Speech evidence unavailable')
   value=json.loads(result.stdout);atomic_json(cache,value)
  value=read(cache)
  if value.get('status')!='speech-evidence':raise ValueError('Unconfirmed speech intervals')
  rows.append((i,value['spans']))
 return dict(rows)

def repair(cfg,job,cues,paths,run,emit):
 from worker import atomic_json,ollama_chat
 from types import SimpleNamespace
 from normal_mode import audio_present
 from natural_delivery import seconds,recover_batch
 from concise_dialogue import compact,units
 from dubbing import gsv_audio,is_vocalization
 from repair_limits import check
 from normal_policy import finish_requested
 from track_control import UserSkipped
 selected=list(paths);job=Path(job);ledger_path=job/'audible-overlap-repairs.json';ledger=read(ledger_path);language=cfg.get('targetLanguage','yue')
 try:
  # Recover accepted candidates first; resume must not spend another operation.
  for i,cue in enumerate(cues):
   key=str(cue.get('reviewIndex',i)+1);entry=ledger.get(key,{})
   if entry.get('status')=='accepted' and cue.get('cantonese') in (entry.get('beforeText'),entry.get('text')) and audio_present(entry.get('audio')) and hashlib.sha256(Path(entry['audio']).read_bytes()).hexdigest()==entry.get('sha'):
    selected[i]=Path(entry['audio']);cue['cantonese']=entry['text'];cue['overlapRepair']=dict(revision=REVISION,previous=entry['beforeText'])
  spans=detect(cfg,job,cues,selected,run)
 except (OSError,RuntimeError,ValueError,subprocess.TimeoutExpired) as error:
  atomic_json(job/'audible-overlap-report.json',dict(status='unconfirmed',error=str(error),action='retain-first-audible'))
  emit('重疊提示','無法確認有聲重疊，保留首輪錄音。');return selected
 reports=[]
 for i,(cue,path) in enumerate(zip(cues,selected)):
  if cue.get('editorAudio') or cue.get('preserveOriginalSpeech') or is_vocalization(cue) or not audio_present(path):continue
  amount=overlap_seconds(cues,spans,i);key=str(cue.get('reviewIndex',i)+1);reports.append(dict(index=int(key),audibleOverlapSeconds=round(amount,4),thresholdSeconds=THRESHOLD))
  if amount<=THRESHOLD+1e-7 or key in ledger or finish_requested(cfg):continue
  length=seconds(path,cfg,run);available=max(.3,length-(amount-THRESHOLD)-.15)
  entry=dict(status='reserved',beforeText=cue.get('cantonese',''),originalAudio=str(path),beforeOverlap=amount,availableSeconds=available,maximumOperations=1);ledger[key]=entry;atomic_json(ledger_path,ledger)
  drafts=[dict(c) for c in cues];w=SimpleNamespace(atomic_json=atomic_json,ollama_chat=lambda *args,**kwargs:ollama_chat(*args,**dict(kwargs,max_attempts=1)))
  try:
   check();targets={i:max(1,round(units(cue['cantonese'],language)*available/length*.95))}
   local=dict(cfg,_generationPurpose='timing',_maximumTimingOperations=1,_measuredOverruns={str(i):dict(seconds=length,availableSeconds=available)})
   changed=compact(w,local,job,drafts,[i],targets,field='cantonese')
   if not changed:entry.update(status='no-safe-shorter-draft');continue
   batch=job/'audible-overlap'/('retake-'+key);batch.mkdir(parents=True,exist_ok=True)
   entry.update(status='generating',text=drafts[i]['cantonese'],batch=str(batch));atomic_json(ledger_path,ledger)
   emit('重疊修正',f'第 {key} 句有聲重疊 {amount:.2f} 秒；只縮稿重錄一次，保留原聲線。')
   candidates=gsv_audio(dict(local,editorCache=str(batch),audioRerunToken=REVISION+key),batch,[dict(drafts[i],reviewIndex=int(key)-1,_targetSeconds=available)],run,emit)
   if not candidates or not audio_present(candidates[0]):entry.update(status='retake-missing-retain-first');continue
   proposed=list(selected);proposed[i]=Path(candidates[0]);fresh=detect(cfg,job,cues,proposed,run);after=overlap_seconds(cues,fresh,i)
   if after>=amount-.01 or seconds(proposed[i],cfg,run)>=length:
    entry.update(status='no-improvement-retain-first',afterOverlap=after,audio=str(proposed[i]));continue
   selected=proposed;spans=fresh;cue['cantonese']=drafts[i]['cantonese'];cue['overlapRepair']=dict(revision=REVISION,previous=entry['beforeText']);entry.update(status='accepted',afterOverlap=after,audio=str(proposed[i]),sha=hashlib.sha256(proposed[i].read_bytes()).hexdigest())
  except UserSkipped:raise
  except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired) as error:entry.update(status='failed-retain-first',error=str(error)[:500])
  finally:atomic_json(ledger_path,ledger)
 atomic_json(job/'audible-overlap-report.json',dict(status='measured',rows=reports,retakeLimit=1,qualityCertified=False))
 return selected

if __name__=='__main__':
 import numpy as np
 from faster_whisper.vad import get_speech_timestamps,VadOptions
 request=read(sys.argv[1]);raw=subprocess.check_output([request['ffmpeg'],'-v','error','-i',request['audio'],'-ar','16000','-ac','1','-f','f32le','pipe:1'])
 samples=np.frombuffer(raw,dtype=np.float32)
 spans=get_speech_timestamps(samples,VadOptions(min_speech_duration_ms=150,min_silence_duration_ms=100,speech_pad_ms=0))
 print(json.dumps(dict(status='speech-evidence',detector='local-silero-vad; not linguistic certification',spans=[[s['start']/16000,s['end']/16000] for s in spans])))
