"""Check desktop caption-gap execution, exact audio evidence and optional export cache."""
import copy,errno,json,sys,tempfile,unittest,wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows')]
import caption_gap445 as gap,final_background445 as background,primary_source,source_workflow,review_report,dialogue_policy441,asr_verify
from desktop_state import Store,read

class CaptionGap445(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.job=Path(self.tmp.name)
  with wave.open(str(self.job/'japanese-original.wav'),'wb') as f:f.setparams((1,2,16000,0,'NONE','not compressed'));f.writeframes(b'\0\0'*64000)
  self.cfg=dict(captionGapPolicyRevision=gap.REVISION,sourceWorkflow='auto',sourceWorkflowRevision=source_workflow.REVISION,sourceWorkflowEffective='subtitles-speech',sourceContentPriority='subtitles',sourcePolicyRevision=primary_source.REVISION,sourceAllocationRevision=primary_source.ALLOCATION_REVISION,duration=4,sourceLanguage='ja')
  self.captions=[dict(id='caption_1',start=0,end=.5,text='字幕前句'),dict(id='caption_2',start=3,end=4,text='字幕後句')]
  (self.job/'subtitle-context.json').write_text(json.dumps(self.captions))
  self.w=Mock();self.w.atomic_json.side_effect=lambda p,v:Path(p).write_text(json.dumps(v,ensure_ascii=False))
 def cue(self,first='今日はみんなと遊びましょう。',second=None):
  c=dict(start=1,end=2,text=first,japanese=first,enabled=True)
  gap.independent(self.cfg,self.job,c,dict(text=first if second is None else second),'fixture-asr');return c
 def rows(self,speech=.8,sound=.01):
  return [dict(start=a,duration=.5,speech=speech,singing=.01,choir_singing=.01,rapping=.01,music=.05,thump_thud=sound,gapTaxonomyComplete445=1) for a in (1,1.5)]
 def prepare(self,c,rows):
  with patch('caption_gap445.sound_for',return_value=rows):primary_source.prepare(self.w,self.cfg,self.job,[c])
  return c
 def test_actual_primary_source_admits_complete_independent_gap_and_keeps_clocks(self):
  c=self.cue(second='えっと、今日はみんなと遊びましょう。');self.prepare(c,self.rows())
  self.assertTrue(c['captionGapSpeech445']);self.assertEqual(primary_source.content(c),'えっと、今日はみんなと遊びましょう。');self.assertEqual((c['start'],c['end']),(1,2));self.assertFalse(c.get('preserveOriginalSpeech'));self.w.ollama_chat.assert_not_called()
 def test_bounded_filler_match_rejects_changed_meaning_short_names_and_substrings(self):
  for language,a,b,ok in [('ja','えっと、今日はみんなと遊びましょう','今日はみんなと遊びましょう',True),('en','Um, we should leave this place','we should leave this place',True),('ja','えっと、田中','田中',False),('ja','今日は行く','今日は行かない',False),('en','um, we will go','we will not go',False),('ja','今日はみんなと遊びましょう','みんなと遊びましょう',False),('ja','えっと今日はみんなと遊びましょう','今日はみんなと遊びましょう',False)]:
   with self.subTest(a=a,b=b):self.assertEqual(gap.agrees(a,b,language),ok)
 def test_positive_complete_sound_is_preserved_and_excluded_from_unknown_and_timeline(self):
  c=self.cue('',second='');self.prepare(c,self.rows(speech=.01,sound=.98))
  self.assertEqual(c['originalSpeechReason'],gap.CONFIRMED);self.assertFalse(dialogue_policy441.source_unconfirmed(c));self.assertTrue(dialogue_policy441.excluded_card(c))
 def test_missing_taxonomy_failed_source_lexical_name_and_incomplete_coverage_stay_unknown(self):
  for change in ('taxonomy','coverage','source-failed','name','corrupt-audio','singing'):
   c=self.cue('',second='');rows=self.rows(speech=.01,sound=.98)
   if change=='taxonomy':rows[0].pop('gapTaxonomyComplete445')
   if change=='coverage':rows=rows[1:]
   if change=='source-failed':c['sourceClockUnconfirmed']=True
   if change=='name':c=self.cue('媽媽',second='媽媽')
   if change=='corrupt-audio':c['captionGapIndependent445']['audioSHA256']='f'*64
   if change=='singing':rows[0]['singing']=.6
   self.prepare(c,rows);self.assertEqual(c['originalSpeechReason'],gap.UNKNOWN,change);self.assertTrue(dialogue_policy441.source_unconfirmed(c));self.assertFalse(c.get('noSpeech'))
 def test_unknown_and_nondialogue_pass_actual_render_validation_as_original_not_missing_script(self):
  import worker
  for text,rows in [('',self.rows(speech=.01,sound=.98)),('今日はみんなと遊びましょう',self.rows(speech=.01,sound=.01))]:
   cue=self.cue(text);self.prepare(cue,rows)
   result=worker.validate_review([cue],copy.deepcopy([cue]),4)
   self.assertTrue(result[0]['preserveOriginalSpeech']);self.assertTrue(result[0]['subtitleContentOnlyGap']);self.assertFalse(result[0].get('missingScript'))
 def test_crossing_coarse_unit_does_not_create_gap_evidence(self):
  self.assertFalse(gap.bounds(dict(start=.25,end=1.5),self.captions,4))
  self.assertIsNone(gap.evidence(self.rows(speech=.01,sound=.98),1.2,2,'',''))
 def test_explicit_subtitle_and_old_requests_keep_old_gap_policy(self):
  for change in ('manual','legacy'):
   cfg=dict(self.cfg)
   if change=='manual':cfg['sourceWorkflow']='subtitles-speech'
   else:cfg.pop('captionGapPolicyRevision')
   c=self.cue()
   with patch('nonverbal.classification') as classify:primary_source.prepare(self.w,cfg,self.job,[c]);classify.assert_not_called()
   self.assertTrue(c['subtitleContentOnlyGap']);self.assertFalse(c.get('captionGapSpeech445'))
 def test_report_cause_is_source_disagreement_without_missing_model_claim(self):
  c=self.cue('今日はみんなと遊びましょう',second='ここに誰もいません');self.prepare(c,self.rows())
  review=dict(config=dict(self.cfg,dubLanguages=['yue'],selectedEngines=['drama3'],ttsBackend='drama3'),cues=[c]);(self.job/'review.json').write_text(json.dumps(review));(self.job/'timing.json').write_text('[]')
  report=review_report.project(self.job,review,dict(status='complete'))
  self.assertEqual(report['reviewState']['sourceUnconfirmed'],1);self.assertEqual(report['reviewState']['needsDubbing'],0)
  self.assertTrue(any(i.get('message')==gap.MESSAGE for i in report['issues']))
 def test_existing_independent_pass_is_bound_and_cached_without_an_extra_call(self):
  cfg=dict(self.cfg,asrModel='fixture-asr',storage=str(self.job));c=dict(start=1,end=2,text='今日はみんなと遊びましょう',japanese='今日はみんなと遊びましょう',enabled=True)
  def model(*args):
   (self.job/'asr-verification.json').write_text(json.dumps(dict(model='fixture-asr',identity=[[1,2,True]],rows=[dict(text=c['text'],agreement=1)])))
  with patch('dubbing.model_job',side_effect=model) as invoke:
   asr_verify.analyze(cfg,self.job,[c],Mock(),Mock());before=(self.job/'asr-verification.json').read_bytes();asr_verify.analyze(cfg,self.job,[c],Mock(),Mock())
   self.assertEqual(invoke.call_count,1);self.assertEqual((self.job/'asr-verification.json').read_bytes(),before)
  self.assertEqual(c['captionGapIndependent445']['audioSHA256'],gap.audio_digest(self.job/'japanese-original.wav',1,2))
 def test_exact_sound_window_reserves_once_and_reuses_cache_on_resume(self):
  c=self.cue();rows=self.rows(speech=.01,sound=.98)
  import nonverbal
  local=[dict({k:.01 for k in nonverbal.SCORE_LABELS},start=r['start']-1,duration=.5,thump_thud=.98,gapTaxonomyComplete445=1) for r in rows]
  self.cfg['executable']='isolated-classifier'
  self.w.run.return_value=json.dumps(local).encode()
  first=gap.sound_for(self.w,self.cfg,self.job,self.job/'japanese-original.wav',1,2,c['captionGapIndependent445']['audioSHA256'])
  self.assertEqual(len(first),2);self.assertEqual(self.w.run.call_count,1)
  ledger=self.job/'source-clock-recovery.json';before=ledger.read_bytes()
  self.assertEqual(gap.sound_for(self.w,self.cfg,self.job,self.job/'japanese-original.wav',1,2,c['captionGapIndependent445']['audioSHA256']),first)
  self.assertEqual(ledger.read_bytes(),before);self.assertEqual(self.w.run.call_count,1)
 def test_spent_or_interrupted_source_allowance_does_not_classify_again(self):
  from source_clock_recovery import REVISION,MAX_WINDOWS
  c=self.cue();path=self.job/'source-clock-recovery.json'
  path.write_text(json.dumps(dict(revision=REVISION,attempts=MAX_WINDOWS,spentSeconds=33,windows={})))
  before=path.read_bytes()
  self.assertEqual(gap.sound_for(self.w,self.cfg,self.job,self.job/'japanese-original.wav',1,2,c['captionGapIndependent445']['audioSHA256']),[])
  self.w.run.assert_not_called();self.assertEqual(path.read_bytes(),before)
 def test_new_english_source_uses_english_independent_request(self):
  cfg=dict(self.cfg,sourceLanguage='en',asrModel='fixture-asr',storage=str(self.job));c=dict(start=1,end=2,text='We should leave this place',japanese='We should leave this place',enabled=True)
  def model(_cfg,_action,request,_emit):
   self.assertEqual(request['sourceLanguage'],'en')
   (self.job/'asr-verification.json').write_text(json.dumps(dict(model='fixture-asr',identity=[[1,2,True]],rows=[dict(text=c['text'],agreement=1)])))
  with patch('dubbing.model_job',side_effect=model):asr_verify.analyze(cfg,self.job,[c],Mock(),Mock())
  self.assertEqual(c['captionGapIndependent445']['text'],c['text'])
 def test_interrupted_sound_time_remains_spent_before_another_window(self):
  from source_clock_recovery import REVISION
  c=self.cue();path=self.job/'source-clock-recovery.json'
  path.write_text(json.dumps(dict(revision=REVISION,attempts=1,spentSeconds=70,activeSince=100,windows={'old':dict(status='reserved')})))
  with patch('caption_gap445.time.time',return_value=125):
   self.assertEqual(gap.sound_for(self.w,self.cfg,self.job,self.job/'japanese-original.wav',1,2,c['captionGapIndependent445']['audioSHA256']),[])
  ledger=json.loads(path.read_text());self.assertEqual(ledger['spentSeconds'],95);self.assertEqual(ledger['attempts'],1);self.assertNotIn('activeSince',ledger);self.w.run.assert_not_called()
 def test_corrupt_sound_ledger_is_not_reset_to_a_new_allowance(self):
  c=self.cue();path=self.job/'source-clock-recovery.json';path.write_text('{invalid')
  self.assertEqual(gap.sound_for(self.w,self.cfg,self.job,self.job/'japanese-original.wav',1,2,c['captionGapIndependent445']['audioSHA256']),[])
  self.assertEqual(path.read_text(),'{invalid');self.w.run.assert_not_called()
 def test_actual_fast_source_analysis_reuses_loaded_whisper_and_saved_gap_hypothesis(self):
  import numpy as np,dialogue
  cfg=dict(self.cfg,productionMode='normal',storage=str(self.job),speechModel='fixture-whisper',video='fixture-video',ffmpeg='fixture-ffmpeg')
  (self.job/'speech-ready.json').write_text('{}');text='今日はみんなと遊びましょう。'
  word=SimpleNamespace(start=1.,end=2.,word=text,probability=.99)
  segment=SimpleNamespace(start=1.,end=2.,text=text,words=[word])
  model=Mock();model.chosen=dict(backend='fixture',id='fixture-whisper');model.transcribe.side_effect=lambda audio,**kw:([segment] if kw['word_timestamps'] else [SimpleNamespace(text=text)],{})
  execute=Mock(return_value=np.zeros(64000,dtype=np.float32).tobytes())
  vad=SimpleNamespace(get_speech_timestamps=lambda *a:[dict(start=16000,end=32000)],VadOptions=lambda **kw:kw)
  with patch.dict(sys.modules,{'faster_whisper':SimpleNamespace(vad=vad),'faster_whisper.vad':vad}),patch('whisper_accel.load',return_value=model) as load,patch('whisper_accel.identity',return_value='fixture'),patch('model_catalog.resolve',return_value=self.job),patch('model_catalog.choice',return_value=dict(revision='pinned-fixture')):
   first=dialogue.analyze(cfg,self.job,self.captions,execute,Mock())
   before=(self.job/'source-clock-recovery.json').read_bytes()
   second=dialogue.analyze(dict(cfg),self.job,self.captions,execute,Mock())
   self.assertEqual(load.call_count,1);self.assertEqual(model.transcribe.call_count,2)
  self.assertEqual(first[0]['captionGapIndependent445'],second[0]['captionGapIndependent445'])
  self.assertEqual((self.job/'source-clock-recovery.json').read_bytes(),before)
  self.assertEqual(first[0]['captionGapIndependent445']['text'],text)
  self.assertEqual(json.loads(before)['attempts'],1)
 def test_fast_gap_comparison_keeps_half_the_remaining_allowance_for_sound(self):
  import numpy as np
  from source_clock_recovery import REVISION,MAX_WINDOWS
  ledger=self.job/'source-clock-recovery.json';ledger.write_text(json.dumps(dict(revision=REVISION,attempts=MAX_WINDOWS-4,spentSeconds=0,windows={})))
  model=Mock();model.transcribe.side_effect=lambda *a,**k:([SimpleNamespace(text='今日はみんなと遊びましょう。')],{})
  cues=[dict(start=1.,end=1.2,text='今日はみんなと遊びましょう。'),dict(start=1.3,end=1.5,text='今日はみんなと遊びましょう。'),dict(start=1.6,end=1.8,text='今日はみんなと遊びましょう。')]
  gap.corroborate(model,np.zeros(64000),self.cfg,self.job,cues,self.captions,'fixture',self.w.atomic_json,Mock())
  self.assertEqual(model.transcribe.call_count,2);self.assertEqual(json.loads(ledger.read_text())['attempts'],MAX_WINDOWS-2)
  self.assertIn('captionGapIndependent445',cues[0]);self.assertNotIn('captionGapIndependent445',cues[2])
 def test_new_basic_expert_freeze_policies_and_resume_preserves_spent_bytes(self):
  for mode in ('basic','expert'):
   folder=self.job/mode;folder.mkdir();v=folder/'fixture.mp4';v.write_bytes(b'fixture');store=Store(folder);store.mode=mode;store.add([v]);row=store.queue[0];p=store.submit(row);cfg=read(p)
   self.assertEqual(cfg['captionGapPolicyRevision'],gap.REVISION);self.assertEqual(cfg['optionalSourceCacheRevision'],background.REVISION)
   cfg.pop('captionGapPolicyRevision');cfg['recoverySpentSeconds']=59;p.write_text(json.dumps(cfg));before=p.read_bytes();row['status']='paused';store.submit(row);self.assertEqual(p.read_bytes(),before)

class OptionalBackground445(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.job=Path(self.tmp.name);v=self.job/'source.mp4';v.write_bytes(b'fixture');self.cfg=dict(video=str(v),storage=str(self.job),duration=4,optionalSourceCacheRevision=background.REVISION)
 def bound(self):
  folder=background.folder(self.cfg);folder.mkdir(parents=True)
  for name in ('background.wav','dialogue.wav'):(folder/name).write_bytes(name.encode())
  background.remember(self.cfg,folder);return folder
 def test_same_source_bound_cache_reuses_without_separation(self):
  folder=self.bound()
  with patch('dubbing.validate_stems') as validate,patch('dubbing.model_job') as models:
   self.assertEqual(background.prepare(self.cfg,self.job,Mock(),Mock()),folder/'background.wav');models.assert_not_called();validate.assert_called_once()
 def test_foreign_range_or_corrupt_cache_falls_back_without_model(self):
  folder=self.bound();(folder/'background.wav').write_bytes(b'changed')
  with patch('dubbing.model_job') as models:self.assertIsNone(background.prepare(self.cfg,self.job,Mock(),Mock()));models.assert_not_called()
  cfg=dict(self.cfg,startOffset=2)
  self.assertIsNone(background.prepare(cfg,self.job,Mock(),Mock()))
  self.assertFalse(json.loads((self.job/'optional-background445.json').read_text())['separationRepeated'])
 def test_optional_preservation_failure_keeps_the_verified_bed(self):
  bed=self.bound()/'background.wav'
  with patch('nonverbal.preserve_background',side_effect=RuntimeError('fixture')):self.assertEqual(background.preserve(self.cfg,self.job,bed,Mock(),Mock()),bed)
 def test_caption_mix_uses_the_same_optional_preservation_guard(self):
  import source_evidence
  audio=self.job/'saved-voice.wav';audio.write_bytes(b'fixture')
  with patch('nonverbal.preserve_background',side_effect=RuntimeError('fixture')):
   self.assertEqual(source_evidence.mix_caption_audio(Mock(),self.cfg,self.job,audio),audio)
  self.assertEqual(json.loads((self.job/'optional-background445.json').read_text())['status'],'source-mix-fallback')
 def test_storage_and_user_pause_are_not_swallowed(self):
  from track_control import UserSkipped
  for error in (OSError(errno.ENOSPC,'full'),UserSkipped('pause')):
   with patch('nonverbal.preserve_background',side_effect=error),self.assertRaises(type(error)):background.preserve(self.cfg,self.job,self.job/'bed',Mock(),Mock())

if __name__=='__main__':unittest.main()
