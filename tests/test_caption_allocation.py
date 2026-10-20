import sys,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import caption_allocation as ca
import worker

class AllocationTests(unittest.TestCase):
 def cues(self):
  return [dict(start=0,end=1,text='いいなお前ら',japanese='いいなお前ら',subtitleHint='你們聽好了 一秒都不能留',cantonese='你哋聽住，唔可以留一秒'),dict(start=1,end=2,text='一秒残らずだ',japanese='一秒残らずだ',subtitleHint='你們聽好了 一秒都不能留',cantonese='唔可以留一秒')]
 def test_shared_caption_duplicate_is_detected_but_real_repeated_speech_is_not(self):
  cues=self.cues();self.assertEqual(ca.suspect_pairs(cues),[(0,1)])
  cues[1]['japanese']=cues[0]['japanese'];self.assertEqual(ca.suspect_pairs(cues),[])
 def test_semantic_rejection_leaves_both_original_lines(self):
  with tempfile.TemporaryDirectory() as directory:
   cues=self.cues();before=[c['cantonese'] for c in cues]
   replies=[json.dumps({'0':'聽住','1':'可以留一秒'}),json.dumps(dict(preserved=False,reason='lost negation'))]
   with patch.object(worker,'ollama_chat',side_effect=replies):ca.repair(dict(port=1,model='local'),Path(directory),cues,lambda *a:None)
   self.assertEqual([c['cantonese'] for c in cues],before)
 def test_verified_allocation_keeps_original_and_source_timestamps(self):
  with tempfile.TemporaryDirectory() as directory:
   cues=self.cues();before=cues[0]['cantonese']
   replies=[json.dumps({'0':'你哋聽住','1':'唔可以留一秒'}),json.dumps(dict(preserved=True,reason='each source turn retained'))]
   with patch.object(worker,'ollama_chat',side_effect=replies):ca.repair(dict(port=1,model='local'),Path(directory),cues,lambda *a:None)
   self.assertEqual(cues[0]['originalCantonese'],before)
   self.assertEqual((cues[0]['start'],cues[0]['end']),(0,1));self.assertEqual(cues[1]['cantonese'],'唔可以留一秒')
