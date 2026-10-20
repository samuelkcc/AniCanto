import copy,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import translation_brevity as brevity,normal_mode,worker

class TranslationBrevityTests(unittest.TestCase):
 def cue(self,**extra):
  return dict(dict(start=0,end=2.7,japanese='秘密忍者隊、ニャンキー一同!',subtitleHint='秘密忍者猫小队出动！',cantonese='秘密忍者貓小隊，忍者貓小隊全體出動！'),**extra)
 def writer(self,response):
  return SimpleNamespace(atomic_json=worker.atomic_json,emit=Mock(),ollama_chat=Mock(return_value=response),traditional_cantonese=lambda cfg,text:text)
 def test_recorded_example_is_nominated_even_with_a_large_following_silent_gap(self):
  cues=[self.cue(),dict(start=8.58,end=10,japanese='はい',cantonese='係呀')]
  result=brevity.assess({},cues,0,'yue')
  self.assertIn('repeated-phrase',result['reasons']);self.assertIn('caption-relative-expansion',result['reasons'])
  self.assertEqual(result['reference']['quality'],'unverified-reference')
 def test_cross_language_length_is_not_compared_as_raw_characters_or_words(self):
  cue=self.cue(subtitleHint='你而家即刻過嚟',cantonese='',english='Come over here right now.')
  result=brevity.assess({},[cue],0,'en')
  self.assertNotIn('caption-relative-expansion',result['reasons'])
 def test_shared_ocr_and_combined_captions_are_not_individual_length_limits(self):
  a=self.cue(captionEvidenceOnly=True);b=dict(a,start=3,end=4,japanese='はい')
  self.assertEqual(brevity.caption_reference({},[a,b],0)['status'],'shared-caption-context')
  a['subtitleHint']='上半句 ／ 下半句'
  self.assertEqual(brevity.caption_reference({},[a],0)['status'],'multiple-caption-context')
 def test_low_confidence_and_time_spanning_caption_are_rejected_as_length_references(self):
  a=self.cue(captionRecords=[dict(start=0,end=2.7,text='秘密忍者猫小队出动！',confidence=.3)])
  self.assertEqual(brevity.caption_reference({},[a],0)['status'],'low-confidence-caption')
  a['captionRecords']=[dict(start=0,end=5,text=a['subtitleHint'],confidence=.99)]
  b=dict(start=3,end=4,japanese='はい',cantonese='係呀',subtitleHint='其他字幕')
  self.assertEqual(brevity.caption_reference({},[a,b],0)['status'],'caption-spans-multiple-turns')
 def test_audio_only_does_not_use_ocr_reference(self):
  self.assertEqual(brevity.caption_reference(dict(translationSource='audio-only'),[self.cue()],0),dict(status='audio-only',text=''))
 def test_semantic_failure_cannot_force_text_to_match_a_short_ocr_caption(self):
  cfg=dict(ocr=True,model='m',port=1);cue=self.cue(subtitleHint='出動！',captionEvidenceOnly=True);before=copy.deepcopy(cue)
  w=self.writer('{"0":"出動！"}')
  with tempfile.TemporaryDirectory() as d,patch('semantic_review.audit',return_value={'0':dict(faithful=False)}) as audit:
   self.assertEqual(brevity.review(w,cfg,d,[cue],{'yue'}),[])
   self.assertEqual(brevity.review(w,cfg,d,[cue],{'yue'}),[])
   self.assertEqual(w.ollama_chat.call_count,1);self.assertEqual(cue,before)
   prompt=w.ollama_chat.call_args.args[2][0]['content']
   self.assertIn('primary source',prompt);self.assertIn('never a hard output limit',prompt)
   self.assertTrue(audit.call_args.args[0]['ocrEvidenceOnly'])
 def test_accepted_edits_preserve_original_and_resume_without_repeating_model_calls(self):
  cfg=dict(model='m',port=1);original=self.cue();w=self.writer('{"0":"秘密忍者貓小隊，全體出動！"}')
  with tempfile.TemporaryDirectory() as d,patch('semantic_review.audit',return_value={'0':dict(faithful=True)}):
   for _ in range(2):
    cue=copy.deepcopy(original)
    self.assertEqual(brevity.review(w,cfg,d,[cue],{'yue'}),[0])
    self.assertEqual(cue['cantonese'],'秘密忍者貓小隊，全體出動！');self.assertEqual(cue['preBrevityCantonese'],original['cantonese'])
   self.assertEqual(w.ollama_chat.call_count,1)
 def test_genuine_repetition_can_remain_and_healthy_lines_do_not_trigger_ai_review(self):
  cue=self.cue(japanese='忍者隊、忍者隊!',subtitleHint='忍者貓小隊，忍者貓小隊！',cantonese='忍者貓小隊，忍者貓小隊！')
  w=self.writer(json.dumps({'0':cue['cantonese']},ensure_ascii=False))
  with tempfile.TemporaryDirectory() as d:
   self.assertEqual(brevity.review(w,dict(model='m',port=1),d,[cue],{'yue'}),[])
   self.assertEqual(cue['cantonese'],'忍者貓小隊，忍者貓小隊！')
  w=self.writer('unused')
  with tempfile.TemporaryDirectory() as d:
   self.assertEqual(brevity.review(w,dict(model='m',port=1),d,[dict(start=0,end=1,japanese='はい',cantonese='係呀。',english='Yes.')],{'yue','en'}),[])
   w.ollama_chat.assert_not_called()
 def test_normal_translation_reviews_existing_overexpanded_drafts_before_tts(self):
  cfg=dict(productionMode='normal',dubLanguages=['yue'],subtitleModes=[],model='m',port=1)
  w=self.writer('{"0":"秘密忍者貓小隊，全體出動！"}');cue=self.cue()
  with tempfile.TemporaryDirectory() as d,patch('normal_mode.glossary',return_value=[]),patch('semantic_review.audit',return_value={'0':dict(faithful=True)}):
   normal_mode.translate(w,cfg,Path(d),[cue])
   self.assertEqual(cue['cantonese'],'秘密忍者貓小隊，全體出動！')
   self.assertEqual(w.ollama_chat.call_count,1)
 def test_editor_scripts_are_never_silently_rewritten(self):
  w=self.writer('unused')
  with tempfile.TemporaryDirectory() as d:
   self.assertEqual(brevity.review(w,dict(editorRender=True),d,[self.cue()],{'yue'}),[])
   w.ollama_chat.assert_not_called()
