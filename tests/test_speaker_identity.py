import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
try: import numpy as np
except ImportError: np=None
import speakers
@unittest.skipIf(np is None,'requires bundled speaker runtime numpy')
class IdentityTests(unittest.TestCase):
 def test_short_voice_variation_keeps_long_anchor_and_distinct_voice_separate(self):
  v=np.array([[1,0,0],[0,1,0],[.8,0,.6],[0,.9,.43589]],dtype='float32');v/=np.linalg.norm(v,axis=1,keepdims=True)
  e=[dict(start=0,end=4,mixed=False),dict(start=10,end=14,mixed=False),dict(start=20,end=21.5,mixed=False),dict(start=30,end=31,mixed=False)]
  self.assertEqual(speakers.stable_assignments(v,e),[0,1,0,1])
 def test_unrelated_new_voice_is_not_forced_into_nearby_character(self):
  v=np.eye(3,dtype='float32');e=[dict(start=0,end=4,mixed=False),dict(start=4,end=8,mixed=False),dict(start=8,end=10,mixed=False)]
  self.assertEqual(speakers.stable_assignments(v,e),[0,1,2])
