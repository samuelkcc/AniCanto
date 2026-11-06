"""Bind new source references to their bytes without changing legacy recordings."""
import copy,hashlib,json,os,sys,tempfile,unittest,shutil,subprocess
from pathlib import Path
from unittest.mock import Mock,patch
import numpy as np
import soundfile as sf
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows')]
import independent_voices as iv,engine_reference
from desktop_state import Store,read

class ReferenceIdentity379(unittest.TestCase):
 def test_changed_source_with_same_size_and_date_cannot_reuse_the_other_actor(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source=root/'source.wav';rate=16000;t=np.arange(rate*4)/rate
   cfg=dict(audio=str(source),job=str(root),storage=str(root),cues=[dict(start=0,end=2,japanese='原聲')],productionMode='normal',voiceReferencePaddingRevision=iv.PADDING_REVISION342,voiceReferenceIdentityRevision=iv.IDENTITY_REVISION379)
   paths=[];digests=[]
   for hz in [210,120]:
    sf.write(source,np.sin(2*np.pi*hz*t)*.1,rate,subtype='PCM_16');os.utime(source,ns=(1700000000000000000,1700000000000000000))
    iv.prepare(cfg,Mock());profile=read(root/'independent-voices.json')['profiles'][0];paths.append(profile['reference']);digests.append(profile['referenceSHA256']);self.assertEqual(profile['referenceSHA256'],hashlib.sha256(Path(profile['reference']).read_bytes()).hexdigest())
   self.assertNotEqual(paths[0],paths[1]);self.assertNotEqual(digests[0],digests[1]);self.assertTrue(all(Path(p).exists() for p in paths))
 def test_changed_reference_rejected_before_conditioning_or_model_use(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);p=root/'reference.wav';p.write_bytes(b'wrong actor');run=Mock(side_effect=AssertionError('Must not decode or generate'))
   cfg=dict(voiceReferenceIdentityRevision=iv.IDENTITY_REVISION379,storage=str(root));profile=dict(reference=str(p),referenceSHA256=hashlib.sha256(b'correct actor').hexdigest(),promptText='原聲')
   with self.assertRaisesRegex(ValueError,'reference bytes changed'):engine_reference.prepare(cfg,root,profile,run)
   run.assert_not_called()
 @unittest.skipUnless(shutil.which('ffmpeg'),'Actual conditioning needs FFmpeg')
 def test_conditioned_cache_cannot_silently_return_modified_reference_bytes(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source=root/'reference.wav';rate=44100;t=np.arange(rate*4)/rate
   sf.write(source,np.sin(2*np.pi*210*t)*.15,rate,subtype='PCM_16')
   profile=dict(reference=str(source),referenceSHA256=hashlib.sha256(source.read_bytes()).hexdigest(),promptText='こんにちは',language='ja',referenceCandidates=[])
   cfg=dict(voiceReferenceIdentityRevision=iv.IDENTITY_REVISION379,storage=str(root),ffmpeg=shutil.which('ffmpeg'),ttsBackend='drama3')
   def run(args):return subprocess.check_output([str(x) for x in args],stderr=subprocess.PIPE)
   prepared=engine_reference.prepare(cfg,root,profile,run);target=Path(prepared['reference']);data=target.read_bytes();self.assertEqual(prepared['referenceSHA256'],hashlib.sha256(data).hexdigest())
   self.assertEqual(engine_reference.prepare(cfg,root,profile,run)['reference'],str(target))
   damaged=data[:-2]+bytes([data[-2]^1,data[-1]]);target.write_bytes(damaged)
   with self.assertRaisesRegex(ValueError,'Conditioned voice reference changed'):engine_reference.prepare(cfg,root,profile,run)
   self.assertEqual(target.read_bytes(),damaged)
 def test_legacy_policy_and_resumed_request_are_unchanged(self):
  self.assertFalse(iv.content_bound({}));self.assertFalse(iv.content_bound(dict(voiceReferenceIdentityRevision='unknown')))
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source=root/'fixture.mkv';source.write_bytes(b'isolated fixture');store=Store(root);store.add([source]);row=store.queue[0];path=store.submit(row);request=read(path);self.assertEqual(request['voiceReferenceIdentityRevision'],iv.IDENTITY_REVISION379)
   request.pop('voiceReferenceIdentityRevision');request['recoverySpentSeconds']=44;path.write_text(json.dumps(request));old=path.read_bytes();row['status']='paused';store.submit(row);self.assertEqual(path.read_bytes(),old)
if __name__=='__main__':unittest.main()
