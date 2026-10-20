import array,json,math,shutil,subprocess,sys,tempfile,unittest,wave
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
from natural_finish import finish
from natural_delivery import seconds

def wav(p,length,edge=0):
 sr=24000;voice=array.array('h',(round(3500*math.sin(i*.07)) for i in range(round(sr*length))))
 raw=array.array('h',[0])*round(edge*sr);raw.extend(voice);raw.extend(array.array('h',[0])*round(edge*sr))
 with wave.open(str(p),'wb') as f:f.setparams((1,2,sr,0,'NONE','not compressed'));f.writeframes(raw.tobytes())
 return p

def run(args):return subprocess.check_output([str(a) for a in args],stderr=subprocess.PIPE)

class NaturalFinishingTests(unittest.TestCase):
 @unittest.skipUnless(shutil.which('ffmpeg'),'FFmpeg required')
 def test_safe_half_second_shift_plus_tiny_tempo_fits_complete_three_second_take(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);p=wav(job/'long.wav',3.343);next=wav(job/'next.wav',1.);before=p.read_bytes()
   # The full take needs 23% acceleration at the original start; a safe early
   # start plus <=5% avoids that large change without moving the next sentence.
   cfg=dict(productionMode='normal',duration=15.,ffmpeg=shutil.which('ffmpeg'))
   cues=[dict(start=5,end=6.9,cantonese='完整測試對白'),dict(start=7.72,end=9.,cantonese='下一句',editorAudio=str(next))]
   with patch('natural_schedule.scene_boundaries',return_value=dict(status='detected',cuts=[])):
    # Match the cached boundary receipt used by the pure tempo simulation.
    (job/'natural-scene-boundaries.json').write_text(json.dumps(dict(status='detected',cuts=[])))
    paths,rows=finish(cfg,job,cues,[p,next],run,Mock())
   self.assertTrue(rows[0]['fit']);self.assertLess(rows[0]['shift'],0);self.assertLessEqual(rows[0]['start']+seconds(paths[0],cfg,run),rows[1]['start'])
   self.assertLessEqual(rows[0]['tempoRate'],1.05);self.assertGreater(rows[0]['tempoRate'],1.)
   self.assertGreaterEqual(seconds(paths[0],cfg,run),3.343/1.05);self.assertEqual(p.read_bytes(),before);self.assertEqual(paths[1],next)
 @unittest.skipUnless(shutil.which('ffmpeg'),'FFmpeg required')
 def test_twenty_three_percent_speedup_is_rejected_when_no_gap_or_shift_is_safe(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);p=wav(job/'take.wav',3.343);cfg=dict(productionMode='normal',duration=2.72,ffmpeg=shutil.which('ffmpeg'))
   with patch('natural_schedule.scene_boundaries',return_value=dict(status='unavailable',cuts=[])):
    paths,rows=finish(cfg,job,[dict(start=0,end=2.72,cantonese='完整對白')],[p],run,Mock())
   self.assertFalse(rows[0]['fit']);self.assertEqual(paths,[p]);self.assertEqual(rows[0]['tempoRate'],1.)
 def test_silent_edges_are_removed_before_any_rewrite_without_losing_voice_samples(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);p=wav(job/'take.wav',.6,edge=.3);original=p.read_bytes();cfg=dict(productionMode='normal',duration=1)
   paths,rows=finish(cfg,job,[dict(start=0,end=1,cantonese='Hello')],[p],Mock(),Mock(),allow_tempo=False)
   self.assertTrue(rows[0]['fit']);self.assertLess(seconds(paths[0],cfg,Mock()),1);self.assertEqual(p.read_bytes(),original)
 def test_manual_editor_is_not_trimmed_retimed_or_accelerated(self):
  with patch('natural_schedule.prepare') as prepare:
   self.assertEqual(finish(dict(productionMode='normal',editorRender=True),'.',[],['manual.wav'],Mock(),Mock()),(['manual.wav'],None));prepare.assert_not_called()

 @unittest.skipUnless(shutil.which('ffmpeg'),'FFmpeg required')
 def test_short_near_miss_uses_eight_percent_without_cutting_or_changing_the_source(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);p=wav(job/'take.wav',1.2074);original=p.read_bytes();cfg=dict(productionMode='normal',duration=1.12,ffmpeg=shutil.which('ffmpeg'))
   with patch('natural_schedule.scene_boundaries',return_value=dict(status='unavailable',cuts=[])):
    paths,rows=finish(cfg,job,[dict(start=0,end=1.12,cantonese='完整短對白')],[p],run,Mock())
   self.assertTrue(rows[0]['fit']);self.assertGreater(rows[0]['tempoRate'],1.05);self.assertLessEqual(rows[0]['tempoRate'],1.10)
   self.assertGreaterEqual(seconds(paths[0],cfg,run),1.2074/1.10-.0001);self.assertEqual(original,p.read_bytes())
 @unittest.skipUnless(shutil.which('ffmpeg'),'FFmpeg required')
 def test_short_exception_never_applies_to_a_larger_gap_or_accumulates_on_resume(self):
  for length,slot in ((1.2539,1.12),(1.8,1.5),(2.4,2.2)):
   with self.subTest(length=length),tempfile.TemporaryDirectory() as d:
    job=Path(d);p=wav(job/'take.wav',length);cfg=dict(productionMode='normal',duration=slot,ffmpeg=shutil.which('ffmpeg'))
    with patch('natural_schedule.scene_boundaries',return_value=dict(status='unavailable',cuts=[])):
     paths,rows=finish(cfg,job,[dict(start=0,end=slot,cantonese='完整對白')],[p],run,Mock())
    self.assertFalse(rows[0]['fit']);self.assertEqual(paths,[p])
