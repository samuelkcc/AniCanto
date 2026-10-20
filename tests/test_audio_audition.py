import sys,json,tempfile,unittest,wave
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import audio_audition,dubbing_runner,delivery
class AuditionTests(unittest.TestCase):
 def test_explicit_rerun_reopens_budget_but_automatic_seed_retry_does_not(self):
  from workflow_policy import reserve
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);reference=root/'reference.wav';reference.write_bytes(b'reference')
   item=dict(text='羈絆紅',reviewIndex=56,profile=dict(id='R06',reference=str(reference),promptText='參考',language='yue'))
   cfg=dict(audioRerunToken='take-one')
   first=dubbing_runner.generation_identity(cfg,item)
   for _ in range(4):self.assertTrue(reserve(root,'gpt',first))
   self.assertFalse(reserve(root,'gpt',dubbing_runner.generation_identity(cfg,dict(item,seed=173))))
   fresh=dubbing_runner.generation_identity(dict(cfg,audioRerunToken='take-two'),item)
   self.assertTrue(reserve(root,'gpt',fresh))
 def test_replaced_reference_bytes_invalidate_exhausted_identity(self):
  with tempfile.TemporaryDirectory() as d:
   reference=Path(d)/'reference.wav';reference.write_bytes(b'old')
   item=dict(text='羈絆紅',profile=dict(id='R06',reference=str(reference),promptText='參考',language='yue'))
   before=dubbing_runner.generation_identity({},item);reference.write_bytes(b'new')
   self.assertNotEqual(before,dubbing_runner.generation_identity({},item))
 def test_exhausted_budget_has_no_invented_sample_rate(self):
  model=Mock()
  sr,audio,attempts=dubbing_runner.gsv_take(model,Mock(),dict(text='羈絆紅！',seed=42),reserve_attempt=lambda:False)
  self.assertEqual(sr,0);self.assertEqual(audio,[]);self.assertEqual(attempts[-1]['problems'],['retry-budget-exhausted']);model.run.assert_not_called()
 def audition(self,heard,confirmed=False):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);path=root/'take.wav'
   with wave.open(str(path),'wb') as f:f.setparams((1,2,48000,0,'NONE','not compressed'));f.writeframes(__import__('array').array('h',[1000,-1000]*24000).tobytes())
   w=Mock();w.atomic_json=lambda p,o:Path(p).write_text(json.dumps(o))
   cue=dict(start=999,end=1001,cantonese='羈絆紅！',editorAudio='old.wav')
   with patch('dubbing.gsv_audio',return_value=[path]) as generate,patch('speechcheck.inspect',return_value=[dict(heard=heard,cantoneseReviewPolicy=__import__('cantonese_review').REVISION,confirmedContentFailure=confirmed)]),patch('dubbing.profile_for',return_value=dict(id='role',reference=str(path))):
    if heard or not confirmed:
     result,seconds=audio_audition.generate(w,{},root,cue);self.assertEqual(result,path);self.assertEqual(seconds,1)
    else:
     with self.assertRaisesRegex(ValueError,'未能辨認'):audio_audition.generate(w,{},root,cue)
     self.assertTrue(json.loads((root/'timing.json').read_text())[0]['skipped'])
    self.assertNotIn('editorAudio',generate.call_args.args[2][0]);self.assertEqual(cue['editorAudio'],'old.wav');w.run.assert_not_called()
 def test_single_native_take_without_video_or_timeline_render(self):self.audition('羈絆紅')
 def test_independently_unrecognized_words_are_rejected(self):self.audition('',confirmed=True)
 def test_unconfirmed_empty_asr_keeps_audible_original_available_for_audition(self):self.audition('')
 def test_critical_negation_mismatch_never_marked_playable(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);path=root/'take.wav'
   with wave.open(str(path),'wb') as f:f.setparams((1,2,48000,0,'NONE','not compressed'));f.writeframes(__import__('array').array('h',[1000,-1000]*24000).tobytes())
   w=Mock();w.atomic_json=lambda p,o:Path(p).write_text(json.dumps(o))
   with patch('dubbing.gsv_audio',return_value=[path]),patch('speechcheck.inspect',return_value=[dict(heard='好放棄',criticalDifferences=['negation:唔'],cantoneseReviewPolicy=__import__('cantonese_review').REVISION,confirmedContentFailure=True)]),patch('dubbing.profile_for',return_value=dict(id='role',reference=str(path))):
    with self.assertRaisesRegex(ValueError,'關鍵字'):audio_audition.generate(w,{},root,dict(start=0,end=1,cantonese='唔好放棄'))
   self.assertTrue(json.loads((root/'timing.json').read_text())[0]['skipped']);self.assertTrue(path.exists())

 def test_short_wordless_take_is_quarantined_after_review(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);path=root/'bad.wav'
   with wave.open(str(path),'wb') as audio:audio.setparams((1,2,48000,0,'NONE','not compressed'));audio.writeframes(bytes(42240))
   cue=dict(start=2,end=3,cantonese='羈絆紅',reviewIndex=0,speakerId='role')
   check=dict(heard='',requiresReview=True,similarity=0,languageUnverified=True,cantoneseReviewPolicy=__import__('cantonese_review').REVISION,confirmedContentFailure=True,independentCheck=dict(heard=''))
   with patch('speechcheck.inspect',return_value=[check]),patch('project_store.record_issue') as issue:
    result=delivery.check_content(dict(autoContentRepair=False),root,[cue],[path],Mock(),Mock(),Mock())
   self.assertTrue(result[0].name.startswith('skipped-'));self.assertTrue(path.exists());issue.assert_called_once()
 def test_correct_words_can_replace_short_noise_despite_longer_duration(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);before=root/'before.wav';after=root/'after.wav';before.touch();after.touch()
   old=dict(heard='',requiresReview=True,similarity=0,languageUnverified=True,cantoneseReviewPolicy=__import__('cantonese_review').REVISION,confirmedContentFailure=True,independentCheck=dict(heard=''));new=dict(heard='羈絆紅',requiresReview=False,similarity=1)
   cue=dict(start=0,end=.5,cantonese='羈絆紅',reviewIndex=0)
   run=lambda args:json.dumps(dict(format=dict(duration=.44 if args[-1]==before else 2))).encode()
   with patch('speechcheck.inspect',side_effect=[[old],[new]]),patch.object(delivery,'prepare_audio',side_effect=lambda c,j,p,r:p):
    paths=delivery.check_content(dict(storage=d,ffprobe='probe'),root,[cue],[before],Mock(return_value=[after]),run,Mock())
   self.assertEqual(paths,[after])
if __name__=='__main__':unittest.main()
