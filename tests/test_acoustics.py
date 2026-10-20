import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
from acoustics import activity,refine,trim_generated
class AcousticTests(unittest.TestCase):
 def test_generated_padding_removed_but_internal_pause_and_soft_edges_retained(self):
  sr=24000;x=np.zeros(sr*3,dtype=np.float32)
  x[12000:24000]=.12;x[48000:60000]=.08;x[11000:12000]=.004
  y=trim_generated(x,sr)
  self.assertTrue(np.array_equal(y[y!=0],x[x!=0]))
  self.assertEqual(np.count_nonzero(y==0),np.count_nonzero(x==0)-(len(x)-len(y)))
  self.assertLess(len(y),len(x));self.assertGreater(len(y),sr*2)
 def test_isolated_click_does_not_anchor_speech(self):
  x=np.zeros(32000,dtype=np.float32);x[10]=1;x[16000:24000]=.1
  self.assertEqual(activity(x,16000),[(1.0,1.5)])
 def test_nearby_acoustic_edges_do_not_change_text_or_extend_into_next_voice(self):
  cues=[dict(start=1,end=3,cantonese='你好'),dict(start=3,end=5,cantonese='早晨')]
  refine(cues,[(1.5,3.2),(3.6,5.2)],6)
  self.assertEqual(cues[0]['speechStart'],1.46)
  self.assertEqual(cues[1]['speechStart'],3.56)
  self.assertLessEqual(cues[0]['deliveryEnd'],cues[1]['speechStart'])
  self.assertEqual(cues[0]['cantonese'],'你好');self.assertEqual(cues[0]['start'],1)
 def test_distant_or_absent_activity_keeps_asr_anchor(self):
  c=dict(start=5,end=7);refine([c],[(.5,1)],10)
  self.assertLess(abs(c['speechStart']-5),.05)
  self.assertLess(abs(c['speechEnd']-7),.05)
 def test_adjacent_turn_padding_never_overlaps_next_turn(self):
  cues=[dict(start=1,end=2),dict(start=2,end=3)]
  refine(cues,[(1,2),(2,3)],4)
  self.assertLessEqual(cues[0]['speechEnd'],cues[1]['speechStart'])
  self.assertLessEqual(cues[0]['deliveryEnd'],cues[1]['speechStart'])
