"""Heavy models live in child processes; one load per job, memory released on exit."""
from fast_mode import enabled as one_pass

import contextlib
import json
import os
os.environ['ORT_DISABLE_TELEMETRY'] = '1'
from pathlib import Path
import sys
import time

RESOURCE_DIR = Path(__file__).resolve().parent
from dubbing_setup import REV, download
MEL_REV = 'ac9b0614ab3cd7f77219e18ba494dfd93956c348'
MEL_SHA = '87201f4d31afb5bc79993230fc49446918425574db48c01c405e44f365c7559e'


def emit(stage,message,**extra):
 print(json.dumps(dict(stage=stage,message=message,**extra),ensure_ascii=False),flush=True)


def offline():
 os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1')
 # Fail closed if an upstream text frontend or model tries an unexpected download.
 import socket
 def deny(*args,**kwargs): raise RuntimeError('離線推理唔允許網絡下載；請先喺環境頁完成部署。')
 socket.socket.connect=deny
 socket.create_connection=deny


def gsv_import(root,version="v4"):
 from gsv_versions import complete,required,title
 bundled=RESOURCE_DIR/'gpt-sovits'/REV
 local=root/'gpt-sovits'/REV
 source=local if complete(local,version) else bundled
 for name,(size,digest) in required(version).items():
  file=source/'GPT_SoVITS/pretrained_models'/name
  if not file.is_file() or file.stat().st_size!=size:
   raise RuntimeError(f'GPT-SoVITS {title(version)} 未部署完整；請到模型中心下載／修復所選版本。')
 os.chdir(source)
 sys.path[:0]=[str(source),str(source/'GPT_SoVITS')]
 os.environ['NLTK_DATA']=str(root/'models/nltk')
 os.environ['PYTORCH_ENABLE_MPS_FALLBACK']='1'
 os.environ['language']='en_US'
 return source


def prepare_gsv(root,version="v4"):
 source=gsv_import(root,version)
 from model_licenses import install_auxiliary_notices
 for repo,folder in [('TencentGameMate/chinese-hubert-base','chinese-hubert-base'),('hfl/chinese-roberta-wwm-ext-large','chinese-roberta-wwm-ext-large'),('nvidia/bigvgan_v2_24khz_100band_256x','models--nvidia--bigvgan_v2_24khz_100band_256x')]:
  if repo.startswith('nvidia/') and version!='v3':continue
  install_auxiliary_notices(repo,source/'GPT_SoVITS/pretrained_models'/folder)
 from text_data import install_nltk
 install_nltk(root)
 import nltk
 import pyopenjtalk
 pyopenjtalk.g2p('こんにちは。')
 from TTS_infer_pack.TTS import TTS, TTS_Config
 from text.cleaner import clean_text
 from text.LangSegmenter import LangSegmenter
 LangSegmenter.getTexts('你好，今日一齊出發。','zh')
 for text,lang in [('你好，今日一齊出發。','yue'),('こんにちは。','ja'),('Hello.','en')]: clean_text(text,lang,version)
 emit('部署配音','GPT-SoVITS 廣東話、日語文字元件檢查通過。')


def prepare_separator(root):
 model=root/'models/separator/MelBandRoformer.ckpt'
 download(f'https://huggingface.co/KimberleyJSN/melbandroformer/resolve/{MEL_REV}/MelBandRoformer.ckpt',model,MEL_SHA)
 from model_licenses import install_auxiliary_notices
 install_auxiliary_notices('KimberleyJSN/melbandroformer',model.parent)
 from audio_separator.separator import Separator
 emit('部署配音','背景分離模型已下載並通過 SHA-256 校驗。')


