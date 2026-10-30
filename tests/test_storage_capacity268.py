"""Download preflight accepts native reclaimable capacity and keeps real limits."""
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import storage_capacity as space
import model_catalog

class StorageTests(unittest.TestCase):
 def test_important_capacity_allows_requested_download_without_cleanup(self):
  with tempfile.TemporaryDirectory() as d,patch.object(space.sys,'platform','darwin'),patch.object(space.shutil,'disk_usage',return_value=SimpleNamespace(total=2_000_000_000_000,free=35_000_000_000)),patch.object(space,'important_capacity',return_value=137_000_000_000):
   r=space.require_space(d,60_000_000_000)
   self.assertEqual(r['method'],'important-usage');self.assertEqual(r['requiredBytes'],62_000_000_000)
   self.assertEqual(list(Path(d).iterdir()),[])
 def test_unavailable_or_invalid_native_capacity_is_conservative(self):
  for value in (None,-1,3_000_000_000_000,True,0):
   with self.subTest(value=value),tempfile.TemporaryDirectory() as d,patch.object(space.sys,'platform','darwin'),patch.object(space.shutil,'disk_usage',return_value=SimpleNamespace(total=2_000_000_000_000,free=35_000_000_000)),patch.object(space,'important_capacity',return_value=value):
    with self.assertRaisesRegex(ValueError,'available 35.0 GB; required 62.0 GB'):space.require_space(d,60_000_000_000)
 def test_windows_does_not_load_apple_framework(self):
  with tempfile.TemporaryDirectory() as d,patch.object(space.sys,'platform','win32'),patch.object(space,'important_capacity',side_effect=AssertionError('Apple API on Windows')):
   self.assertEqual(space.capacity(d)['method'],'ordinary-free')
 def test_resume_counts_missing_bytes_and_wrong_size_files(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'complete').write_bytes(b'abcd');(root/'wrong').write_bytes(b'a');(root/'next.partial').write_bytes(b'ab')
   self.assertEqual(space.remaining_bytes([dict(path='complete',size=4),dict(path='wrong',size=4),dict(path='next',size=4)],root),6)
 def test_installer_uses_native_capacity_before_download_and_preserves_existing(self):
  row=dict(id='fixture',title='Fixture',repo='fixture',revision='revision',bytes=60_000_000_000,category='text',files=[dict(path='weights',size=60_000_000_000,sha='fixture')])
  for available,allowed in [(137_000_000_000,True),(35_000_000_000,False)]:
   with self.subTest(allowed=allowed),tempfile.TemporaryDirectory() as d,patch.object(model_catalog,'choice',return_value=row),patch('engine_availability.require'),patch('model_licenses.install_notices'),patch('model_ownership.mark_available'),patch.object(model_catalog,'resolve',return_value=Path(d)),patch('dubbing_setup.download') as download,patch.object(space,'capacity',return_value=dict(volumePath=d,availableBytes=available)),contextlib.redirect_stdout(io.StringIO()):
    retained=Path(d)/'existing-model';retained.write_bytes(b'keep')
    if allowed:model_catalog.install(d,'fixture');self.assertEqual(download.call_count,1)
    else:
     with self.assertRaisesRegex(ValueError,'Insufficient storage'):model_catalog.install(d,'fixture')
     download.assert_not_called()
    self.assertEqual(retained.read_bytes(),b'keep')

if __name__=='__main__':unittest.main()
