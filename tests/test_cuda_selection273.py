"""Compare real deployment planning with the native host selection boundary."""
import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows')]
import native_setup,drama_full_cuda as cuda
class Selection273(unittest.TestCase):
 def hardware(self):return dict(platform='windows',architecture='x86_64',backend='cuda',memoryGB=32,acceleratorMemoryGB=16,acceleratorName='NVIDIA GeForce RTX 4090 Laptop GPU',cudaComputeCapability=8.9,cudaDriverVersion='617.42',selectedTorchIndex='cu130')
 def test_raw_setup_hardware_and_enriched_plan_select_the_same_cuda13(self):
  with tempfile.TemporaryDirectory() as d,patch.object(native_setup,'data_root',return_value=Path(d)):
   h=self.hardware();plan=native_setup.plan(hardware=h,drama_backend='cuda');self.assertEqual(plan['tools'][0]['id'],'drama-full-cuda13')
   selected=[]
   with patch.object(cuda,'prepare',side_effect=lambda root,hardware,*args:selected.append(cuda.cuda_version(hardware))),patch.object(native_setup,'call'):
    backend,reason=cuda.checked_deployment(Path(d),h,plan['voiceMemory'],'worker','cuda',Mock())
   self.assertEqual(backend,'cuda');self.assertEqual(selected,['13']);self.assertEqual(plan['tools'][0]['id'],'drama-full-cuda'+selected[0])
 def test_manual_versions_keep_the_same_selection_in_presets_and_probes(self):
  with tempfile.TemporaryDirectory() as d,patch.object(native_setup,'data_root',return_value=Path(d)):
   for version in ['12','13']:
    plan=native_setup.plan(hardware=self.hardware(),drama_backend='cuda'+version)
    self.assertEqual(plan['dramaBackend'],'cuda'+version);self.assertEqual(plan['hardware']['nativeDramaRuntimeVersion'],version);self.assertEqual(plan['tools'][0]['id'],'drama-full-cuda'+version)
    for row in plan['qualityPresets']:
     if row['plan'].get('voiceBackend')=='cuda':self.assertEqual(row['plan']['dramaBackend'],'cuda'+version)
 def test_manual_cuda13_failure_does_not_silently_test_cuda12(self):
  with tempfile.TemporaryDirectory() as d:
   h=dict(self.hardware(),nativeDramaRuntimeVersion='13');selected=[]
   def fail(root,hardware,*args):selected.append(cuda.cuda_version(hardware));raise RuntimeError('fixture failure')
   with patch.object(cuda,'prepare',side_effect=fail),patch.object(native_setup,'call') as cpu:
    backend,reason=cuda.checked_deployment(Path(d),h,{},'worker','cuda',Mock())
   self.assertEqual(selected,['13']);self.assertEqual(backend,'cpu');self.assertIn('fixture failure',reason);self.assertEqual(cpu.call_args.args[0][-1],'cpu')
 def test_incompatible_generation_is_refused(self):
  for version,cc,name in [('12',12.0,'RTX 5090'),('13',6.1,'GTX 1080')]:
   with self.assertRaises(ValueError):native_setup.plan(hardware=dict(self.hardware(),cudaComputeCapability=cc,acceleratorName=name),drama_backend='cuda'+version)
if __name__=='__main__':unittest.main()
