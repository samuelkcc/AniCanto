"""Source clocks, caption ownership and independent repair controls; isolated data only."""
import copy,json,sys,tempfile,unittest,math,wave,shutil
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'Resources'),str(R/'windows'),str(R/'studio')]
import source_clock_recovery as clock,caption_coverage,primary_source,translation_editorial
from atomic_files import write_json

def broad():return dict(start=0,end=20,text='⑸ себе転移',words=[dict(start=0,end=1,word='⑸',probability=.3),dict(start=1,end=19,word='転',probability=.3),dict(start=19,end=20,word='移',probability=.5)])
class ClockTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.job=Path(self.temp.name);self.cfg=dict(sourceClockRecoveryRevision=clock.REVISION,duration=30,sourceLanguage='ja');self.calls=[]
 def model(self,fail=False):
  def transcribe(audio,**kw):
   self.calls.append(len(audio))
   if fail:raise RuntimeError('interrupted')
   words=[NS(start=k*.5,end=(k+1)*.5,word=x,probability=.95) for k,x in enumerate(['今日','は','いい','天気','です','ね'])]
   return iter([NS(words=words)]),None
  return NS(transcribe=transcribe)
 def run_repair(self,model):return clock.repair(model,[0.0]*480000,[broad()],self.cfg,self.job,lambda *a,**k:None)
 def test_exact_sparse_long_word_trigger_with_one_vad_span(self):self.assertTrue(clock.suspect(broad()))
 def test_real_elongated_cry_not_triggered(self):
  r=broad();r['text']='ああああ';self.assertFalse(clock.suspect(r))
 def test_healthy_fast_dialogue_not_triggered(self):
  self.assertFalse(clock.suspect(dict(start=0,end=20,text='今日はとても天気が良いですね'*5,words=[dict(start=0,end=.5,word='今日')])) )
 def test_windows_are_bounded_audio_clocks_without_caption_input(self):
  ws=clock.windows(broad(),20);self.assertEqual(len(ws),3);self.assertEqual(ws[-1]['end'],20);self.assertTrue(all(w['end']-w['start']<=8 for w in ws))
 def test_new_policy_only_and_legacy_input_unchanged(self):
  rows=[broad()];self.assertIs(clock.repair(self.model(),[],rows,{},self.job,None),rows);self.assertFalse(self.calls)
 def test_complete_recovery_keeps_segment_boundaries(self):
  rows=self.run_repair(self.model());self.assertEqual(len(rows),3);self.assertTrue(all(r.get('sourceClockRepaired') for r in rows));self.assertEqual(len(self.calls),3)
 def test_resume_reuses_reserved_attempts_without_refund(self):
  first=self.run_repair(self.model(True));self.assertTrue(first[0]['sourceClockUnconfirmed']);self.run_repair(self.model());self.assertEqual(len(self.calls),3)
 def test_unavailable_recovery_never_erases_original_passage(self):
  result=self.run_repair(self.model(True));self.assertEqual((result[0]['start'],result[-1]['end']),(0,20));self.assertTrue(all(r['words']==[] for r in result));self.assertEqual(result[0]['sourceClockOriginal']['text'],'⑸ себе転移')
 def test_budget_exhausted_before_calls_still_retains_source(self):
  write_json(self.job/'source-clock-recovery.json',dict(revision=clock.REVISION,attempts=12,spentSeconds=90,windows={}));self.run_repair(self.model());self.assertFalse(self.calls)
 def test_healthy_adjacent_words_are_not_borrowed(self):
  model=self.model();segments,_=model.transcribe([0]*100);self.assertEqual(clock.accepted(segments,dict(start=0,end=8,listenStart=0,listenEnd=8),[dict(start=0,end=4)]),[])
 def test_cancel_not_swallowed(self):
  from track_control import UserSkipped
  with patch('track_control.check',side_effect=UserSkipped('stop')):
   with self.assertRaises(UserSkipped):self.run_repair(self.model())

