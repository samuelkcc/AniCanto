"""Check own-utterance padding at the actual submission and worker boundaries."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
import numpy as np
import soundfile as sf
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'windows'),str(ROOT/'Resources')]
import independent_voices as iv
from desktop_state import Store,read

class OwnUtterance342(unittest.TestCase):
 def test_quiet_external_voice_is_never_read_for_new_requests(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);sr=16000;t=np.arange(sr*10)/sr
   # The source after the first second contains a quiet different harmonic voice.
   audio=np.where(t<1,.2*np.sin(2*np.pi*210*t),.001*np.sin(2*np.pi*120*t)).astype('float32')
   source=root/'source.wav';sf.write(source,audio,sr,subtype='FLOAT')
   cues=[dict(start=0,end=.8,speechStart=.1,speechEnd=.7,japanese='原句')]
   cfg=dict(audio=str(source),job=str(root),storage=str(root),cues=cues,productionMode='normal',voiceReferencePaddingRevision=iv.PADDING_REVISION342)
   before=copy.deepcopy(cues)
   with patch('reference_padding.pad',side_effect=AssertionError('External fill must not run')):
    iv.prepare(cfg,Mock())
   result=read(root/'independent-voices.json');p=result['profiles'][0]
   self.assertEqual(result['revision'],iv.REFERENCE_REVISION342);self.assertEqual(p['paddingMethod'],'silence');self.assertIsNone(p['paddingRange'])
   out,rate=sf.read(p['reference'],dtype='float32');own=audio[round(.1*sr):round(.7*sr)]
   np.testing.assert_allclose(out[:len(own)],own,atol=1/32768)
   self.assertTrue(np.all(out[len(own):]==0));self.assertAlmostEqual(len(out)/rate,3.1)
   self.assertEqual(cues,before)
 def test_absent_and_unknown_keep_legacy_revision(self):
  for cfg in [{},{'voiceReferencePaddingRevision':'unknown'}]:
   self.assertFalse(iv.own_padding(cfg));self.assertEqual(iv.policy_revision(cfg),iv.REVISION)
 def test_new_submission_and_paused_request_preserve_policy_and_budgets(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source=root/'fixture.mkv';source.write_bytes(b'isolated request fixture')
   store=Store(root);store.add([source]);row=store.queue[0];request=store.submit(row)
   current=read(request);self.assertEqual(current['voiceReferencePaddingRevision'],iv.PADDING_REVISION342)
   self.assertTrue(current['preferFirstAudibleTake']);self.assertFalse(current['aiAutoFix'])
   current.pop('voiceReferencePaddingRevision');current['recoverySpentSeconds']=77;current['testAttempts']={'voice':2}
   request.write_text(json.dumps(current));before=request.read_bytes();row['status']='paused'
   self.assertEqual(store.submit(row),request);self.assertEqual(request.read_bytes(),before)
