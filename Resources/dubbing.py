"""Local dubbing orchestration; no model libraries in the main media worker."""
from whisper_audio import load as whisper_pcm
import array
import hashlib
import json
import math
import os
import re
from pathlib import Path
import subprocess
import time
import threading
import wave
from fast_mode import enabled as one_pass

REVISION='gsv-v2-mel-kj-1'
MAX_TEMPO=1.25


def model_job(cfg, action, request, emit):
 if one_pass(cfg):return _model_job(cfg,action,dict(request,productionMode=cfg['productionMode']),emit)
 from runtime_recovery import run
 return run(cfg,action,request,emit,_model_job)


def _model_job(cfg, action, request, emit):
 from execution_timing import measure
 folder=request.get('job') or request.get('out') or cfg.get('storage')
 if folder:
  with measure(folder,'model:'+action,items=len(request.get('items',[])),engine=cfg.get('ttsBackend'),language=cfg.get('targetLanguage','yue')):
   return _model_job_impl(cfg,action,request,emit)
 return _model_job_impl(cfg,action,request,emit)


def _model_job_impl(cfg, action, request, emit):
 from recording_history import preserve_request
 if action in ('tts','cosy','qwen','voxcpm2','wsyue','drama3') and request.get('items'):
  from take_reuse import recover,archive
  try:
   archive(request['job'],request,action)
   recover(request['job'],request,action,emit)
  except (OSError,ValueError) as error:emit('錄音沿用','快取沿用未完成，按原有生成流程繼續：'+str(error))
  from audio_fallback import healthy
  if request.get('items') and all(healthy(i['output']) for i in request['items']):
   emit('配音','全部片段已有完成錄音，跳過模型載入。',workID='tts',workCompleted=len(request['items']),workTotal=len(request['items']),primaryGeneration=bool(request.get('primaryGeneration')))
   return
 preserve_request(cfg,action,request)
 try:
  return _run_model_job(cfg,action,request,emit)
 finally:
  preserve_request(cfg,action,request)


def _run_model_job(cfg, action, request, emit):
 from runtime_paths import python_for
 request=dict(request,asrModel=cfg.get('asrModel'))
 if action in ('tts','cosy','qwen','voxcpm2','wsyue','drama3') and cfg.get('_trackControl'):
  request['_trackControl']=cfg['_trackControl']
  from track_control import check
  check(request)
 from model_handoff import release_text
 release_text(cfg,emit)
 root=Path(cfg['storage']);kind='drama3' if action=='drama3' else 'local-tts' if action in ('voxcpm2','wsyue','drama3') else 'asr' if action in ('asr','normal-listen') else ('separator' if action in ('separate','speakers','independent-voices') else ('qwen' if action=='qwen' else 'cosy' if action=='cosy' else 'gsv'))
 python=python_for(root,'text-runtime' if kind=='drama3' else f'{kind}-runtime')
 if not python.exists() or not (root/f'{kind}-ready.json').exists():
  label={'asr':'日語核對模型','separator':'背景分離模型','cosy':'CosyVoice 3','gsv':'GPT-SoVITS','qwen':'Qwen3-TTS','local-tts':'VoxCPM2 / WenetSpeech-Yue','drama3':'Drama 3'}[kind]
  raise ValueError('請先到「環境與模型」部署 '+label+'。')
 req=Path(request['out'] if action=='separate' else request['job'])/f'{action}-request.json'
 req.parent.mkdir(parents=True,exist_ok=True);req.write_text(json.dumps(request,ensure_ascii=False))
 env=os.environ.copy();env['PATH']=str(Path(cfg['ffmpeg']).parent)+os.pathsep+env.get('PATH','');env['PYTORCH_ENABLE_MPS_FALLBACK']='1';env['ORT_DISABLE_TELEMETRY']='1'
 log=req.with_suffix('.log');error=None
 with open(log,'w') as errors:
  script='normal_mode.py' if action=='normal-listen' else 'drama3.py' if action=='drama3' else 'asr_verify.py' if action=='asr' else 'qwen_voice.py' if action=='qwen' else 'dubbing_runner.py'
  p=subprocess.Popen([str(python),str(Path(__file__).with_name(script)),action,str(req)],stdout=subprocess.PIPE,stderr=errors,env=env,text=True)
  # A stalled model must not hold the queue indefinitely. Progress events reset
  # the deadline; termination is of this child only, not another user process.
  last=[time.monotonic()];stalled=[False];finish_now=[False];finished=threading.Event()
  def watchdog():
   while not finished.wait(2):
    from normal_policy import finish_requested
    if action=='normal-listen' and finish_requested(cfg):
     finish_now[0]=True;p.terminate();return
    if time.monotonic()-last[0]>float(cfg.get('modelStallSeconds',600)):
     stalled[0]=True;p.terminate()
     try:p.wait(timeout=10)
     except subprocess.TimeoutExpired:p.kill()
     return
  threading.Thread(target=watchdog,daemon=True).start()
  for line in p.stdout:
   last[0]=time.monotonic()
   try:
    event=json.loads(line)
    if event.get('stage')=='錯誤': error=event['message']
    fields={key:event[key] for key in ('cueIndex','workID','workCompleted','workTotal','componentProgress') if event.get(key) is not None}
    if fields.get('workID')=='tts' and 'primaryGeneration' in request:fields['primaryGeneration']=bool(request['primaryGeneration'])
    emit(event['stage'],event['message'],event.get('progress'),**fields)
   except (json.JSONDecodeError,KeyError): pass
  code=p.wait();finished.set()
  if stalled[0]:raise RuntimeError('模型超過等待上限；已保存成功錄音，未完成片段列入摘要。')
 if finish_now[0]:return
 if code:
  from track_control import check
  check(request)
  detail=error or model_error_detail(log.read_text(errors='replace'))
  reason=f'訊號 {-code}' if code<0 else f'退出碼 {code}'
  raise RuntimeError(f'模型程序異常結束（{reason}）：{detail}（詳見 {log}）')


def model_error_detail(log):
 lines=[line.strip() for line in log.splitlines() if line.strip() and not re.search(r'\d+%\|.*\d+/\d+\s*\[',line)]
 return '\n'.join(lines[-5:])[-900:] or '未有詳細錯誤紀錄。'