class Ownership(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.job=Path(self.temp.name)
  self.cues=[dict(start=0,end=2,speechStart=0,speechEnd=2,japanese='お前',text='お前',enabled=True,cantonese='',primarySource=dict(captionIDs=['a'],text='快走')),dict(start=2,end=3,speechStart=2,speechEnd=3,japanese='走れ',text='走れ',enabled=True,cantonese='',primarySource=dict(captionIDs=['a'],text=''),preserveOriginalSpeech=True,originalSpeechReason='subtitle-continuation')]
  self.cfg=dict(captionContinuationRevision=caption_coverage.REVISION,duration=4)
 def test_same_caption_once_without_source_mix(self):
  caption_coverage.apply(self.cfg,self.cues);self.assertFalse(self.cues[1]['enabled']);self.assertFalse(self.cues[1]['preserveOriginalSpeech']);self.assertEqual(self.cues[1]['captionCoverageOwners'],[1]);self.assertEqual(self.cues[1]['japanese'],'走れ')
 def test_unmatched_caption_not_suppressed(self):
  self.cues[1]['primarySource']['captionIDs'].append('b');caption_coverage.apply(self.cfg,self.cues);self.assertTrue(self.cues[1]['preserveOriginalSpeech'])
 def test_manual_original_and_legacy_not_changed(self):
  for flag in ['legacy','editorAudio']:
   with self.subTest(flag=flag):
    c=copy.deepcopy(self.cues)
    if flag=='editorAudio':c[1]['editorAudio']='manual.wav'
    before=copy.deepcopy(c);caption_coverage.apply({} if flag=='legacy' else self.cfg,c);self.assertEqual(c,before)
 def test_nonlexical_reaction_not_suppressed(self):
  c=self.cues[1];c.update(japanese='',text='',nonlexicalTail=True);caption_coverage.apply(self.cfg,self.cues);self.assertTrue(c['preserveOriginalSpeech'])
 def test_delivery_audit_excludes_covered_without_calling_it_original(self):
  import dialogue_delivery
  caption_coverage.apply(self.cfg,self.cues);a=dialogue_delivery.audit([dict(folder=str(self.job),engine='drama3',language='yue',review=dict(config=self.cfg,cues=self.cues))]);self.assertEqual(a['tracks'][0]['excluded'][0]['reason'],'caption-owned-by-neighbour')
 def test_rendered_covered_fragment_never_falls_back_to_japanese(self):
  import fast_mode,worker
  ff=shutil.which('ffmpeg');probe=shutil.which('ffprobe')
  if not ff or not probe:self.skipTest('FFmpeg not available')
  caption_coverage.apply(self.cfg,self.cues);c=self.cues[1]
  cfg=dict(self.cfg,ffmpeg=ff,ffprobe=probe,productionMode='fast',speechRatePolicy='natural',ttsBackend='gpt-sovits',startOffset=0)
  with patch('preview_continuity.fill',side_effect=AssertionError('Must not restore duplicate Japanese')):
   path,warnings=fast_mode.synthesize(cfg,self.job,[c],worker.run,lambda *a,**k:None,generated_paths=[self.job/'skipped-2.wav'])
  rows=json.loads((self.job/'timing.json').read_text());self.assertTrue(rows[0]['captionCovered']);self.assertFalse(rows[0]['originalPreserved']);self.assertEqual(warnings,[])

class Submission(unittest.TestCase):
 def test_new_basic_and_expert_freeze_caption_only_and_new_policies(self):
  from desktop_state import Store,read
  for mode in ['basic','expert']:
   with self.subTest(mode=mode),tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);video=root/'source.mp4';video.touch();store=Store(root);store.mode=mode;store.add([str(video)])
    request=store.submit(store.row());cfg=read(request,{})
    self.assertTrue(cfg['skipNonDialogueCaptions']);self.assertEqual(cfg['sourceClockRecoveryRevision'],clock.REVISION);self.assertEqual(cfg['captionContinuationRevision'],caption_coverage.REVISION)
    self.assertFalse(cfg['translationTextReview']);self.assertFalse(cfg['safeEndpointCheck']);self.assertFalse(cfg['analyzeBackgroundGaps'])
    before=request.read_bytes();store.row()['status']='paused';store.settings.update(skipNonDialogueCaptions=False,translationTextReview=True)
    self.assertEqual(store.submit(store.row()),request);self.assertEqual(request.read_bytes(),before)

