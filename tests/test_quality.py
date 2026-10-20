import json,sys,tempfile,unittest,wave
from pathlib import Path
from unittest.mock import Mock,patch
import numpy as np
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
from quality import check_voice,inspect_rendered_voice
from speechcheck import similarity,critical_omissions
from delivery import fit_audio

class QualityTests(unittest.TestCase):
 def test_final_check_reads_rendered_segment_instead_of_original_take(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder)
   with wave.open(str(root/'cantonese.wav'),'wb') as f:
    f.setnchannels(1);f.setsampwidth(2);f.setframerate(24000)
    f.writeframes(np.concatenate([np.zeros(24000,dtype=np.int16),np.full(12000,3456,dtype=np.int16)]).tobytes())
   def inspect(cfg,job,cues,paths,emit):
    with wave.open(str(paths[0])) as f:
     self.assertEqual(f.getnframes(),12000)
     self.assertTrue(np.all(np.frombuffer(f.readframes(12000),dtype=np.int16)==3456))
    return [dict(requiresReview=False)]
   with patch('speechcheck.inspect',side_effect=inspect):
    result=inspect_rendered_voice({},root,[dict(cantonese='你好',text='こんにちは')],[dict(index=7,renderedStart=1,renderedEnd=1.5)],lambda *args:None)
   self.assertEqual(result['rows'][0]['index'],7)
 def test_full_length_silent_turn_fails_even_when_other_turn_is_audible(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder);x=np.zeros(48000,dtype=np.int16);x[:24000]=5000
   with wave.open(str(path/'cantonese.wav'),'wb') as f:
    f.setnchannels(1);f.setsampwidth(2);f.setframerate(24000);f.writeframes(x.tobytes())
   cues=[dict(cantonese='你好'),dict(cantonese='早晨')]
   timing=[dict(index=1,renderedStart=0,renderedEnd=1),dict(index=2,renderedStart=1,renderedEnd=2)]
   with self.assertRaisesRegex(ValueError,'第 2 句'):check_voice(path,cues,timing)
   with self.assertRaisesRegex(ValueError,'數量'):check_voice(path,cues,timing[:1])
 def test_atempo_correction_measures_output_and_stays_bounded(self):
  calls=[]
  def run(args):
   rate=float(args[args.index('-af')+1].split('=')[1]);calls.append(rate)
   return b'\1\0'*round((2/rate+.04)*24000)
  raw,rate=fit_audio(dict(ffmpeg='ffmpeg'),'voice.wav',1,2,run)
  self.assertLessEqual(abs(len(raw)/48000-2),.015)
  self.assertLessEqual(len(calls),3)
  self.assertTrue(all(.8<=r<=1.25 for r in calls))
 def test_text_check_does_not_ignore_omission_or_repetition(self):
  self.assertEqual(similarity('你好！','你好'),1)
  self.assertLess(similarity('我唔會走。','我會走。'),1)
  self.assertLess(similarity('你好','你好你好你好'),.72)
  self.assertTrue(critical_omissions('我唔會走','我會走'))
  self.assertTrue(critical_omissions('我唔係唔想走','我唔想走'))
  self.assertFalse(critical_omissions('我唔會走','我不會走'))
