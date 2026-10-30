"""Full Q2 CUDA deployment contracts; actual Windows GPU inference is separate."""
import hashlib,json,os,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows')]
import drama_full_cuda as cuda,native_setup,native_models,drama_gguf,studio_core
from memory_plan import pools

class FullDramaCUDA(unittest.TestCase):
 def hardware(self,backend='cuda',vram=16):
  return dict(platform='windows',architecture='x86_64',memoryGB=32,backend=backend,acceleratorMemoryGB=vram,nativeWorkflowVersion=1,acceleratorName='NVIDIA GeForce RTX 4080 Laptop GPU',nativeDramaCUDA=True)
 def verified(self,root,version='12'):
  catalog=json.loads((ROOT/'windows/native-tools.json').read_text())
  for key in ('drama-full-cuda'+version,'drama-full-cudart'+version):
   directory=root/'tools'/key;directory.mkdir(parents=True);files={}
   for name in catalog[key]['requiredFiles']:
    p=directory/name;p.write_bytes(('verified-'+name).encode());files[name]=dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
   (directory/'verified.json').write_text(json.dumps(dict(sha256=catalog[key]['sha256'],files=files)))
  memory=dict(backend='cuda',systemGB=22,gpuGB=12,cpuExpertLayers=16,contextLength=2048,policy='full-drama-q2-split-1')
  record=dict(runtimeTool='drama-full-cuda'+version,cudartTool='drama-full-cudart'+version,cudaVersion=version,deviceProbePassed=True,speechInferencePassed=True,memory=memory)
  (root/cuda.MARKER).write_text(json.dumps(record));return record
 def test_real_planner_nvidia_uses_complete_q2_in_both_memory_pools(self):
  for vram,gpu,layers in [(16,12,16),(24,18,0)]:
   with self.subTest(vram=vram):
    p=studio_core.call('deployment',hardware=self.hardware(vram=vram),models=native_setup.catalog(),engine='drama3',dramaBackend='auto',singleModelPerCategory=True)
    self.assertEqual(p['roles']['voice'],'drama3-native-q2');self.assertEqual(p['voiceBackend'],'cuda')
    self.assertEqual(p['voiceMemory']['cpuExpertLayers'],layers)
    memory=pools(p);self.assertEqual(memory['system']['peak'],22);self.assertEqual(memory['gpu']['peak'],gpu)
    self.assertTrue(next(q for q in p['qualityPresets'] if q['id']=='quality')['available'])
    self.assertNotIn('drama3-small-iq3',json.dumps(p))
 def test_usable_ram_and_vram_below_nominal_size_keep_the_correct_tier(self):
  h=self.hardware();h.update(memoryGB=31.7,acceleratorMemoryGB=15.99)
  p=studio_core.call('deployment',hardware=h,models=native_setup.catalog(),engine='drama3',dramaBackend='auto')
  self.assertEqual(p['engine'],'drama3');self.assertEqual(p['voiceMemory']['cpuExpertLayers'],16)
  self.assertEqual(p['voiceMemory']['gpuGB'],12);self.assertTrue(p['qualityPresets'][0]['available'])
  h.update(memoryGB=29.9)
  p=studio_core.call('deployment',hardware=h,models=native_setup.catalog(),engine='drama3',dramaBackend='auto')
  self.assertFalse(p['qualityPresets'][0]['available'])
 def test_amd_igpu_and_explicit_cpu_do_not_download_cuda(self):
  with tempfile.TemporaryDirectory() as d,patch.object(native_setup,'data_root',return_value=Path(d)):
   for backend,preference in [('rocm','auto'),('cpu','auto'),('cuda','cpu')]:
    with self.subTest(backend=backend):
     p=native_setup.plan('drama3',hardware=self.hardware(backend),drama_backend=preference)
     self.assertEqual(p['voiceBackend'],'cpu');self.assertEqual(p['tools'],[]);self.assertEqual(p['toolDownloadBytes'],0)
     self.assertEqual(p['voiceMemory']['gpuGB'],0)
   with self.assertRaisesRegex(ValueError,'requires-nvidia'):
    native_setup.plan('drama3',hardware=self.hardware('rocm'),drama_backend='cuda')
 def test_templates_include_the_cuda_tools_and_reuse_installed_model_weights(self):
  with tempfile.TemporaryDirectory() as d,patch.object(native_setup,'data_root',return_value=Path(d)),patch.object(native_setup,'available',return_value=True):
   p=native_setup.plan('drama3',hardware=self.hardware(),drama_backend='cuda')
   self.assertEqual(p['modelDownloadBytes'],0);self.assertGreater(p['toolDownloadBytes'],1_000_000_000)
   self.assertEqual(p['totalDownloadBytes'],p['toolDownloadBytes'])
   self.assertEqual([t['id'] for t in p['tools']],['drama-full-cuda12','drama-full-cudart12'])
   quality=next(q for q in p['qualityPresets'] if q['id']=='quality')['plan']
   self.assertEqual(quality['tools'],p['tools']);self.assertEqual(quality['memoryPools']['system']['peak'],22)
   self.assertFalse(p['setupReady'])
 def test_verified_cuda12_remains_ready_when_torch_prefers_cuda13(self):
  import copy
  with tempfile.TemporaryDirectory() as d,patch.object(native_setup,'data_root',return_value=Path(d)),patch.object(native_setup,'available',return_value=True):
   root=Path(d);self.verified(root)
   h=dict(self.hardware(),acceleratorName='NVIDIA GeForce RTX 4090 Laptop GPU',cudaComputeCapability=8.9,selectedTorchIndex='cu130',cudaDriverVersion='617.42',gpuRuntime=dict(torchIndex='cu130'))
   first=native_setup.plan('drama3',hardware=h,drama_backend='cuda')
   roles=copy.deepcopy(first['roles'])
   (root/'model-selections.json').write_text(json.dumps(roles))
   (root/'native-ready.json').write_text(json.dumps(dict(engine='drama3',voiceBackend='cuda',roles=roles,modelLoadPassed=True,speechInferencePassed=True)))
   again=native_setup.plan('drama3',hardware=h,drama_backend='cuda')
   self.assertEqual([t['id'] for t in again['tools']],['drama-full-cuda12','drama-full-cudart12'])
   self.assertEqual(again['toolDownloadBytes'],0);self.assertTrue(again['setupReady'],again['setupStatus'])
   (root/'tools/drama-full-cuda12/ggml-cuda.dll').write_bytes(b'broken')
   broken=native_setup.plan('drama3',hardware=h,drama_backend='cuda')
   self.assertFalse(broken['setupReady']);self.assertIn('cuda-verification-required',broken['setupStatus']['reasons'])
 def test_old_cuda12_is_not_reused_for_blackwell_or_failed_speech(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);record=self.verified(root)
   h=dict(self.hardware(),acceleratorName='NVIDIA GeForce RTX 5090',cudaComputeCapability=12.0,gpuRuntime=dict(torchIndex='cu130'))
   self.assertEqual(cuda.components(root,h)[0]['id'],'drama-full-cuda13')
   record['speechInferencePassed']=False;(root/cuda.MARKER).write_text(json.dumps(record))
   h.update(acceleratorName='NVIDIA GeForce RTX 4090',cudaComputeCapability=8.9)
   self.assertEqual(cuda.components(root,h)[0]['id'],'drama-full-cuda13')
 def test_cuda_major_matches_gpu_generation(self):
  self.assertEqual(cuda.cuda_version(self.hardware()),'12')
  for name in ['NVIDIA GeForce RTX 5090','NVIDIA RTX PRO 6000 Blackwell','NVIDIA B200']:
   self.assertEqual(cuda.cuda_version(dict(acceleratorName=name)),'13')
 def test_cuda_device_check_is_not_a_speech_pass_and_cpu_only_is_rejected(self):
  for gpu in (True,False):
   with self.subTest(gpu=gpu),tempfile.TemporaryDirectory() as d:
    root=Path(d);record=self.verified(root)
    with patch.object(native_setup,'tool',side_effect=lambda key:root/'tools'/key),patch.object(cuda.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='CUDA:0 "NVIDIA GPU" [gpu]' if gpu else 'CPU:0 "CPU" [cpu]',stderr='')):
     if gpu:
      cuda.prepare(root,self.hardware(),record['memory'],Mock())
      self.assertTrue(cuda.ready(root));self.assertFalse(cuda.ready(root,require_speech=True))
     else:
      with self.assertRaisesRegex(RuntimeError,'CUDA device check failed'):cuda.prepare(root,self.hardware(),record['memory'],Mock())
      self.assertFalse((root/cuda.MARKER).exists())
 def test_tamper_and_mixed_runtime_cannot_pass_validation(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);record=self.verified(root);self.assertTrue(cuda.ready(root))
   dll=root/'tools/drama-full-cuda12/ggml-cuda.dll';original=dll.read_bytes();dll.write_bytes(b'x'*len(original));self.assertFalse(cuda.ready(root))
   dll.write_bytes(original);record['cudaVersion']='13';(root/cuda.MARKER).write_text(json.dumps(record));self.assertFalse(cuda.ready(root))
 def test_production_recovery_keeps_full_cuda_instead_of_legacy_gpt_fallback(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);record=self.verified(root)
   (root/'drama3-windows-ready.json').write_text(json.dumps(dict(variant='drama3-native-q2',backend='cuda',modelLoadPassed=True,speechInferencePassed=True,memory=record['memory'])))
   cfg=dict(storage=d,selectedEngines=['drama3'],ttsBackend='drama3',nativeDramaCPU=True)
   native_models.recover(cfg,Mock());self.assertEqual(cfg['drama3Backend'],'cuda');self.assertFalse(cfg['nativeDramaCPU']);self.assertEqual(cfg['selectedEngines'],['drama3']);self.assertEqual(cfg['nativeDramaFormat'],'gguf-cuda')
   self.assertEqual(native_models.missing_setup(root,['drama3']),[])
   (root/'tools/drama-full-cudart12/cudart64_12.dll').unlink()
   with self.assertRaisesRegex(ValueError,'needs repair'):native_models.recover(cfg,Mock())
   self.assertEqual(native_models.missing_setup(root,['drama3']),['drama3'])
 def test_actual_server_configuration_uses_full_host_and_cpu_expert_split(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);record=self.verified(root);model_folder=root/'weights';model_folder.mkdir()
   (model_folder/'drama-3-backbone-8bit-experts-Q2_K.gguf').touch()
   process=Mock(poll=Mock(return_value=None));response=Mock();response.__enter__=Mock(return_value=SimpleNamespace(status=200));response.__exit__=Mock(return_value=False)
   with patch('voice_models.resolve',return_value=model_folder),patch.object(drama_gguf.sys,'platform','win32'),patch.object(drama_gguf.subprocess,'Popen',return_value=process) as popen,patch.object(drama_gguf.urllib.request,'urlopen',return_value=response):
    model=drama_gguf.NativeDrama(dict(storage=d,job=str(root/'job'),drama3Model='drama3-native-q2',drama3Backend='cuda'))
    model.close()
   args=popen.call_args;self.assertEqual(Path(args.args[0][0]),root/'tools/drama-full-cuda12/audiocpp_server.exe')
   settings=json.loads((root/'job/native-drama-server.json').read_text());voice=settings['models'][0]
   self.assertEqual(settings['backend'],'cuda');self.assertEqual(voice['family'],'fish_drama3');self.assertEqual(voice['session_options']['fish_drama3.cpu_expert_layers'],16)
   self.assertEqual(voice['session_options']['fish_drama3.context_length'],2048)
   self.assertIn(str(root/'tools/drama-full-cudart12'),args.kwargs['env']['PATH'])
 def test_failed_setup_restores_previous_cpu_receipts_and_choices(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);old={'native-ready.json':dict(voiceBackend='cpu',speechInferencePassed=True),'drama3-windows-ready.json':dict(variant='drama3-native-q2',backend='cpu'),'model-selections.json':dict(voice='drama3-native-q2')}
   for name,value in old.items():(root/name).write_text(json.dumps(value))
   def failure(*args):
    for name in old:(root/name).write_text('{}')
    (root/cuda.MARKER).write_text('{}');raise RuntimeError('CUDA speech probe failed')
   with patch.object(native_setup,'data_root',return_value=root),patch.object(native_setup,'_setup',side_effect=failure):
    with self.assertRaisesRegex(RuntimeError,'CUDA speech probe'):native_setup.setup(drama_backend='cuda')
   for name,value in old.items():self.assertEqual(json.loads((root/name).read_text()),value)
   self.assertFalse((root/cuda.MARKER).exists())
 def test_removing_optional_cuda_keeps_weights_and_working_cpu(self):
  import setup_inventory
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.verified(root);weights=root/'existing-q2.gguf';weights.write_bytes(b'preserved')
   cpu=root/'drama3-windows-ready.json';cpu.write_text(json.dumps(dict(backend='cpu')))
   setup_inventory.remove(root,'tool','drama-full-cuda12',[])
   self.assertTrue(cpu.exists());self.assertEqual(weights.read_bytes(),b'preserved');self.assertFalse((root/'setup-invalidated.json').exists())

if __name__=='__main__':unittest.main()
