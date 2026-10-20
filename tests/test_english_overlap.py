import copy,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import english_overlap as overlap,worker

class EnglishOverlapTests(unittest.TestCase):
 def rows(self):return [dict(start=0,end=1,japanese='僕は彼を信じている',english='I know I can trust him.'),dict(start=1,end=2,japanese='走れ',english='I know I can trust him. Run!')]
 def test_long_neighbour_prefix_is_flagged_but_real_repetition_and_names_are_not(self):
  a,b=self.rows();a.update(start=0,end=1);b.update(start=1,end=2);self.assertTrue(overlap.suspect(a,b))
  self.assertFalse(overlap.suspect(a,dict(b,japanese=a['japanese'])))
  self.assertFalse(overlap.suspect(dict(japanese='source A',english='Roger!'),dict(japanese='source B',english='Roger, run!')))
 def test_confirmed_leak_retranslates_only_own_turn_and_keeps_previous_version(self):
  rows=self.rows();before=copy.deepcopy(rows)
  w=SimpleNamespace(ollama_chat=Mock(side_effect=['{"dialogue":"I know I can trust him."}','{"dialogue":"Run!"}']),atomic_json=worker.atomic_json,emit=Mock())
  with tempfile.TemporaryDirectory() as d,patch('semantic_review.audit',return_value={'line':dict(faithful=True)}) as audit:
   self.assertEqual(overlap.repair(w,dict(model='m',port=1),d,rows),[1])
   self.assertNotIn('approved_translation',audit.call_args.args[1]['line']['source'])
   self.assertEqual(rows[0],before[0]);self.assertEqual(rows[1]['english'],'Run!')
   self.assertEqual(rows[1]['preOverlapEnglish'],before[1]['english'])
   # A resumed original script consumes the saved result, not another model call.
   overlap.repair(w,dict(model='m',port=1),d,copy.deepcopy(before))
   self.assertEqual(w.ollama_chat.call_count,2)
 def test_all_three_leaked_drafts_and_short_name_paraphrase_are_nominated(self):
  rows=[dict(start=i,end=i+1,japanese=text,english='Please remember who you really are, Tomo!') for i,text in enumerate(('だからお願い','本当のあなたに戻って','トモ'))]
  rows.append(dict(start=3,end=4,japanese='ごめん',english="Sorry, I do not mind which request comes first."))
  w=SimpleNamespace(ollama_chat=Mock(side_effect=['{"dialogue":"Please!"}','{"dialogue":"Remember who you are!"}','{"dialogue":"Tomo!"}','{"dialogue":"Sorry."}']),atomic_json=worker.atomic_json,emit=Mock())
  with tempfile.TemporaryDirectory() as d,patch('semantic_review.audit',return_value={'line':dict(faithful=True)}):
   self.assertEqual(overlap.repair(w,dict(model='m',port=1),d,rows),[0,1,2,3])
   self.assertEqual([c['english'] for c in rows],['Please!','Remember who you are!','Tomo!','Sorry.'])
 def test_unverified_shorter_version_never_deletes_possible_real_dialogue(self):
  rows=self.rows();before=copy.deepcopy(rows)
  w=SimpleNamespace(ollama_chat=Mock(return_value='{"dialogue":"Run!"}'),atomic_json=worker.atomic_json,emit=Mock())
  with tempfile.TemporaryDirectory() as d,patch('semantic_review.audit',return_value={'line':dict(faithful=False)}):
   self.assertEqual(overlap.repair(w,dict(model='m',port=1),d,rows),[])
   self.assertEqual(rows[1]['english'],before[1]['english']);self.assertTrue(rows[1]['englishOverlapReview'])
