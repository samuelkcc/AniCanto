import json,sys,unittest
from pathlib import Path
from unittest.mock import Mock
import numpy as np
import soundfile as sf
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import independent_voices,reference_padding as rp

SR=16000

def tone(seconds,amplitude,frequency=180.):
    t=np.arange(int(seconds*SR))/SR
    return (amplitude*np.sin(2*np.pi*frequency*t)).astype('float32')

class ReferencePaddingTests(unittest.TestCase):
 def test_short_ranges_are_merged(self):
  cues=[dict(start=1,end=2,speechStart=1.2,speechEnd=1.4),dict(start=2.1,end=3)]
  self.assertEqual(rp.speech_ranges(cues,10),[(1.,3.)])  # A 0.1 s gap between windows is merged.
 def test_quiet_gap_is_used(self):
  clip=tone(1.2,.2);cues=[dict(start=0,end=1.5,speechStart=0.,speechEnd=1.4),dict(start=6,end=7.4,speechStart=6.1,speechEnd=7.3)]
  source=np.concatenate([clip,tone(4.5,.002,120.),tone(1.2,.2)])
  def read(a,b):return source[int(a*SR):int(b*SR)]
  need=int(rp.MINIMUM_SECONDS*SR)-len(clip)
  padded,method,rng=rp.pad(clip,SR,1.4,need,read,cues,len(source)/SR)
  self.assertEqual(method,'scene-tone');self.assertIsNotNone(rng)
  self.assertEqual(len(padded),len(clip)+need)
  self.assertGreater(float(np.max(np.abs(padded[len(clip)+need-200:]))),0.)
 def test_loud_gap_is_refused_and_silence_is_used(self):
  clip=tone(1.2,.2);cues=[dict(start=0,end=1.5,speechStart=0.,speechEnd=1.4),dict(start=6,end=7.4,speechStart=6.1,speechEnd=7.3)]
  source=np.concatenate([clip,tone(4.5,.2,frequency=490.),tone(1.2,.2)])
  def read(a,b):return source[int(a*SR):int(b*SR)]
  need=int(rp.MINIMUM_SECONDS*SR)-len(clip)
  padded,method,rng=rp.pad(clip,SR,1.4,need,read,cues,len(source)/SR)
  self.assertEqual(method,'silence');self.assertIsNone(rng)
  n=len(clip)+need-200
  self.assertTrue(np.all(padded[n:]==0.))
 def test_music_level_fill_is_not_quiet(self):
  self.assertFalse(rp.is_quiet(tone(2,.15,440.),SR,.2))
  self.assertTrue(rp.is_quiet(np.zeros(int(2*SR),dtype='float32'),SR,.2))
  self.assertTrue(rp.is_quiet(tone(2,.002,240.),SR,.2))
 def test_prepare_uses_scene_tone_in_a_quiet_scene(self):
  import tempfile
  with tempfile.TemporaryDirectory() as d:
   folder=Path(d);room=tone(3.,.0015,110.)+tone(3.,.0012,230.);audio=np.concatenate([tone(1.2,.2,180.),room,tone(1.2,.2,490.),room,tone(1.2,.2,320.)])
   path=folder/'dialogue.wav';sf.write(path,audio.astype('float32'),SR,subtype='FLOAT')
   cues=[dict(start=0,end=1.3,speechStart=.02,speechEnd=1.18,text='一',japanese='一',cantonese='第一句'),
         dict(start=4.2,end=5.5,speechStart=4.22,speechEnd=5.38,text='二',japanese='二',cantonese='第二句')]
   cfg=dict(storage=str(folder),job=str(folder),audio=str(path),dialoguePath=str(path),cues=cues,roleAnalysisMode='independent',continueOnError=True)
   independent_voices.prepare(cfg,Mock())
   profiles=json.loads((folder/'independent-voices.json').read_text())['profiles']
   self.assertEqual(len(profiles),2)
   for profile in profiles:
    self.assertTrue(profile['shortReference'])
    self.assertEqual(profile['paddingMethod'],'scene-tone')
    a,b=profile['referenceRanges'][0];n=round((b-a)*SR)
    reference,_=sf.read(profile['reference'],dtype='float32')
    self.assertAlmostEqual(len(reference)/SR,rp.MINIMUM_SECONDS,places=3)
    self.assertFalse(np.all(reference[n:]==0.))
   for profile in profiles:
    manifest=json.loads((Path(profile['reference']).parent/'source.json').read_text())
    self.assertEqual(manifest['paddingMethod'],'scene-tone')
    self.assertTrue(manifest['paddingRange'])
    self.assertEqual(manifest['silencePaddingSeconds'],0.)
    self.assertEqual(manifest['method'],independent_voices.REVISION)

if __name__=='__main__':unittest.main()
