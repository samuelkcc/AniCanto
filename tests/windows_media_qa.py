"""Actual FFmpeg fixture export with synthetic voice takes, never model acceptance."""
import hashlib
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'windows'))
import jobs
import numpy as np
import soundfile as sf
import av

folder=ROOT/'.build/windows/media-qa'
folder.mkdir(parents=True,exist_ok=True)
os.environ['CANTOSYNC_WINDOWS_DATA']=str(folder/'data')
source=folder/'來源 source.mp4'
jobs.run([jobs.ffmpeg(),'-v','error','-y','-f','lavfi','-i','testsrc2=size=320x180:rate=24',
          '-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','6','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',source])
before=hashlib.sha256(source.read_bytes()).hexdigest()
reference=folder/'role.wav'
sf.write(reference,.1*np.sin(2*np.pi*180*np.arange(4*24000)/24000),24000,subtype='PCM_16')
root=jobs.data_root();root.mkdir(parents=True,exist_ok=True)
runtime=jobs.env_python('qwen');runtime.parent.mkdir(parents=True,exist_ok=True);runtime.write_text('fixture')
(root/'qwen-windows-ready.json').write_text('{}')
cfg=dict(input=str(source),output=str(folder/'Windows test.mp4'),engine='qwen',language='yue',device='cpu',
         qwenModel='qwen-small',videoAcceleration='software',duration=6,profiles=[dict(id='A',reference=str(reference),language='ja')],
         cues=[dict(start=.5,end=.9,text='hello',target='等等！',role='A'),dict(start=5.7,end=5.9,text='end',target='走啦！',role='A')])
class SyntheticVoice:
    def __init__(self,args):
        request=json.loads(Path(args[-1]).read_text())
        for item in request['items']:
            sf.write(item['output'],.1*np.sin(2*np.pi*260*np.arange(31200)/24000),24000,subtype='PCM_16')
    def wait(self,timeout=None):return 0
    def poll(self):return 0
real_popen=jobs.subprocess.Popen
def spawn(args,*a,**kw):
    return SyntheticVoice(args) if len(args)>1 and str(args[1]).endswith('native_tts.py') else real_popen(args,*a,**kw)
target=Path(cfg['output']);target.unlink(missing_ok=True)
with patch.object(jobs.subprocess,'Popen',side_effect=spawn):jobs.render(cfg)
report=json.loads(target.with_suffix('.report.json').read_text())
assert report['decodePassed'] and report['encoder']=='libx264'
assert all(t['rate']<=1.15 for t in report['timings'])
assert report['duration']>6
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
with av.open(str(target)) as movie:
    assert len(movie.streams.audio)==2 and len(movie.streams.subtitles)==1
    assert float(movie.duration/av.time_base)>6
try:jobs.render(cfg)
except ValueError as error:assert 'already exists' in str(error)
else:raise AssertionError('Existing output should be preserved')
cfg['output']=str(folder/'Background test.mp4');cfg['background']=str(reference)
Path(cfg['output']).unlink(missing_ok=True)
with patch.object(jobs.subprocess,'Popen',side_effect=spawn):jobs.render(cfg)
receipt=dict(sourcePreserved=True,fullDecodePassed=True,audioStreams=2,subtitleStreams=1,
             naturalRateLimit=1.15,overrunSpeechRetained=True,backgroundMixPassed=True,
             existingOutputPreserved=True,voiceFixture='synthetic tones; no model inference',platform=sys.platform)
(folder/'receipt.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt,indent=2))
