import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'studio'),str(ROOT/'windows'),str(ROOT/'Resources')]
from backend import Studio
from desktop_state import write,read
from editing_tools import alignment,impact,coverage,boundaries,boundary_token,apply_boundary,waveform
from native_queue import dispatch as queue_dispatch

class DesktopImprovements(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  self.app=Studio(self.root,ROOT/'Resources',platform='darwin')
  self.app.store.queue=[dict(id=k,video=str(self.root/(k+'.mkv')),status=s) for k,s in [('a','running'),('b','complete'),('c','paused'),('d','waiting')]]
  self.app.store.selected='a';self.app.store.save()
 def test_bulk_remove_retains_every_file_and_running_selection(self):
  work=self.root/'jobs'/'b';work.mkdir(parents=True);audio=work/'voice.wav';audio.write_bytes(b'keep')
  result=self.app.dispatch('remove-videos',dict(ids=['b','c']))
  self.assertEqual([r['id'] for r in result['state']['queue']],['a','d']);self.assertEqual(result['state']['selected'],'a');self.assertEqual(audio.read_bytes(),b'keep')
  self.app.dispatch('restore-videos',dict(batch=result['batch']));self.app.dispatch('restore-videos',dict(batch=result['batch']))
  self.assertEqual(len(self.app.store.queue),4)
 def test_bulk_invalid_or_running_selection_is_atomic(self):
  before=self.app.store.path.read_bytes()
  for ids in [['a','b'],['b','gone'],['b','b'],[],['b',1]]:
   with self.assertRaises(ValueError):self.app.dispatch('remove-videos',dict(ids=ids))
   self.assertEqual(before,self.app.store.path.read_bytes())
 def test_native_queue_reserves_before_prepare_respects_reorder_and_ignores_complete(self):
  queue_dispatch(self.app,'queue-arm',dict(epoch=5,id='a'));self.app.store.queue[0]['status']='complete'
  self.app.store.queue=[self.app.store.queue[i] for i in [0,3,2,1]]
  seen=[]
  def call(op,p):
   seen.append((op,p['id']))
   ledger=read(self.root/'studio'/'queue-session.json',{});self.assertIn(p['id'],ledger['attempted'])
   return dict(needsConfirmation=False) if op=='source-language' else dict(rowID=p['id'],action='batch')
  self.app.dispatch=call
  spec=queue_dispatch(self.app,'queue-next',dict(epoch=5));self.assertEqual(spec['rowID'],'d');self.assertEqual(spec['nativeQueue'],5)
  self.assertEqual(seen,[('source-language','d'),('start','d')])
  self.assertIsNone(queue_dispatch(self.app,'queue-next',dict(epoch=4)))
 def test_native_queue_confirmation_does_not_block_other_ready_video(self):
  queue_dispatch(self.app,'queue-arm',dict(epoch=1,id='a'));self.app.store.queue[0]['status']='complete';self.app.store.queue[2]['status']='waiting'
  def call(op,p):return dict(needsConfirmation=p['id']=='c') if op=='source-language' else dict(rowID=p['id'])
  self.app.dispatch=call;spec=queue_dispatch(self.app,'queue-next',dict(epoch=1));self.assertEqual(spec['rowID'],'d');self.assertIn('Confirm',self.app.store.queue[2]['queueNotice'])
  queue_dispatch(self.app,'queue-stop',{});self.assertIsNone(queue_dispatch(self.app,'queue-next',dict(epoch=1)))
 def test_offset_and_drift_preserve_original_timing(self):
  source=[dict(start=10,end=12,text='one'),dict(start=100,end=102,text='two')];before=copy.deepcopy(source)
  result=alignment(source,dict(mode='anchors',subtitle1=10,video1=12,subtitle2=100,video2=111))
  self.assertAlmostEqual(result['scale'],1.1);self.assertEqual(result['cues'][0]['start'],12);self.assertEqual(result['cues'][1]['start'],111);self.assertEqual(source,before)
  for params in [dict(offset=-20),dict(offset=float('nan')),dict(mode='anchors',subtitle1=1,video1=3,subtitle2=1,video2=4)]:
   with self.assertRaises(ValueError):alignment(source,params)
 def fixture(self):
  review=dict(cues=[dict(start=0,end=4,speakerId='r')]);analysis=dict(segments=[dict(words=[dict(start=0,end=1,word='A',probability=.9),dict(start=2,end=4,word='B',probability=.9)])]);draft=dict(segments=[dict(id='a',sources=[0],start=0,end=4,original='AB',text='甲乙',enabled=True)],settings=dict(dubLanguages=['yue'],selectedEngines=['drama3']))
  return review,analysis,draft
 def test_boundary_requires_real_word_times_and_explicit_scripts(self):
  review,analysis,draft=self.fixture();self.assertEqual(boundaries(review,{}),[])
  proposals=boundaries(review,analysis);self.assertEqual(proposals[0]['seconds'],2)
  params=dict(proposalIndex=0,token=boundary_token(review,analysis,draft),parts=dict(original=dict(left='A',right='B'),text=dict(left='甲',right='乙')))
  result=apply_boundary(review,analysis,draft,params);self.assertEqual([x['end'] for x in result['segments']],[2,4]);self.assertEqual(draft['segments'][0]['text'],'甲乙')
  changed=copy.deepcopy(draft);changed['segments'][0]['text']='changed'
  with self.assertRaises(ValueError):apply_boundary(review,analysis,changed,params)
  params['parts'].pop('text')
  with self.assertRaises(ValueError):apply_boundary(review,analysis,draft,params)
 def test_impact_read_only_and_sensitive_to_changes(self):
  review,_,draft=self.fixture();before=copy.deepcopy(draft);params=dict(operation='all',engine='drama3',language='yue')
  one=impact(review,draft,params);self.assertEqual(one['dialogueCount'],1);self.assertEqual(draft,before);self.assertTrue(one['retainsPreviousRecordings'])
  draft['settings']['dramaTemperature']=.5;self.assertNotEqual(impact(review,draft,params)['token'],one['token'])
 def test_coverage_does_not_call_missing_files_quality_pass(self):
  review,_,_=self.fixture();review['config']=dict(selectedEngines=['drama3'],dubLanguages=['yue'])
  result=coverage(dict(review=review,takes=[dict(index=1,engine='drama3',language='yue',audio=str(self.root/'missing.wav'))]));self.assertEqual(result['tracks'][0]['missing'],[1]);self.assertFalse(result['qualityCertified'])
 def test_waveform_measures_real_audio_and_caches_without_model(self):
  import math,struct,wave
  file=self.root/'sample.wav'
  with wave.open(str(file),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(8000);w.writeframes(b''.join(struct.pack('<h',round(10000*math.sin(n*.2))) for n in range(8000)))
  result=waveform(file,0,1,'/opt/homebrew/bin/ffmpeg',self.root/'peaks');self.assertGreater(result['peak'],.1);self.assertLessEqual(len(result['peaks']),1000);self.assertEqual(result,waveform(file,0,1,'not-run-on-cache',self.root/'peaks'))
  with self.assertRaises(ValueError):waveform(file,0,181,'not-run',self.root/'peaks')

class HardwareRecommendationTests(unittest.TestCase):
 def plan(self,name,ram,vram,backend='cuda'):
  import native_setup,studio_core
  h=dict(platform='windows',architecture='x86_64',nativeWorkflowVersion=1,backend=backend,memoryGB=ram,acceleratorMemoryGB=vram,acceleratorName=name,nativeDramaCUDA=True)
  return studio_core.call('deployment',hardware=h,models=native_setup.catalog(),engine='drama3',installedModels=[],selectedModels={},requestedModels={},dramaBackend='auto')
 def test_gtx1080_does_not_recommend_incompatible_cuda_wheel(self):
  p=self.plan('NVIDIA GeForce GTX 1080',32,8);self.assertEqual(p['hardware']['backend'],'cuda');self.assertEqual(p['hardware']['torchIndex'],'cu126');self.assertEqual(p['recommendedPreset'],'quality')
  chosen=next(x for x in p['qualityPresets'] if x['id']==p['recommendedPreset']);self.assertTrue(chosen['available']);self.assertEqual(chosen['plan']['voiceBackend'],'cuda');self.assertGreater(chosen['plan']['systemMemoryBudgetGB'],0)
 def test_supported_large_gpu_retains_quality_and_cpu_choice(self):
  p=self.plan('NVIDIA GeForce RTX 4090',32,24);self.assertEqual(p['hardware']['backend'],'cuda');self.assertEqual(p['recommendedPreset'],'quality');self.assertTrue(any(x['id']=='balanced-cpu' and x['available'] for x in p['qualityPresets']))
 def test_4gb_gpu_offers_real_system_memory_fallback(self):
  p=self.plan('NVIDIA GeForce RTX 3050',32,4);recommended=next(x for x in p['qualityPresets'] if x['id']==p['recommendedPreset']);self.assertEqual(recommended['plan']['voiceBackend'],'cpu');self.assertTrue(recommended['available'])
 def test_amd_igpu_cpu_advice_never_counts_shared_memory_as_vram(self):
  p=self.plan('Intel integrated graphics',32,0,'cpu');chosen=next(x for x in p['qualityPresets'] if x['id']==p['recommendedPreset']);self.assertEqual(chosen['plan']['setupBackend'],'cpu');self.assertEqual(chosen['plan']['acceleratorMemoryBudgetGB'],0)

 def test_each_nvidia_generation_selects_an_architecture_compatible_profile(self):
  from hardware_runtimes import nvidia,amd_supported
  for name,index in [('NVIDIA GeForce GTX 1080','cu126'),('RTX 2080 Ti','cu128'),('RTX 3070','cu128'),('RTX 4080','cu128'),('RTX 5090','cu128')]:
   with self.subTest(name=name):self.assertEqual(nvidia(name)['torchIndex'],index)
  self.assertEqual(nvidia('unknown GPU')['torchIndex'],'cpu');self.assertEqual(nvidia('Laptop GPU',6.1)['torchIndex'],'cu126')
  self.assertTrue(amd_supported('AMD Radeon RX 9070 XT'));self.assertTrue(amd_supported('AMD Radeon RX 7900 XTX'))
  self.assertFalse(amd_supported('AMD Radeon RX 7900 XT'));self.assertFalse(amd_supported('AMD Radeon RX 6800 XT'))
 def test_unsupported_rdna_does_not_claim_rocm_support(self):
  p=self.plan('AMD Radeon RX 6800 XT',32,16,'rocm');self.assertEqual(p['hardware']['backend'],'cpu');self.assertIn('outside',p['hardware']['gpuCompatibilityReason'])
 def test_torch_install_requests_the_selected_legacy_wheel(self):
  import install
  with patch.object(install,'call') as call,patch.object(install,'data_root',return_value=Path('/tmp/fixture')):
   install.install_torch(Path('/tmp/fixture/runtime/python.exe'),'nvidia',cuda_index='cu126')
  args=call.call_args.args[0];self.assertIn('https://download.pytorch.org/whl/cu126',args);self.assertIn('torch==2.9.1',args)

class RuntimeFallbackTests(unittest.TestCase):
 def test_failed_gpu_kernel_retries_once_on_cpu_before_model_download(self):
  import native_setup,types
  class Planned(Exception):pass
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory)
   with patch.object(native_setup.sys,'platform','win32'),patch.object(native_setup,'data_root',return_value=root),patch.object(native_setup,'environment',return_value=root/'python.exe') as environment,patch.object(native_setup,'probe_runtime',side_effect=[RuntimeError('no kernel image'),dict(backend='cpu',memoryGB=0,name='CPU')]) as probe,patch.object(native_setup,'hardware_snapshot',return_value={}),patch('gpu.planning_hardware',return_value=dict(acceleratorName='RTX 2080',cudaComputeCapability=7.5)),patch.object(native_setup,'emit'),patch.object(native_setup,'plan',side_effect=Planned) as plan:
    with self.assertRaises(Planned):native_setup._setup('drama3','nvidia')
   self.assertEqual([c.args for c in environment.call_args_list],[('worker',),('analysis','nvidia'),('analysis','cpu')]);self.assertEqual([c.args[1] for c in probe.call_args_list],['nvidia','cpu']);self.assertEqual(plan.call_args.args[1]['backend'],'cpu');self.assertEqual(plan.call_args.kwargs['drama_backend'],'cpu')
 def test_cpu_kernel_failure_is_not_retried_indefinitely(self):
  import native_setup
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory)
   with patch.object(native_setup.sys,'platform','win32'),patch.object(native_setup,'data_root',return_value=root),patch.object(native_setup,'environment',return_value=root/'python.exe'),patch.object(native_setup,'probe_runtime',side_effect=RuntimeError('CPU failed')) as probe,patch.object(native_setup,'emit'):
    with self.assertRaisesRegex(RuntimeError,'CPU failed'):native_setup._setup('drama3','cpu')
   self.assertEqual(probe.call_count,1)
 def test_loaded_torch_architecture_and_free_memory_are_checked_separately(self):
  import compute_policy,types
  cuda=Mock();cuda.is_available.return_value=True;cuda.mem_get_info.return_value=(8*1024**3,8*1024**3);cuda.get_device_capability.return_value=(6,1);cuda.get_arch_list.return_value=['sm_75','sm_86']
  torch=types.SimpleNamespace(cuda=cuda,version=types.SimpleNamespace(hip=None))
  with patch.object(compute_policy,'system_memory_gb',return_value=32):
   self.assertEqual(compute_policy.torch_device(torch,minimum_gb=4),'cpu');cuda.get_arch_list.return_value=['sm_61'];self.assertEqual(compute_policy.torch_device(torch,minimum_gb=4),'cuda:0');cuda.mem_get_info.return_value=(1*1024**3,8*1024**3);self.assertEqual(compute_policy.torch_device(torch,minimum_gb=4),'cpu')

