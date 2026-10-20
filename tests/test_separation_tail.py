import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import dubbing
ROOT=Path(__file__).resolve().parents[1]
BIN=ROOT/'dist/AniCanto.app/Contents/Resources/bin'

def run(args):return subprocess.check_output([str(a) for a in args],stderr=subprocess.PIPE)

def metadata(path):return json.loads(run([BIN/'ffprobe','-v','error','-show_format','-show_streams','-of','json',path]))

class SeparationTailTests(unittest.TestCase):
 def cfg(self,root,duration=2):return dict(ffmpeg=str(BIN/'ffmpeg'),ffprobe=str(BIN/'ffprobe'),storage=str(root),video=str(root/'video.wav'),duration=duration)
 def wav(self,path,duration,channels=2):
  run([BIN/'ffmpeg','-v','error','-y','-f','lavfi','-i','sine=frequency=440:sample_rate=44100','-t',str(duration),'-ac',str(channels),'-c:a','pcm_f32le',path])
 def fixture(self,root,length=1.835):
  self.wav(root/'original.wav',length)
  for n in ('background.wav','dialogue.wav'):self.wav(root/n,length)
 def test_small_common_decoded_tail_is_padded_preserving_existing_samples(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);self.fixture(r);before=run([BIN/'ffmpeg','-v','error','-i',r/'dialogue.wav','-f','f32le','-'])
   events=[];dubbing.validate_stems(self.cfg(r),r,run,lambda *a:events.append(a))
   for n in ('background.wav','dialogue.wav'):
    self.assertAlmostEqual(float(metadata(r/n)['format']['duration']),2,places=5)
   after=run([BIN/'ffmpeg','-v','error','-i',r/'dialogue.wav','-f','f32le','-'])
   self.assertEqual(after[:len(before)],before)
   self.assertEqual(set(after[len(before):]),{0})
   self.assertEqual(len(events),1)
 def test_small_difference_without_source_proof_is_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);self.fixture(r);(r/'original.wav').unlink()
   with self.assertRaisesRegex(RuntimeError,'原音訊'):dubbing.validate_stems(self.cfg(r),r,run)
 def test_truncated_mono_or_disagreeing_stems_are_not_committed(self):
  for badlength,channels in [(1,2),(1.835,1),(1.9,2)]:
   with self.subTest(length=badlength,channels=channels),tempfile.TemporaryDirectory() as d:
    r=Path(d);self.fixture(r);self.wav(r/'dialogue.wav',badlength,channels)
    with self.assertRaises(RuntimeError):dubbing.validate_stems(self.cfg(r),r,run)
    self.assertFalse((r/'complete.json').exists())
 def test_uncommitted_valid_stems_recover_without_model_inference_and_bad_cache_regenerates(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);self.wav(r/'video.wav',2);cfg=self.cfg(r);events=[]
   with patch.object(dubbing,'model_job') as model:
    def produce(*args):
     out=Path(args[2]['out']);self.fixture(out,2)
    model.side_effect=produce
    bg,voice=dubbing.separate(cfg,run,lambda *a,**k:events.append(a));self.assertEqual(model.call_count,1)
    (bg.parent/'complete.json').unlink();self.fixture(bg.parent)
    dubbing.separate(cfg,run,lambda *a,**k:events.append(a));self.assertEqual(model.call_count,1)
    self.assertTrue((bg.parent/'complete.json').exists())
    self.wav(voice,1)
    dubbing.separate(cfg,run,lambda *a,**k:None);self.assertEqual(model.call_count,2)
 def test_new_extraction_pads_short_source_before_the_separator_runs(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);self.wav(r/'video.wav',1.835);cfg=self.cfg(r)
   def model(c,a,request,e):
    self.assertAlmostEqual(float(metadata(request['input'])['format']['duration']),2,places=5)
    out=Path(request['out']);self.fixture(out,2)
   with patch.object(dubbing,'model_job',side_effect=model):dubbing.separate(cfg,run,lambda *a,**k:None)
if __name__=='__main__':unittest.main()
