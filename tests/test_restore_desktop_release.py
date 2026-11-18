"""Verify recovery ZIP boundaries with isolated release fixtures."""
import io
import stat
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import restore_desktop_release as restore


class RestoreTests(unittest.TestCase):
    def test_appledouble_does_not_become_a_bundle_resource(self):
        raw=io.BytesIO()
        with zipfile.ZipFile(raw,'w') as archive:
            archive.writestr('AniCanto.app/._Contents',b'metadata')
            archive.writestr('AniCanto.app/Contents/._Info.plist',b'metadata')
            archive.writestr('AniCanto.app/Contents/Info.plist',b'actual resource')
        with tempfile.TemporaryDirectory() as scratch, zipfile.ZipFile(raw) as archive:
            root=Path(scratch);restore.safe_zip(archive,root)
            self.assertEqual((root/'AniCanto.app/Contents/Info.plist').read_bytes(),b'actual resource')
            self.assertEqual(list(root.rglob('._*')),[])

    def test_traversal_and_zip_symlinks_are_rejected(self):
        for name,mode in [('../outside',0),('link',stat.S_IFLNK | 0o777)]:
            raw=io.BytesIO()
            with zipfile.ZipFile(raw,'w') as archive:
                entry=zipfile.ZipInfo(name);entry.external_attr=mode<<16;archive.writestr(entry,b'outside')
            with tempfile.TemporaryDirectory() as scratch, zipfile.ZipFile(raw) as archive:
                with self.assertRaises(ValueError):restore.safe_zip(archive,Path(scratch))


if __name__=='__main__':unittest.main()
