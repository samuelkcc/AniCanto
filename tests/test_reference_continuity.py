"""Episode 05: lexical concatenations were skipped by every cloned voice engine."""
import copy,json,sys,tempfile,unittest,wave,subprocess
from pathlib import Path
from unittest.mock import Mock,patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import reference_recovery as recovery,dubbing,gsv_reference
FFMPEG=Path(__file__).resolve().parents[1]/'dist/AniCanto.app/Contents/Resources/bin/ffmpeg'

def wav(path,seconds=5):
 with wave.open(str(path),'wb') as f:
  f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes((np.sin(np.arange(round(seconds*24000))*.1)*4000).astype('<i2').tobytes())

class ContinuityTests(unittest.TestCase):
 def setup_profile(self,root):
  wav(root/'source.wav',10);wav(root/'joined.wav',4)
  p=dict(id='actor',name='Actor',reference=str(root/'joined.wav'),promptText='実際の日本語です',language='ja',referenceRanges=[[1,3],[6,8]],transcriptSource='original-japanese-words')
  pool=[dict(start=0,end=2.7,japanese='実際の日本語です',speakerId='actor'),dict(start=2.8,end=4,japanese='別の人物です',speakerId='other')]
  (root/'cues.json').write_text(json.dumps(pool));cfg=dict(voiceStyleMode='clone',dialoguePath=str(root/'source.wav'),storage=str(root),ffmpeg=str(FFMPEG),executable='classifier',_referenceCueFile=str(root/'cues.json'),_referenceRecoveryRoot=str(root),referenceSpeechModel='local-whisper')
  return cfg,p
 def run_command(self,args):
  if str(args[0])=='classifier':return json.dumps([dict(speech=.95,singing=.01)]).encode()
  if str(args[0])==str(FFMPEG):return subprocess.run(list(map(str,args)),check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
  request=json.loads(Path(args[-1]).read_text());return json.dumps(dict(rows=[dict(x,verified=True,promptText='実際の日本語です') for x in request['items']])).encode()
 def test_spoken_concatenation_recovers_another_same_role_utterance_and_pads_only_silence(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cfg,p=self.setup_profile(root);before=copy.deepcopy(p);original=Path(p['reference']).read_bytes();run=Mock(side_effect=self.run_command)
   with patch.object(gsv_reference,'prepare',return_value={}):result=recovery.prepare(cfg,root,p,run,Mock())
   self.assertEqual(result['referenceRanges'],[[0,2.7]]);self.assertEqual(p,before);self.assertEqual(Path(p['reference']).read_bytes(),original)
   with wave.open(result['reference']) as f:
    rate=f.getframerate();samples=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2');self.assertAlmostEqual(len(samples)/rate,3.1)
    self.assertGreater(np.max(np.abs(samples[:int(2.6*rate)])),1000);self.assertEqual(np.max(np.abs(samples[int(2.72*rate):])),0)
   calls=run.call_count
   with patch.object(gsv_reference,'prepare',side_effect=AssertionError('cached across engines')):again=recovery.prepare(dict(cfg,ttsBackend='drama3'),root/'other-engine',p,run,Mock())
   self.assertEqual(again,result);self.assertEqual(run.call_count,calls)
 def test_neighbour_voice_and_nonlexical_source_cannot_supply_reference(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cfg,p=self.setup_profile(root)
   (root/'cues.json').write_text(json.dumps([dict(start=0,end=4,japanese='実際の日本語です',speakerId='actor'),dict(start=3,end=5,japanese='別の人物です',speakerId='other'),dict(start=6,end=9,japanese='ああああああ',speakerId='actor')]))
   with patch.object(gsv_reference,'prepare',return_value={}):
    with self.assertRaises(ValueError):recovery.prepare(cfg,root,p,Mock(side_effect=self.run_command),Mock())
 def test_ep07_expressive_lexical_original_survives_classifier_only_rejection(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cfg,p=self.setup_profile(root);p.update(referenceRanges=[[1,3]],promptText='痛い痛い痛い痛',shortReference=True)
   before=copy.deepcopy(p);run=Mock(return_value=json.dumps([dict(speech=.1635,singing=.0162,laughter=.578,music=.58)]).encode())
   result=recovery.prepare(cfg,root,p,run,Mock())
   self.assertEqual(result['reference'],p['reference']);self.assertIn('referenceAdvisory',result);self.assertEqual(p,before)
 def test_strong_singing_mixed_and_silent_samples_are_not_rescued_by_transcript(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cfg,p=self.setup_profile(root);p.update(referenceRanges=[[1,3]])
   self.assertFalse(recovery.expressive_reference(p['reference'],p,[dict(speech=.1,singing=.9)]))
   self.assertFalse(recovery.expressive_reference(p['reference'],dict(p,mixedReference=True),[dict(speech=.1)]))
   with wave.open(str(root/'silent.wav'),'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(bytes(24000*6))
   self.assertFalse(recovery.expressive_reference(root/'silent.wav',p,[dict(speech=.1)]))
 def test_manual_and_independent_references_remain_unchanged(self):
  for p in [dict(referenceRanges=[],language='ja',transcriptSource='original-japanese-words'),dict(referenceRanges=[[0,4]],language='yue',transcriptSource='manual')]:
   run=Mock();self.assertIs(recovery.prepare(dict(voiceStyleMode='clone'),Path('/unused'),p,run,Mock()),p);run.assert_not_called()
 def test_every_active_clone_engine_prepares_each_role_once_before_dispatch(self):
  class Prepared(Exception):pass
  for engine in ['gpt-sovits-v2','gpt-sovits','cosyvoice3','voxcpm2','wsyue','drama3']:
   with self.subTest(engine=engine),tempfile.TemporaryDirectory() as d:
    root=Path(d);cfg,p=self.setup_profile(root);cfg.update(ttsBackend=engine,voiceProfiles=[p],gsvVersion='v4' if engine=='gpt-sovits' else 'v2ProPlus',targetLanguage='yue',continueOnError=False)
    cue=dict(start=1,end=3,cantonese='出發啦。',speakerId='actor')
    with patch('natural_voices.prepare_cast'),patch('local_tts.validate'),patch.object(recovery,'prepare',side_effect=Prepared) as prepare:
     with self.assertRaises(Prepared):dubbing.gsv_audio(cfg,root,[cue],Mock(),Mock())
     self.assertEqual(prepare.call_count,1)

class AIReferenceActionTests(unittest.TestCase):
 def test_repair_action_requires_automatic_same_role_source_not_manual_card(self):
  import ai_result_repair as ai
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);wav(root/'source.wav');(root/'pool.json').write_text('[]')
   cfg=dict(voiceStyleMode='clone',dialoguePath=str(root/'source.wav'),_referenceCueFile=str(root/'pool.json'),voiceProfiles=[dict(id='actor',transcriptSource='original-japanese-words')])
   cue=dict(start=0,end=2,text='日本語',cantonese='出發啦。',speakerId='actor')
   (root/'timing.json').write_text(json.dumps([dict(index=1,skipped=True,renderedSeconds=0)]));(root/'segment-issues.json').write_text(json.dumps([dict(index=1,kind='reference',message='參考錄音不連續')]))
   track=dict(folder=root,engine='cosyvoice3',language='yue')
   (root/'review.json').write_text(json.dumps(dict(config=cfg,cues=[cue])))
   self.assertIn('repair-reference',ai.collect(track,[track])[0]['allowedActions'])
   cfg['voiceProfiles'][0]['transcriptSource']='manual'
   (root/'review.json').write_text(json.dumps(dict(config=cfg,cues=[cue])))
   self.assertNotIn('repair-reference',ai.collect(track,[track])[0]['allowedActions'])
