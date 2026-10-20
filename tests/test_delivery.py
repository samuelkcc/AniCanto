import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
from delivery import phrase_plan,valid_plan
class DeliveryTests(unittest.TestCase):
 def test_preserves_pause_and_exact_approved_phrases(self):
  c=dict(cantonese='我今日嚟，有件事同你講。',recognitionParts=[dict(start=1,end=3),dict(start=5,end=8),dict(start=8,end=9)])
  p=phrase_plan(c)
  self.assertEqual([(x['start'],x['end']) for x in p],[(1,3),(5,9)])
  self.assertEqual(''.join(x['text'] for x in p),c['cantonese'])
 def test_no_guessed_split_when_text_and_source_parts_do_not_match(self):
  self.assertEqual(phrase_plan(dict(cantonese='唔好亂嚟。',recognitionParts=[dict(start=1,end=3),dict(start=5,end=8)])),[])
 def test_brief_pause_does_not_create_artificial_phrase(self):
  self.assertEqual(phrase_plan(dict(cantonese='唔好，亂嚟。',recognitionParts=[dict(start=1,end=3),dict(start=3.2,end=4)])),[])

 def test_model_plan_cannot_drop_duplicate_or_rewrite_words(self):
  c=dict(start=0,end=4,cantonese='你唔係想退出呀嘛？')
  good=[dict(start=0,end=1,text='你唔係'),dict(start=2,end=4,text='想退出呀嘛？')]
  self.assertTrue(valid_plan(c,good))
  for bad in [[dict(good[0],text='你係'),good[1]],[good[0],dict(good[1],text='想退出？')],[good[0],dict(good[1],start=.5)]]:
   self.assertFalse(valid_plan(c,bad))
 def test_plan_is_invalidated_when_user_edits_script(self):
  c=dict(start=0,end=4,cantonese='等陣，我同你講。',deliveryPlan=[dict(start=0,end=1,text='你好，'),dict(start=2,end=4,text='我同你講。')])
  self.assertEqual(phrase_plan(c),[])

 def test_drama_receives_whole_ep07_turn_without_pause_fragmentation(self):
  import tempfile
  from unittest.mock import Mock,patch
  import delivery
  approved='唔好走！一個接一個變，人類，你哋唔好諗逃！'
  cue=dict(start=768.66,end=772.6,cantonese=approved,deliveryPlan=[dict(start=768.66,end=770.6,text='唔好走！一個接一個變，'),dict(start=770.7,end=772.6,text='人類，你哋唔好諗逃！')])
  cfg=dict(ttsBackend='drama3',autoValidate=False,autoFit=False,targetLanguage='yue')
  with tempfile.TemporaryDirectory() as temp:
   audio=Path(temp)/'full.wav';audio.touch()
   generate=Mock(return_value=[audio])
   with patch.object(delivery,'plan_pauses') as plan,patch.object(delivery,'prepare_audio',side_effect=lambda c,j,p,r:p),patch.object(delivery,'retained_takes',side_effect=lambda j,c,p:p),patch.object(delivery,'remember_takes'):
    result=delivery.synthesize(cfg,Path(temp),[cue],generate,Mock(),Mock())
   plan.assert_not_called()
   sent=generate.call_args.args[2]
   self.assertEqual(len(sent),1);self.assertEqual(sent[0]['cantonese'],approved)
   self.assertEqual((sent[0]['start'],sent[0]['end']),(768.66,772.6))
   self.assertEqual(result,[audio]);self.assertNotIn('_phraseAligned',cue)
