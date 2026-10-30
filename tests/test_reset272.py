"""Repair an existing Windows venv after its base was partly removed."""
import subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import runtime_installer as ri
class Reset272(unittest.TestCase):
 def fixture(self,folder):
  root=Path(folder);env=root/'runtimes/ui';py=env/'Scripts/python.exe';py.parent.mkdir(parents=True);py.write_bytes(b'partial executable');package=env/'Lib/site-packages/keep.py';package.parent.mkdir(parents=True);package.write_text('retained');return root,env,py,package
 def test_missing_base_with_existing_executable_is_reconnected(self):
  with tempfile.TemporaryDirectory() as d:
   root,env,py,package=self.fixture(d);run=Mock(side_effect=[subprocess.CalledProcessError(1,['python.exe']),None])
   with patch.object(ri.sys,'platform','win32'),patch.object(ri,'base_python',return_value=root/'python/new/python.exe') as base:
    self.assertEqual(ri.ensure_env(root,env,run=run),py)
   base.assert_called_once();self.assertEqual(run.call_count,2);self.assertIn('venv',run.call_args.args[0]);self.assertNotIn('--clear',run.call_args.args[0]);self.assertEqual(package.read_text(),'retained')
 def test_healthy_existing_env_does_not_download_or_reinstall(self):
  with tempfile.TemporaryDirectory() as d:
   root,env,py,package=self.fixture(d);run=Mock()
   with patch.object(ri.sys,'platform','win32'),patch.object(ri,'base_python') as base:ri.ensure_env(root,env,run=run)
   base.assert_not_called();run.assert_called_once();self.assertEqual(run.call_args.kwargs['timeout'],30)
 def test_timed_out_interpreter_is_repaired_without_model_removal(self):
  with tempfile.TemporaryDirectory() as d:
   root,env,py,package=self.fixture(d);model=root/'models/keep.gguf';model.parent.mkdir();model.write_bytes(b'kept');run=Mock(side_effect=[subprocess.TimeoutExpired('python.exe',30),None])
   with patch.object(ri.sys,'platform','win32'),patch.object(ri,'base_python',return_value=root/'python/new/python.exe'):ri.ensure_env(root,env,run=run)
   self.assertEqual(model.read_bytes(),b'kept');self.assertEqual(package.read_text(),'retained')
if __name__=='__main__':unittest.main()