def separate(cfg):
 root=Path(cfg['storage']); out=Path(cfg['out']);out.mkdir(parents=True,exist_ok=True)
 offline()
 import torch
 from audio_separator.separator import Separator
 import logging
 class LocalSeparator(Separator):
  def download_model_files(self, model_filename):
   return ('MelBandRoformer.ckpt','MDXC','Mel-Band RoFormer',str(root/'models/separator/MelBandRoformer.ckpt'),str(RESOURCE_DIR/'mel-roformer.yaml'))
 # Output stems stay at their original relative loudness; final mix handles peak limiting.
 separator=LocalSeparator(model_file_dir=str(root/'models/separator'),output_dir=str(out),output_format='WAV',use_soundfile=True,normalization_threshold=1.0,amplification_threshold=0.0,log_level=logging.WARNING,mdxc_params={'segment_size':256,'override_model_segment_size':False,'batch_size':1,'overlap':2,'pitch_shift':0})
 if cfg.get('device')=='cpu':
  separator.torch_device=torch.device('cpu');separator.torch_device_mps=None
 emit('分離','載入 Mel-Band RoFormer；分離日語對白同背景音樂／音效。')
 started=time.monotonic()
 separator.load_model('MelBandRoformer.ckpt')
 # The pinned library's soundfile writer ignores output_dir and can flatten stereo.
 # Write model stems explicitly as stereo float WAV, preserving their levels.
 import soundfile as sf
 import numpy as np
 def write_stem(name,data):
  data=np.asarray(data)
  if data.ndim!=2 or data.shape[1]!=2 or not np.isfinite(data).all(): raise ValueError('分離模型輸出聲道／數值無效')
  target=out/Path(name).name
  tmp=target.with_suffix('.partial.wav');sf.write(tmp,data,44100,subtype='FLOAT');tmp.replace(target)
 separator.model_instance.write_audio=write_stem
 files=separator.separate(cfg['input'],{'Vocals':'dialogue','Instrumental':'background','other':'background'})
 emit('分離','音軌已寫入，正在完成程序檢查。',files=files,seconds=round(time.monotonic()-started,2))



def gsv_level(audio,sr,text,target):
 import numpy as np
 from tts_health import problems
 from speech_level import condition
 raw=np.asarray(audio)
 x=raw.astype(np.float32)
 if np.issubdtype(raw.dtype,np.integer):x/=max(abs(np.iinfo(raw.dtype).min),np.iinfo(raw.dtype).max)
 original=problems(x,sr,text,target)
 leveled,report=condition(x.reshape(-1),sr)
 # Lowering gain cannot repair clipped or runaway original generation.
 errors=list(dict.fromkeys([e for e in original if e!='no-audible-voice']+problems(leveled,sr,text,target)))
 from signal_quality import compare
 report['signalQuality']=compare(x,leveled,sr)
 return np.asarray(leveled,dtype=np.float32),errors,report