def validate_stems(cfg, folder, run, emit=None):
 # Container duration can exceed decoded OPUS audio by a few trailing packets.
 # Only repair a small, common tail discrepancy verified against the actual input.
 measurements=[]
 for name in ('background.wav','dialogue.wav'):
  path=folder/name
  if not path.is_file(): raise RuntimeError('背景分離缺少 '+name+'；未標記為完成。')
  meta=json.loads(run([cfg['ffprobe'],'-v','error','-show_format','-show_streams','-of','json',path]))
  audio=next((s for s in meta.get('streams',[]) if s.get('codec_type')=='audio'),{})
  duration=float(meta.get('format',{}).get('duration',0))
  if audio.get('channels')!=2 or not math.isfinite(duration) or abs(duration-cfg['duration'])>.25:
   raise RuntimeError('背景分離音軌長度／聲道唔完整：'+name+'；未標記為完成。')
  measurements.append((path,duration))
 if any(abs(duration-cfg['duration'])>.001 for _,duration in measurements):
  source=folder/'original.wav'
  if not source.is_file():raise RuntimeError('背景分離缺少原音訊作長度核對；未標記為完成。')
  meta=json.loads(run([cfg['ffprobe'],'-v','error','-show_format','-show_streams','-of','json',source]))
  audio=next((s for s in meta.get('streams',[]) if s.get('codec_type')=='audio'),{})
  duration=float(meta.get('format',{}).get('duration',0))
  if audio.get('channels')!=2 or not math.isfinite(duration) or abs(duration-cfg['duration'])>.25 or any(abs(value-duration)>.001 for _,value in measurements):
   raise RuntimeError('背景分離同原音訊長度不一致；未標記為完成。')
  for path,_ in measurements:
   tmp=path.with_name(path.stem+'.aligned.wav')
   try:
    run([cfg['ffmpeg'],'-v','error','-y','-i',path,'-af','apad','-t',str(cfg['duration']),'-ac','2','-ar','44100','-c:a','pcm_f32le',tmp])
    # Verify the repaired file before replacing the successfully generated stem.
    repaired=json.loads(run([cfg['ffprobe'],'-v','error','-show_format','-show_streams','-of','json',tmp]))
    streams=repaired.get('streams',[])
    repaired_duration=float(repaired.get('format',{}).get('duration',0))
    if not any(s.get('codec_type')=='audio' and s.get('channels')==2 for s in streams) or not math.isfinite(repaired_duration) or abs(repaired_duration-cfg['duration'])>.001:
     raise RuntimeError('音軌片尾對齊失敗；未標記為完成。')
    tmp.replace(path)
   finally:tmp.unlink(missing_ok=True)
  if emit:emit('分離修正','已核對原音訊，自動對齊片尾長度；保留已完成嘅背景及對白音軌。',.18)


def separate(cfg, run, emit):
 video=Path(cfg['video']);stat=video.stat()
 identity=[str(video.resolve()),stat.st_size,stat.st_mtime_ns,cfg.get('startOffset',0),cfg['duration'],REVISION,cfg.get('sourceAudioStream')]
 key=hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:20]
 folder=Path(cfg['storage'])/'separations'/key;folder.mkdir(parents=True,exist_ok=True)
 bg=folder/'background.wav';dialogue=folder/'dialogue.wav'
 ready=False
 if bg.is_file() and dialogue.is_file():
  try:
   validate_stems(cfg,folder,run,emit);ready=True
  except (RuntimeError,ValueError,subprocess.CalledProcessError):pass
 if not ready:
  emit('分離','抽取所選片段，準備分離日語對白。',0.06)
  source=folder/'original.wav'
  run([cfg['ffmpeg'],'-v','error','-y','-ss',str(cfg.get('startOffset',0)),'-i',video,'-map',f"0:{cfg['sourceAudioStream']}" if cfg.get('sourceAudioStream') is not None else '0:a:0','-t',str(cfg['duration']),'-vn','-af','apad','-ac','2','-ar','44100','-c:a','pcm_s16le',source])
  model_job(cfg,'separate',dict(storage=cfg['storage'],input=str(source),out=str(folder),device=cfg.get('separationDevice','mps')),emit)
  validate_stems(cfg,folder,run,emit)
 (folder/'complete.json').write_text(json.dumps(identity))
 emit('背景已就緒','可獨立試聽背景軌，檢查音效同日語殘留。',0.18,background=str(bg),dialogue=str(dialogue))
 return bg,dialogue


def profile_for(cue,cfg):
 profiles=cfg.get('voiceProfiles',[])
 ident=cue.get('speakerId') or cfg.get('defaultSpeaker')
 profile=next((p for p in profiles if p['id']==ident),None)
 if not profile: raise ValueError('請為每句配音選擇角色，並設定角色參考聲音。')
 key=cfg.get('ttsBackend','gpt-sovits')+':'+cfg.get('targetLanguage','yue')
 own=(profile.get('engineReferences') or {}).get(key,{})
 if own.get('enabled'):profile=dict(profile,reference=own.get('reference',''),promptText=own.get('promptText',''),language=own.get('language') or cfg.get('targetLanguage','yue'),mixedReference=False,shortReference=False,referenceRanges=[],referenceCandidates=[],referenceQuality={})
 if cfg.get('voiceStyleMode')=='natural':
  if own.get('enabled') and profile.get('language')!=cfg.get('targetLanguage','yue'):
   raise ValueError('自然配音嘅獨立參考必須同目標語言一致。')
  from natural_voices import resolve
  profile=resolve(profile,cfg)
 if not Path(profile.get('reference','')).is_file() or not profile.get('promptText','').strip(): raise ValueError(f'{profile["name"]} 未有參考聲音或參考原文。')
 return profile


def required_dialogue(cfg,cues):
 from workflow_policy import original_allowed
 return [(c.get('reviewIndex',i)+1,c) for i,c in enumerate(cues)
         if c.get('enabled',True) and c.get('cantonese','').strip()
         and not original_allowed(cfg,c) and not is_vocalization(c)
         and not (cfg.get('editorRender') and c.get('editorAudio'))]


def require_profiles(cfg,cues):
 required=required_dialogue(cfg,cues)
 if not required:return
 for _,cue in required:
  try:profile_for(cue,cfg);return
  except (ValueError,OSError):pass
 raise ValueError('全部對白未有可用角色參考；請先自動配對角色或設定參考聲音。未生成配音，未交付無聲配音軌。')


def generated_dialogue(cfg,job,cues,report=None):
 required={i for i,_ in required_dialogue(cfg,cues)}
 path=Path(job)/'timing.json'
 if not required or not path.is_file():return None
 rows=json.loads(path.read_text())
 delivered={r['index'] for r in rows if r.get('index') in required and not r.get('skipped') and r.get('renderedSeconds',0)>0}
 delivered.update(r['index'] for r in (report or {}).get('audioFallbacks',[]) if r.get('index') in required and r.get('sourceLanguage')==cfg.get('targetLanguage','yue'))
 return len(delivered)


