import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import worker,script_preflight as sp
from voicecheck import inconsistent_takes

class PreflightTests(unittest.TestCase):
 def cue(self):return dict(start=0,end=2,text='彼は行った',japanese='彼は行った',cantonese='佢已經走了',requiredNames=[])
 def test_manual_script_never_calls_model(self):
  with tempfile.TemporaryDirectory() as d,patch.object(worker,'ollama_chat') as model:
   sp.repair(dict(scriptLocked=True),Path(d),[self.cue()],lambda *a:None);model.assert_not_called()
 def test_uncertain_source_cannot_replace_script(self):
  with tempfile.TemporaryDirectory() as d:
   cue=self.cue();responses=[{'0':dict(meaning='He left',clear=False)},{'0':'佢走咗喇'},{'0':dict(faithful=True,defects=[],reason='assumed')}]
   with patch.object(worker,'ollama_chat',side_effect=[json.dumps(x) for x in responses]):sp.repair(dict(port=1,model='local'),Path(d),[cue],lambda *a:None)
   self.assertEqual(cue['cantonese'],'佢已經走了')
 def test_verified_spoken_repair_is_cached_and_keeps_source(self):
  with tempfile.TemporaryDirectory() as d:
   cue=self.cue();responses=[{'0':dict(meaning='He left',clear=True)},{'0':'佢走咗喇'},{'0':dict(faithful=True,defects=[],reason='same source meaning')}]
   with patch.object(worker,'ollama_chat',side_effect=[json.dumps(x) for x in responses]):sp.repair(dict(port=1,model='local'),Path(d),[cue],lambda *a:None)
   self.assertEqual(cue['cantonese'],'佢走咗喇');self.assertEqual(cue['originalCantonese'],'佢已經走了');self.assertEqual(cue['end'],2)
   with patch.object(worker,'ollama_chat') as model:
    sp.repair(dict(port=1,model='local'),Path(d),[cue],lambda *a:None);model.assert_not_called()
 def test_food_term_grounded_in_source_cannot_disappear(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);(job/'scene-glossary.json').write_text(json.dumps([dict(japanese='パン',cantonese='麵包')]))
   cue=dict(start=0,end=1,text='パンください',cantonese='請畀一份麵包我好嗎？')
   responses=[{'0':dict(meaning='Bread please',clear=True)},{'0':'唔該畀我'},{'0':dict(faithful=True,defects=[],reason='incorrect positive')}]
   with patch.object(worker,'ollama_chat',side_effect=[json.dumps(x) for x in responses]):sp.repair(dict(port=1,model='local'),job,[cue],lambda *a:None)
   self.assertIn('麵包',cue['cantonese']);self.assertIn('missing-name',json.loads((job/'script-preflight.json').read_text())[0]['rejectionReasons'])
 def test_generated_voice_outlier_requires_three_agreeing_takes(self):
  cues=[dict(speakerId='a') for _ in range(4)]
  vectors=[[1,0],[1,0],[1,0],[0,1]]
  self.assertEqual([r['index'] for r in inconsistent_takes(cues,vectors)],[3])
  self.assertEqual(inconsistent_takes(cues[:3],[vectors[0],vectors[1],vectors[3]]),[])
  cues[3]['speakerId']='b';self.assertEqual(inconsistent_takes(cues,vectors),[])
 def test_spoken_json_wrapper_does_not_become_dialogue(self):
  self.assertEqual(worker.clean_spoken_line('{"配音台詞":"佢走咗喇"}'),'佢走咗喇')
  self.assertEqual(worker.clean_spoken_line('{"意思":"說明唔係台詞","配音":"佢走咗喇"}'),'佢走咗喇')
 def test_delivery_context_cannot_turn_into_placing_an_order(self):
  source=dict(japanese='会社までひとつ',independent_japanese='')
  previous=dict(japanese='配達です')
  self.assertTrue(sp.action_conflicts('送一份去公司','去公司點一份',source,previous))
  self.assertFalse(sp.action_conflicts('送一份去公司','送去公司',source,previous))
