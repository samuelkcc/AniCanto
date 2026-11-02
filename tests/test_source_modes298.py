"""Check actual source resolution, immutable clocks, and bounded later proofreading."""
import copy,json,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'Resources'))
import source_workflow as workflow,source_modes,subtitle_preference,subtitle_choice,subtitle_versions,source_proofread,primary_source

def stream(index,language):return dict(index=index,codec_type='subtitle',codec_name='subrip',tags=dict(language=language))
class SourceModes(unittest.TestCase):
 def config(self,mode='auto',**extra):return dict(sourceWorkflowRevision=source_modes.REVISION,sourceWorkflow=mode,interfaceMode='expert',dubLanguages=['yue'],**extra)
 def configure(self,cfg,tracks):return workflow.configure(cfg,dict(streams=tracks),subtitle_preference.pick)
 def test_automatic_uses_subtitles_or_speech_without_implicit_ocr(self):
  yes=self.configure(self.config(),[stream(3,'zh')]);no=self.configure(self.config(),[])
  self.assertEqual(yes['sourceWorkflowEffective'],'subtitles-speech');self.assertEqual(no['sourceWorkflowEffective'],'speech-subtitles');self.assertFalse(no['ocr']);self.assertEqual(no['translationSource'],'audio-only')
 def test_explicit_ocr_ignores_text_tracks_and_missing_import(self):
  cfg=self.configure(self.config('speech-ocr',subtitle='/missing/subtitles.ass',batchExplicitStream=True,subtitleStream=99),[stream(3,'zh')])
  self.assertEqual(cfg['sourceWorkflowEffective'],'speech-ocr');self.assertTrue(cfg['ocr']);self.assertIsNone(cfg['subtitle']);self.assertTrue(cfg['sourceWorkflowResolution']['authoredSubtitlesIgnored'])
 def test_speech_first_is_valid_with_or_without_captions(self):
  for tracks in [[],[stream(3,'zh')]]:
   cfg=self.configure(self.config('speech-subtitles'),tracks);self.assertEqual(cfg['sourceWorkflowEffective'],'speech-subtitles');self.assertFalse(cfg['ocr'])
 def test_subtitle_first_uses_only_authored_content(self):
  cfg=self.configure(self.config('subtitles-speech'),[stream(3,'zh')]);self.assertTrue(workflow.subtitle_content_only(cfg));self.assertIn('ONLY translation content',workflow.SUBTITLE_ONLY_RULES)
 def test_legacy_frozen_ocr_first_remains_ocr_primary(self):
  cfg=dict(sourceWorkflowRevision=workflow.LEGACY_REVISION,sourceWorkflow='ocr-speech',interfaceMode='expert',defaultOCRWorkflow='ocr-speech')
  self.configure(cfg,[]);self.assertEqual(cfg['sourceContentPriority'],'ocr');self.assertEqual(cfg['sourceWorkflowEffective'],'ocr-speech')
 def test_old_ocr_first_preference_migrates_only_for_new_jobs(self):
  old=dict(sourceWorkflowRevision=workflow.SUBTITLE_REVISION,sourceWorkflow='ocr-speech');saved=copy.deepcopy(old)
  source_modes.prepare_request(old);self.assertEqual(old,saved)
  new=self.config('ocr-speech');source_modes.prepare_request(new);self.assertEqual(new['sourceWorkflow'],'speech-ocr')
 def test_existing_proofread_budget_is_never_refunded(self):
  cfg=self.config('speech-subtitles',sourceProofreadBudgetSeconds=25,sourceProofreadMaxAttempts=1);self.configure(cfg,[])
  self.assertEqual(cfg['sourceProofreadBudgetSeconds'],25)
 def test_speech_initial_payload_excludes_captions_then_proofreads_same_turn(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);cfg=self.configure(self.config('speech-subtitles',sourcePolicyRevision=primary_source.REVISION,sourceLanguage='ja'),[stream(3,'zh')]);cfg.update(port=1,model='fixture')
   cues=[dict(start=1,end=2,speechStart=1.1,speechEnd=1.9,japanese='こんにちは',text='こんにちは',cantonese='你好',reviewIndex=4)]
   writes=lambda p,x:Path(p).write_text(json.dumps(x,ensure_ascii=False))
   w=types.SimpleNamespace(atomic_json=writes,emit=lambda *a,**k:None,traditional_cantonese=lambda c,t:t)
   captions=[dict(id='caption-1',start=1,end=2,text='你好')]
   with patch('source_evidence.caption_records',return_value=captions),patch('target_delivery.prepare'),patch('caption_only.apply'):
    primary_source.prepare(w,cfg,job,cues)
   self.assertEqual(primary_source.content(cues[0]),'こんにちは');self.assertEqual(primary_source.caption(cues[0]),'');self.assertEqual(cues[0]['subtitleHint'],'')
   calls=[]
   def chat(*args,**kwargs):calls.append((args,kwargs));return json.dumps({'yue:4':'你好呀'})
   w.ollama_chat=chat;before={k:cues[0][k] for k in ['start','end','speechStart','speechEnd','japanese']}
   source_proofread.review(w,cfg,job,cues);self.assertEqual(cues[0]['cantonese'],'你好呀');self.assertEqual(before,{k:cues[0][k] for k in before})
   payload=json.loads(calls[0][0][2][1]['content']);self.assertEqual(payload['yue:4']['draft'],'你好');self.assertEqual(payload['yue:4']['sameTurnCaptions'][0]['text'],'你好')
   source_proofread.review(w,cfg,job,cues);self.assertEqual(len(calls),1)
   receipt=json.loads((job/'source-proofread.json').read_text());self.assertEqual(receipt['rows']['yue:4']['attempts'],1)
 def test_proofread_failure_keeps_draft_and_does_not_retry_on_resume(self):
  with tempfile.TemporaryDirectory() as d:
   calls=[]
   def fail(*a,**kw):calls.append(1);raise RuntimeError('fixture failure')
   w=types.SimpleNamespace(atomic_json=lambda p,x:Path(p).write_text(json.dumps(x)),emit=lambda *a,**k:None,ollama_chat=fail)
   cfg=dict(sourceWorkflowRevision=source_modes.REVISION,sourceProofreadRevision=source_modes.REVISION,port=1,model='fixture')
   cues=[dict(start=0,end=1,cantonese='你好',sourceProofreadEvidence=[dict(text='你好')])]
   source_proofread.review(w,cfg,d,cues);source_proofread.review(w,cfg,d,cues)
   self.assertEqual(cues[0]['cantonese'],'你好');self.assertEqual(len(calls),1)

