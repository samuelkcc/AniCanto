"""Exercise directory repair against isolated saved work and linked locations."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Resources'))
from storage_health import inspect, repair, default_root


class StorageHealthTests(unittest.TestCase):
    def test_repair_creates_folders_without_changing_saved_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'jobs').mkdir();saved=root/'jobs/saved.json';saved.write_bytes(b'keep budgets and recordings')
            before=saved.read_bytes();report=repair(root)
            self.assertTrue(report['complete']);self.assertEqual(report['removedFiles'],0)
            self.assertEqual(saved.read_bytes(),before);self.assertTrue((root/'models').is_dir())
            self.assertEqual(repair(root)['created'],[])

    def test_repair_preserves_file_conflicts_and_external_links(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as ext:
            root=Path(tmp);(root/'models').write_bytes(b'keep unexpected file')
            (root/'cache').symlink_to(ext,target_is_directory=True)
            result=repair(root)
            self.assertFalse(result['complete']);self.assertEqual(set(result['skipped']),{'models','cache'})
            self.assertEqual((root/'models').read_bytes(),b'keep unexpected file')
            self.assertEqual(os.listdir(ext),[])

    def test_inspection_counts_a_shared_inode_once_and_skips_external_files(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as ext:
            root=Path(tmp);(root/'models').mkdir();a=root/'models/a.bin';a.write_bytes(b'model'*1024)
            (root/'cache').mkdir();os.link(a,root/'cache/b.bin')
            Path(ext,'outside').write_bytes(b'outside'*100)
            (root/'external').symlink_to(ext,target_is_directory=True)
            result=inspect(root)
            self.assertEqual(result['bytes'],2*a.stat().st_size)
            self.assertEqual(result['allocatedBytes'],a.stat().st_blocks*512)
            self.assertFalse(result['reclaimableEstimate']);self.assertTrue(result['modelsAndProjectsProtected'])

    def test_new_installs_use_anicanto_and_existing_libraries_remain_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);parent=root/'Library/Application Support';parent.mkdir(parents=True)
            self.assertEqual(default_root('darwin',root),parent/'AniCanto')
            (parent/'SamCantoSync').mkdir()
            self.assertEqual(default_root('darwin',root),parent/'SamCantoSync')
            (parent/'AniCanto').mkdir()
            self.assertEqual(default_root('darwin',root),parent/'AniCanto')
            self.assertEqual(default_root('win32',root,root/'Local'),root/'Local/AniCanto')


if __name__=='__main__':unittest.main()
