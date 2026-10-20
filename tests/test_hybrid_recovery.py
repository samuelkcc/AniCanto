import sys,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
from hybrid_script import complete_lines

def row(text):return dict(cantonese=text,evidence_id='1',quote='え',uncertain=True)
def clean(cfg,text):
 if not text.strip():raise ValueError('配音台詞係空白。')
 return text
class RecoveryTests(unittest.TestCase):
 def run_repair(self,result,responses,fallback=None,cues=None):
  with tempfile.TemporaryDirectory() as d:
   w=SimpleNamespace(emit=Mock(),traditional_cantonese=clean,atomic_json=lambda p,x:p.write_text(json.dumps(x)),parse_editor_response=json.loads,ollama_chat=Mock(side_effect=[json.dumps(x) for x in responses]))
   context=[dict(id=k,start=int(k),end=int(k)+1,japanese='え',caption='') for k in ['1','2']]
   own=lambda x:{k:dict(v,evidence_id=k) for k,v in (x or {}).items()}
   result=own(result);responses=[own(x) for x in responses];fallback=own(fallback)
   w.ollama_chat.side_effect=[json.dumps(x) for x in responses]
   keys=['1','2'];schema=dict(properties={k:{} for k in keys},required=keys)
   answer=complete_lines(w,dict(port=1,model='test'),Path(d),'script','prompt',{'dialogue':context},result,keys,cues or [{},{}],schema,fallback)
   return answer,w
 def test_empty_rows_repaired_without_modifying_valid_neighbour(self):
  result,w=self.run_repair({'1':row('你好'),'2':row('')},[{'1':row('唔應該套用'),'2':row('咦？')}])
  self.assertEqual(result['1']['cantonese'],'你好');self.assertEqual(result['2']['cantonese'],'咦？')
  payload=json.loads(w.ollama_chat.call_args.args[2][1]['content']);self.assertEqual(payload['requested_ids'],['2']);self.assertEqual([c['id'] for c in payload['dialogue']],['1','2'])
 def test_second_repair_recovers_missing_and_punctuation_only(self):
  result,w=self.run_repair({'1':row('你好')},[{'2':row('。')},{'2':row('哦！')}])
  self.assertEqual(w.ollama_chat.call_count,2);self.assertEqual(result['2']['cantonese'],'哦！')
 def test_exhausted_retry_keeps_valid_first_draft_for_conflict_pass(self):
  result,w=self.run_repair({'1':row('你好'),'2':row('')},[{},{}],{'2':row('哦！')})
  self.assertEqual(result['2']['cantonese'],'哦！');self.assertTrue(result['2']['uncertain'])
 def test_exhaustion_is_bounded_and_names_failed_cue(self):
  with self.assertRaisesRegex(ValueError,'第 2 句'):
   self.run_repair({'1':row('你好'),'2':row('')},[{},{}])
 def test_known_nonlexical_tail_does_not_need_invented_translation(self):
  result,w=self.run_repair({'1':row('你好'),'2':row('')},[],cues=[{},dict(nonlexicalTail=True)])
  self.assertEqual(w.ollama_chat.call_count,0)
 def test_editor_notes_are_not_accepted_as_dialogue(self):
  result,w=self.run_repair({'1':row('你好'),'2':row('（無語音，僅有笑聲）')},[{'2':row('（語音斷續，配合上一句意思）')},{'2':row('哦！')}])
  self.assertEqual(result['2']['cantonese'],'哦！');self.assertEqual(w.ollama_chat.call_count,2)
