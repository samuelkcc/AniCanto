import hashlib,json,sys,tempfile,unittest,wave
from pathlib import Path
from unittest.mock import Mock
import numpy as np
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import gsv_reference

class ContinuousReferenceTests(unittest.TestCase):
 def profile(self,root):
  rate=44100;t=np.arange(round(2.8*rate))/rate;a=(.15*np.sin(2*np.pi*200*t)*32768).astype('<i2').tobytes()
  t=np.arange(round(2.2*rate))/rate;b=(.15*np.sin(2*np.pi*800*t)*32768).astype('<i2').tobytes()
  p=root/'original.wav'
  with wave.open(str(p),'wb') as f:f.setparams((1,2,rate,0,'NONE','not compressed'));f.writeframes(a+b)
  return dict(id='same-role',reference=str(p),promptText='兩段原文',language='ja',transcriptSource='original-japanese-words',referenceRanges=[[10,12.8],[20,22.2]]),a
 def test_extracts_one_continuous_original_keeps_bandwidth_and_source(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p,a=self.profile(root);before=Path(p['reference']).read_bytes();r=gsv_reference.candidate(p,root)
   self.assertIsNotNone(r);self.assertEqual(r['id'],'same-role')
   with wave.open(r['reference']) as f:
    self.assertEqual(f.getframerate(),44100);self.assertAlmostEqual(f.getnframes()/f.getframerate(),3.1);raw=f.readframes(f.getnframes())
   self.assertEqual(raw[:len(a)],a);self.assertEqual(set(raw[len(a):]),{0})
   self.assertEqual(Path(p['reference']).read_bytes(),before)
 def test_manual_single_reference_short_or_inconsistent_ranges_are_preserved(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p,a=self.profile(root)
   for changes in [dict(transcriptSource='manual'),dict(referenceRanges=[]),dict(referenceRanges=[[10,15]]),dict(referenceRanges=[[10,11.9],[20,21.9],[30,31.2]]),dict(referenceRanges=[[10,11],[20,23]]),dict(mixedReference=True)]:
    self.assertIsNone(gsv_reference.candidate(dict(p,**changes),root))
 def test_exact_clip_transcript_is_cached_without_mutating_the_card(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p,a=self.profile(root);before=dict(p);cfg=dict(storage=d,ttsBackend='gpt-sovits',referenceSpeechModel='whisper-large-v3')
   def transcribe(args):
    req=json.loads(Path(args[-1]).read_text());return json.dumps({'rows':[dict(row,verified=True,promptText='實際連續原文') for row in req['items']]}).encode()
   run=Mock(side_effect=transcribe);first=gsv_reference.prepare(cfg,root,[p],run,lambda *a:None);second=gsv_reference.prepare(cfg,root,[p],run,lambda *a:None)
   self.assertEqual(first,second);self.assertEqual(run.call_count,1);self.assertEqual(p,before)
   self.assertEqual(first[p['id']]['promptText'],'實際連續原文');self.assertEqual(first[p['id']]['originalReference'],p['reference'])
 def test_unverified_transcript_or_worker_failure_never_replaces_original(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p,a=self.profile(root);cfg=dict(storage=d,ttsBackend='gpt-sovits',referenceSpeechModel='whisper-large-v3')
   def uncertain(args):
    req=json.loads(Path(args[-1]).read_text());return json.dumps({'rows':[dict(row,verified=False,promptText='') for row in req['items']]}).encode()
   self.assertEqual(gsv_reference.prepare(cfg,root,[p],uncertain,lambda *a:None),{})
   self.assertEqual(gsv_reference.prepare(dict(cfg,referenceSpeechModel='whisper-small'),root,[p],Mock(side_effect=RuntimeError('failed')),lambda *a:None),{})
