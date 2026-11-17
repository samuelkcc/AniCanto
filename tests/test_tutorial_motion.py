"""Keep actor head anchors fixed at different sizes and breathing phases."""
import importlib.util
from pathlib import Path
import math
import unittest
SPEC=importlib.util.spec_from_file_location('motion',Path(__file__).resolve().parents[1]/'mobile/DemoFilm/tutorial_motion.py');M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)
class CalmMotion(unittest.TestCase):
 def test_head_and_horizontal_anchors_stay_fixed(self):
  for w,h in [(300,400),(440,390),(270,270)]:
   for n in range(144):
    phase=n*math.pi/72
    for y in [0,.3*h,.5*h,.7*h]:self.assertEqual(M.source_point(.5*w,y,w,h,phase),(.5*w,y))
 def test_body_motion_is_small_and_cannot_fold_limbs(self):
  for h in [250,350,440]:
   for n in range(144):
    points=[M.source_point(30,y,300,h,n*math.pi/72)for y in range(h+1)]
    self.assertTrue(all(0<=py-y<=.600001 for y,(_,py)in enumerate(points)))
    self.assertTrue(all(a[1]<b[1]for a,b in zip(points,points[1:])))
 def test_feet_and_canvas_bounds_stay_fixed(self):
  for phase in [0,math.pi/2,math.pi]:self.assertEqual(M.source_point(40,400,300,400,phase),(40,400))
if __name__=='__main__':unittest.main()
