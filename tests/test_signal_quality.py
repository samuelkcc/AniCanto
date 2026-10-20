import sys,unittest,tempfile,wave
from pathlib import Path
from unittest.mock import Mock,patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import signal_quality as q
import dubbing_runner as g

class SignalQualityTests(unittest.TestCase):
 def clean(self):
  t=np.arange(24000*2)/24000
  return (.14*np.sin(2*np.pi*180*t)+.06*np.sin(2*np.pi*430*t)).astype(np.float32)
 def corrupt(self):
  x=self.clean();x[2000:2020]=0;x[5000:5020]=0;x[8000:8020]=0
  x[[2010,5010,8010]]=.95
  return x
 def test_repeated_digital_impulses_and_integer_scaling(self):
  report=q.measure(self.corrupt(),24000)
  self.assertEqual(report['impulses'],3);self.assertIn('repeated-digital-impulses',report['warnings'])
  self.assertEqual(q.measure((self.corrupt()*32767).astype(np.int16),24000)['impulses'],3)
 def test_carriers_broad_bursts_and_voice_noise_do_not_trigger(self):
  self.assertFalse(q.measure(self.clean(),24000)['warnings'])
  self.assertFalse(q.measure(np.sign(self.clean())*.7,24000)['warnings'])
  x=self.clean();x[2000:2020]=.6;x[5000:5020]=.6;x[8000:8020]=.6
  self.assertFalse(q.measure(x,24000)['warnings'])
  self.assertFalse(q.measure(np.random.default_rng(12).normal(0,.05,48000),24000)['warnings'])
 def test_single_click_is_evidence_not_automatic_rejection(self):
  x=self.clean();x[2000:2020]=0;x[2010]=.95
  report=q.measure(x,24000);self.assertEqual(report['impulses'],1);self.assertFalse(report['warnings'])
 def test_invalid_signal_and_source_clipping_are_separate(self):
  self.assertFalse(q.measure([np.nan],24000)['valid'])
  evidence=q.compare(np.ones(48000),np.ones(48000)*.5,24000)
  self.assertIn('raw-generation-clipping',evidence['suspectedCauses']);self.assertFalse(evidence['certifiedCause'])
 def test_raw_vs_conditioning_root_evidence(self):
  evidence=q.compare(self.clean(),self.corrupt(),24000)
  self.assertEqual(evidence['suspectedCauses'],['conditioning-digital-impulses'])
 def test_bad_raw_take_retries_clean_same_role_reference(self):
  model=Mock();model.run.side_effect=[iter([(24000,self.corrupt())]),iter([(24000,self.clean())])]
  capture=Mock()
  _,audio,attempts=g.gsv_take(model,Mock(),dict(text='一齊出發！',seed=42,ref_audio_path='same-role-original.wav'),alternate_requests=[dict(ref_audio_path='same-role-clean.wav')],capture_raw=capture)
  self.assertIn('repeated-digital-impulses',attempts[0]['problems']);self.assertFalse(attempts[1]['problems'])
  self.assertEqual(attempts[1]['reference'],'same-role-clean.wav');self.assertEqual(capture.call_count,2)
 def test_persistent_retry_budget_does_not_loop(self):
  model=Mock();model.run.return_value=iter([(24000,self.corrupt())])
  calls=[]
  def reserve():calls.append(1);return len(calls)<=1
  _,_,attempts=g.gsv_take(model,Mock(),dict(text='出發！',seed=42),reserve_attempt=reserve)
  self.assertEqual(model.run.call_count,1);self.assertEqual(len(attempts),1)
 def test_unavailable_file_is_not_a_pass_or_pipeline_abort(self):
  report=q.measure_file('/no-such-voice.wav')
  self.assertFalse(report['valid']);self.assertEqual(report['status'],'measurement-unavailable')
 def test_media_worker_pcm_does_not_need_soundfile(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'voice.wav'
   with wave.open(str(path),'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes((self.clean()*32767).astype('<i2').tobytes())
   with patch.dict(sys.modules,{'soundfile':None}):report=q.measure_file(path)
   self.assertTrue(report['valid']);self.assertEqual(report['impulses'],0)
 def render(self,root,manual=False):
  import dubbing,delivery
  path=root/'source.wav';clean=(self.clean()*32767).astype('<i2').tobytes();bad=(self.corrupt()*32767).astype('<i2').tobytes()
  with wave.open(str(path),'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(clean)
  cue=dict(start=0,end=1,cantonese='大家一齊出發，唔好落後！',speakerId='same-role')
  if manual:cue.update(editorAudio=str(path),editorRate=1.1)
  row=dict(index=1,seconds=2,slot=1)
  run=Mock(return_value=bad if manual else clean)
  with patch.object(delivery,'fit_audio',return_value=(bad,1.25)):
   dubbing.render_complete_preview(dict(duration=2,ffmpeg='ffmpeg',editorRender=manual),root,[cue],[path],[row],run,Mock())
  return row,run
 def test_time_fit_impulses_recover_full_clear_take_once(self):
  with tempfile.TemporaryDirectory() as directory:
   row,run=self.render(Path(directory))
   self.assertTrue(row['signalQuality']['timeFitBypassed']);self.assertEqual(row['rate'],1)
   self.assertFalse(row['signalQuality']['rendered']['warnings']);self.assertTrue(row['requiresTimingReview'])
   self.assertEqual(run.call_count,1)
 def test_explicit_manual_take_is_not_replaced_silently(self):
  with tempfile.TemporaryDirectory() as directory:
   row,_=self.render(Path(directory),True)
   self.assertFalse(row['signalQuality']['timeFitBypassed']);self.assertEqual(row['rate'],1.1)
   self.assertTrue(row['requiresSignalReview'])

if __name__=='__main__':unittest.main()
