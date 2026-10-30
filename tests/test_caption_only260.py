"""Conservative screen-caption gates, export text and contextual wording fixtures."""
import copy,hashlib,json,sys,tempfile,unittest,wave
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows'),str(ROOT/'studio')]
import caption_only as gate,hk_spoken_style as hk
from worker import atomic_json,save_srt,traditional_cantonese

class CaptionOnly(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.cfg=dict(captionOnlyRevision=gate.REVISION,skipNonDialogueCaptions=True,duration=5,startOffset=0,dialoguePath=str(self.root/'stem.wav'),targetLanguage='yue',ttsBackend='drama3')
  self.cue=dict(start=1,end=2,text='',japanese='',enabled=True,subtitleHint='三年前',subtitleClockFallbackID='caption_1',captionRecords=[dict(id='caption_1',start=1,end=2,text='三年前')],cantonese='三年前',primarySource=dict(revision='subtitle-first-1',kind='embedded',text='三年前',captionIDs=['caption_1']))
  self.evidence=dict(complete=True,dualInput=True,duration=5,segments=[],spans=[])
  self.measure=dict(coveredSeconds=1.5,peak=0.,rms=0.,quantum=1/32768)
  for name in ('japanese-original.wav','stem.wav'):
   with wave.open(str(self.root/name),'wb') as f:f.setparams((1,2,16000,0,'NONE','not compressed'));f.writeframes(b'\0'*160000)
  self.saved=dict(key='fixture',segments=[],spans=[],noDialogueEvidence=dict(complete=True,dualInput=True,startOffset=0,sourceSHA256=self.sha('japanese-original.wav'),stemSHA256=self.sha('stem.wav')))
  atomic_json(self.root/'japanese-analysis.json',self.saved)
 def sha(self,name):return hashlib.sha256((self.root/name).read_bytes()).hexdigest()
 def apply(self,c=None):
  c=copy.deepcopy(c or self.cue);gate.apply(self.cfg,self.root,[c],atomic_json);return c
 def test_positive_gate(self):self.assertEqual(gate.decide(self.cue,self.evidence,self.measure),gate.REASON)
 def test_no_asr_alone_cannot_suppress(self):
  self.evidence['complete']=False;self.assertNotEqual(gate.decide(self.cue,self.evidence,self.measure),gate.REASON)
 def test_single_vad_cannot_suppress(self):
  self.evidence['dualInput']=False;self.assertNotEqual(gate.decide(self.cue,self.evidence,self.measure),gate.REASON)
 def test_no_stem_measurement_cannot_suppress(self):self.assertNotEqual(gate.decide(self.cue,self.evidence,None),gate.REASON)
 def test_quiet_vocal_not_assumed_silent(self):
  self.measure.update(peak=.001,rms=.0001);self.assertNotEqual(gate.decide(self.cue,self.evidence,self.measure),gate.REASON)
 def test_offscreen_or_quiet_lexical_words_block_gate(self):
  for r in [dict(start=1.5,end=1.8,text='はい'),dict(start=.8,end=1.1,text='あ')]:
   with self.subTest(r=r):
    e=dict(self.evidence,segments=[r]);self.assertNotEqual(gate.decide(self.cue,e,self.measure),gate.REASON)
 def test_original_or_stem_vad_blocks_gate(self):
  self.evidence['spans']=[dict(start=1.4,end=1.5)];self.assertNotEqual(gate.decide(self.cue,self.evidence,self.measure),gate.REASON)
 def test_unknown_or_bad_vad_window_blocks_gate(self):
  self.evidence['spans']=[{}];self.assertNotEqual(gate.decide(self.cue,self.evidence,self.measure),gate.REASON)
 def test_manual_protected_and_source_words_unchanged(self):
  for changes in [dict(editorAudio='a.wav'),dict(preserveOriginalSpeech=True),dict(opEdKind='opening'),dict(enabled=False),dict(japanese='はい')]:
   with self.subTest(changes=changes):self.assertNotEqual(gate.decide(dict(self.cue,**changes),self.evidence,self.measure),gate.REASON)
 def test_no_caption_is_not_a_caption_only_case(self):
  c=dict(self.cue,captionRecords=[],subtitleClockFallbackID=None);self.assertNotEqual(gate.decide(c,self.evidence,self.measure),gate.REASON)
 def test_incomplete_and_invalid_audio_measurements_block_gate(self):
  for changes in [dict(coveredSeconds=.8),dict(peak=float('nan')),dict(quantum=0)]:
   with self.subTest(changes=changes):self.assertNotEqual(gate.decide(self.cue,self.evidence,dict(self.measure,**changes)),gate.REASON)
 def test_apply_preserves_translation_and_clock_for_all_languages(self):
  from dubbing import required_dialogue
  for lang in ('yue','zh','en'):
   self.cfg['targetLanguage']=lang;c=self.apply();self.assertTrue(c['captionOnly']);self.assertTrue(c['enabled']);self.assertEqual((c['start'],c['end']),(1,2));self.assertEqual(c['cantonese'],'三年前');self.assertEqual(required_dialogue(self.cfg,[c]),[])
 def test_translated_caption_is_written_to_srt(self):
  c=self.apply();save_srt(self.root/'out.srt',[c]);text=(self.root/'out.srt').read_text();self.assertIn('三年前',text);self.assertIn('00:00:01,000 --> 00:00:02,000',text)
 def test_resume_flag_off_or_old_request_does_not_reclassify(self):
  for cfg in [dict(self.cfg,skipNonDialogueCaptions=False),dict(self.cfg,captionOnlyRevision='old')]:
   c=copy.deepcopy(self.cue);gate.apply(cfg,self.root,[c],atomic_json);self.assertNotIn('captionOnly',c)
 def test_wrong_audio_hash_or_offset_keeps_dubbing(self):
  for field,value in [('stemSHA256','wrong'),('sourceSHA256','wrong'),('startOffset',20)]:
   saved=copy.deepcopy(self.saved);saved['noDialogueEvidence'][field]=value;atomic_json(self.root/'japanese-analysis.json',saved);self.assertNotIn('captionOnly',self.apply())
 def test_old_analysis_without_receipt_keeps_dubbing(self):
  atomic_json(self.root/'japanese-analysis.json',dict(key='old',segments=[],spans=[]));self.assertNotIn('captionOnly',self.apply())
 def test_prior_automatic_caption_decision_needs_current_proof(self):
  c=self.apply();self.assertTrue(c['captionOnly']);self.cfg['startOffset']=2;gate.apply(self.cfg,self.root,[c],atomic_json);self.assertNotIn('captionOnly',c)
 def test_missing_analysis_or_stem_keeps_dubbing(self):
  (self.root/'stem.wav').unlink();self.assertNotIn('captionOnly',self.apply())
 def test_silent_display_caption_never_requests_mandatory_tts_retry(self):
  from normal_mode import repair_missing_only
  c=self.apply()
  with patch('dubbing.gsv_audio',side_effect=AssertionError('No TTS for silent display caption')):
   result=repair_missing_only(self.cfg,self.root,[c],[self.root/'stem.wav'],lambda *x:None,lambda *x:None)
  self.assertEqual(result,[self.root/'stem.wav']);self.assertEqual(json.loads((self.root/'normal-checks.json').read_text())['repairs'],[])
 def test_actual_mixer_keeps_caption_and_does_not_invent_a_voice(self):
  import fast_mode,basic_flow,speech_duration,worker,shutil
  ff=shutil.which('ffmpeg');probe=shutil.which('ffprobe')
  if not ff or not probe:self.skipTest('FFmpeg tools unavailable')
  c=self.apply();audio=self.root/'caption-silent.wav'
  with wave.open(str(audio),'wb') as f:f.setparams((1,2,44100,0,'NONE','not compressed'));f.writeframes(b'\0'*88200)
  cfg=dict(self.cfg,ffmpeg=ff,ffprobe=probe,basicFlowRevision=basic_flow.REVISION,speechDurationRevision=speech_duration.REVISION,productionMode='fast',speechRatePolicy='natural',maximumMissingRepairAttempts=0)
  with patch('dubbing.gsv_audio',side_effect=AssertionError('No TTS for caption-only interval')):
   result,warnings=fast_mode.synthesize(cfg,self.root,[c],worker.run,lambda *a,**k:None,generated_paths=[audio])
  self.assertTrue(Path(result).is_file());self.assertEqual(c['cantonese'],'三年前');timing=json.loads((self.root/'timing.json').read_text());self.assertTrue(timing[0]['originalPreserved']);self.assertFalse(timing[0]['skipped'])
 def test_delivery_audit_has_explicit_caption_reason_not_japanese_fallback(self):
  from dialogue_delivery import audit
  from target_delivery import source_windows
  c=self.apply();report=audit([dict(folder=str(self.root),engine='drama3',language='yue',review=dict(config=self.cfg,cues=[c]))]);self.assertEqual(report['tracks'][0]['excluded'][0]['reason'],'caption-only-no-dialogue');self.assertEqual(source_windows([c],{}),[])
 def test_report_excludes_caption_only_from_missing(self):
  import review_report
  c=self.apply();review=dict(config=dict(self.cfg,selectedEngines=['drama3'],dubLanguages=['yue']),cues=[c]);atomic_json(self.root/'review.json',review)
  p=review_report.project(self.root,review,dict(status='complete'));self.assertEqual(p['reportRows'][0]['reportGroup'],'reportPreserved');self.assertTrue(p['reportRows'][0]['captionOnly']);self.assertEqual(p['reviewState']['pending'],0)

class Ownership(unittest.TestCase):
 setUp=CaptionOnly.setUp
 sha=CaptionOnly.sha

 def test_primary_ownership_routes_keep_screen_text(self):
  from types import SimpleNamespace
  import primary_source
  from source_workflow import REVISION
  for priority,effective,ocr in [('subtitles','subtitles-speech',False),('speech','speech-subtitles',False),('ocr','ocr-speech',True),('speech','speech-ocr',True)]:
   with self.subTest(priority=priority,effective=effective):
    cfg=dict(self.cfg,sourcePolicyRevision=primary_source.REVISION,sourceAllocationRevision=primary_source.ALLOCATION_REVISION,sourceWorkflowRevision=REVISION,sourceContentPriority=priority,sourceWorkflowEffective=effective,translationSource='audio-and-ocr' if ocr else 'audio-and-subtitles',ocr=ocr)
    atomic_json(self.root/'subtitle-context.json',[dict(start=1,end=2,text='三年前')])
    cues=[];w=SimpleNamespace(atomic_json=atomic_json,ollama_chat=lambda *a,**k: self.fail('No allocation inference needed for one screen caption'))
    primary_source.prepare(w,cfg,self.root,cues)
    self.assertEqual(len(cues),1);self.assertTrue(cues[0]['captionOnly']);self.assertEqual(primary_source.content(cues[0]),'三年前');self.assertEqual((cues[0]['start'],cues[0]['end']),(1,2))

class Wording(unittest.TestCase):
 def setUp(self):self.cfg=dict(hongKongStyleRevision=hk.REVISION)
 def test_safe_full_phrase(self):self.assertEqual(hk.normalize(self.cfg,'廢話少說，快走！'),'廢話少講，快走！')
 def test_novel_titles_names_and_uncertainty_not_mechanically_replaced(self):
  for text in ['呢本小說幾好睇','說明書','搞不好佢會走','唔係唔好','不好意思']:
   with self.subTest(text=text):self.assertEqual(hk.normalize(self.cfg,text),text)
 def test_context_examples_distinguish_probability_from_inability(self):
  examples=hk.rules()['examples'];self.assertTrue(any('分分鐘' in x['target'] for x in examples));self.assertTrue(any('整唔好' in x['target'] for x in examples));self.assertTrue(any('小說' in x['target'] for x in examples))
 def test_old_requests_and_other_languages_keep_their_prompt(self):
  self.assertEqual(hk.instruction({},'yue'),'');self.assertEqual(hk.instruction(self.cfg,'en'),'');self.assertEqual(hk.instruction(self.cfg,'zh'),'')
 def test_explicit_project_term_is_not_rewritten(self):self.assertEqual(hk.normalize(dict(self.cfg,termRules=[dict(source='廢話少說',yue='廢話少說')]),'廢話少說'),'廢話少說')
 def test_quoted_fixed_phrase_is_kept(self):self.assertEqual(hk.normalize(self.cfg,'佢話「廢話少說」'),'佢話「廢話少說」')
 def test_real_draft_normalizer_uses_new_rule_only_for_new_requests(self):
  self.assertEqual(traditional_cantonese(self.cfg,'廢話少說'),'廢話少講');self.assertEqual(traditional_cantonese({},'廢話少說'),'廢話少說')
 def test_first_translation_request_contains_contextual_rules(self):
  import fast_mode,basic_flow
  from types import SimpleNamespace
  with tempfile.TemporaryDirectory() as tmp:
   calls=[]
   def generate(*args,**kwargs):calls.append(args[2]);return json.dumps({'0':'廢話少說！'})
   w=SimpleNamespace(atomic_json=atomic_json,ollama_chat=generate,emit=lambda *a,**k:None,traditional_cantonese=traditional_cantonese)
   cfg=dict(self.cfg,basicFlowRevision=basic_flow.REVISION,productionMode='fast',targetLanguage='yue',dubLanguages=['yue'],subtitleModes=['yue'],port=1,model='fixture',ttsBackend='drama3')
   cues=[dict(start=0,end=2,text='無駄話はやめろ',japanese='無駄話はやめろ',cantonese='',enabled=True)]
   fast_mode.translate(w,cfg,Path(tmp),cues)
   self.assertEqual(len(calls),1);self.assertIn('HONG KONG CONTEXTUAL WORDING',calls[0][0]['content']);self.assertIn('分分鐘',calls[0][0]['content']);self.assertEqual(cues[0]['cantonese'],'廢話少講！')
 def test_new_submit_freezes_controls_and_resume_does_not_rewrite(self):
  from desktop_state import Store
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source=root/'fixture.mp4';source.write_bytes(b'isolated submission fixture');store=Store(root);store.add([source]);row=store.queue[0];request=store.submit(row);saved=json.loads(request.read_text());self.assertIs(saved['skipNonDialogueCaptions'],True);self.assertEqual(saved['captionOnlyRevision'],gate.REVISION);self.assertEqual(saved['hongKongStyleRevision'],hk.REVISION)
   row['status']='paused';before=request.read_bytes();store.settings['skipNonDialogueCaptions']=False;self.assertEqual(store.submit(row),request);self.assertEqual(request.read_bytes(),before)
 def test_no_extra_inference(self):self.assertEqual(hk.rules()['extraAIRequests'],0)
 def test_future_defaults_and_validation(self):
  from desktop_state import defaults
  from workflow_settings import validated
  self.assertIs(defaults()['skipNonDialogueCaptions'],True)
  with self.assertRaises(ValueError):validated(dict(defaults(),skipNonDialogueCaptions='false'))
if __name__=='__main__':unittest.main()
