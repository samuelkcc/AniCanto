import json,subprocess,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'windows'),str(ROOT/'Resources')]
import drama_cuda,drama_gguf,native_setup,runtime_health

class NativeCudaTests(unittest.TestCase):
 def test_strict_cantonese_retake_keeps_source_reference_and_complete_text(self):
  import io,numpy as np,soundfile as sf
  raw=io.BytesIO();sf.write(raw,np.full(4410,.1,dtype=np.float32),44100,format='WAV')
  model=SimpleNamespace(backend='cuda',variant='drama3-small-iq3',silence='silence.json')
  item=dict(text='等陣先，唔好走！',deliveryStyle='cantonese-strict',seed=104771,profile=dict(reference='own-source.wav',promptText='原聲參考'))
  with patch.object(drama_gguf,'monitored_request',return_value=raw.getvalue()) as request:
   drama_gguf.generate(model,item,dict(targetLanguage='yue'))
  sent=request.call_args.args[1]
  self.assertRegex(sent['input'],r'唔好[^。]*普通話');self.assertTrue(sent['input'].endswith(item['text']))
  self.assertEqual(sent['voice_ref'],'own-source.wav');self.assertEqual(sent['seed'],104771)
  self.assertEqual({k:sent[k] for k in ('temperature','top_p','top_k')},dict(temperature=1.,top_p=.9,top_k=30))
 def fixture(self,root):
  package=root/'package';host=package/'tools/drama-small-cuda';host.mkdir(parents=True)
  for name in ('audiocpp_server.exe','ggml.dll','ggml-base.dll','ggml-cpu.dll'):(host/name).write_bytes(b'patched-host')
  cuda=root/'cuda';cuda.mkdir();(cuda/'ggml-cuda.dll').write_bytes(b'cuda');(cuda/'audiocpp_server.exe').write_bytes(b'wrong-stock-host');(cuda/'ggml-base.dll').write_bytes(b'wrong-base')
  runtime=root/'cuda-runtime';runtime.mkdir();(runtime/'cudart64_12.dll').write_bytes(b'cudart')
  return package,cuda,runtime
 def test_installer_uses_patched_host_and_verifies_real_cuda_device(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);package,cuda,runtime=self.fixture(root);data=root/'data'
   with patch.object(drama_cuda,'HERE',package),patch.object(native_setup,'tool',side_effect=lambda n:cuda if n=='drama-cuda' else runtime),patch.object(drama_cuda.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='CUDA:0 "NVIDIA RTX 4090 Laptop GPU" [gpu]\n',stderr='')) as probe:
    target=drama_cuda.prepare(data,lambda *a,**kw:None)
   self.assertEqual((target/'audiocpp_server.exe').read_bytes(),b'patched-host');self.assertEqual((target/'ggml-base.dll').read_bytes(),b'patched-host')
   self.assertIn('--list-devices',probe.call_args.args[0]);self.assertTrue(drama_cuda.ready(data))
   self.assertFalse(json.loads((target/'verified.json').read_text())['speechInferencePassed'])
   (target/'ggml-cuda.dll').unlink();self.assertFalse(drama_cuda.ready(data))
 def test_cpu_device_does_not_pass_cuda_verification_or_leave_receipt(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);package,cuda,runtime=self.fixture(root);data=root/'data'
   with patch.object(drama_cuda,'HERE',package),patch.object(native_setup,'tool',side_effect=lambda n:cuda if n=='drama-cuda' else runtime),patch.object(drama_cuda.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='CPU:0 "CPU" [cpu]\n',stderr='')):
    with self.assertRaisesRegex(RuntimeError,'device check failed'):drama_cuda.prepare(data,lambda *a,**kw:None)
   self.assertFalse(drama_cuda.ready(data));self.assertTrue((data/'tools/drama-small-cuda/device-probe.log').is_file())
 def test_production_backend_is_read_from_receipt_and_explicit_cpu_is_honoured(self):
  with tempfile.TemporaryDirectory() as d,patch.object(drama_gguf.sys,'platform','win32'):
   root=Path(d);(root/'drama3-windows-ready.json').write_text(json.dumps(dict(modelLoadPassed=True,backend='cuda')))
   self.assertEqual(drama_gguf.native_backend(root,{}),'cuda');self.assertEqual(drama_gguf.native_backend(root,dict(drama3Backend='cpu')),'cpu')
   with self.assertRaises(ValueError):drama_gguf.native_backend(root,dict(drama3Backend='mps'))

class NativeRuntimeReceiptTests(unittest.TestCase):
 def test_existing_receipt_still_checks_packages_and_imports_without_install(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);python=root/'runtimes/worker/bin/python';python.parent.mkdir(parents=True);python.touch()
   (root/'worker-runtime-ready.json').write_text('{"identity":"old"}')
   with patch.object(native_setup,'data_root',return_value=root),patch.object(native_setup,'env_python',return_value=python),patch.object(runtime_health,'missing',return_value=[]),patch.object(runtime_health,'probe') as probe,patch.object(native_setup,'call') as install:
    native_setup.environment('worker')
   probe.assert_called_once();install.assert_not_called();self.assertTrue((root/'worker-runtime-ready.json').is_file())
 def test_failed_check_never_preserves_ready_receipt_or_blindly_reinstalls(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);python=root/'runtimes/worker/bin/python';python.parent.mkdir(parents=True);python.touch();marker=root/'worker-runtime-ready.json';marker.write_text('{}')
   with patch.object(native_setup,'data_root',return_value=root),patch.object(native_setup,'env_python',return_value=python),patch.object(runtime_health,'missing',return_value=[]),patch.object(runtime_health,'probe',side_effect=subprocess.CalledProcessError(1,['probe'])),patch.object(runtime_health,'damaged',return_value=[]),patch.object(native_setup,'call') as install:
    with self.assertRaisesRegex(RuntimeError,'intact'):native_setup.environment('worker')
   install.assert_not_called();self.assertFalse(marker.exists())

if __name__=='__main__':unittest.main()
