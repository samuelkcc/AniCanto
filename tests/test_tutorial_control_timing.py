"""Keep OCR selected for the narrated OCR clause after different quiet edits."""
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'mobile/DemoFilm'))
from tutorial_control_timing import ocr_control_frames,external_control
class NarratedControls(unittest.TestCase):
 def test_second_clause_and_prior_quiet_edit_use_one_clock(self):
  a,b=ocr_control_frames(20,5.9,[{'start':1,'end':3}],432,720)
  self.assertEqual(b,round((20+.35+5.9-2)*24))
  self.assertEqual([external_control(n,a,b)for n in [432,a,b,719]],[1,2,3,3])
 def test_quiet_edit_inside_a_clause_maps_its_boundary(self):
  a,b=ocr_control_frames(10,6,[{'start':12,'end':13}],240,480)
  self.assertEqual(b,round((10+.35+6-1)*24));self.assertLess(a,b)
 def test_unverified_or_removed_clauses_do_not_get_a_fake_boundary(self):
  with self.assertRaises(ValueError):ocr_control_frames(0,0,[],0,240)
  with self.assertRaises(ValueError):ocr_control_frames(0,15,[],0,24)
if __name__=='__main__':unittest.main()
