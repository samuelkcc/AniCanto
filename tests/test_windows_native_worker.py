import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'windows'))
import native_worker

class NativeWorkerTests(unittest.TestCase):
 def fixture(self,root):
  package=root/'package';(package/'tools').mkdir(parents=True);(package/'tools/AniCanto-helper.exe').touch()
  for name in ['ffmpeg.exe','ffprobe.exe']:(root/name).touch()
  ready=dict(modelLoadPassed=True,speechInferencePassed=True,backend='nvidia',ffmpeg=str(root/'ffmpeg.exe'),ffprobe=str(root/'ffprobe.exe'),textModel='qwen3.5:9b-canto-pinned',roles=dict(asr='asr-native-1.7b',speech='whisper-large-v3',referenceSpeech='whisper-small',vision='qwen3.5:9b'))
  return package,ready
 def test_native_projection_preserves_submission_and_expert_device(self):
  with tempfile.TemporaryDirectory() as name:
   root=Path(name);package,ready=self.fixture(root)
   original=dict(storage=str(root),model='mlx:qwen3.5-35b-a3b:4bit',selectedEngines=['gpt-sovits-v2'],gsvDevice='cpu',voiceProfiles=[dict(id='actor',reference='original.wav')])
   before=copy.deepcopy(original);cfg=native_worker.configure(original,ready,package)
   self.assertEqual(original,before)
   self.assertEqual(cfg['model'],ready['textModel']);self.assertEqual(cfg['visualModel'],ready['textModel'])
   self.assertEqual(cfg['gsvDevice'],'cpu');self.assertEqual(cfg['gsvVersion'],'v2ProPlus')
   self.assertEqual(cfg['asrModel'],'asr-native-1.7b');self.assertEqual(cfg['referenceSpeechModel'],'whisper-small')
   self.assertEqual(cfg['voiceProfiles'],before['voiceProfiles'])
 def test_drama_gpu_fallback_is_visible_and_resolved_before_shared_plan(self):
  with tempfile.TemporaryDirectory() as name:
   root=Path(name);package,ready=self.fixture(root)
   (root/'gpt-windows-ready.json').write_text(json.dumps(dict(modelLoadPassed=True,modelVersions=['v4'])))
   cfg=native_worker.configure(dict(storage=str(root),selectedEngines=['drama3'],ttsBackend='drama3'),ready,package)
   self.assertEqual(cfg['requestedEngines'],['drama3']);self.assertEqual(cfg['selectedEngines'],['gpt-sovits'])
   self.assertEqual(cfg['ttsBackend'],'gpt-sovits');self.assertEqual(cfg['defaultAudioEngine'],'gpt-sovits')
   self.assertEqual(cfg['nativeEngineFallback']['selected'],'gpt-sovits')
 def test_unprobed_setup_and_missing_helper_cannot_be_reported_ready(self):
  with tempfile.TemporaryDirectory() as name:
   root=Path(name);package,ready=self.fixture(root)
   with self.assertRaisesRegex(ValueError,'probes'):native_worker.configure(dict(storage=str(root)),dict(ready,speechInferencePassed=False),package)
   (package/'tools/AniCanto-helper.exe').unlink()
   with self.assertRaisesRegex(ValueError,'helper'):native_worker.configure(dict(storage=str(root)),ready,package)
 def test_explicit_native_model_and_cpu_drama_selection_are_retained(self):
  with tempfile.TemporaryDirectory() as name:
   root=Path(name);package,ready=self.fixture(root);ready['allowDramaCPU']=True
   cfg=native_worker.configure(dict(storage=str(root),selectedEngines=['drama3'],model='qwen3.5:4b-canto-pinned',voxcpmDevice='cpu'),ready,package)
   self.assertEqual(cfg['selectedEngines'],['drama3']);self.assertEqual(cfg['model'],'qwen3.5:4b-canto-pinned')
   self.assertTrue(cfg['nativeDramaCPU']);self.assertEqual(cfg['voxcpmDevice'],'cpu')
 def test_batch_uses_staged_remote_video_instead_of_overwriting_submitted_source(self):
  with tempfile.TemporaryDirectory() as name:
   root=Path(name);package,ready=self.fixture(root)
   original=str(root/'episode.mkv');staged=root/'cache'/'episode.mkv';staged.parent.mkdir();staged.touch()
   submitted=dict(storage=str(root),video=original,videos=[dict(id='one',video=original)],selectedEngines=['gpt-sovits-v2'])
   before=copy.deepcopy(submitted)
   with patch('source_access.cloud_or_remote',return_value=True),patch('source_access.accessible',return_value=(staged,b'{}')):
    cfg=native_worker.configure(submitted,ready,package)
   self.assertEqual(submitted,before)
   self.assertEqual(cfg['video'],str(staged))
   self.assertEqual(cfg['videos'][0]['video'],str(staged))
   self.assertEqual(cfg['videos'][0]['sourceMediaOriginal'],original)

if __name__=='__main__':unittest.main()
