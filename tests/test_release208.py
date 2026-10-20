import array,json,sys,tempfile,unittest,wave,subprocess
from pathlib import Path
from unittest.mock import Mock
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import audio_fallback,dubbing_runner
class Release208(unittest.TestCase):
 def test_gpt_exception_does_not_abort_retry(self):
  good=.1*np.sin(np.arange(24000)*.1);m=Mock();m.run.side_effect=[ValueError('Please enter valid text'),iter([(24000,good)])]
  _,audio,rows=dubbing_runner.gsv_take(m,Mock(),dict(text='Hello!',seed=42),device='cpu')
  self.assertEqual(rows[0]['problems'],['generation-exception']);self.assertEqual(rows[1]['problems'],[]);self.assertEqual(len(audio),24000)
 def test_gpt_exhausted_exceptions_produce_failed_cue_evidence(self):
  m=Mock();m.run.side_effect=ValueError('bad frontend')
  _,audio,rows=dubbing_runner.gsv_take(m,lambda:m,dict(text='Hello!',seed=42),device='mps')
  self.assertFalse(audio);self.assertEqual(len(rows),3);self.assertTrue(all(r['problems'] for r in rows))
 def test_hundreds_of_mutes_preserve_stereo_and_samples(self):
  with tempfile.TemporaryDirectory() as d:
   folder=Path(d);native=folder/'native.wav';rate=24000;data=array.array('h',[1000,2000])*rate*3
   with wave.open(str(native),'wb') as f:f.setparams((2,2,rate,0,'NONE','not compressed'));f.writeframes(data.tobytes())
   ffmpeg=str(Path(__file__).resolve().parents[1]/'dist/AniCanto.app/Contents/Resources/bin/ffmpeg')
   def run(cmd):return subprocess.run([str(c) for c in cmd],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
   intervals=[(i*.01,i*.01+.002) for i in range(250)]
   muted=audio_fallback.muted_base(dict(ffmpeg=ffmpeg),native,folder,intervals,run)
   with wave.open(str(muted)) as f:self.assertEqual(f.getnchannels(),2);pcm=array.array('h',f.readframes(f.getnframes()))
   for a,b in intervals:
    lo,hi=round(a*rate)*2,round(b*rate)*2;self.assertFalse(any(pcm[lo:hi]));self.assertEqual(pcm[hi:hi+2],array.array('h',[1000,2000]))
   self.assertEqual(len(pcm),len(data));self.assertFalse((folder/'fallback-base-decoded.wav').exists())

 def test_pacing_flag_can_use_verified_same_language_donor(self):
  with tempfile.TemporaryDirectory() as d:
   folder=Path(d);path=folder/'take.wav'
   with wave.open(str(path),'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(array.array('h',[1000,-1000]*12000).tobytes())
   row=dict(index=1,start=0,end=2,renderedAudio=str(path),requiresTimingReview=True,overrun=0,startDrift=0)
   (folder/'timing.json').write_text(json.dumps([row]));target=dict(language='yue');donor=dict(engine='cosyvoice3',language='yue',folder=folder)
   self.assertIsNotNone(audio_fallback.choose(row,target,[donor]))
   row['overrun']=.5;(folder/'timing.json').write_text(json.dumps([row]));self.assertIsNone(audio_fallback.choose(row,target,[donor]))
 def test_overlap_repair_preserves_other_role_and_removes_wrong_language_take(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);ffmpeg=str(Path(__file__).resolve().parents[1]/'dist/AniCanto.app/Contents/Resources/bin/ffmpeg')
   def run(args):
    p=subprocess.run([str(x) for x in args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True);return p.stdout
   def tone(name,freq,seconds):
    p=root/name;x=(np.sin(np.arange(int(seconds*24000))*2*np.pi*freq/24000)*4000).astype('<i2')
    with wave.open(str(p),'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(x.tobytes())
    return p
   bad=tone('bad.wav',1800,2);good=tone('good.wav',400,1);replacement=tone('replacement.wav',700,2)
   native=root/'native.mp4';run([ffmpeg,'-v','error','-y','-f','lavfi','-i','color=s=64x64:r=10:d=3','-i',bad,'-i',good,'-filter_complex','[2:a]adelay=1000:all=1[g];[1:a][g]amix=inputs=2:normalize=0[a]','-map','0:v','-map','[a]','-t','3','-c:v','libx264','-c:a','aac',native])
   target=root/'target';donor=root/'donor';target.mkdir();donor.mkdir()
   rows=[dict(index=1,start=0,end=2,renderedStart=0,renderedEnd=2,renderedSeconds=2,renderedAudio=str(bad)),dict(index=2,start=1,end=2,renderedStart=1,renderedEnd=2,renderedSeconds=1,renderedAudio=str(good))]
   (target/'timing.json').write_text(json.dumps(rows));(target/'final-speech-check.json').write_text(json.dumps(dict(rows=[dict(index=1,expected='This is the wrong language',similarity=.1,languageMismatch=True)])))
   (donor/'timing.json').write_text(json.dumps([dict(rows[0],renderedAudio=str(replacement))]))
   t=dict(id='qwen-tts',engine='qwen-tts',language='en',folder=target,report=dict(duration=3),output=native);other=dict(engine='cosyvoice3',language='en',folder=donor)
   choose=audio_fallback.choose
   from unittest.mock import patch
   with patch.object(audio_fallback,'choose',side_effect=lambda cue,t,ignored,**kwargs:choose(cue,t,[other],**kwargs)):
    repaired=audio_fallback.repair(dict(ffmpeg=ffmpeg,allowCrossEngineRepair=True,selectedEngines=['qwen-tts','cosyvoice3']),root,[t],run,lambda *a:None)
   self.assertEqual(len(repaired),2)
   x=np.frombuffer(run([ffmpeg,'-v','error','-ss','1.1','-i',t['output'],'-t','0.7','-ar','24000','-ac','1','-f','s16le','pipe:1']),dtype='<i2').astype(float)
   def energy(f):return abs(np.dot(x,np.exp(-2j*np.pi*f*np.arange(len(x))/24000)))
   self.assertGreater(energy(400),energy(1800)*20);self.assertGreater(energy(700),energy(1800)*20)

class StrictDonorTimingTests(unittest.TestCase):
 def test_legacy_donor_is_compressed_to_target_speech_slot_before_final_overlay(self):
  import subprocess
  from unittest.mock import Mock
  ffmpeg=Path(__file__).parents[1]/'dist/AniCanto.app/Contents/Resources/bin/ffmpeg'
  if not ffmpeg.is_file():self.skipTest('Bundled FFmpeg required')
  def run(cmd):return subprocess.check_output([str(c) for c in cmd],stderr=subprocess.PIPE)
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);target=root/'target';donor=root/'donor';target.mkdir();donor.mkdir()
   voice=donor/'long.wav';sr=24000
   samples=(np.sin(np.arange(sr*2)*2*np.pi*330/sr)*5000).astype('<i2')
   with wave.open(str(voice),'wb') as f:f.setparams((1,2,sr,0,'NONE','not compressed'));f.writeframes(samples.tobytes())
   native=target/'native.mp4'
   run([ffmpeg,'-v','error','-y','-f','lavfi','-i','color=s=64x64:r=10:d=3','-f','lavfi','-i','anullsrc=r=24000:cl=mono','-t','3','-c:v','libx264','-c:a','aac',native])
   cue=dict(index=1,start=0.,end=2.,speechStart=.1,speechEnd=.6,cantonese='出發啦',text='出發啦',speakerId='actor')
   (target/'review.json').write_text(json.dumps(dict(cues=[cue])))
   (target/'timing.json').write_text(json.dumps([dict(cue,skipped=True,renderedSeconds=0)]))
   (donor/'timing.json').write_text(json.dumps([dict(cue,renderedAudio=str(voice),renderedStart=0.,renderedEnd=2.,renderedSeconds=2.)]))
   t=dict(id='drama3',engine='drama3',language='yue',folder=target,report=dict(duration=3),output=native)
   d=dict(engine='drama3',language='yue',folder=donor)
   rows=audio_fallback.repair(dict(ffmpeg=str(ffmpeg),strictSpeechTiming=True,allowCrossEngineRepair=True,selectedEngines=['drama3']),root,[t],run,Mock(),donor_tracks=[d])
   self.assertEqual(len(rows),1,t['report'].get('fallbackError'))
   self.assertEqual(rows[0]['renderedStart'],.1);self.assertLessEqual(rows[0]['renderedEnd'],.6)
   self.assertGreater(rows[0]['slotCompression'],1)
   with wave.open(rows[0]['audio']) as f:self.assertLessEqual(f.getnframes()/f.getframerate(),.5)

class RepairDeduplicationTests(unittest.TestCase):
 def test_asr_and_planner_flags_overlay_the_same_turn_once(self):
  from unittest.mock import Mock
  ffmpeg=Path(__file__).parents[1]/'dist/AniCanto.app/Contents/Resources/bin/ffmpeg'
  if not ffmpeg.is_file():self.skipTest('Bundled FFmpeg required')
  def run(cmd):return subprocess.check_output([str(c) for c in cmd],stderr=subprocess.PIPE)
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);target=root/'target';donor=root/'donor';target.mkdir();donor.mkdir()
   voice=donor/'voice.wav';samples=(np.sin(np.arange(24000)*2*np.pi*330/24000)*3000).astype('<i2')
   with wave.open(str(voice),'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(samples.tobytes())
   native=target/'native.mp4'
   run([ffmpeg,'-v','error','-y','-f','lavfi','-i','color=s=64x64:r=10:d=2','-f','lavfi','-i','anullsrc=r=24000:cl=mono','-t','2','-c:v','libx264','-c:a','aac',native])
   cue=dict(index=1,start=0.,end=1.,cantonese='我哋一齊出發啦',text='我哋一齊出發啦',speakerId='actor')
   (target/'review.json').write_text(json.dumps(dict(cues=[cue])))
   (target/'timing.json').write_text(json.dumps([dict(cue,renderedSeconds=1.,renderedAudio=str(voice))]))
   (target/'final-speech-check.json').write_text(json.dumps(dict(rows=[dict(index=1,expected=cue['text'],heard='wrong language',similarity=.1,languageMismatch=True)])))
   (donor/'timing.json').write_text(json.dumps([dict(cue,renderedAudio=str(voice),renderedStart=0.,renderedEnd=1.,renderedSeconds=1.)]))
   t=dict(id='drama3',engine='drama3',language='yue',folder=target,report=dict(duration=2),output=native,aiRepairIndices=[1],aiRepairActions={1:'role-voice'})
   d=dict(engine='drama3',language='yue',folder=donor)
   rows=audio_fallback.repair(dict(ffmpeg=str(ffmpeg),selectedEngines=['drama3']),root,[t],run,Mock(),donor_tracks=[d])
   self.assertEqual(len(rows),1,t['report'].get('fallbackError'))
   self.assertEqual(t['report']['channelSummary']['repaired'],1)


class RepairResumeTests(unittest.TestCase):
 def test_second_repair_retains_previous_donors_without_doubling_their_voice(self):
  from unittest.mock import Mock
  ffmpeg=Path(__file__).parents[1]/'dist/AniCanto.app/Contents/Resources/bin/ffmpeg'
  def run(cmd):return subprocess.check_output([str(c) for c in cmd],stderr=subprocess.PIPE)
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);target=root/'target';donor=root/'donor';target.mkdir();donor.mkdir()
   native=target/'native.mp4';voice=donor/'voice.wav'
   with wave.open(str(voice),'wb') as f:
    f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes((np.sin(np.arange(24000)*2*np.pi*330/24000)*2500).astype('<i2').tobytes())
   run([ffmpeg,'-v','error','-y','-f','lavfi','-i','color=s=64x64:r=10:d=2','-f','lavfi','-i','anullsrc=r=24000:cl=stereo','-t','2','-c:v','libx264','-c:a','aac',native])
   cue=dict(index=1,start=0.,end=1.,text='我哋出發啦',cantonese='我哋出發啦',speakerId='actor')
   (target/'review.json').write_text(json.dumps(dict(cues=[cue])))
   (target/'timing.json').write_text(json.dumps([dict(cue,skipped=True,renderedSeconds=0)]))
   (donor/'timing.json').write_text(json.dumps([dict(cue,renderedAudio=str(voice),renderedStart=0.,renderedEnd=1.,renderedSeconds=1.)]))
   t=dict(id='drama3',engine='drama3',language='yue',folder=target,report=dict(duration=2.,output=str(native)),output=native)
   cfg=dict(ffmpeg=str(ffmpeg),selectedEngines=['drama3'],allowCrossEngineRepair=True)
   other=dict(engine='drama3',language='yue',folder=donor)
   audio_fallback.repair(cfg,root,[t],run,Mock(),donor_tracks=[other])
   first=run([ffmpeg,'-v','error','-i',t['output'],'-map','0:a:0','-f','s16le','pipe:1'])
   audio_fallback.repair(cfg,root,[t],run,Mock(),donor_tracks=[])
   second=run([ffmpeg,'-v','error','-i',t['output'],'-map','0:a:0','-f','s16le','pipe:1'])
   self.assertEqual(first,second,t['report'].get('fallbackError'))
   self.assertEqual(len(t['report']['audioFallbacks']),1)