ASS='''[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:03.00,CHT,,0,0,0,,你好朋友
Dialogue: 0,0:00:01.00,0:00:03.00,JPN,,0,0,0,,こんにちは
Dialogue: 0,0:00:01.00,0:00:03.00,ENG,,0,0,0,,Hello my friend
'''
class SubtitleSelection(unittest.TestCase):
 def fixture(self,root):
  video=root/'fixture.mp4';video.write_bytes(b'isolated video');return video
 def check(self,video,streams,settings,row,**kwargs):
  with patch.object(subtitle_choice.subprocess,'check_output',return_value=json.dumps(dict(streams=streams)).encode()):
   return subtitle_choice.preflight(video,dict(ffprobe='fixture'),settings,row,**kwargs)
 def test_output_language_selects_chinese_and_english_falls_back_to_chinese(self):
  with tempfile.TemporaryDirectory() as d:
   video=self.fixture(Path(d));tracks=[stream(2,'ja'),stream(3,'zh'),stream(4,'en')]
   for target,index in [('yue',3),('zh',3),('en',4)]:
    result=self.check(video,tracks,dict(dubLanguages=[target]),{});self.assertFalse(result['needsConfirmation']);self.assertEqual(result['selected']['stream'],index)
   result=self.check(video,tracks[:2],dict(dubLanguages=['en']),{});self.assertEqual(result['selected']['stream'],3)
 def test_uncertain_language_requires_choice_and_changed_media_invalidates_it(self):
  with tempfile.TemporaryDirectory() as d:
   video=self.fixture(Path(d));tracks=[stream(2,'und')];settings=dict(dubLanguages=['yue']);row={}
   self.assertTrue(self.check(video,tracks,settings,row)['needsConfirmation'])
   result=self.check(video,tracks,settings,row,selected='embedded:2',selected_language='zh');subtitle_choice.apply_to_row(row,result)
   self.assertFalse(self.check(video,tracks,settings,row)['needsConfirmation'])
   video.write_bytes(b'changed media');self.assertTrue(self.check(video,tracks,settings,row)['needsConfirmation'])
 def test_mixed_ass_selects_one_language_and_preserves_clocks(self):
  self.assertEqual(subtitle_versions.languages(ASS),['en','ja','zh'])
  selected=subtitle_versions.selected_srt(ASS,'zh');self.assertIn('你好朋友',selected);self.assertNotIn('こんにちは',selected);self.assertNotIn('Hello',selected);self.assertIn('00:00:01,000 --> 00:00:03,000',selected)
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);video=self.fixture(root);sub=root/'fixture.ass';sub.write_text(ASS)
   result=self.check(video,[],dict(dubLanguages=['en']),dict(externalSubtitle=str(sub)))
   self.assertEqual(result['selected']['language'],'en');self.assertTrue(result['selected']['key'].endswith('#lang:en'))
 def test_ocr_does_not_probe_or_read_an_imported_subtitle(self):
  result=subtitle_choice.preflight('/missing/video',{},dict(sourceWorkflow='speech-ocr'),dict(externalSubtitle='/missing/file'))
  self.assertTrue(result['ignored']);self.assertFalse(result['needsConfirmation'])

if __name__=='__main__':unittest.main()
