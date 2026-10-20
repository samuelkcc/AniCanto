import copy,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import worker

class TranslationRecoveryTests(unittest.TestCase):
 def cue(self,text='不要動',seconds=.5):
  return dict(start=0,end=seconds,text=text,japanese='動くな',scenePlan={'meaning':text},cantonese='')
 def response(self,lines):
  return json.dumps({f'line_{i}':dict(meaning='不要動',speech_act='statement',names=[],cantonese=t) for i,t in enumerate(lines)},ensure_ascii=False)
 def test_metadata_only_length_edit_keeps_complete_translation_and_checkpoints(self):
  cues=[self.cue()];cues[0]['reviewNote']='原聲分句需核對。';saved=[]
  answers=[self.response(['唔好郁，企喺嗰度等我！']),json.dumps({'line_0':'{"reason":"too long","target":2}'})]
  with patch.object(worker,'ollama_chat',side_effect=answers),patch.object(worker,'emit'):
   worker.translate_batch(dict(port=1,model='test'),cues,[],lambda:saved.append(copy.deepcopy(cues)))
  self.assertEqual(cues[0]['cantonese'],'唔好郁，企喺嗰度等我！')
  self.assertIn('原聲分句需核對',cues[0]['reviewNote'])
  self.assertEqual(len(saved),1);self.assertEqual(cues[0]['translationWarnings'][0]['stage'],'length-editor')
 def test_nested_valid_dialogue_unwrapped_before_name_guard(self):
  cue=self.cue(seconds=2)
  with patch.object(worker,'ollama_chat',return_value=self.response(['{"cantonese":"唔好郁！"}'])):
   worker.translate_batch(dict(port=1,model='test'),[cue],[],lambda:None)
  self.assertEqual(cue['cantonese'],'唔好郁！')
 def test_invalid_first_draft_retries_single_cue_once_then_saves(self):
  cue=self.cue(seconds=2);saves=[]
  with patch.object(worker,'ollama_chat',side_effect=[self.response(['{"reason":"editor only"}']),self.response(['唔好郁！'])]) as call,patch.object(worker,'emit'):
   worker.translate_batch(dict(port=1,model='test'),[cue],[],lambda:saves.append(1))
  self.assertEqual(call.call_count,2);self.assertEqual(saves,[1]);self.assertEqual(cue['cantonese'],'唔好郁！')
 def test_invalid_first_draft_has_bounded_retry_and_never_commits_metadata(self):
  cue=self.cue(seconds=2);saved=[]
  with patch.object(worker,'ollama_chat',return_value=self.response(['{"reason":"editor only"}'])) as call,patch.object(worker,'emit'):
   with self.assertRaises(ValueError):worker.translate_batch(dict(continueOnError=False,port=1,model='test'),[cue],[],lambda:saved.append(1))
  self.assertEqual(call.call_count,2);self.assertEqual(saved,[]);self.assertEqual(cue['cantonese'],'')
 def test_resume_keeps_previously_saved_dialogue_without_calling_model(self):
  cue=self.cue();cue['cantonese']='唔好郁！'
  with patch.object(worker,'ollama_chat') as call:
   worker.translate_batch(dict(port=1,model='test'),[cue],[],lambda:None)
  call.assert_not_called()
 def test_optional_editor_keeps_valid_draft_with_review_evidence(self):
  cue=self.cue();cue['cantonese']='唔好郁！'
  with patch.object(worker,'emit'):
   result=worker.editor_dialogue({},cue,'{"reason":"needs editing"}','spoken-editor')
  self.assertIsNone(result);self.assertEqual(cue['cantonese'],'唔好郁！')
  self.assertIn('供覆核',cue['reviewNote']);self.assertEqual(len(cue['translationWarnings']),1)
 def test_optional_editor_must_not_hide_invalid_initial_draft(self):
  cue=self.cue();cue['cantonese']='{"reason":"not dialogue"}'
  with self.assertRaises(ValueError):worker.editor_dialogue({},cue,'{"reason":"still not dialogue"}','spoken-editor')
 def test_optional_editor_rejects_object_instead_of_crashing(self):
  cue=self.cue();cue['cantonese']='唔好郁！'
  with patch.object(worker,'emit'):
   self.assertIsNone(worker.editor_dialogue({},cue,{'reason':'notes'},'spoken-editor'))
  self.assertEqual(cue['cantonese'],'唔好郁！')
 def test_broken_optional_response_preserves_initial_translation(self):
  for broken in ['{oops','[]','{"line_0":{"reason":"notes"}}','{}']:
   with self.subTest(response=broken):
    cue=self.cue()
    with patch.object(worker,'ollama_chat',side_effect=[self.response(['唔好郁，企喺嗰度等我！']),broken]),patch.object(worker,'emit'):
     worker.translate_batch(dict(port=1,model='test'),[cue],[],lambda:None)
    self.assertEqual(cue['cantonese'],'唔好郁，企喺嗰度等我！');self.assertTrue(cue['translationWarnings'])
 def test_partial_polish_preserves_missing_line_and_keeps_valid_edit(self):
  import tempfile
  cues=[self.cue(seconds=2),self.cue(seconds=2)]
  for c in cues:c['cantonese']='唔好郁！'
  with tempfile.TemporaryDirectory() as d,patch.object(worker,'ollama_chat',return_value='{"line_0":"企定！"}'),patch.object(worker,'emit'):
   worker.polish_script(dict(port=1,model='test'),Path(d),cues)
  self.assertEqual(cues[0]['cantonese'],'企定！');self.assertEqual(cues[1]['cantonese'],'唔好郁！');self.assertTrue(cues[1]['translationWarnings'])
 def test_duration_editor_rejects_metadata_without_aborting_or_semantic_call(self):
  import tempfile,duration_fit
  cue=dict(text='動くな',cantonese='唔好郁，企喺嗰度等我！')
  with tempfile.TemporaryDirectory() as d,patch.object(worker,'ollama_chat',return_value='{"line_0":"{\\"reason\\":\\"notes\\"}"}') as model,patch.object(duration_fit.urllib.request,'urlopen'),patch.object(worker,'emit'):
   changed=duration_fit.shorten(dict(port=1,model='test',autoApprove=True),Path(d),[cue],[dict(index=1,seconds=5,slot=2,needsReview=True)],1,lambda *a:None)
  self.assertFalse(changed);self.assertEqual(model.call_count,1);self.assertEqual(cue['cantonese'],'唔好郁，企喺嗰度等我！');self.assertTrue(cue['translationWarnings'])
 def test_caption_editor_rejects_broken_pair_without_replacing_either_turn(self):
  import tempfile,caption_allocation
  cues=[dict(text='動くな',cantonese='唔好郁！'),dict(text='待て',cantonese='等等！')]
  with tempfile.TemporaryDirectory() as d,patch.object(caption_allocation,'suspect_pairs',return_value=[(0,1)]),patch.object(worker,'ollama_chat',return_value='{"0":"{\\"reason\\":\\"notes\\"}","1":"企定！"}') as model,patch.object(worker,'emit'):
   caption_allocation.repair(dict(port=1,model='test'),Path(d),cues,lambda *a:None)
  self.assertEqual(model.call_count,1);self.assertEqual([c['cantonese'] for c in cues],['唔好郁！','等等！']);self.assertTrue(cues[0]['translationWarnings'])
 def test_invalid_semantic_verdict_never_approves_optional_edit(self):
  import semantic_review
  items={'0':dict(source={'japanese':'動くな'},candidate='唔好郁！')}
  for raw in ['{oops','{}','{"0":{"faithful":true,"defects":[{"kind":"omission","source_quote":3}]}}']:
   with self.subTest(raw=raw),patch.object(worker,'ollama_chat',return_value=raw):
    result=semantic_review.audit(dict(port=1,model='test'),items)
   self.assertFalse(result['0']['faithful']);self.assertTrue(result['0']['invalidEvidence'])
