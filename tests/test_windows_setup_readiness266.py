"""Verified deployment survives recommendation drift without weakening setup gates."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'windows'),str(R/'Resources')]
import native_setup as setup,drama_full_cuda as cuda
from setup_readiness import status

class WindowsReadinessTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.hw=dict(platform='windows',architecture='x86_64',nativeWorkflowVersion=1,backend='cuda',memoryGB=32,acceleratorMemoryGB=16,acceleratorName='NVIDIA GeForce RTX 4090 Laptop GPU',cudaComputeCapability=8.9)
  for obj,name,value in [(setup,'data_root',self.root),(setup,'available',True),(cuda,'ready',True)]:
   p=patch.object(obj,name,return_value=value);p.start();self.addCleanup(p.stop)
  p=patch('setup_inventory.inventory',return_value=[]);p.start();self.addCleanup(p.stop)
  p=patch.object(cuda,'components',return_value=[dict(id='checked-cuda-fixture',installed=True,bytes=1)]);p.start();self.addCleanup(p.stop)
 def commit(self,plan):
  roles=copy.deepcopy(plan['roles']);roles['drama3']=roles['voice']
  ready=dict(engine=plan['engine'],voiceBackend=plan['voiceBackend'],roles=roles,modelLoadPassed=True,speechInferencePassed=True)
  for name,row in [('model-selections.json',roles),('native-ready.json',ready),('drama3-windows-ready.json',dict(variant=roles['voice'],backend=plan['voiceBackend'],modelLoadPassed=True,speechInferencePassed=True))]:
   (self.root/name).write_text(json.dumps(row))
  return ready
 def test_optional_visual_added_after_restart_keeps_verified_deployment(self):
  original=setup.plan(hardware=dict(self.hw,acceleratorFreeMemoryGB=8),drama_backend='cpu');self.assertIsNone(original['roles']['visual']);self.commit(original)
  result=setup.plan(hardware=self.hw,drama_backend='cpu');self.assertTrue(result['setupReady']);self.assertIsNone(result['roles']['visual']);self.assertEqual(result['roleAnalysisMode'],'audio')
 def test_automatic_cpu_setup_does_not_turn_into_unverified_cuda_after_restart(self):
  original=setup.plan(hardware=dict(self.hw,acceleratorFreeMemoryGB=8));self.assertEqual(original['voiceBackend'],'cpu');self.commit(original)
  result=setup.plan(hardware=self.hw);self.assertTrue(result['setupReady']);self.assertEqual(result['voiceBackend'],'cpu');self.assertEqual(result['tools'],[])
 def test_explicit_cuda_change_still_requires_setup(self):
  original=setup.plan(hardware=self.hw,drama_backend='cpu');self.commit(original)
  result=setup.plan(hardware=self.hw,drama_backend='cuda');self.assertFalse(result['setupReady']);self.assertIn('backend-changed',result['setupStatus']['reasons'])
 def test_completed_cuda_still_needs_cuda_validation(self):
  original=setup.plan(hardware=self.hw,drama_backend='cuda');self.commit(original)
  with patch.object(cuda,'ready',return_value=False):result=setup.plan(hardware=self.hw,drama_backend='cuda')
  self.assertFalse(result['setupReady']);self.assertIn('cuda-verification-required',result['setupStatus']['reasons'])
 def test_downloaded_models_without_speech_probe_are_not_ready(self):
  result=setup.plan(hardware=self.hw);self.assertEqual(result['modelDownloadBytes'],0);self.assertFalse(result['setupReady']);self.assertIn('verification-required',result['setupStatus']['reasons']);self.assertTrue(result['setupStatus']['filesPresent'])
 def test_new_model_selection_does_not_reuse_old_verification(self):
  original=setup.plan(hardware=self.hw,drama_backend='cpu');self.commit(original)
  altered=copy.deepcopy(original);altered['roles']['speech']='another-speech-model'
  self.assertIn('selection-changed',status(altered,json.loads((self.root/'native-ready.json').read_text()))['reasons'])
 def test_missing_files_invalidated_setup_and_failed_probes_stay_blocked(self):
  original=setup.plan(hardware=self.hw,drama_backend='cpu');ready=self.commit(original)
  for kind in ['model','tool','invalidated','speech']:
   with self.subTest(kind=kind):
    plan=copy.deepcopy(original);record=copy.deepcopy(ready)
    if kind=='model':plan['downloads'][0]['installed']=False
    if kind=='tool':plan['tools']=[dict(installed=False)]
    if kind=='speech':record['speechInferencePassed']=False
    self.assertFalse(status(plan,record,kind=='invalidated')['ready'])

if __name__=='__main__':unittest.main()
