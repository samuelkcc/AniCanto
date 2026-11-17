"""Keep progress baselines, clipping and segment joins stable at every fill width."""
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'mobile/DemoFilm'))
from tutorial_progress import geometry,draw_progress
from PIL import Image
class ProgressTrack(unittest.TestCase):
 def test_integer_segments_share_one_baseline_and_endpoints(self):
  for w,h in [(720,1080),(1280,720),(1024,768),(721,1081)]:
   for n in [1,3,9,13]:
    g=geometry(w,h,n);self.assertEqual(g[0][0],40);self.assertEqual(g[-1][2],w-40)
    self.assertEqual({(x[1],x[3])for x in g},{(h-30,h-26)})
    self.assertTrue(all(b[0]-a[2]==5 for a,b in zip(g,g[1:])))
 def test_partial_fill_cannot_expand_outside_the_track(self):
  for w,h in [(720,1080),(1280,720)]:
   mask=Image.new('RGBA',(w,h));draw_progress(mask,0,0,9);allowed=mask.getchannel('A')
   for index in range(9):
    for p in [0,.001,.01,.25,.5,.99,1]:
     out=Image.new('RGBA',(w,h));draw_progress(out,index,p,9);self.assertEqual(out.getchannel('A').tobytes(),allowed.tobytes())
 def test_full_progress_fills_the_final_pixel_without_a_cap_bulge(self):
  im=Image.new('RGBA',(720,1080));draw_progress(im,8,1,9)
  for x,y,x2,y2 in geometry(720,1080,9):
   self.assertEqual(im.getpixel(((x+x2)//2,y)),(170,128,255,255));self.assertEqual(im.getpixel(((x+x2)//2,y2)),(0,0,0,0))
if __name__=='__main__':unittest.main()
