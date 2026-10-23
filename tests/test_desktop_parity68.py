"""Desktop policy parity and bandwidth; classifier accuracy is not mocked as certified."""
import hashlib,json,math,subprocess,sys,tempfile,unittest,wave
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows')]
import nonverbal,fast_mode,native_tools
FF=ROOT/'dist/AniCanto.app/Contents/Resources/bin/ffmpeg'

class SharedPolicyTests(unittest.TestCase):
 def test_nonverbal_preservation_is_independent_of_fast_quality_checks(self):
  for platform in ('darwin','win32'):
   for mode in ('normal','fast'):
    with self.subTest(platform=platform,mode=mode),patch.object(sys,'platform',platform):
     cfg=fast_mode.configure(dict(productionMode=mode,preserveNonverbal=False))
     self.assertTrue(cfg['preserveNonverbal'])
     self.assertFalse(cfg['aiAutoFix'])
     self.assertFalse(cfg['autoValidate'])
  cfg=fast_mode.configure(dict(productionMode='fast',preserveNonverbal=False))
  cfg['productionMode']='standard';fast_mode.configure(cfg)
  self.assertFalse(cfg['preserveNonverbal'])

 def test_classifier_context_is_not_truncated_to_an_unvalidated_short_clip(self):
  sr=16000;audio=[0.]*(sr*6)
  rows=list(native_tools.classifier_windows(audio,sr,detailed=True))
  self.assertEqual([start for start,_,_ in rows],[0.,2.5,5.])
  self.assertEqual(len(rows[0][2]),5*sr)
  self.assertEqual(rows[-1][1],1.)
  self.assertEqual(nonverbal.classification_profile('win32')['windowSeconds'],5.)
  self.assertEqual(nonverbal.classification_profile('darwin')['windowSeconds'],1.)

 def test_windows_maps_crying_laughter_and_breath_categories_without_lowering_thresholds(self):
  labels={0:'Baby cry, infant cry',1:'Chuckle, chortle',2:'Pant',3:'Speech',4:'Singing'}
  result=native_tools.performance_scores(labels,[.96,.88,.82,.03,.01])
  self.assertEqual(result['crying_sobbing'],.96)
  self.assertEqual(result['laughter'],.88)
  self.assertEqual(result['breathing'],.82)
  events=nonverbal.event_ranges([dict(start=0,duration=1,**result)],[],2)
  self.assertEqual(events[0]['label'],'crying_sobbing')
  result['speech']=.7
  self.assertFalse(nonverbal.event_ranges([dict(start=0,duration=1,**result)],[],2))

 def test_events_use_same_shared_rules_on_both_platforms(self):
  rows=[dict(start=1.,duration=1.,laughter=.91,speech=.03),dict(start=2.,duration=1.,crying_sobbing=.92,speech=.03)]
  output=[]
  for platform in ('darwin','win32'):
   with patch.object(sys,'platform',platform):
    output.append(nonverbal.event_ranges(rows,[dict(start=2.5,end=3.5,japanese='行こう')],4))
  self.assertEqual(output[0],output[1]);self.assertTrue(output[0])
  self.assertTrue(all(e['end']<=2.38 for e in output[0]))

 def test_classification_cached_across_language_and_engine_tracks_and_invalidated_by_audio(self):
  calls=[]
  def run(args):calls.append(args);return json.dumps([dict(start=0.,duration=1.,laughter=.9,speech=.01)]).encode()
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);audio=root/'dialogue.wav';audio.write_bytes(b'first source')
   cfg=dict(storage=str(root),dialoguePath=str(audio),executable='native')
   for name in ('track-yue-drama','track-en-gpt'):
    (root/name).mkdir();nonverbal.classification(cfg,root/name,run)
   self.assertEqual(len(calls),1)
   audio.write_bytes(b'another source');nonverbal.classification(cfg,root/'track-yue-drama',run)
   self.assertEqual(len(calls),2)
   local=root/'track-yue-drama/nonverbal-classification-v3.json'
   metadata=json.loads(local.read_text());self.assertEqual(metadata['windowSeconds'],1.)
   self.assertEqual(metadata['hopSeconds'],.5)

 def test_old_unkeyed_classification_is_not_reused(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);audio=root/'dialogue.wav';audio.write_bytes(b'source')
   (root/'nonverbal-classification-v2.json').write_text('[{"start":0,"duration":5,"speech":0.9}]')
   calls=[]
   def run(args):calls.append(args);return b'[]'
   self.assertEqual(nonverbal.classification(dict(dialoguePath=str(audio),executable='native'),root,run),[])
   self.assertEqual(len(calls),1)

@unittest.skipUnless(FF.is_file(),'Bundled FFmpeg required')
class DeliveryTests(unittest.TestCase):
 def test_preserved_original_vocalization_keeps_rate_and_rebuilds_low_rate_cache(self):
  import dubbing
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);source=root/'source.wav'
   def tool(args):return subprocess.check_output([str(x) for x in args],stderr=subprocess.STDOUT)
   tool([FF,'-v','error','-f','lavfi','-i','sine=frequency=14000:sample_rate=44100:duration=1','-y',source])
   cfg=dict(ttsBackend='drama3',productionMode='fast',dialoguePath=str(source),ffmpeg=str(FF),storage=d,continueOnError=False)
   cue=dict(start=0,end=1,japanese='ああ',cantonese='啊')
   with patch('local_tts.validate'),patch('natural_voices.prepare_cast'):
    low=dubbing.gsv_audio(dict(cfg,audioSampleRate=24000),root,[cue],tool,lambda *a:None)[0]
    native=dubbing.gsv_audio(cfg,root,[cue],tool,lambda *a:None)[0]
   self.assertNotEqual(low,native)
   with wave.open(str(native)) as f:self.assertEqual(f.getframerate(),44100)

 def test_restoring_performance_keeps_drama_and_gpt_bandwidth(self):
  import numpy as np
  for engine,sr in [('drama3',44100),('gpt-sovits',48000)]:
   with self.subTest(engine=engine),tempfile.TemporaryDirectory() as d:
    root=Path(d);voice=root/'voice.wav';source=root/'source.wav'
    def tool(args):return subprocess.check_output([str(x) for x in args],stderr=subprocess.STDOUT)
    tool([FF,'-v','error','-f','lavfi','-i',f'sine=frequency=14000:sample_rate={sr}:duration=3','-y',voice])
    tool([FF,'-v','error','-f','lavfi','-i',f'sine=frequency=600:sample_rate={sr}:duration=3','-y',source])
    cfg=dict(ttsBackend=engine,ffmpeg=str(FF),duration=3,dialoguePath=str(source),executable='native')
    # Speech=.15 excludes whole-original restoration but permits an isolated event.
    rows=[dict(start=1.,duration=.5,laughter=.9,speech=.15)]
    with patch.object(nonverbal,'classification',return_value=rows):
     result=nonverbal.restore(cfg,root,[],voice,tool,lambda *a:None)
    with wave.open(str(result)) as f:
     self.assertEqual(f.getframerate(),sr);self.assertEqual(f.getnframes(),3*sr)
     samples=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').astype(float)
    spectrum=abs(np.fft.rfft(samples[:sr]));frequencies=np.fft.rfftfreq(sr,1/sr)
    self.assertLess(abs(frequencies[int(spectrum.argmax())]-14000),2)
    self.assertGreater(spectrum.max(),1e6)

if __name__=='__main__':unittest.main()
