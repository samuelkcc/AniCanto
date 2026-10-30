"""Installed policy lookup with real native IPC and no user-model work."""
import importlib.util
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]

class CorePackageTests(unittest.TestCase):
 def package(self,root,windows=False):
  base=root/'package with spaces 日本語'/'shared';base.mkdir(parents=True)
  shutil.copy2(ROOT/'Resources/studio_core.py',base/'studio_core.py')
  shutil.copy2(ROOT/'Resources/production-contract.json',base/'production-contract.json')
  binary=base/'bin'/('anicanto-core.exe' if windows else 'anicanto-core');binary.parent.mkdir()
  shutil.copy2(ROOT/'Resources/bin/anicanto-core',binary)
  spec=importlib.util.spec_from_file_location('isolated_policy269',base/'studio_core.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  return module,binary
 def test_intact_windows_package_ignores_stale_external_override(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);module,binary=self.package(root,True)
   with patch.object(module.sys,'platform','win32'),patch.dict(os.environ,{'CANTOSYNC_CORE':str(root/'removed-old-package/core.exe')}):
    self.assertEqual(module.executable(),binary.resolve())
    self.assertEqual(module.call('catalog')['catalog'],module.catalog())
 def test_missing_bundle_cannot_execute_external_unverified_core(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);module,binary=self.package(root,True);binary.unlink()
   with patch.object(module.sys,'platform','win32'),patch.dict(os.environ,{'CANTOSYNC_CORE':str(ROOT/'Resources/bin/anicanto-core')}):
    with self.assertRaisesRegex(RuntimeError,'shared core is missing'):module.executable()
 def test_setup_core_failure_does_not_invalidate_previous_installation(self):
  sys.path[:0]=[str(ROOT/'windows'),str(ROOT/'Resources')]
  import native_setup,studio_core
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);ready=root/'native-ready.json';ready.write_bytes(b'{"speechInferencePassed":true}')
   with patch.object(native_setup.sys,'platform','win32'),patch.object(native_setup,'data_root',return_value=root),patch.object(native_setup,'environment',side_effect=AssertionError('No runtime work')),patch.object(native_setup,'emit'),patch.object(studio_core,'verify',side_effect=RuntimeError('missing test core')):
    with self.assertRaisesRegex(RuntimeError,'missing test core'):native_setup._setup()
   self.assertEqual(ready.read_bytes(),b'{"speechInferencePassed":true}')
   self.assertFalse((root/'setup-invalidated.json').exists())
 def test_catalog_mismatch_still_blocks_a_real_packaged_call(self):
  with tempfile.TemporaryDirectory() as d:
   module,binary=self.package(Path(d));(binary.parent.parent/'production-contract.json').write_text('{}')
   with patch.dict(os.environ,{'CANTOSYNC_CORE':str(binary)}):
    with self.assertRaisesRegex(RuntimeError,'core/catalog version mismatch'):module.call('hardware')

if __name__=='__main__':unittest.main()
