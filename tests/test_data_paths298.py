"""Check path relocation without changing policies, budget keys or media bytes."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import types
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('data_paths298',Path(__file__).resolve().parents[1]/'scripts/migrate_data_paths.py')
migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)

class DataPaths(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.parent=Path(self.temp.name).resolve()
        self.root=self.parent/'AniCanto';self.root.mkdir();self.old=self.parent/'SamCantoSync';self.old.symlink_to(self.root)
        self.record=self.root/'saved.json';self.value=dict(audio=str(self.old/'audio.wav'),revision='frozen-v1',attempts=2,records={'spent-hash':{'spentSeconds':137.5}})
        self.original=json.dumps(self.value).encode();self.record.write_bytes(self.original)
        self.audio=self.root/'audio.wav';self.audio.write_bytes(b'original recording')
        self.link=self.root/'python-link';self.link.symlink_to(self.old/'audio.wav')
        with sqlite3.connect(self.root/'projects.sqlite3') as db:
            db.execute('CREATE TABLE projects (path TEXT PRIMARY KEY, attempts INTEGER)')
            db.execute('INSERT INTO projects VALUES (?,?)',(str(self.old/'saved.json'),2))
        self.plan=dict(oldRoot=str(self.old),newRoot=str(self.root),files=[dict(path='saved.json')],symlinks=[dict(path='python-link',target=str(self.old/'audio.wav'))])
    def tearDown(self):self.temp.cleanup()
    def probe(self,args,**kwargs):
        return types.SimpleNamespace(stdout=json.dumps(dict(prefix=str(Path(args[0]).parents[1]),version=[3,11])))
    def test_dry_run_keeps_original_records_and_alias(self):
        result=migration.migrate(self.plan,self.parent/'evidence')
        self.assertFalse(result['aliasRemoved']);self.assertEqual(self.record.read_bytes(),self.original);self.assertTrue(self.old.is_symlink())
    def test_relocation_keeps_policies_attempts_hash_keys_and_audio(self):
        with patch.object(migration.subprocess,'run',side_effect=self.probe):result=migration.migrate(self.plan,self.parent/'evidence',True)
        self.assertTrue(result['aliasRemoved']);self.assertFalse(self.old.is_symlink())
        self.assertEqual(json.loads(self.record.read_text()),dict(self.value,audio=str(self.root/'audio.wav')))
        self.assertEqual(self.audio.read_bytes(),b'original recording');self.assertEqual(self.link.read_bytes(),b'original recording')
        with sqlite3.connect(self.root/'projects.sqlite3') as db:self.assertEqual(db.execute('SELECT * FROM projects').fetchall(),[(str(self.root/'saved.json'),2)])
    def test_failed_runtime_probe_restores_all_files_database_and_alias(self):
        with patch.object(migration.subprocess,'run',side_effect=RuntimeError('isolated probe failure')):
            with self.assertRaises(RuntimeError):migration.migrate(self.plan,self.parent/'evidence',True)
        self.assertTrue(self.old.is_symlink());self.assertEqual(self.record.read_bytes(),self.original)
        self.assertEqual(self.link.readlink(),self.old/'audio.wav')
        with sqlite3.connect(self.root/'projects.sqlite3') as db:self.assertEqual(db.execute('SELECT * FROM projects').fetchall(),[(str(self.old/'saved.json'),2)])
    def test_database_collision_stops_before_live_changes(self):
        with sqlite3.connect(self.root/'projects.sqlite3') as db:db.execute('INSERT INTO projects VALUES (?,?)',(str(self.root/'saved.json'),7))
        with self.assertRaises(sqlite3.IntegrityError):migration.migrate(self.plan,self.parent/'evidence',True)
        self.assertEqual(self.record.read_bytes(),self.original);self.assertTrue(self.old.is_symlink())

if __name__=='__main__':unittest.main()