class CompleteMixer(unittest.TestCase):
 def test_covered_turn_has_no_failure_warning_or_source_audio(self):
  import dubbing
  cue=dict(start=0,end=1,cantonese='',captionCovered=True,captionCoverageOwners=[1])
  with tempfile.TemporaryDirectory() as folder:
   row=dict(index=2)
   def run(args):raise AssertionError('Covered interval must not decode or mix source audio')
   try:
    result=dubbing.render_complete_preview(dict(duration=1),Path(folder),[cue],[Path(folder)/'skipped-2.wav'],[row],run,lambda *a,**k:None)
   except KeyError as e:
    # The fixture supplies only this exclusion; later mix assembly needs ffmpeg.
    self.assertEqual(str(e),"'ffmpeg'")
   self.assertTrue(row['captionCovered']);self.assertFalse(row['needsReview']);self.assertFalse(row['originalPreserved'])

class Editorial(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.job=Path(self.temp.name);self.cfg=dict(repairGroupsRevision='repair-groups-263',translationTextReview=True,sourceLanguage='ja',port=1,model='fixture');self.calls=[]
  self.cues=[dict(start=0,end=1,enabled=True,cantonese='快啲走啦',japanese='早く')]
  def chat(*args,**kw):self.calls.append(args);return json.dumps({'yue:0':'快啲走啦'})
  self.w=NS(emit=lambda *a,**k:None,ollama_chat=chat,traditional_cantonese=lambda c,t:t)
 def test_optional_off_runs_no_model(self):translation_editorial.review(self.w,dict(self.cfg,translationTextReview=False),self.job,self.cues);self.assertFalse(self.calls)
 def test_repeated_call_does_not_repeat_review(self):
  translation_editorial.review(self.w,self.cfg,self.job,self.cues);translation_editorial.review(self.w,self.cfg,self.job,self.cues);self.assertEqual(len(self.calls),1)
 def test_existing_recording_and_editor_mode_retained(self):
  write_json(self.job/'timing.json',[]);translation_editorial.review(self.w,self.cfg,self.job,self.cues);self.assertFalse(self.calls)
 def test_failed_editorial_keeps_first_draft(self):
  self.w.ollama_chat=lambda *a,**k:'{}';translation_editorial.review(self.w,self.cfg,self.job,self.cues);self.assertEqual(self.cues[0]['cantonese'],'快啲走啦')
 def test_numeric_change_retains_first_draft(self):
  self.cues[0]['cantonese']='10分鐘內送到';self.w.ollama_chat=lambda *a,**k:json.dumps({'yue:0':'20分鐘內送到'})
  translation_editorial.review(self.w,self.cfg,self.job,self.cues);self.assertEqual(self.cues[0]['cantonese'],'10分鐘內送到')
 def test_required_name_retained(self):
  self.cues[0].update(cantonese='路飛快啲走啦',requiredNames=['路飛']);self.w.ollama_chat=lambda *a,**k:json.dumps({'yue:0':'快啲走啦'})
  translation_editorial.review(self.w,self.cfg,self.job,self.cues);self.assertEqual(self.cues[0]['cantonese'],'路飛快啲走啦')
 def test_cancel_not_swallowed(self):
  from track_control import UserSkipped
  self.w.ollama_chat=lambda *a,**k:(_ for _ in ()).throw(UserSkipped('stop'))
  with self.assertRaises(UserSkipped):translation_editorial.review(self.w,self.cfg,self.job,self.cues)

if __name__=='__main__':unittest.main()