def gsv_take(model, cpu_model, request, target=None, device='cpu',reserve_attempt=None,alternate_requests=None,capture_raw=None,fast=False):
 """Bounded same-word retries; CPU alone with an identical seed is insufficient."""
 import re
 from tts_health import problems
 base=dict(request)
 if fast:
  import numpy as np
  from fast_mode import basic_problems
  try:
   with contextlib.redirect_stdout(sys.stderr):sr,audio=next(model.run(base))
  except (ValueError,RuntimeError,StopIteration) as error:
   return 0,[],[dict(device=device,seed=base['seed'],text=base['text'],problems=['generation-exception'],error=str(error),seconds=0,qualityChecked=False)]
  if capture_raw:capture_raw(sr,audio,base)
  raw=np.asarray(audio);x=raw.astype(np.float32)
  if np.issubdtype(raw.dtype,np.integer):x/=max(abs(np.iinfo(raw.dtype).min),np.iinfo(raw.dtype).max)
  # One inference skips content/quality retakes, not deterministic gain staging.
  # Normal mode shares this branch; returning raw GPT amplitude made it quiet
  # against the untouched background on both Windows and Mac.
  from speech_level import condition
  leveled,level=condition(x,sr)
  return sr,np.asarray(leveled,dtype=np.float32),[dict(level=level,device=device,seed=base['seed'],text=base['text'],problems=basic_problems(x,sr),seconds=len(x)/sr if sr>0 else 0,qualityChecked=False)]
 normalized=re.sub(r'(?:\.{2,}|…+|⋯+)', '。', base['text'])
 variants=[dict(base)]
 if normalized!=base['text']:variants.append(dict(base,text=normalized))
 if alternate_requests:variants.append(dict(base,**alternate_requests[0],text=normalized,seed=int(base['seed'])+17))
 variants.append(dict(base,text=normalized,seed=int(base['seed'])+31))
 # Reserve the fourth persistent attempt for CPU recovery on Apple Silicon.
 if device=='mps':variants=variants[:3]
 attempts=[]
 sr=0;audio=[]
 for params in variants:
  if reserve_attempt and not reserve_attempt():break
  try:
   with contextlib.redirect_stdout(sys.stderr):sr,audio=next(model.run(params))
  except (ValueError,RuntimeError,StopIteration) as error:
   attempts.append(dict(device=device,seed=params['seed'],text=params['text'],reference=params.get('ref_audio_path'),problems=['generation-exception'],error=str(error),seconds=0));continue
  if capture_raw:capture_raw(sr,audio,params)
  audio,errors,level=gsv_level(audio,sr,base['text'],target)
  attempts.append(dict(level=level,device=device,seed=params['seed'],text=params['text'],reference=params.get('ref_audio_path'),problems=errors,seconds=len(audio)/sr))
  if not errors:return sr,audio,attempts
 if device=='mps':
  if reserve_attempt and not reserve_attempt():return sr,audio,attempts or [dict(problems=['retry-budget-exhausted'],seconds=0)]
  try:
   with contextlib.redirect_stdout(sys.stderr):sr,audio=next(cpu_model().run(variants[-1]))
  except (ValueError,RuntimeError,StopIteration) as error:
   attempts.append(dict(device='cpu',seed=variants[-1]['seed'],text=variants[-1]['text'],problems=['generation-exception'],error=str(error),seconds=0));return sr,audio,attempts
  if capture_raw:capture_raw(sr,audio,variants[-1])
  audio,errors,level=gsv_level(audio,sr,base['text'],target)
  attempts.append(dict(level=level,device='cpu',seed=variants[-1]['seed'],text=variants[-1]['text'],reference=variants[-1].get('ref_audio_path'),problems=errors,seconds=len(audio)/sr))
 return sr,audio,attempts or [dict(problems=['retry-budget-exhausted'],seconds=0)]


def generation_identity(cfg,item):
 """Automatic recovery shares a budget; an explicit new recording gets its own."""
 import hashlib
 voice=item['profile']
 identity=['gsv-version-recovery-3',cfg.get('gsvVersion','v4'),item.get('reviewIndex'),voice['id'],item.get('approvedText',item['text']),cfg.get('targetLanguage','yue'),
           hashlib.sha256(Path(voice['reference']).read_bytes()).hexdigest(),voice.get('promptText',''),voice.get('language','ja'),int(cfg.get('sampleSteps',32))]
 if cfg.get('audioRerunToken'):identity.append(['explicit-rerun',cfg['audioRerunToken']])
 if item.get('expressionSettings'):identity.append(['expression-settings-1',item['expressionSettings']])
 if item.get('cantoneseReadings'):identity.append(['v4-jyutping-1',item['cantoneseReadings']])
 return identity


