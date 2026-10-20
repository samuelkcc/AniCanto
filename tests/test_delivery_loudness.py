import os
"""Reproduce quiet single-pass GPT and test actual per-engine delivered PCM."""
import array,json,sys,tempfile,unittest,wave,subprocess
from pathlib import Path
from unittest.mock import Mock,patch
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows')]
import dubbing_runner,fast_mode,speech_level,mix_balance

class DeliveryLoudnessTests(unittest.TestCase):
 def test_gpt_single_pass_gain_does_not_add_quality_inference_or_change_silence(self):
  x=np.r_[np.zeros(2400),.008*np.sin(np.arange(12000)*.08),np.zeros(2400)].astype('float32')
  model=Mock();model.run.return_value=iter([(24000,x)])
  with patch('dubbing_runner.gsv_level',side_effect=AssertionError('Full quality review')):
   sr,y,attempts=dubbing_runner.gsv_take(model,Mock(side_effect=AssertionError('Retry')),dict(text='你好呀。',seed=42),fast=True)
  self.assertEqual(model.run.call_count,1);self.assertEqual(len(y),len(x));self.assertFalse(attempts[0]['qualityChecked'])
  self.assertGreater(attempts[0]['level']['gainDB'],10);np.testing.assert_array_equal(y[:2400],x[:2400]);self.assertLess(np.max(np.abs(y)),.85)
 def test_all_six_engines_level_cached_quiet_take_at_final_timing_without_changing_native_file(self):
  from audio_format import delivery_rate
  ffmpeg=Path(os.environ.get('ANICANTO_TEST_FFMPEG',str(ROOT/'dist/AniCanto.app/Contents/Resources/bin/ffmpeg')))
  for engine in ('drama3','gpt-sovits-v2','gpt-sovits','cosyvoice3','voxcpm2','wsyue'):
   with self.subTest(engine=engine),tempfile.TemporaryDirectory() as d:
    job=Path(d);cfg=dict(productionMode='normal',ttsBackend=engine,duration=2,ffmpeg=str(ffmpeg));sr=delivery_rate(cfg)
    x=np.r_[np.zeros(sr//10),.01*np.sin(np.arange(sr//2)*.08),np.zeros(sr//10)]
    native=job/'cached.wav';pcm=(x*32767).astype('<i2').tobytes()
    with wave.open(str(native),'wb') as f:f.setparams((1,2,sr,0,'NONE','not compressed'));f.writeframes(pcm)
    before=native.read_bytes();cue=dict(start=.2,end=1.2,cantonese='你好呀。',speakerId='one')
    def run(args):return subprocess.check_output(list(map(str,args)))
    with patch('dubbing.gsv_audio',return_value=[native]),patch('normal_mode.repair_paths',side_effect=lambda cfg,job,cues,paths,*args:paths):
     output,_=fast_mode.synthesize(cfg,job,[cue],run,Mock())
    self.assertEqual(native.read_bytes(),before)
    row=json.loads((job/'timing.json').read_text())[0];level=row['speechLevel']
    self.assertGreater(level['gainDB'],20);self.assertAlmostEqual(level['outputActiveRMSDB'],-19,delta=.2)
    self.assertLessEqual(row['renderedEnd'],cue['end']);self.assertEqual(row['renderedSeconds'],len(pcm)/2/sr)
    self.assertEqual(row['mixGain'],1)
    with wave.open(str(output)) as f:self.assertEqual(f.getframerate(),sr);self.assertEqual(f.getnframes(),sr*2)
 def test_pcm_delivery_does_not_lift_silence_and_respects_a_loud_peak(self):
  quiet=array.array('h',[0]*2400).tobytes();out,level=speech_level.condition_pcm(quiet,24000)
  self.assertEqual(out,quiet);self.assertEqual(level['gainDB'],0)
  x=np.sin(np.arange(24000)*.08)*.02;x[12000]=.8;raw=(x*32767).astype('<i2').tobytes()
  out,level=speech_level.condition_pcm(raw,24000);self.assertLessEqual(np.max(np.abs(np.frombuffer(out,dtype='<i2').astype(float)))/32768,.842)
  self.assertIn('gain-limited',level['warnings'])
 def test_normal_background_audibility_does_not_require_expensive_ai_review(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);sr=24000;t=np.arange(sr)/sr
   for n,amplitude in [('voice',.05),('background',.2)]:
    with wave.open(str(job/(n+'.wav')),'wb') as f:f.setparams((1,2,sr,0,'NONE','not compressed'));f.writeframes((amplitude*np.sin(t*2*np.pi*(200 if n=='voice' else 700))*32767).astype('<i2').tobytes())
   (job/'timing.json').write_text(json.dumps([dict(index=1,start=0,end=1,renderedAudio=str(job/'voice.wav'),mixGain=.5)]))
   cfg=dict(productionMode='normal',aiAutoFix=False,backgroundGain=.8)
   self.assertEqual(mix_balance.resolve(cfg,job,job/'background.wav'),'auto')
   row=json.loads((job/'mix-audibility.json').read_text())['rows'][0]
   self.assertAlmostEqual(row['voice']['activeRMSDB']-row['voice']['takeActiveRMSDB'],-6.02,delta=.02)
   self.assertFalse(mix_balance.resolve(dict(cfg,productionMode='fast'),job,job/'background.wav'))

if __name__=='__main__':unittest.main()
