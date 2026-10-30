"""Paired evidence must reject voices and incomplete or unvalidated analyses."""
import copy,json,sys,tempfile,time,unittest,wave
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import caption_quiet_proof as proof
from nonverbal import SCORE_LABELS

class QuietCaption270(unittest.TestCase):
 def rows(self):
  return [dict(start=0,duration=1,**{k:(.9 if k=='music' else .001) for k in SCORE_LABELS}),dict(start=.5,duration=1,**{k:(.9 if k=='music' else .001) for k in SCORE_LABELS})]
 def test_music_with_low_voice_classes_passes_only_supported_profile(self):
  self.assertTrue(proof.confirms(self.rows(),.2,1.4,'apple-soundanalysis-v1',original=True))
  self.assertFalse(proof.confirms(self.rows(),.2,1.4,'ast-audioset-f826b80d',original=True))
 def test_float_residue_below_delivery_quantum_is_quiet(self):
  self.assertTrue(proof.quiet(dict(peak=4.424356120580342e-6,rms=6.734522717951161e-7)))
  self.assertFalse(proof.quiet(dict(peak=.001,rms=.0001)))
  self.assertFalse(proof.quiet(dict(peak=float('nan'),rms=0)))
 def test_any_weak_or_strong_voice_class_blocks(self):
  for label in SCORE_LABELS:
   if label=='music':continue
   with self.subTest(label=label):
    rows=self.rows();rows[0][label]=.06
    self.assertFalse(proof.confirms(rows,.2,1.4,'apple-soundanalysis-v1',original=True))
 def test_gap_truncation_malformed_and_unconfirmed_music_block(self):
  for rows in [[],self.rows()[:1],[dict(start=0,duration=2,speech=0)]]:
   self.assertFalse(proof.confirms(rows,.2,1.4,'apple-soundanalysis-v1',original=True))
  rows=self.rows();rows[0]['music']=.49
  self.assertFalse(proof.confirms(rows,.2,1.4,'apple-soundanalysis-v1',original=True))
 def test_failed_inspection_is_reserved_and_not_retried_after_resume(self):
  with tempfile.TemporaryDirectory() as d:
   folder=Path(d);source=folder/'source.wav'
   with wave.open(str(source),'wb') as audio:audio.setparams((1,2,16000,0,'NONE','not compressed'));audio.writeframes(b'\0'*160000)
   cfg=dict(executable='fixture',startOffset=0)
   cue=dict(start=1,end=2);evidence=dict(duration=5,sourceSHA256='source-hash',stemSHA256='stem-hash',sourcePath=str(source),stemPath=str(source))
   write=lambda p,v:p.write_text(json.dumps(v))
   with patch('worker.run',side_effect=RuntimeError('fixture classifier failure')) as run:
    a=proof.inspect(cfg,folder,cue,evidence,dict(peak=0,rms=0),write,dict(started=time.monotonic(),windows=0))
    b=proof.inspect(cfg,folder,cue,evidence,dict(peak=0,rms=0),write,dict(started=time.monotonic(),windows=0))
   self.assertEqual(run.call_count,1);self.assertFalse(a['complete']);self.assertFalse(b['complete'])
   self.assertEqual(len(list((folder/'caption-quiet-proof').glob('*.json'))),1)
if __name__=='__main__':unittest.main()