def tts(cfg):
 version=cfg.get('gsvVersion','v4')
 from gsv_versions import RATES,required,title
 required(version)
 root=Path(cfg['storage']);source=gsv_import(root,version);offline()
 import torch
 import soundfile as sf
 import numpy as np
 from TTS_infer_pack.TTS import TTS,TTS_Config
 device=cfg.get('device','mps')
 if device=='mps' and not torch.backends.mps.is_available(): device='cpu'
 steps=int(cfg.get('sampleSteps',32))
 if steps not in (16,32):raise ValueError('V4 配音製作模式無效。')
 torch.set_num_threads(6)
 settings=dict(TTS_Config.default_configs[version]);settings.update(device=device,is_half=False)
 emit('配音','準備生成音軌。',workID='tts',workCompleted=0,workTotal=len(cfg['items']))
 emit('配音',f'載入 GPT-SoVITS {title(version)}（{device.upper()}），生成角色配音。')
 def inference_config(selected,name):
  config=TTS_Config({'custom':selected})
  # Upstream saves config while loading weights. Never modify the signed app
  # bundle (or a shared model checkout) during inference.
  folder=Path(cfg['job']);folder.mkdir(parents=True,exist_ok=True)
  config.configs_path=str(folder/name)
  return config
 with contextlib.redirect_stdout(sys.stderr): model=TTS(inference_config(settings,'gpt-infer-config.yaml'))
 from cantonese_pronunciation import install as install_readings,select as select_readings
 install_readings(model)
 cpu_model=None
 def fallback():
  nonlocal cpu_model
  if cpu_model is None:
   cpu_model=TTS(inference_config(dict(settings,device='cpu'),'gpt-infer-cpu-config.yaml'))
   install_readings(cpu_model)
  select_readings(cpu_model,active_readings)
  return cpu_model
 failed=[]
 for index,item in enumerate(cfg['items']):
  from track_control import check
  check(cfg)
  path=Path(item['output'])
  if path.exists() and path.stat().st_size>100:
   emit('配音','沿用已生成音檔。',workID='tts',workCompleted=index+1,workTotal=len(cfg['items']),cueIndex=item.get('reviewIndex'))
   continue
  emit('配音',f'正在生成第 {index+1}/{len(cfg["items"])} 句。',workID='tts',workCompleted=index,workTotal=len(cfg['items']),cueIndex=item.get('reviewIndex'))
  voice=item['profile'];text=item['text'].strip()
  active_readings=item.get('cantoneseReadings',{}) if cfg.get('targetLanguage','yue')=='yue' else {}
  select_readings(model,active_readings)
  info=sf.info(voice['reference'])
  if not 3<=info.duration<=10.1: raise ValueError('角色參考聲音必須係 3–10 秒。')
  if not voice.get('promptText','').strip(): raise ValueError('請填寫角色參考錄音嘅日語原文。')
  from voice_expression import settings as expression_settings
  expressive=expression_settings(item.get('expressionSettings',{}))
  request={'text':text,'text_lang':{'en':'en','zh':'all_zh','yue':'all_yue'}[cfg.get('targetLanguage','yue')],'ref_audio_path':voice['reference'],'prompt_text':voice['promptText'],'prompt_lang':{'ja':'all_ja','yue':'all_yue','en':'en','zh':'all_zh','ko':'all_ko'}.get(voice.get('language','ja'),'all_ja'),'text_split_method':'cut0','batch_size':1,'speed_factor':1.0,'seed':item.get('seed',42),'parallel_infer':False,'streaming_mode':False,'fragment_interval':0.0,'repetition_penalty':1.35,'sample_steps':steps,'super_sampling':False}
  request.update(top_k=expressive['gptTopK'],top_p=expressive['gptTopP'],temperature=expressive['gptTemperature'],repetition_penalty=expressive['gptRepetitionPenalty'])
  if index==0 and voice.get('language','ja')!=cfg.get('targetLanguage','yue'):
   emit('配音語言',f'GPT {title(version)} 跨語言配音 · 原生 {RATES[version]//1000} kHz；按目標語言生成並覆聽。')
  started=time.monotonic()
  from workflow_policy import reserve
  identity=generation_identity(cfg,item)
  reserve_attempt=lambda:reserve(Path(cfg['job']),'gpt-generation',identity,4)
  alternates=[dict(ref_audio_path=p['reference'],prompt_text=p.get('promptText','')) for p in voice.get('referenceCandidates',[]) if p.get('reference')]
  raw_capture={}
  def capture_raw(sr,audio,params):
   from signal_quality import float_audio
   raw_capture.update(sr=sr,audio=float_audio(audio).copy(),reference=params.get('ref_audio_path'))
  sr,audio,attempts=gsv_take(model,fallback,request,item.get('targetSeconds'),device,reserve_attempt,alternates,capture_raw,fast=one_pass(cfg))
  from signal_quality import measure
  for attempt in attempts:
   attempt['modelVersion']=version
   attempt['inferenceParameters']={key:request.get(key,default) for key,default in [('batch_size',1),('parallel_infer',False),('top_k',15),('top_p',1),('temperature',1),('repetition_penalty',1.35),('sample_steps',32),('speed_factor',1),('text_lang','all_yue'),('prompt_lang','all_ja')]}
   try:attempt['referenceSHA256']=__import__('hashlib').sha256(Path(attempt.get('reference') or voice['reference']).read_bytes()).hexdigest()
   except OSError:attempt['referenceSHA256']=None
   attempt['recoveryPolicy']='v4-recovery-2; automatic attempts share a budget; explicit reruns are independent'
   if active_readings:attempt['cantoneseReadings']=active_readings
   reference=attempt.get('reference')
   if reference and 'level' in attempt:
    try:
     samples,reference_sr=sf.read(reference,dtype='float32')
     evidence=measure(samples,reference_sr);attempt['level']['signalQuality']['reference']=evidence
     if evidence['warnings'] or evidence.get('clippedFraction',0)>.005:
      attempt['level']['signalQuality']['suspectedCauses'].append('reference-signal-risk')
    except (ValueError,OSError,RuntimeError) as error:
     attempt['level']['signalQuality']['referenceReadError']=str(error)[:180]
  if raw_capture and raw_capture['sr']!=RATES[version]:
   attempts[-1]['problems']=list(dict.fromkeys(attempts[-1]['problems']+[version+'-native-rate-mismatch']))
  errors=attempts[-1]['problems']
  path.parent.mkdir(parents=True,exist_ok=True)
  if raw_capture and np.isfinite(raw_capture['audio']).all():
   raw_path=path.with_suffix('.rejected-raw.wav' if errors else '.raw.wav')
   sf.write(raw_path,raw_capture['audio'],raw_capture['sr'],subtype='FLOAT')
  path.with_suffix('.health.json').write_text(json.dumps(attempts,ensure_ascii=False,indent=2))
  if errors:
   if len(audio):sf.write(path.with_suffix('.rejected.wav'),audio,sr,subtype='PCM_16')
   label=f'校稿第 {item["reviewIndex"]+1} 句' if item.get('reviewIndex') is not None else f'第 {index+1} 個生成片段'
   failed.append(f'{label}（{", ".join(errors)}）')
   notice='高速生成失敗（不重錄）' if one_pass(cfg) else '重試仍失敗'
   emit('配音需修正',f'GPT-SoVITS {label} {notice}；繼續保存其餘片段。')
   emit('配音',f'{label} 已處理，等待修正。',workID='tts',workCompleted=index+1,workTotal=len(cfg['items']))
   continue
  path.parent.mkdir(parents=True,exist_ok=True)
  tmp=path.with_suffix('.partial.wav');sf.write(tmp,audio,sr,subtype='PCM_16');tmp.replace(path)
  path.with_suffix('.level.json').write_text(json.dumps(attempts[-1].get('level',{}),indent=2))
  emit('配音',f'GPT-SoVITS：{voice["name"]} · 第 {index+1}/{len(cfg["items"])} 句',progress=0.55+0.3*(index+1)/len(cfg['items']),workID='tts',workCompleted=index+1,workTotal=len(cfg['items']),cueIndex=item.get('reviewIndex'),seconds=round(time.monotonic()-started,2))

 if failed:raise ValueError('GPT-SoVITS '+ '；'.join(failed) +'；其餘片段已保存，未將缺聲音軌封裝為完成。')


