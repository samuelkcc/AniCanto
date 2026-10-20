import os
import array,hashlib,math,sys,tempfile,unittest,wave,subprocess
from pathlib import Path
from unittest.mock import Mock
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import speech_level,dubbing_runner,repair_budget,mix_balance,engine_reference,dubbing

class SpeechLevelTests(unittest.TestCase):
 def tone(self,gain=.005):return np.r_[np.zeros(2400),gain*np.sin(np.arange(12000)*.08),np.zeros(2400)]
 def test_quiet_voice_boost_preserves_pauses_and_limits_gain(self):
  x=self.tone();y,r=speech_level.condition(x,24000)
  self.assertAlmostEqual(r['gainDB'],12,delta=.02)
  np.testing.assert_array_equal(np.asarray(y)[:2400],x[:2400]);self.assertEqual(len(y),len(x))
  self.assertLessEqual(max(abs(v) for v in y),10**(-1.5/20));self.assertIn('gain-limited',r['warnings'])
 def test_silence_and_extremely_weak_signal_are_not_amplified(self):
  for x in (np.zeros(2400),self.tone(.0002)):
   y,r=speech_level.condition(x,24000);self.assertEqual(r['gainDB'],0);np.testing.assert_array_equal(x,y)
 def test_healthy_voice_and_expressive_peak_are_not_compressed(self):
  x=self.tone(.16);y,r=speech_level.condition(x,24000);self.assertEqual(r['gainDB'],0);np.testing.assert_array_equal(x,y)
 def test_clear_original_reference_is_not_attenuated_to_minus24(self):
  x=self.tone(.22);y,r=speech_level.condition(x,24000,reference=True)
  self.assertEqual(r['gainDB'],0);np.testing.assert_array_equal(x,y)
 def test_previously_accepted_quiet_speech_is_boosted_with_peak_protection(self):
  x=self.tone(.094);x[7000]=.5
  y,r=speech_level.condition(x,24000)
  self.assertGreater(r['gainDB'],3);self.assertLessEqual(max(abs(v) for v in y),10**(-1.5/20)+.0001)
  self.assertLess(abs(r['outputActiveRMSDB']+19),1)
 def test_gpt_integer_output_is_scaled_before_saving_not_clipped(self):
  raw=(self.tone(.008)*32768).astype(np.int16);m=Mock();m.run.return_value=iter([(24000,raw)])
  sr,audio,attempts=dubbing_runner.gsv_take(m,Mock(),dict(text='我哋一齊出發啦。',seed=42))
  self.assertFalse(attempts[-1]['problems']);self.assertGreater(attempts[-1]['level']['gainDB'],8)
  self.assertLess(np.max(abs(audio)),.2);self.assertEqual(len(audio),len(raw))
 def test_clipping_is_still_rejected_after_lowering_gain(self):
  audio,errors,level=dubbing_runner.gsv_level(np.ones(24000),24000,'你好',None)
  self.assertIn('clipping',errors);self.assertIn('source-clipping',level['warnings'])
 def test_derived_stereo_take_is_cached_and_original_unchanged(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'native.wav';data=np.column_stack((self.tone(.005),self.tone(.8))).flatten()
   with wave.open(str(p),'wb') as f:f.setparams((2,2,24000,0,'NONE','not compressed'));f.writeframes((data*32767).astype('<i2').tobytes())
   before=hashlib.sha256(p.read_bytes()).hexdigest();a,r=speech_level.prepare_file(p,Path(d)/'derived');b,_=speech_level.prepare_file(p,Path(d)/'derived')
   self.assertEqual(a,b);self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),before)
   with wave.open(str(a)) as f:self.assertEqual(f.getnchannels(),2);x=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2')
   self.assertLessEqual(np.max(abs(x.astype(float)))/32768,10**(-1.5/20)+.001)
 def test_language_label_alone_does_not_discard_matching_cantonese(self):
  self.assertFalse(repair_budget.clear_content_problem(dict(cantonese='我哋一齊出發啦'),dict(languageMismatch=True,detectedLanguage='chinese',similarity=1)))
  self.assertFalse(repair_budget.clear_content_problem(dict(cantonese='路飛'),dict(languageMismatch=True,detectedLanguage='chinese',similarity=1)))
 def test_single_engine_reference_override_does_not_inherit_overlap_warning(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'ref.wav';p.write_bytes(b'x')
   profile=dict(id='one',name='one',reference=str(p),promptText='a',mixedReference=True,shortReference=True,engineReferences={'gpt-sovits:yue':dict(enabled=True,reference=str(p),promptText='你好')})
   result=dubbing.profile_for(dict(speakerId='one'),dict(voiceProfiles=[profile],ttsBackend='gpt-sovits',targetLanguage='yue'))
   self.assertFalse(result.get('mixedReference'));self.assertFalse(result.get('shortReference'))
 def test_mixed_reference_is_not_used_for_cloning(self):
  with self.assertRaisesRegex(ValueError,'多人重疊'):engine_reference.prepare({},Path('.'),dict(mixedReference=True),None)
 def test_optional_ducking_lowers_only_background_during_speech(self):
  ffmpeg=Path(os.environ.get('ANICANTO_TEST_FFMPEG',str(Path(__file__).resolve().parents[1]/'dist/AniCanto.app/Contents/Resources/bin/ffmpeg')))
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);sr=24000;t=np.arange(3*sr)/sr;voice=.15*np.sin(2*np.pi*200*t)*((t>1)&(t<2));bg=.05*np.sin(2*np.pi*700*t)
   for name,x in [('voice',voice),('bg',bg)]:
    with wave.open(str(p/(name+'.wav')),'wb') as f:f.setparams((1,2,sr,0,'NONE','not compressed'));f.writeframes((x*32767).astype('<i2').tobytes())
   levels=[]
   for duck in (False,True):
    filters=mix_balance.separated_filter(.8,duck=duck)
    cmd=[str(ffmpeg),'-v','error','-i',str(p/'bg.wav'),'-i',str(p/'voice.wav'),'-i',str(p/'bg.wav'),'-i',str(p/'bg.wav'),'-filter_complex',filters,'-map','[dub]','-ar',str(sr),'-ac','1','-f','f32le','pipe:1']
    x=np.frombuffer(subprocess.check_output(cmd),dtype='<f4')
    def amplitude(a,b):
     selected=x[round(a*sr):round(b*sr)];window=t[:len(selected)];return abs(np.mean(selected*np.exp(-2j*np.pi*700*window)))*2
    levels.append((amplitude(.3,.7),amplitude(1.3,1.7)))
   self.assertAlmostEqual(levels[0][0],levels[1][0],delta=.002);self.assertLess(levels[1][1],levels[0][1]*.65)