class CUDA13SelectionTests(unittest.TestCase):
 def test_new_cards_and_driver_must_both_qualify(self):
  from hardware_runtimes import nvidia
  self.assertEqual(nvidia('RTX 4090',8.9,'580.97')['torchIndex'],'cu130')
  self.assertEqual(nvidia('RTX 5090',12.0,'581.10')['torchIndex'],'cu130')
  self.assertEqual(nvidia('RTX 4090',8.9,'570.65')['torchIndex'],'cu128')
  self.assertEqual(nvidia('RTX 5090',12.0,None)['torchIndex'],'cu128')
  self.assertEqual(nvidia('GTX 1080',6.1,'580.97')['torchIndex'],'cu126')
  self.assertEqual(nvidia('RTX 4090',8.9,'580.97','cu128')['torchIndex'],'cu128')
 def test_core_and_drama_follow_driver_qualified_profile(self):
  import native_setup,studio_core,drama_full_cuda
  h=dict(platform='windows',architecture='x86_64',nativeWorkflowVersion=1,nativeDramaCUDA=True,backend='cuda',memoryGB=32,acceleratorMemoryGB=24,acceleratorName='RTX 4090',cudaComputeCapability=8.9,cudaDriverVersion='580.97')
  p=studio_core.call('deployment',hardware=h,models=native_setup.catalog(),engine='drama3',installedModels=[],requestedModels={},dramaBackend='auto');self.assertEqual(p['hardware']['torchIndex'],'cu130');self.assertEqual(drama_full_cuda.cuda_version(p['hardware']),'13')
  h['cudaDriverVersion']='570.65';p=studio_core.call('deployment',hardware=h,models=native_setup.catalog(),engine='drama3',installedModels=[],requestedModels={},dramaBackend='auto');self.assertEqual(p['hardware']['torchIndex'],'cu128');self.assertEqual(drama_full_cuda.cuda_version(p['hardware']),'12')
 def test_gpu13_failure_tries_gpu12_before_cpu(self):
  import native_setup
  class Planned(Exception):pass
  h=dict(acceleratorName='RTX 4090',cudaComputeCapability=8.9,cudaDriverVersion='580.97')
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory)
   with patch.object(native_setup.sys,'platform','win32'),patch.object(native_setup,'data_root',return_value=root),patch.object(native_setup,'environment',return_value=root/'python.exe') as environment,patch.object(native_setup,'probe_runtime',side_effect=[RuntimeError('GPU13 failed'),dict(backend='cuda',memoryGB=24,name='RTX 4090')]) as probe,patch.object(native_setup,'hardware_snapshot',return_value={}),patch('gpu.planning_hardware',return_value=h),patch.object(native_setup,'emit'),patch.object(native_setup,'plan',side_effect=Planned) as plan:
    with self.assertRaises(Planned):native_setup._setup('drama3','nvidia')
   self.assertEqual(environment.call_args_list[-1].kwargs,dict(cuda_index='cu128'));self.assertEqual(plan.call_args.args[1]['backend'],'cuda');self.assertEqual(probe.call_count,2)

