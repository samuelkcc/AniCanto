"""Runtime repair must reuse healthy GPU wheels and expose slow steps."""
import contextlib,io,json,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'windows'),str(ROOT/'Resources')]
import native_setup,runtime_health,runtime_progress

class Runtime270(unittest.TestCase):
 def fixture(self,d):
  root=Path(d);python=root/'runtimes/analysis/Scripts/python.exe';python.parent.mkdir(parents=True);python.touch()
  return root,python
 def check_reuse(self,receipt=True):
  with tempfile.TemporaryDirectory() as d:
   root,py=self.fixture(d)
   if receipt:(root/'analysis-runtime-ready.json').write_text('{"identity":"older-lock"}')
   packages={'torch':'2.9.1+cu128','torchaudio':'2.9.1+cu128'}
   with patch.object(native_setup,'data_root',return_value=root),patch.object(native_setup,'env_python',return_value=py),patch.object(runtime_health,'missing',return_value=[]),patch.object(runtime_health,'state',return_value={'packages':packages}),patch.object(runtime_health,'probe') as probe,patch.object(native_setup,'install_torch') as torch,patch.object(native_setup,'call') as pip,patch.object(native_setup.subprocess,'check_output',return_value='["2.9.1+cu128","2.9.1+cu128"]'),patch('runtime_exclusions.cleanup_command',return_value=None),contextlib.redirect_stdout(io.StringIO()):
    native_setup.environment('analysis','nvidia','cu128')
   torch.assert_not_called();pip.assert_not_called();probe.assert_called_once()
   self.assertTrue((root/'analysis-runtime-ready.json').is_file())
 def test_requirement_digest_change_does_not_reinstall_matching_gpu_wheels(self):
  self.check_reuse()
 def test_missing_receipt_does_not_force_gpu_download(self):
  self.check_reuse(receipt=False)
 def test_backend_match_rejects_cpu_wrong_cuda_missing_and_old_version(self):
  for packages in [{},{'torch':'2.9.1+cpu','torchaudio':'2.9.1+cpu'},{'torch':'2.9.1+cu130','torchaudio':'2.9.1+cu130'},{'torch':'2.8.0+cu128','torchaudio':'2.8.0+cu128'}]:
   self.assertFalse(runtime_health.backend_matches(packages,'nvidia','cu128'))
  self.assertTrue(runtime_health.backend_matches({'torch':'2.9.1+cpu','torchaudio':'2.9.1+cpu'},'cpu'))
 def test_heartbeat_reports_elapsed_without_claiming_completion(self):
  events=[]
  def emit(message,**kw):events.append(kw['runtimeProgress'])
  result=runtime_progress.step(emit,'analysis','Checking runtime imports',lambda:time.sleep(.06),interval=.01)
  self.assertIsNone(result);self.assertGreater(len(events),3)
  self.assertTrue(all(x['state']=='running' for x in events[:-1]));self.assertEqual(events[-1]['state'],'complete')
  count=len(events);time.sleep(.03);self.assertEqual(len(events),count)
 def test_failed_step_stops_heartbeat_and_preserves_error(self):
  events=[]
  with self.assertRaisesRegex(RuntimeError,'original'):
   runtime_progress.step(lambda m,**kw:events.append(kw),'analysis','Checking runtime imports',lambda:(_ for _ in ()).throw(RuntimeError('original')),interval=.01)
  self.assertEqual(events[-1]['runtimeProgress']['state'],'failed');count=len(events);time.sleep(.02);self.assertEqual(len(events),count)
 def test_missing_package_requirements_does_not_recreate_python(self):
  with tempfile.TemporaryDirectory() as d:
   root,py=self.fixture(d)
   with patch.object(native_setup,'HERE',root),patch.object(native_setup,'env_python',return_value=py),patch.object(native_setup,'ensure_env') as recreate,contextlib.redirect_stdout(io.StringIO()):
    with self.assertRaisesRegex(RuntimeError,'requirements are missing'):native_setup.environment('analysis','nvidia')
   recreate.assert_not_called()
 def test_inventory_is_bounded_and_does_not_request_platform_discovery(self):
  with patch.object(runtime_health.subprocess,'check_output',return_value='{"python":[3,12],"packages":{}}') as run:
   self.assertEqual(runtime_health.state('fixture-python')['python'],[3,12])
  self.assertEqual(run.call_args.kwargs['timeout'],60);self.assertNotIn('platform',run.call_args.args[0][-1])
 def test_version_probe_timeout_never_marks_runtime_ready(self):
  with tempfile.TemporaryDirectory() as d:
   root,py=self.fixture(d);marker=root/'analysis-runtime-ready.json';marker.write_text('{}')
   with patch.object(native_setup,'data_root',return_value=root),patch.object(native_setup,'env_python',return_value=py),patch.object(runtime_health,'missing',return_value=[]),patch.object(runtime_health,'state',return_value={'packages':{'torch':'2.9.1+cu128','torchaudio':'2.9.1+cu128'}}),patch.object(native_setup.subprocess,'check_output',side_effect=subprocess.TimeoutExpired('versions',60)),contextlib.redirect_stdout(io.StringIO()):
    with self.assertRaises(subprocess.TimeoutExpired):native_setup.environment('analysis','nvidia','cu128')
   self.assertFalse(marker.exists())
if __name__=='__main__':unittest.main()
