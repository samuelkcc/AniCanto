"""Use complete local source PCM before optional performance refinement."""
import json,math
from pathlib import Path

def source_job(job):
 root=Path(job).resolve()
 while root.parent.name in ('tracks','versions'):root=root.parent.parent
 return root

def usable(path,cfg,check_config=False):
 if not path.is_file():return False
 try:
  import soundfile as sf
  info=sf.info(str(path));duration=float(cfg['duration'])
  if not math.isfinite(duration) or duration<=0 or info.frames<=0 or abs(info.duration-duration)>.3:return False
  if check_config:
   review=json.loads((path.parent/'review.json').read_text()).get('config',{})
   if str(review.get('video'))!=str(cfg.get('video')):return False
   if abs(float(review.get('startOffset',0))-float(cfg.get('startOffset',0)))>.01:return False
   if review.get('sourceAudioStream')!=cfg.get('sourceAudioStream'):return False
  return True
 except (OSError,ValueError,RuntimeError,TypeError,KeyError):return False

def original(cfg,job,folder,run,emit):
 job=Path(job);root=source_job(job)
 for p,shared in [(job/'japanese-original.wav',False),(root/'japanese-original.wav',root!=job),(folder/'original-analysis.wav',False)]:
  if usable(p,cfg,shared):
   emit('原聲表演','重用已驗證本機原聲；唔會重新讀取雲端原片。',.92)
   return p
 from source_preparation import cloud
 if cloud(cfg['video']):raise RuntimeError('Optional source-performance refinement has no complete local source audio. Keep the existing conservative sound rules; do not read the cloud movie again.')
 from source_language import audio_label
 p=folder/'original-analysis.wav';temporary=folder/'original-analysis.partial.wav'
 try:
  run([cfg['ffmpeg'],'-v','error','-y','-ss',str(cfg.get('startOffset',0)),'-i',cfg['video'],'-map',audio_label(cfg),'-t',str(cfg['duration']),'-vn','-ar','16000','-ac','1',temporary],timeout=90)
  if not usable(temporary,cfg):raise RuntimeError('Optional source-performance audio is incomplete.')
  temporary.replace(p);return p
 finally:temporary.unlink(missing_ok=True)