class FallbackPersistenceTests(unittest.TestCase):
 def test_failed_gpu_does_not_force_redeployment_and_new_driver_invalidates_cache(self):
  import gpu
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);(root/'gpu-runtime-selection.json').write_text(json.dumps(dict(name='RTX 4090',driver='580.97',torchIndex='cpu',kernelPassed=False)))
   h=dict(backend='cuda',acceleratorName='RTX 4090',cudaDriverVersion='580.97',acceleratorMemoryGB=24)
   with patch.object(gpu,'data_root',return_value=root):
    saved=gpu.apply_runtime_selection(copy.deepcopy(h));self.assertEqual(saved['backend'],'cpu');self.assertEqual(saved['acceleratorMemoryGB'],24)
    h['cudaDriverVersion']='581.10';self.assertEqual(gpu.apply_runtime_selection(h)['backend'],'cuda')

class NativeAttentionQueueTests(unittest.TestCase):
 def test_explicit_resume_all_retains_attention_intent_without_rechecking_source(self):
  with tempfile.TemporaryDirectory() as directory:
   app=Studio(Path(directory),ROOT/'Resources',platform='darwin');app.store.queue=[dict(id='a',status='attention',output='old-a.mp4',video='a.mkv'),dict(id='b',status='attention',output='old-b.mp4',video='b.mkv')];app.store.save()
   queue_dispatch(app,'queue-arm',dict(epoch=1,id='a',includeAttention=True));calls=[]
   def call(op,p):calls.append((op,p['id']));return dict(rowID=p['id'],action='render-project')
   app.dispatch=call;spec=queue_dispatch(app,'queue-next',dict(epoch=1));self.assertEqual(spec['rowID'],'b');self.assertEqual(calls,[('start','b')])
   queue_dispatch(app,'queue-arm',dict(epoch=2,id='a',includeAttention=False));self.assertIsNone(queue_dispatch(app,'queue-next',dict(epoch=2)))

