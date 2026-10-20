import copy,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import caption_span_recovery as recovery,worker

class CaptionSpanRecoveryTests(unittest.TestCase):
 def cues(self,prefix='你们昨晚'):
  cap=dict(id='a',start=0.,end=3.,text=prefix+'光子起動了')
  rows=[dict(start=0.,end=1.,japanese='君たちは昨夜',cantonese='你哋昨晚光子起動咗呀係咪真係呀',captionRecords=[cap],speakerId='one'),dict(start=1.,end=2.,japanese='テスト起動',cantonese='光子起動',captionRecords=[cap],speakerId='two'),dict(start=2.,end=3.,japanese='しましたか',cantonese='係咁',captionRecords=[cap],speakerId='one')]
  for i,word in enumerate(('開始光子起動','光子起動'),start=1):
   rows.append(dict(start=i*10.,end=i*10.+1,japanese='テスト起動',cantonese='光子起動',captionRecords=[dict(id=str(i),start=i*10.,end=i*10.+1,text=word)],speakerId='two'))
  return rows
 def test_anchor_partition_covers_all_original_characters_once(self):
  cues=self.cues();before=copy.deepcopy(cues);groups=recovery.plan(cues)
  self.assertEqual(len(groups),1);g=groups[0]
  self.assertEqual(g['indices'],[0,1,2]);self.assertEqual([n['source'] for n in g['nodes']],['你们昨晚','光子起動','了'])
  self.assertEqual(''.join(n['source'] for n in g['nodes']),''.join(r['text'] for r in g['records']))
  self.assertEqual(cues,before)
 def test_ambiguous_or_manual_scene_is_not_reassigned(self):
  for mode in ('extra-anchor','manual'):
   cues=self.cues()
   if mode=='extra-anchor':cues[0]['captionRecords'][0]['text']+='光子起動'
   else:cues[1]['editorID']='user-edited'
   self.assertEqual(recovery.plan(cues),[])
 def test_only_owned_fragments_are_translated_and_all_clocks_roles_preserved(self):
  cues=self.cues();before=copy.deepcopy(cues)
  w=SimpleNamespace(atomic_json=worker.atomic_json,emit=Mock(),traditional_cantonese=lambda c,t:t,ollama_chat=Mock(side_effect=[json.dumps({'0':'你哋噚晚'}),json.dumps({'0':dict(supported=True,reason='完整')})]))
  with tempfile.TemporaryDirectory() as temp:
   changes=recovery.recover(w,dict(port=1,model='test'),temp,cues)
   self.assertEqual([r['index'] for r in changes],[1,3]);self.assertEqual(cues[0]['cantonese'],'你哋噚晚');self.assertEqual(cues[2]['cantonese'],'咗')
   payload=json.loads(w.ollama_chat.call_args_list[0].args[2][1]['content'])
   self.assertEqual(payload['fragments']['0']['source'],'你们昨晚')
   self.assertNotIn('japanese',payload['fragments']['0'])
  for a,b in zip(cues,before):
   for key in ('start','end','japanese','speakerId'):self.assertEqual(a[key],b[key])
 def test_a_model_cannot_approve_a_dropped_negation(self):
  cues=self.cues('你们不要');before=copy.deepcopy(cues)
  w=SimpleNamespace(atomic_json=worker.atomic_json,emit=Mock(),traditional_cantonese=lambda c,t:t,ollama_chat=Mock(side_effect=[json.dumps({'0':'你哋要'}),json.dumps({'0':dict(supported=True,reason='wrong approval')})]))
  with tempfile.TemporaryDirectory() as temp:
   self.assertEqual(recovery.recover(w,dict(port=1,model='test'),temp,cues),[])
  self.assertEqual(cues,before)
 def test_group_with_different_number_of_source_and_spoken_calls_is_not_guessed(self):
  cues=self.cues();cues[2]['japanese']='テスト起動'
  self.assertEqual(recovery.plan(cues),[])
 def test_locked_manual_editor_does_not_call_model(self):
  cues=self.cues();w=SimpleNamespace(ollama_chat=Mock())
  self.assertEqual(recovery.recover(w,dict(editorRender=True),Path('/unused'),cues),[])
  w.ollama_chat.assert_not_called()
