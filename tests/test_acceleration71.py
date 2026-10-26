import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows')]
import compute_policy,whisper_accel,secondary_speech

class HardwarePolicyTests(unittest.TestCase):
 def test_reserve_ram_and_vram_without_double_counting_integrated_memory(self):
  p=compute_policy.budgets(32,16,16,True);self.assertEqual(p['systemBudgetGB'],24);self.assertEqual(p['acceleratorBudgetGB'],12.8)
  shared=compute_policy.budgets(32,16,16,False);self.assertEqual(shared['dedicatedVRAMGB'],0);self.assertEqual(shared['acceleratorBudgetGB'],0);self.assertFalse(shared['sharedMemoryIsAdditionalVRAM'])
 def test_busy_gpu_shrinks_budget_instead_of_using_physical_vram_total(self):
  p=compute_policy.budgets(32,16,6,True);self.assertEqual(p['acceleratorBudgetGB'],4.4)
  self.assertEqual(compute_policy.budgets(32,16,.2,True)['acceleratorBudgetGB'],0)
 def test_mac_large_v3_selects_installed_mlx_but_other_selected_variants_are_preserved(self):
  with patch.object(whisper_accel.sys,'platform','darwin'),patch.object(whisper_accel.platform,'machine',return_value='arm64'),patch('model_catalog.resolve',return_value=Path('/verified')):
   self.assertEqual(whisper_accel.selection(dict(storage='/tmp',speechModel='whisper-large-v3'))['backend'],'mlx')
   self.assertEqual(whisper_accel.selection(dict(storage='/tmp',speechModel='whisper-small'))['id'],'whisper-small')
   self.assertEqual(whisper_accel.selection(dict(storage='/tmp',speechModel='whisper-large-v3',speechAcceleration='cpu'))['backend'],'cpu')
 def test_missing_accelerator_model_uses_existing_cpu_without_implicit_download(self):
  def resolve(root,ident):
   if ident.endswith('-mlx'):raise ValueError('not installed')
   return Path('/verified-cpu')
  with patch.object(whisper_accel.sys,'platform','darwin'),patch.object(whisper_accel.platform,'machine',return_value='arm64'),patch('model_catalog.resolve',side_effect=resolve),patch('model_catalog.install') as install:
   value=whisper_accel.selection(dict(storage='/tmp',speechModel='whisper-large-v3'));self.assertEqual(value['backend'],'cpu');install.assert_not_called()
 def test_windows_cuda_requires_native_runtime_marker_and_amd_stays_cpu_for_ctranslate2(self):
  with tempfile.TemporaryDirectory() as d,patch.object(whisper_accel.sys,'platform','win32'),patch('model_catalog.resolve',return_value=Path('/verified')):
   p=Path(d)/'native-ready.json';cfg=dict(storage=d,speechModel='whisper-large-v3')
   self.assertEqual(whisper_accel.selection(cfg)['backend'],'cpu')
   p.write_text(json.dumps(dict(backend='amd',hardware=dict(backend='rocm'))));self.assertEqual(whisper_accel.selection(cfg)['backend'],'cpu')
   p.write_text(json.dumps(dict(backend='nvidia')));self.assertEqual(whisper_accel.selection(cfg)['backend'],'cuda')
 def test_invalid_accelerator_word_clocks_are_rejected_not_invented(self):
  for rows in ([dict(start=0,end=1,text='言葉',words=[])],[dict(start=0,end=1,text='言葉',words=[dict(start=0,end=float('nan'))])],[dict(start=1,end=4,text='言葉')]):
   with self.assertRaises(ValueError):whisper_accel.validate_segments(rows,2,True)
  rows=[dict(start=0,end=1,text='言葉',words=[dict(start=.1,end=.9,word='言葉')])];self.assertEqual(whisper_accel.validate_segments(rows,2,True),rows)
 def test_gpu_exception_falls_back_once_and_reports_actual_cpu_model(self):
  with tempfile.TemporaryDirectory() as d,patch.object(whisper_accel,'selection',return_value=dict(backend='mlx',id='whisper-large-v3-mlx',path='/model')),patch.object(whisper_accel,'cpu_model',return_value=Mock()) as cpu:
   instance=whisper_accel.AcceleratedWhisper(dict(storage=d,speechModel='whisper-large-v3'),d,Mock());instance.request=Mock(side_effect=RuntimeError('GPU failed'))
   instance.transcribe([0.],language='ja');instance.transcribe([0.],language='ja')
   cpu.assert_called_once();instance.request.assert_called_once();self.assertEqual(instance.chosen['id'],'whisper-large-v3');self.assertEqual(instance.chosen['backend'],'cpu')
 def test_pause_does_not_trigger_cpu_retry(self):
  from track_control import UserSkipped
  with tempfile.TemporaryDirectory() as d,patch.object(whisper_accel,'selection',return_value=dict(backend='mlx')),patch.object(whisper_accel,'cpu_model') as cpu:
   instance=whisper_accel.AcceleratedWhisper(dict(storage=d),d,Mock());instance.request=Mock(side_effect=UserSkipped('stop'))
   with self.assertRaises(UserSkipped):instance.transcribe([0.])
   cpu.assert_not_called()
 def test_busy_vram_is_reflected_in_existing_windows_model_planning(self):
  from memory_plan import fit_model,pools
  h=dict(memoryGB=32,acceleratorMemoryGB=16,acceleratorFreeMemoryGB=6,backend='cuda')
  self.assertEqual(fit_model(dict(id='model',estimatedMemoryGB=5),h),(False,'gpu'))
  self.assertEqual(pools(dict(hardware=h,downloads=[],roles={}))['gpu']['budget'],4.4)

 def test_secondary_lazy_cuda_failure_retries_cpu_once_and_records_actual_backend(self):
  import types
  fake=types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda:True),__file__='/tmp/torch/__init__.py')
  gpu=Mock();cpu=Mock();seen=[]
  def broken(*a,**k):
   def rows():raise RuntimeError('CUDA failed during decode');yield None
   return rows(),types.SimpleNamespace(language='zh')
  gpu.transcribe.side_effect=broken;cpu.transcribe.return_value=(iter([types.SimpleNamespace(text='聲音')]),types.SimpleNamespace(language='zh'))
  req=dict(backend='cuda',model='/model',storage='/tmp',language='zh')
  with patch.dict(sys.modules,{'torch':fake,'faster_whisper':types.SimpleNamespace(WhisperModel=Mock(side_effect=[gpu,cpu]))}),patch('compute_policy.torch_device',return_value='cuda:0'),patch.object(secondary_speech,'whisper_pcm',return_value=[0.]):
   infer=secondary_speech.load_transcriber(req);self.assertEqual(infer('/clip')['heard'],'聲音')
   self.assertEqual(req['backend'],'cpu');gpu.transcribe.assert_called_once();cpu.transcribe.assert_called_once()
 def test_source_success_receipt_is_visible_in_hardware_decisions(self):
  with tempfile.TemporaryDirectory() as d,patch.object(whisper_accel,'selection',return_value=dict(backend='mlx',id='whisper-large-v3-mlx')):
   instance=whisper_accel.AcceleratedWhisper(dict(storage=d),d,Mock())
   instance.record(dict(state='inference-passed',backend='mlx'))
   row=compute_policy.summary(d)['rows'][0];self.assertTrue(row['modelInferencePassed']);self.assertEqual(row['backend'],'mlx')
 def test_onnx_pinned_non_finite_coreml_combination_keeps_cpu_before_inference(self):
  import types,onnx_accel
  session=Mock();session.get_providers.return_value=['CPUExecutionProvider']
  ort=types.SimpleNamespace(__version__='1.30.0',get_available_providers=lambda:['CoreMLExecutionProvider','CPUExecutionProvider'],SessionOptions=Mock,InferenceSession=Mock(return_value=session))
  with tempfile.TemporaryDirectory() as d,patch.dict(sys.modules,{'onnxruntime':ort}),patch.object(onnx_accel.sys,'platform','darwin'),patch.object(onnx_accel.hashlib,'file_digest',return_value=types.SimpleNamespace(hexdigest=lambda:'7bb2f06e9df17cdf1ef14ee8a15ab08ed28e8d0ef5054ee135741560df2ec068')):
   p=Path(d)/'model.onnx';p.write_bytes(b'model');checked=onnx_accel.session(p,root=d)
   self.assertIsNone(checked.provider);self.assertIn('non-finite',checked.reason)
   self.assertEqual(ort.InferenceSession.call_args.kwargs['providers'],['CPUExecutionProvider'])

if __name__=='__main__':unittest.main()