if __name__=='__main__':
 try:
  action=sys.argv[1]
  if action=='prepare-cosy':
   from cosy import prepare
   prepare(Path(sys.argv[2]),sys.argv[3] if len(sys.argv)>3 else None)
  elif action=='prepare-gsv': prepare_gsv(Path(sys.argv[2]),sys.argv[3] if len(sys.argv)>3 else 'v4')
  elif action=='prepare-separator': prepare_separator(Path(sys.argv[2]))
  elif action=='prepare-speakers':
   from speakers import prepare
   prepare(Path(sys.argv[2]))
  else:
   cfg=json.loads(Path(sys.argv[2]).read_text())
   if action=='separate': separate(cfg)
   elif action=='independent-voices':
    from independent_voices import prepare
    prepare(cfg,emit)
   elif action=='speakers':
    from speakers import analyze
    analyze(cfg,emit)
   elif action=='cosy':
    from cosy import synthesize
    synthesize(cfg,emit)
   elif action in ('voxcpm2','wsyue','drama3'):
    from local_tts import synthesize
    synthesize(cfg,emit,action)
   elif action=='tts': tts(cfg)
   else: raise ValueError('未知配音動作')
 except Exception as e:
  import traceback;traceback.print_exc(file=sys.stderr)
  emit('錯誤',str(e));sys.exit(1)
