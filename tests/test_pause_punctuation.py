import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
from delivery import valid_plan,phrase_plan
class PunctuationPlanTests(unittest.TestCase):
 def test_punctuation_is_not_a_spoken_phrase(self):
  cue=dict(start=0,end=3,cantonese='我係布蕾。',deliveryPlan=[dict(start=0,end=2,text='我係布蕾'),dict(start=2,end=3,text='。')])
  self.assertFalse(valid_plan(cue,cue['deliveryPlan']))
  self.assertEqual(phrase_plan(cue),[])
 def test_real_phrases_keep_all_characters(self):
  cue=dict(start=0,end=3,cantonese='我係布蕾。你好！')
  plan=[dict(start=0,end=1.5,text='我係布蕾。'),dict(start=1.5,end=3,text='你好！')]
  self.assertTrue(valid_plan(cue,plan))