class NativeDramaFallbackTests(unittest.TestCase):
 def test_native_prepare_failure_tries_12_after_13_for_ada(self):
  import drama_full_cuda,native_setup
  h=dict(acceleratorName='RTX 4090',cudaComputeCapability=8.9,gpuRuntime=dict(torchIndex='cu130'))
  with patch.object(drama_full_cuda,'prepare',side_effect=[RuntimeError('CUDA13 unavailable'),None]) as prepare,patch.object(native_setup,'call') as call:
   backend,reason=drama_full_cuda.checked_deployment(Path('/tmp/root'),h,{},Path('/tmp/python.exe'),'cuda',Mock())
  self.assertEqual(backend,'cuda');self.assertIn('CUDA13 unavailable',reason);self.assertEqual([drama_full_cuda.cuda_version(c.args[1]) for c in prepare.call_args_list],['13','12']);self.assertEqual(call.call_args.args[0][-1],'cuda')
 def test_blackwell_never_uses_incompatible_native_cuda12_bundle(self):
  import drama_full_cuda,native_setup
  h=dict(acceleratorName='RTX 5090',cudaComputeCapability=12.0,gpuRuntime=dict(torchIndex='cu130'))
  with patch.object(drama_full_cuda,'prepare',side_effect=RuntimeError('GPU unavailable')) as prepare,patch.object(native_setup,'call') as call:
   backend,reason=drama_full_cuda.checked_deployment(Path('/tmp/root'),h,{},Path('/tmp/python.exe'),'cuda',Mock())
  self.assertEqual(backend,'cpu');self.assertEqual(prepare.call_count,1);self.assertEqual(call.call_args.args[0][-1],'cpu')
 def test_cpu_load_failure_remains_failure(self):
  import drama_full_cuda,native_setup
  with patch.object(native_setup,'call',side_effect=RuntimeError('CPU model failed')) as call:
   with self.assertRaisesRegex(RuntimeError,'CPU model failed'):drama_full_cuda.checked_deployment(Path('/tmp/root'),{}, {},Path('/tmp/python.exe'),'cpu',Mock())
  self.assertEqual(call.call_count,1)

class UnknownMemoryReadingTests(unittest.TestCase):
 def test_unknown_free_vram_retains_a_bounded_estimate_and_zero_is_not_ignored(self):
  from memory_plan import pools
  plan=dict(hardware=dict(memoryGB=32,acceleratorMemoryGB=8,acceleratorFreeMemoryGB=None,backend='cuda'),roles=dict(asr='qwen'),downloads=[dict(id='qwen',estimatedMemoryGB=5)])
  self.assertEqual(pools(plan)['gpu']['peak'],5)
  plan['hardware']['acceleratorFreeMemoryGB']=0
  result=pools(plan);self.assertEqual(result['gpu']['peak'],0);self.assertEqual(result['system']['peak'],5)

if __name__=='__main__':unittest.main()
