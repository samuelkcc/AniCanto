"""Regression for the Windows OP/ED classifier's 13-sample tail crash."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'windows'))
from native_tools import classifier_windows

class ClassifierTailTests(unittest.TestCase):
 def test_empty_and_sub_kaldi_window_fragments_do_not_become_events(self):
  for size in (0,1,13,399):
   self.assertEqual(list(classifier_windows([0.0]*size)),[])
 def test_exact_window_and_real_final_speech_remain(self):
  for size in (400,401,799,16000,39999,40000):
   rows=list(classifier_windows([0.0]*size));self.assertEqual(len(rows),1)
   self.assertEqual(len(rows[0][2]),size);self.assertAlmostEqual(rows[0][1],min(2.5,size/16000))
 def test_reported_case_full_hops_plus_thirteen_samples(self):
  data=list(range(40000*3+13));rows=list(classifier_windows(data))
  self.assertEqual([r[0] for r in rows],[0,2.5,5])
  self.assertTrue(all(len(r[2])>=400 for r in rows))
  self.assertEqual(rows[-1][2],data[80000:])
 def test_a_valid_last_hop_is_not_silently_dropped(self):
  rows=list(classifier_windows([0.0]*(80000+400)))
  self.assertEqual([r[0] for r in rows],[0,2.5,5])
  self.assertEqual(len(rows[-1][2]),400);self.assertEqual(rows[-1][1],.025)
 def test_no_float_drift_in_long_episode_sample_clock(self):
  class Samples:
   def __len__(self):return 16000*1800+13
   def __getitem__(self,s):return range(s.start,min(s.stop,len(self)))
  rows=list(classifier_windows(Samples()))
  self.assertEqual(len(rows),720);self.assertEqual(rows[-1][0],1797.5)
  self.assertTrue(all(len(r[2])>=400 for r in rows))

if __name__=='__main__':unittest.main()