def gsv_audio(cfg,job,cues,run,emit):
 job=Path(job).resolve()
 primary_generation=bool(cfg.pop('_primaryGenerationPending',False))
 from natural_voices import prepare_cast
 prepare_cast(cfg,job,cues,run)
 backend=cfg.get("ttsBackend","gpt-sovits")
 if backend not in ("gpt-sovits","gpt-sovits-v2","gpt-sovits-v3","cosyvoice3","qwen-tts","voxcpm2","wsyue","drama3"): raise ValueError("請選擇角色配音引擎。")
 if backend in ('voxcpm2','wsyue','drama3'):
  from local_tts import validate
  validate(cfg,backend)
 if backend.startswith('gpt-sovits'):
  from gsv_versions import version
  cfg['gsvVersion']=version(cfg)
  cfg['gsvReferenceMode']='original'
  if int(cfg.get('gsvSampleSteps',32)) not in (16,32):raise ValueError('V4 配音製作模式無效。')
  if cfg.get('targetLanguage','yue')=='yue':
   from cantonese_pronunciation import rules as pronunciation_rules
   pronunciation_rules(cfg.get('cantonesePronunciationText',''))
 reference_profiles={}
 eligible={}
 if cfg.get('voiceStyleMode')=='natural':
  from natural_voices import record
  cast={}
  for cue in cues:
   try:
    p=profile_for(cue,cfg);cast[p['id']]=p
   except (ValueError,OSError):pass
  record(cfg,job,list(cast.values()))
 if backend.startswith('gpt-sovits') or (backend in ('cosyvoice3','voxcpm2','wsyue','drama3','qwen-tts') and cfg.get('voiceStyleMode')=='clone'):
  eligible={}
  for cue in cues:
   if cue.get('editorAudio') or cue.get('preserveOriginalSpeech'):continue
   try:
    profile=profile_for(cue,cfg)
    if profile['id'] in eligible or profile['id'] in reference_profiles:continue
    from reference_recovery import prepare as recover_reference
    try:profile=profile if one_pass(cfg) else recover_reference(cfg,job,profile,run,emit)
    except ValueError as error:
     if not cfg.get('continueOnError',True):raise
     reference_profiles[profile['id']]={'referenceError':str(error)};continue
    eligible[profile['id']]=profile
   except (ValueError,OSError):
    if not cfg.get("continueOnError",True):raise
    continue
  from gsv_reference import prepare as prepare_gpt_references
  if not one_pass(cfg):reference_profiles.update(prepare_gpt_references(dict(cfg,ttsBackend='gpt-sovits',gsvReferenceMode='original'),job,list(eligible.values()),run,emit))
 for ident,p in eligible.items():reference_profiles.setdefault(ident,p)
 items=[];paths=[]
 for cue in cues:
  count=len(paths)
  try:
   if cue.get('missingScript') or (not cue.get('cantonese','').strip() and cue.get('originalSpeechReason')=='missing-script'):
    raise ValueError('未有有效翻譯稿；未交畀配音引擎，禁止日文補聲。')
   if (cfg.get("editorRender") or cfg.get('_reviewRetry') or cue.get('_retryRetained')) and cue.get("editorAudio"):
    paths.append(Path(cue["editorAudio"]));continue
   stem=Path(cfg.get('dialoguePath',''))
   from workflow_policy import original_allowed
   if cue.get('preserveOriginalSpeech') and not original_allowed(cfg,cue):cue['preserveOriginalSpeech']=False
   if original_allowed(cfg,cue) or (is_vocalization(cue) and stem.is_file()):
    separated=stem.is_file()
    source=stem if separated else Path(cfg['video'])
    start=cue['start']+(0 if separated else float(cfg.get('startOffset',0)))
    from audio_format import delivery_rate
    preserved_rate=delivery_rate(cfg)
    identity=[str(source),source.stat().st_mtime_ns,start,cue['end']-cue['start'],'preserved-performance-native-rate-2',preserved_rate]
    key=hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:24]
    path=job/f'original-vocalization-{key}.wav';paths.append(path)
    if not path.exists():
     run([cfg['ffmpeg'],'-v','error','-y','-ss',str(start),'-i',source,'-t',str(cue['end']-cue['start']),'-ar',str(preserved_rate),'-ac','1','-c:a','pcm_s16le',path])
    emit('配音',f'校稿第 {cue.get("reviewIndex",0)+1} 句：'+('按本段設定保留原聲。' if original_allowed(cfg,cue) else '保留角色原聲氣息（非語言發聲）。'),.8)
    continue
   profile=profile_for(cue,cfg)
   original_hash=hashlib.sha256(Path(profile['reference']).read_bytes()).hexdigest()
   if cfg.get('_voiceManifest',{}).get(profile['id'],original_hash)!=original_hash:
    raise ValueError('配音途中角色參考聲音有變，已保留進度；請重新開始。')
   profile=reference_profiles.get(profile['id'],profile)
   if profile.get('referenceError'):raise ValueError(profile['referenceError'])
   if cfg.get('voiceStyleMode')=='clone' and profile.get('transcriptSource')=='original-japanese-words' and len(profile.get('referenceRanges',[]))>1:
    raise ValueError('原角色模仿未有完整、已核對原文嘅連續參考；請匯入清晰完整原聲。')
   if cfg.get('voiceStyleMode'):
    cue['voiceStyleMode']=cfg['voiceStyleMode']
    cue['naturalReferenceId']=profile.get('naturalReferenceId','')
   if not one_pass(cfg) and backend in ('qwen-tts','gpt-sovits','gpt-sovits-v2','gpt-sovits-v3'):
    from qwen_reference import prepare
    profile=prepare(dict(cfg,ttsBackend=backend),job,profile,emit)
   if cfg.get('independentReferences',True) and ((backend=='qwen-tts' and cfg.get('qwenReferenceMode','original')=='original') or (backend.startswith('gpt-sovits') and cfg.get('gsvReferenceMode','original')=='original') or backend in ('cosyvoice3','voxcpm2','wsyue','drama3')):
    from engine_reference import prepare as engine_prepare
    profile=engine_prepare(dict(cfg,ttsBackend=backend),job,profile,run)
    manifest=json.loads(Path(profile['referenceProvenance']).read_text()) if profile.get('referenceProvenance') else {}
    if profile.get('referenceProvenance') and profile['referenceProvenance'] not in cfg.setdefault('_referenceNotices',[]):
     cfg['_referenceNotices'].append(profile['referenceProvenance'])
     level=manifest.get('quality',{})
     cleanup=manifest.get('cleanup',{})
     if emit:emit('參考錄音檢查',f"{backend} · {profile.get('name','')}：音量補償 {level.get('gainDB',0):+.1f} dB；有效聲音 {level.get('activeSeconds',0):.1f} 秒；改用較乾淨同角色原聲：{bool(manifest.get('selectedAlternate'))}；輕量降噪：{bool(cleanup.get('applied'))}。純度未認證，原錄音仍保留。")
   from pronunciation import spoken
   spoken_text=cue['cantonese'] if cfg.get('targetLanguage')=='en' else spoken(cfg,cue['cantonese'])
   from cantonese_pronunciation import matching
   readings=matching(cfg.get('cantonesePronunciationText',''),spoken_text) if backend.startswith('gpt-sovits') and cfg.get('targetLanguage','yue')=='yue' else {}
   fingerprint=hashlib.sha256(Path(profile['reference']).read_bytes()).hexdigest()
   from voice_expression import settings as expression_settings
   expression=expression_settings(cfg)
   from voice_parameters import overrides as voice_parameter_overrides
   parameter_overrides=voice_parameter_overrides(cfg,backend)
   identity=[REVISION,cfg.get('productionMode','standard'),backend,"cosy-yue-instruct-trim-1",cfg.get('gsvDevice','mps'),cue['cantonese'],{k:profile.get(k) for k in ('id','promptText','language')},fingerprint]
   if backend in ('gpt-sovits','gpt-sovits-v2','gpt-sovits-v3','cosyvoice3'):identity.append(['expression-settings-1',expression])
   if backend=='qwen-tts':identity.append('qwen-auto-dialect-verified-4')
   if backend.startswith('gpt-sovits'):
    from speech_level import REVISION as level_revision
    identity.extend(['gsv-versions-native-prompt-1',cfg['gsvVersion'],level_revision,int(cfg.get('gsvSampleSteps',32))])
   if cfg.get('voiceStyleMode'):identity.extend(['voice-style',cfg['voiceStyleMode'],profile.get('naturalReferenceId','')])
   identity.extend([cfg.get('targetLanguage','yue'),cfg.get('qwenModel') if backend=='qwen-tts' else cfg.get('cosyModel') if backend=='cosyvoice3' else cfg.get('gsvVersion','v4')])
   if backend in ('voxcpm2','wsyue','drama3'):
    from local_tts import selection,REVISION as local_revision
    identity.extend([local_revision,selection(cfg,backend),cfg.get('voxcpmDevice','mps') if backend=='voxcpm2' else cfg.get('nativeDramaFormat','mlx') if backend=='drama3' else 'cpu'])
   if backend=='drama3':
    from drama3 import REVISION as drama_revision
    identity.append(drama_revision)
   if parameter_overrides:identity.append(['expert-voice-parameters-1',parameter_overrides])
   if cfg.get('audioRerunToken'):identity.extend(['audio-rerun',cfg['audioRerunToken']])
   if spoken_text!=cue['cantonese']:identity.extend(['spoken-alias',spoken_text])
   if readings:identity.extend(['v4-jyutping-1',readings])
   if cue.get('_deliveryStyle'): identity.append(cue['_deliveryStyle'])
   if cue.get('_seed'): identity.extend([cue['_seed'],cue.get('_targetSeconds')])
   key=hashlib.sha256(json.dumps(identity,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:24]
   cache=Path(cfg.get('editorCache',job));cache.mkdir(parents=True,exist_ok=True)
   path=cache/f'{backend}-{key}.wav';paths.append(path)
   if not one_pass(cfg) and backend.startswith('gpt-sovits') and path.exists():
    import numpy as np
    from tts_health import problems
    with wave.open(str(path)) as f:
     health=problems(np.frombuffer(f.readframes(f.getnframes()),dtype='<i2'),f.getframerate(),spoken_text)
    if health:path.rename(path.with_suffix('.rejected.wav'))
   items.append(dict(profile=profile,text=spoken_text,cantoneseReadings=readings,approvedText=cue.get('_approvedText',cue['cantonese']),output=str(path),reviewIndex=cue.get('reviewIndex'),deliveryStyle=cue.get('_deliveryStyle','cantonese-strict' if cfg.get('productionMode')=='normal' and cfg.get('targetLanguage','yue')=='yue' else 'normal'),seed=cue.get('_seed',42),targetSeconds=cue.get('_targetSeconds'),expressionSettings=expression))
  except (ValueError,RuntimeError) as error:
   if not cfg.get('continueOnError',True):raise
   from project_store import record_issue
   record_issue(cfg,job,cue,'missing-script' if cue.get('missingScript') else 'reference',error)
   emit('跳過待修正',f"第 {cue.get('reviewIndex',0)+1} 段參考聲音無效：{error}；繼續其他對白。")
   silence=job/f"skipped-{backend}-{cue.get('reviewIndex',count)}.wav"
   with wave.open(str(silence),'wb') as f:
    f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(bytes(round(max(.1,cue['end']-cue['start'])*24000)*2))
   paths[count:]=[silence]
 from worker import atomic_json
 from audio_manifest import publish
 publish(job,backend,cfg.get('targetLanguage','yue'),cues,paths)
 if any(not Path(item['output']).exists() for item in items):
  request=dict(gsvVersion=cfg.get('gsvVersion','v4'),storage=cfg['storage'],job=str(job),items=items,device=cfg.get('gsvDevice','mps'),sampleSteps=int(cfg.get('gsvSampleSteps',32)),targetLanguage=cfg.get('targetLanguage','yue'),qwenModel=cfg.get('qwenModel'),cosyModel=cfg.get('cosyModel'),voxcpmModel=cfg.get('voxcpmModel'),wsyueModel=cfg.get('wsyueModel'),drama3Model=cfg.get('drama3Model'),voxcpmDevice=cfg.get('voxcpmDevice','mps'),localTTSThreads=cfg.get('localTTSThreads',2),audioRerunToken=cfg.get('audioRerunToken'))
  from voice_parameters import overrides as voice_parameter_overrides
  request.update(voice_parameter_overrides(cfg,backend))
  request['primaryGeneration']=primary_generation
  try:
   if backend=='qwen-tts':
    from qwen_recovery import generate
    generate(cfg,job,request,emit,model_job)
   else:model_job(cfg,backend if backend in ('voxcpm2','wsyue','drama3') else 'cosy' if backend=='cosyvoice3' else 'tts',request,emit)
  except (RuntimeError,ValueError) as error:
   from track_control import UserSkipped
   skipped=isinstance(error,UserSkipped)
   if not cfg.get('continueOnError',True) and not skipped:raise
   if skipped:cfg['_userSkipped']=True
   from project_store import record_issue
   paths=[Path(cfg.get('_runtimeReplacements',{}).get(str(p),str(p))) for p in paths]
   for i,(cue,path) in enumerate(zip(cues,paths)):
    if path.is_file():continue
    failure=path.with_suffix('.failure.json')
    try:detail=json.loads(failure.read_text()).get('error') or str(error)
    except (OSError,ValueError):detail=str(error)
    record_issue(cfg,job,cue,'user-skipped' if skipped else 'tts-generation',detail)
    notice="高速模式不重錄，缺聲已記錄" if one_pass(cfg) else "稍後自動補聲"
    emit('跳過待修正',f"{backend} 第 {cue.get('reviewIndex',i)+1} 段：本次生成未完成，{notice}；繼續其他對白。{detail[:180]}")
    silence=job/f"skipped-{backend}-{cue.get('reviewIndex',i)}.wav"
    with wave.open(str(silence),'wb') as f:
     f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(bytes(round(max(.1,cue['end']-cue['start'])*24000)*2))
    paths[i]=silence
 resolved=[Path(cfg.get('_runtimeReplacements',{}).get(str(p),str(p))) for p in paths]
 if cfg.get('_userSkipped') or one_pass(cfg):return resolved
 from speech_level import prepare_file
 levels=[];leveled=[]
 for cue,path in zip(cues,resolved):
  if path.is_file() and not path.name.startswith('skipped-'):
   target,level=prepare_file(path,job/'leveled-takes')
   raw_level=json.loads(path.with_suffix('.level.json').read_text()) if path.with_suffix('.level.json').is_file() else {}
   level=dict(level,synthesisLevel=raw_level,totalGainDB=round(level.get('gainDB',0)+raw_level.get('gainDB',0),2),warnings=list(dict.fromkeys(level.get('warnings',[])+raw_level.get('warnings',[]))))
   leveled.append(target if abs(level.get('gainDB',0))>.01 else path);levels.append(dict(level,index=cue.get('reviewIndex'),engine=backend,language=cfg.get('targetLanguage','yue')))
  else:leveled.append(path)
 atomic_json(job/'speech-levels.json',levels)
 publish(job,backend,cfg.get('targetLanguage','yue'),cues,leveled)
 boosted=sum(r.get('totalGainDB',r.get('gainDB',0))>.5 for r in levels);limited=sum(bool(r.get('warnings')) for r in levels)
 if emit:emit('音量摘要',f"{backend} · {cfg.get('targetLanguage','yue')}：{boosted} 段已補償細聲；{limited} 段達到增益上限或有訊號提示。只校正音量，語言／內容仍會獨立覆聽。")
 return leveled


def is_vocalization(cue):
 if cue.get("nonlexicalTail"):return True
 source=re.sub(r'[\s、。！？!?…ーっッ]', '',cue.get('japanese',''))
 target=re.sub(r'\W','',cue.get('cantonese',''))
 prolonged_vowels=len(source)>=3 and re.fullmatch(r'[あぁアァいぃイィうぅウゥえぇエェおぉオォ]+',source)
 return bool((source in ('あ','ああ','ア','アア','はあ','はぁ','うう','うぅ') or prolonged_vowels) and len(cue.get('sourceParts',[cue]))==1 and (not target or target in ('啊','呀','吓','嗚','哦','噢','唉','啊啊') or bool(target and set(target)<=set('啊呀吓嗚哦噢唉')) or re.fullmatch(r'(?:a+h+|o+h+|u+h+)',target,re.I)))


def candidate_content_matches(cfg,path,text,model=None,evidence=None):
 """A shorter take must still say the line, not merely produce a shorter WAV."""
 from difflib import SequenceMatcher
 from speechcheck import inspect,critical_omissions
 # Verification has its own installed ASR runtime. Never import its dependencies
 # into the conversion worker or keep another model resident beside TTS.
 verification=dict(cfg,pronunciationText='')  # text already passed through spoken()
 if evidence is None:evidence=inspect(verification,Path(path).parent,[dict(cantonese=text)],[path],lambda *args:None)[0]
 recognized=evidence.get('heard','')
 clean=lambda s: ''.join(c for c in s.lower() if c.isalnum())
 a,b=clean(text),clean(recognized)
 matched=bool(a and not evidence.get('languageMismatch') and not evidence.get('languageUnverified') and not critical_omissions(text,recognized) and len(b)>=max(1,math.ceil(len(a)*.95)) and len(b)<=len(a)*1.15+1 and SequenceMatcher(None,a,b).ratio()>=.92)
 return matched,recognized,None


def fit_rate(length,slot):
 if not math.isfinite(length) or length<=0 or not math.isfinite(slot) or slot<=0: raise ValueError('無效配音長度')
 rate=max(1.0,length/slot)
 return max(1.0,length/slot),rate<=MAX_TEMPO+1e-6


def short_line_limit(text,slot):
 """Permit moderate compression of a slowly generated short Chinese utterance.

 Never use this to squeeze a dense translation into an impossible speech window.
 Numbers and Latin names need pronunciation expansion, so keep the ordinary cap.
 """
 syllables=''.join(c for c in text if c.isalnum())
 if slot>=.65 and 2<=len(syllables)<=10 and all('\u3400'<=c<='\u9fff' for c in syllables) and len(syllables)/slot<=5.5:
  return 1.5
 return MAX_TEMPO


def natural_rate_limit(cfg,text,slot):
 # Explicit editor rates remain a user choice. Automatic fitting must never
 # turn a slow short rendition into 1.5x speech just because it has few words.
 return min(short_line_limit(text,slot),1.15)


def synthesize(cfg,job,cues,run,emit):
 cfg['_primaryGenerationPending']=True
 if one_pass(cfg):
  from fast_mode import synthesize as fast_synthesize
  return fast_synthesize(cfg,job,cues,run,emit)
 natural=cfg.get('speechRatePolicy')=='natural'
 import acoustics
 from natural_voices import prepare_cast
 prepare_cast(cfg,job,cues,run)
 require_profiles(cfg,cues)
 cfg['_voiceManifest']={}
 for cue in cues:
  cue.setdefault('_approvedText',cue.get('cantonese',''))
  try:
   profile=profile_for(cue,cfg)
   cfg['_voiceManifest'][profile['id']]=hashlib.sha256(Path(profile['reference']).read_bytes()).hexdigest()
  except (ValueError,OSError):
   # gsv_audio records a missing reference per cue so healthy roles can continue.
   if not cfg.get('continueOnError',True):raise
 (Path(job)/'voice-reference-manifest.json').write_text(json.dumps(cfg['_voiceManifest'],indent=2))
 if not cfg.get("editorRender"):acoustics.align(cfg,cues,run)
 preferred={}
 warnings=[]
 brisk_attempted=set()
 def seconds(path):
  info=json.loads(run([cfg['ffprobe'],'-v','error','-show_format','-of','json',path]))
  return float(info['format']['duration'])
 for attempt in range(2 if cfg.get("boundedRepairs") else 3):
  import delivery
  paths=delivery.synthesize(cfg,job,cues,gsv_audio,run,emit) if cfg.get('previewLooseTiming') else gsv_audio(cfg,job,cues,run,emit)
  if not cfg.get('previewLooseTiming'):
   trimmed=delivery.prepare_audio(cfg,job,paths,run)
   paths=[raw if is_vocalization(c) or c.get('preserveOriginalSpeech') or c.get('editorAudio') else clean for c,raw,clean in zip(cues,paths,trimmed)]
   originals=list(paths)
   from repair_budget import retained_takes,remember_takes
   paths=retained_takes(job,cues,originals)
   if cfg.get('autoValidate',True) and (Path(cfg.get('storage',''))/'asr-ready.json').is_file():
    try:paths=delivery.check_content(cfg,job,cues,paths,gsv_audio,run,emit)
    except (RuntimeError,ValueError,ImportError) as error:
     from track_control import UserSkipped
     if isinstance(error,UserSkipped):cfg['_userSkipped']=True
     elif not cfg.get('continueOnError',True):raise
     emit('核對待修正','內容核對未完成，保留錄音並列為待覆核：'+str(error))
     from worker import atomic_json
     atomic_json(job/'verification-error.json',dict(error=str(error),status='not-checked'))
   remember_takes(job,cues,originals,paths)
  if cfg.get('autoFit') and not natural:
   paths=delivery.match_natural_delivery(cfg,job,cues,paths,gsv_audio,run,emit)
  if natural:
   from natural_delivery import repair
   paths=repair(cfg,job,cues,paths,run,emit)
  lengths=[seconds(path) for path in paths]
  for i,cue in enumerate(cues):
   prior=preferred.get((i,cue['cantonese']))
   if prior and prior[1] < lengths[i]: paths[i],lengths[i]=prior
  slots=[min(c.get('deliveryEnd',c.get('speechEnd',c['end'])),cfg['duration'])-c.get('speechStart',c['start']) for c in cues]
  if natural:
   from speech_timing import natural_window
   slots=[b-a for a,b in (natural_window(c,cues,cfg['duration'],cfg) for c in cues)]
  if not natural and cfg.get('autoFit') and cfg.get('ttsBackend')=='cosyvoice3' and not cfg.get('previewLooseTiming'):
   pending=[i for i,(length,slot) in enumerate(zip(lengths,slots)) if not fit_rate(length,slot)[1] and (i,cues[i]['cantonese']) not in brisk_attempted]
   from repair_budget import claim
   pending=[i for i in pending if claim(cfg,job,cues[i],"brisk")]
   if pending:
    emit('語速調整',f'{len(pending)} 句超時，保留台詞用較爽快語氣重試一次。',.85)
    retry=gsv_audio(cfg,job,[dict(cues[i],_deliveryStyle='brisk') for i in pending],run,emit)
    for i,path in zip(pending,retry):
     brisk_attempted.add((i,cues[i]['cantonese']))
     length=seconds(path)
     if length < lengths[i]: paths[i]=path; lengths[i]=length
  for i,cue in enumerate(cues): preferred[(i,cue['cantonese'])]=(paths[i],lengths[i])
  report=[];bad=[]
  for i,(cue,path) in enumerate(zip(cues,paths)):
   length=lengths[i];slot=slots[i]
   rate,valid=fit_rate(length,slot)
   if natural:rate,valid=1.,length<=slot+.005
   valid=valid and rate<=natural_rate_limit(cfg,cue['cantonese'],slot)+1e-6
   report.append(dict(index=cue.get('reviewIndex',i)+1,start=cue['start'],end=cue['end'],speaker=next((p.get('name','未指定') for p in cfg.get('voiceProfiles',[]) if p.get('id')==cue.get('speakerId',cfg.get('defaultSpeaker'))),'未指定'),seconds=length,slot=slot,rate=rate,maxRate=natural_rate_limit(cfg,cue['cantonese'],slot),needsReview=not valid,audio=str(path)))
   if not valid: bad.append(str(cue.get('reviewIndex',i)+1))
  (job/'timing.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
  if natural:break
  if not bad: break
  if (cfg.get('previewLooseTiming') and not cfg.get('autoApprove')) or attempt >= 2 or not (cfg.get('autoFit') and cfg.get('speechTiming') and cfg.get('translate')): break
  from duration_fit import shorten
  try:
   if not shorten(cfg,job,cues,report,attempt+1,emit): break
  except (RuntimeError,ValueError) as error:
   if not cfg.get('previewLooseTiming'):raise
   emit('保留完整台詞','自動改短未完成，沿用已生成廣東話並容許時間偏移。'+str(error)[:180],.89)
   break
 if bad and not natural:
  # Record alternate takes of the SAME approved line before asking for more cuts.
  # Only accept a bounded take whose Cantonese ASR still matches the text.
  checks=[];verifier=None
  if cfg.get('autoFit') and cfg.get('ttsBackend')=='cosyvoice3':
   for seed in ((73,) if cfg.get('previewLooseTiming') else (73,127)):
    from repair_budget import claim
    pending=[i for i,r in enumerate(report) if r['needsReview'] and not cues[i].get('editorAudio') and not cues[i].get('_phraseAligned') and claim(cfg,job,cues[i],'timed')]
    if not pending: break
    emit('配音重錄',f'{len(pending)} 段保留台詞再錄一個版本，核對讀音同實際時長。',.89)
    takes=gsv_audio(cfg,job,[dict(cues[i],_deliveryStyle='timed',_seed=seed,_targetSeconds=slots[i]) for i in pending],run,emit)
    takes=delivery.prepare_audio(cfg,job,takes,run)
    for i,path in zip(pending,takes):
     length=seconds(path);rate,valid=fit_rate(length,slots[i]);valid=valid and rate<=natural_rate_limit(cfg,cues[i]['cantonese'],slots[i])+1e-6
     if not valid: continue
     from pronunciation import spoken
     matched,recognized,verifier=candidate_content_matches(cfg,path,spoken(cfg,cues[i]['cantonese']),verifier)
     if matched and cfg.get('autoValidate',True):
      from voicecheck import preserves
      matched=preserves(cfg,job,paths[i],path,profile_for(cues[i],cfg)['reference'])
     checks.append(dict(index=report[i]['index'],seed=seed,text=cues[i]['cantonese'],recognized=recognized,accepted=matched))
     if matched:
      paths[i]=path;report[i].update(seconds=length,rate=rate,needsReview=False,audio=str(path))
   del verifier
   (job/'take-checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2))
   (job/'timing.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
   bad=[str(r['index']) for r in report if r['needsReview']]
 if bad and not natural and cfg.get('autoFit') and not cfg.get('previewLooseTiming'):
  for cue,row in zip(cues,report):
   if not row['needsReview']: continue
   limit=natural_rate_limit(cfg,cue['cantonese'],row['slot'])
   if limit>MAX_TEMPO and row['rate']<=limit-.02:
    row.update(needsReview=False,maxRate=limit,fitMethod='bounded-short-line-compression')
    emit('語速調整',f'校稿第 {row["index"]} 句保留完整台詞，以 {row["rate"]:.2f} 倍調整慢讀短句；唔截尾、唔推遲下一句。',.9)
  bad=[str(r['index']) for r in report if r['needsReview']]
  (job/'timing.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 if cfg.get('previewLooseTiming') or natural:
  return render_complete_preview(cfg,job,cues,paths,report,run,emit)
 if bad:
  raise ValueError('第 '+ '、'.join(bad[:15])+' 句配音仍然超時，超出原聲可用時間，已保留試音同時長報告。請核對呢幾句日語辨識／譯文；唔會截斷句尾或擠入下一句。')
 from audio_format import delivery_rate
 sr=delivery_rate(cfg)
 total=int(cfg['duration']*sr);mix=array.array('h',[0])*total
 for cue,path,row in zip(cues,paths,report):
  offset=max(0,round(cue.get('speechStart',cue['start'])*sr))
  available=min(total,round((cue.get('speechStart',cue['start'])+row['slot'])*sr))-offset
  # atempo uses windows: requested ratio is not an exact sample-count guarantee.
  # Measure the transformed waveform too, and retry rather than clip a syllable.
  for fit_attempt in range(3):
   raw=run([cfg['ffmpeg'],'-v','error','-i',path,'-af',f'atempo={row["rate"]:.8f}','-ar',str(sr),'-ac','1','-f','s16le','pipe:1'])
   samples=array.array('h');samples.frombytes(raw)
   if len(samples)<=available: break
   next_rate=row['rate']*len(samples)/max(1,available-round(sr*.01))
   if next_rate>row.get('maxRate',MAX_TEMPO): break
   row['rate']=next_rate
  if len(samples)>available:
   row['needsReview']=True
   (job/'timing.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
   raise ValueError(f'第 {row["index"]} 句調整後仍超出原聲時段，音檔已保留，未截斷句尾。')
  row['renderedSeconds']=len(samples)/sr
  row['renderedEnd']=(offset+len(samples))/sr
  for j,sample in enumerate(samples): mix[offset+j]=max(-32768,min(32767,mix[offset+j]+sample))
 (job/'timing.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 output=job/'cantonese.wav'
 with wave.open(str(output),'wb') as f:
  f.setnchannels(1);f.setsampwidth(2);f.setframerate(sr);f.writeframes(mix.tobytes())
 return output,warnings


def reference(cfg,run,emit):
 length=float(cfg.get('referenceDuration',6))
 if not math.isfinite(length) or not 3<=length<=10: raise ValueError('參考聲音請揀 3–10 秒。')
 cfg=dict(cfg,duration=length)
 _,dialogue=separate(cfg,run,emit)
 folder=Path(cfg['storage'])/'voices'/cfg['profileId'];folder.mkdir(parents=True,exist_ok=True)
 reference=folder/f'reference-{time.time_ns()}.wav'
 run([cfg['ffmpeg'],'-v','error','-y','-i',dialogue,'-ar','32000','-ac','1',reference])
 prompt=''
 from model_catalog import folder,choice,selected
 model_path=folder(cfg['storage'],choice(cfg.get('referenceSpeechModel') or selected(cfg['storage'],'referenceSpeech')))
 if model_path.exists():
  from faster_whisper import WhisperModel
  model=WhisperModel(str(model_path),device='cpu',compute_type='int8',local_files_only=True)
  segments,_=model.transcribe(whisper_pcm(reference),language='ja',vad_filter=True)
  prompt=''.join(s.text for s in segments).strip()
 emit('參考已準備','已抽取分離後角色聲音；請聽清楚並核對日語原文。',1,reference=str(reference),promptText=prompt,profileId=cfg['profileId'])


def align_cues(cues, spans):
 """Trim only within subtitle windows; never move a line into its neighbour."""
 for cue in cues:
  hits=[(max(cue['start'],s['start']),min(cue['end'],s['end'])) for s in spans if s['end']>cue['start'] and s['start']<cue['end']]
  hits=[(a,b) for a,b in hits if b-a>=0.08]
  if hits:
   a=max(cue['start'],hits[0][0]-0.06);b=min(cue['end'],hits[-1][1]+0.10)
   if b-a>=0.25: cue.update(speechStart=a,speechEnd=b)
  else:
   cue['reviewNote']=(cue.get('reviewNote','')+' 未偵測到對應日語發聲，請對照影片確認。').strip()
 return cues


def align_dialogue(cfg,cues,run,emit):
 from faster_whisper.vad import get_speech_timestamps,VadOptions
 import numpy as np
 emit('時間對齊','根據分離後日語發聲範圍，收窄字幕內嘅配音時段。',0.25)
 raw=run([cfg['ffmpeg'],'-v','error','-i',cfg['dialoguePath'],'-ar','16000','-ac','1','-f','f32le','pipe:1'])
 spans=get_speech_timestamps(np.frombuffer(raw,dtype=np.float32),VadOptions(min_speech_duration_ms=100,min_silence_duration_ms=120,speech_pad_ms=60))
 return align_cues(cues,[dict(start=s['start']/16000,end=s['end']/16000) for s in spans])


def render_complete_preview(cfg,job,cues,paths,report,run,emit):
 from audio_format import delivery_rate
 sr=delivery_rate(cfg)
 """Every translated utterance is audible in full; drift is explicit, never hidden."""
 timeline=array.array('i');warnings=[];intervals=[]
 rendered_dir=Path(job)/'rendered-takes';rendered_dir.mkdir(exist_ok=True)
 for cue,path,row in zip(cues,paths,report):
  natural=cfg.get('speechRatePolicy')=='natural'
  if Path(path).name.startswith('skipped-'):
   row.update(speakerId=cue.get('speakerId'),text=cue.get('cantonese',''),skipped=True,needsReview=True,renderedStart=cue['start'],renderedEnd=cue['end'],renderedSeconds=0)
   warnings.append(dict(index=row['index'],kind='skipped-voice',message='生成失敗；呢段配音留空，等待手動修正。'))
   continue
  requested=round(cue.get('speechStart',cue['start'])*sr)
  offset=max(0,requested)
  limit=natural_rate_limit(cfg,cue['cantonese'],row['slot'])
  rate=min(limit,max(1.0,row['seconds']/max(.18,cue.get('speechEnd',cue['end'])-cue.get('speechStart',cue['start'])))) if cfg.get('autoFit',True) and not cue.get('_phraseAligned') and not is_vocalization(cue) else 1.0
  if natural:rate=1.
  if not natural and cfg.get('autoFit',True) and not cfg.get('strictSpeechTiming') and not cue.get('_phraseAligned') and not is_vocalization(cue) and not cue.get('editorAudio'):
   from delivery import fit_audio
   raw,rate=fit_audio(cfg,path,rate,max(.18,cue.get('speechEnd',cue['end'])-offset/sr),run,1.0,limit)
  else:
   raw=run([cfg['ffmpeg'],'-v','error','-i',path,'-ar',str(sr),'-ac','1','-f','s16le','pipe:1'])
   if cfg.get('strictSpeechTiming'):rate=1.
  if cfg.get('editorRender') and (cue.get('editorAudio') or cue.get('editorRate',1)!=1 or cue.get('editorTrimStart',0) or cue.get('editorTrimEnd',0)):
   trim_start=cue.get('editorTrimStart',0);trim_end=cue.get('editorTrimEnd',0)
   end_seconds=row['seconds']-trim_end
   if end_seconds<=trim_start:raise ValueError('配音裁切後冇剩餘聲音。')
   rate=cue.get('editorRate',1)
   raw=run([cfg['ffmpeg'],'-v','error','-i',path,'-af',f'atrim=start={trim_start}:end={end_seconds},asetpts=PTS-STARTPTS,atempo={rate}','-ar',str(sr),'-ac','1','-f','s16le','pipe:1'])
  samples=array.array('h');samples.frombytes(raw)
  if not samples:raise ValueError(f'第 {row["index"]} 句配音係空白，未輸出靜音代替。')
  from signal_quality import measure,measure_file
  source_signal=measure_file(path);rendered_signal=measure(samples,sr)
  bypassed=False
  if rendered_signal['warnings'] and source_signal.get('valid') and not source_signal['warnings'] and rate!=1 and not cue.get('editorAudio') and not is_vocalization(cue):
   # One bounded recovery: retain clear full speech instead of a bad tempo
   # derivative. Any resulting overrun is reported by the normal timing checks.
   raw=run([cfg['ffmpeg'],'-v','error','-i',path,'-ar',str(sr),'-ac','1','-f','s16le','pipe:1'])
   samples=array.array('h');samples.frombytes(raw);rate=1.0;bypassed=True
   rendered_signal=measure(samples,sr)
   emit('聲音修正',f'第 {row["index"]} 句時長處理後有數碼脈衝；保留原本清晰配音，時間差會列入音軌報告。')
  row['signalQuality']=dict(source=source_signal,rendered=rendered_signal,timeFitBypassed=bypassed,certifiedCause=False)
  if rendered_signal['warnings']:
   warnings.append(dict(index=row['index'],kind='signal-quality',message='偵測到重複數碼脈衝；請比較原始生成、參考聲音及時長處理。',evidence=row['signalQuality']))
   row['requiresSignalReview']=True
  if cfg.get('strictSpeechTiming',False):
   from speech_timing import fit_pcm,window,natural_window
   anchor,deadline=natural_window(cue,cues,cfg['duration'],cfg) if natural else window(cue,cues,cfg['duration'])
   offset=round(anchor*sr)
   if natural:
    if len(samples)>math.floor(deadline*sr)-offset:
     explicitly_accepted=cue.get('manualReviewChoice')=='accepted-defect-recording' and len(samples)/sr <= deadline-anchor+2.0 and anchor+len(samples)/sr <= cfg['duration']+.015
     if explicitly_accepted:
      row.update(needsReview=True,requiresTimingReview=True,acceptedTimingOverlap=True)
      warnings.append(dict(index=row['index'],kind='timing-overrun',message='用家選用嘅完整錄音超出原定時段；已保留並標示重疊。'))
     else:
      row.update(needsReview=True,requiresTimingReview=True,audio=str(path),failureKind='timing-overrun',rate=rate)
      (job/'timing.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
      raise ValueError(f'第 {row["index"]} 句精簡後仍超時；完整錄音及原稿已保留，未加速、截尾或推遲下一句。')
    raw,compression=samples.tobytes(),1.
   else:raw,compression=fit_pcm(cfg,samples.tobytes(),max(1/sr,(math.floor(deadline*sr)-offset)/sr),run)
   samples=array.array('h');samples.frombytes(raw)
   if compression>1:
    rate*=compression
    # Phrase timing must describe the delivered compressed take, not its
    # previous pre-tempo timestamps.
    cue['deliveryParts']=[dict(p,renderedStart=anchor+(p['renderedStart']-anchor)/compression,
                            renderedEnd=anchor+(p['renderedEnd']-anchor)/compression)
                          for p in cue.get('deliveryParts',[])]
    emit('時長對齊',f'第 {row["index"]} 句完整配音已調整至日文發聲時段內，下一句起點保持不變。',.90)
   row['speechDeadline']=deadline
   row['hardSlotCompression']=compression
   row['signalQuality']['rendered']=measure(samples,sr)
   row['signalQuality']['timeFitBypassed']=False
   if row['signalQuality']['rendered']['warnings'] and not row.get('requiresSignalReview'):
    row['requiresSignalReview']=True
    warnings.append(dict(index=row['index'],kind='signal-quality',message='時段調速後聲音品質需要留意；完整字句及原錄音保留。',evidence=row['signalQuality']))
   if rate>limit+.01:
    warnings.append(dict(index=row['index'],kind='accelerated-delivery',rate=rate,message='完整台詞已放入日文發聲時段；語速較快。'))
  end=offset+len(samples)
  if len(timeline)<end:timeline.extend(array.array('i',[0])*(end-len(timeline)))
  overlaps=[index for a,b,index in intervals if offset<b and end>a]
  intervals.append((offset,end,row['index']))
  from pcm_mix import add
  add(timeline,samples,offset)
  take=rendered_dir/f'{row["index"]}.wav'
  with wave.open(str(take),'wb') as f:
   f.setparams((1,2,sr,0,'NONE','not compressed'));f.writeframes(samples.tobytes())
  from overlap_policy import expected
  lookup={r['index']:c for c,r in zip(cues,report)}
  expected_overlaps=[index for a,b,index in intervals[:-1] if index in overlaps and expected(cue,lookup[index],max(offset,a)/sr,min(end,b)/sr)]
  row.update(speakerId=cue.get('speakerId'),text=cue.get('cantonese',''),renderedAudio=str(take),overlaps=overlaps,expectedOverlaps=expected_overlaps,originalPreserved=bool(cue.get('preserveOriginalSpeech')))
  late=max(0,(end-round(cue.get('deliveryEnd',cue['end'])*sr))/sr)
  drift=(offset-requested)/sr
  row.update(rate=rate,deliverySampleRate=sr,renderedSeconds=len(samples)/sr,renderedStart=offset/sr,renderedEnd=end/sr,startDrift=drift,overrun=late,needsReview=late>.02,requiresTimingReview=late>.02 or drift>.02 or bool(set(overlaps)-set(expected_overlaps)),maxRate=limit,fitMethod='source-slot-measured-tempo' if cfg.get('strictSpeechTiming') else 'verified-take-bounded-tempo')
  row['sourceEndError']=end/sr-cue.get('speechEnd',cue['end'])
  row['requiresTimingReview']=row['requiresTimingReview'] or (row['sourceEndError']>.5 if cfg.get('strictSpeechTiming') else abs(row['sourceEndError'])>.5)
  row['acousticStart']=cue.get('acousticStart')
  row['acousticEnd']=cue.get('acousticEnd')
  row['acousticAdjusted']=cue.get('acousticAdjusted',False)
  row['phraseAligned']=bool(cue.get('_phraseAligned'))
  row['deliveryParts']=cue.get('deliveryParts',[])
  for part in row['deliveryParts']:
   part['requiresTimingReview']=abs(part['renderedStart']-part['sourceStart'])>.1 or abs(part['renderedEnd']-part['sourceEnd'])>.5
  for part in row['deliveryParts']:
   part['renderedStart']+=drift;part['renderedEnd']+=drift
  row['requiresTimingReview']=row['requiresTimingReview'] or any(p['requiresTimingReview'] for p in row['deliveryParts'])
  cue['subtitleStart']=offset/sr;cue['subtitleEnd']=end/sr
  if row['requiresTimingReview']:
   warnings.append(dict(index=row['index'],kind='timing-drift',startDrift=round(drift,3),overrun=round(late,3),message='完整配音已保留，配音時間未完全對齊。'))
 output_duration=cfg['duration'] if cfg.get('strictSpeechTiming') else max(cfg['duration'],len(timeline)/sr)
 if len(timeline)<round(output_duration*sr):timeline.extend(array.array('i',[0])*(round(output_duration*sr)-len(timeline)))
 from pcm_mix import finish
 timeline,gain=finish(timeline)
 for row in report:row['mixGain']=gain
 output=job/'cantonese.wav'
 with wave.open(str(output),'wb') as f:
  f.setnchannels(1);f.setsampwidth(2);f.setframerate(sr);f.writeframes(timeline.tobytes())
 (job/'timing.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 cfg['outputDuration']=output_duration
 if warnings:
  if cfg.get('strictSpeechTiming'):
   skipped=sum(bool(r.get('skipped')) for r in report)
   emit('配音時段已對齊',f"{len(report)-skipped}/{len(report)} 段有錄音；{sum(w['kind']=='accelerated-delivery' for w in warnings)} 段已調速至日文時段內。"+(' 未完成片段繼續自動補聲。' if skipped else ' 繼續合成影片。'),.92)
  else:emit('試片時間',f'{len(warnings)} 段需要核對時間／重疊或修正；失敗段落已標記，其他完整配音保留。',.92)
 return output,warnings
