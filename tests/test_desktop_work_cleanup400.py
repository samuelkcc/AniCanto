"""Verify explicit saved-work deletion against an isolated legacy project index."""
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Resources'))
import desktop_work_cleanup as cleanup


class SavedWorkCleanup(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.job = self.root / 'jobs' / ('a' * 16)
        self.job.mkdir(parents=True)
        self.original = self.root / 'original.mp4'
        self.original.write_bytes(b'original')
        self.review = self.job / 'review.json'
        self.review.write_text(json.dumps({'config': {'video': str(self.original)}}))
        (self.job / 'take.wav').write_bytes(b'recording')
        (self.job / 'sample-AniCanto.mp4').write_bytes(b'intermediate movie')
        sep = self.root / 'separations' / ('b' * 20)
        sep.mkdir(parents=True)
        (sep / 'vocals.wav').write_bytes(b'derived audio')
        self.export = self.root / 'exports' / 'finished.mp4'
        self.export.parent.mkdir()
        self.export.write_bytes(b'finished movie')
        self.model = self.root / 'models' / 'weights.safetensors'
        self.model.parent.mkdir()
        self.model.write_bytes(b'model')
        db = sqlite3.connect(self.root / 'projects.sqlite3')
        db.executescript('CREATE TABLE projects(review TEXT PRIMARY KEY,video TEXT,status TEXT,updated REAL);'
                         'CREATE TABLE outputs(path TEXT PRIMARY KEY,project TEXT,status TEXT,updated REAL);'
                         'CREATE TABLE documents(project TEXT,payload TEXT);')
        db.execute('INSERT INTO projects VALUES(?,?,?,?)', (str(self.review), str(self.original), 'paused', 1))
        db.execute('INSERT INTO outputs VALUES(?,?,?,?)', (str(self.export), str(self.review), 'complete', 1))
        db.execute('INSERT INTO documents VALUES(?,?)', (str(self.review), 'saved dialogue'))
        db.commit()
        db.close()

    def run_cleanup(self):
        p = cleanup.plan(self.root)
        return cleanup.execute(self.root, [], p['token'])

    def test_saved_project_is_visible_when_the_video_list_is_empty(self):
        p = cleanup.plan(self.root)
        self.assertEqual((p['jobCount'], p['separationCount']), (1, 1))
        self.assertTrue(p['canRemove'])
        self.assertGreater(p['bytes'], 0)
        self.assertTrue(self.review.exists())

    def test_explicit_cleanup_removes_work_and_preserves_original_export_and_model(self):
        result = self.run_cleanup()
        self.assertTrue(result['complete'])
        self.assertFalse(self.job.exists())
        self.assertEqual(self.original.read_bytes(), b'original')
        self.assertEqual(self.export.read_bytes(), b'finished movie')
        self.assertEqual(self.model.read_bytes(), b'model')
        db = sqlite3.connect(self.root / 'projects.sqlite3')
        self.assertEqual(db.execute('SELECT count(*) FROM projects').fetchone()[0], 0)
        self.assertEqual(db.execute('SELECT project FROM outputs').fetchone()[0], '')
        db.close()

    def test_nonempty_queue_blocks_all_deletion(self):
        p = cleanup.plan(self.root, [{'status': 'paused'}])
        with self.assertRaises(ValueError):
            cleanup.execute(self.root, [{'status': 'paused'}], p['token'])
        self.assertTrue(self.review.exists())

    def test_changed_work_rejects_the_old_plan(self):
        p = cleanup.plan(self.root)
        (self.job / 'new-take.wav').write_bytes(b'new audio')
        with self.assertRaises(ValueError):
            cleanup.execute(self.root, [], p['token'])
        self.assertTrue(self.review.exists())

    def test_registered_movie_original_and_weights_inside_work_stay_protected(self):
        original = self.job / 'imported.mp4'
        original.write_bytes(b'owned original')
        self.review.write_text(json.dumps({'config': {'video': str(original)}}))
        final = self.job / 'registered-AniCanto.mp4'
        final.write_bytes(b'registered export')
        weights = self.job / 'extra.gguf'
        weights.write_bytes(b'weights')
        db = sqlite3.connect(self.root / 'projects.sqlite3')
        db.execute('INSERT INTO outputs VALUES(?,?,?,?)', (str(final), str(self.review), 'complete', 1))
        db.commit()
        db.close()
        self.run_cleanup()
        self.assertEqual(original.read_bytes(), b'owned original')
        self.assertEqual(final.read_bytes(), b'registered export')
        self.assertEqual(weights.read_bytes(), b'weights')

    def test_unknown_media_and_linked_data_are_never_followed(self):
        unknown = self.job / 'unclassified.mov'
        unknown.write_bytes(b'unknown media')
        external = self.root / 'external.wav'
        external.write_bytes(b'external')
        (self.job / 'linked.wav').symlink_to(external)
        self.run_cleanup()
        self.assertEqual(unknown.read_bytes(), b'unknown media')
        self.assertEqual(external.read_bytes(), b'external')

    def test_unknown_job_retains_its_index_and_files(self):
        folder = self.root / 'jobs' / 'not-an-owned-hash'
        folder.mkdir()
        review = folder / 'review.json'
        review.write_text('{}')
        db = sqlite3.connect(self.root / 'projects.sqlite3')
        db.execute('INSERT INTO projects VALUES(?,?,?,?)', (str(review), str(self.original), 'paused', 1))
        db.commit()
        db.close()
        self.run_cleanup()
        self.assertTrue(review.exists())
        db = sqlite3.connect(self.root / 'projects.sqlite3')
        self.assertEqual(db.execute('SELECT count(*) FROM projects').fetchone()[0], 1)
        db.close()

    def test_inflight_batch_blocks_saved_work_cleanup_without_queue_rows(self):
        (self.root/'batch-inflight.json').write_text(json.dumps({'review':str(self.review),'status':'running'}))
        p=cleanup.plan(self.root)
        self.assertFalse(p['canRemove'])
        with self.assertRaises(ValueError):cleanup.execute(self.root,[],p['token'])
        self.assertTrue((self.job/'take.wav').exists())

    def test_combined_cache_cleanup_keeps_one_progress_total(self):
        import project_cache
        cache=self.root/'cache/pip/download.whl';cache.parent.mkdir(parents=True);cache.write_bytes(b'package')
        p=project_cache.plan(self.root,[])
        events=[]
        # Read progress from the real receipt after each atomic update.
        from atomic_files import write_json
        from unittest.mock import patch
        def write(path,value):
            if path.name=='project-cache-progress.json':events.append(dict(value))
            return write_json(path,value)
        with patch('atomic_files.write_json',side_effect=write):
            result=project_cache.tracked_execute(self.root,[],p['token'],operation_id='fixture-400',saved_work_token=p['savedWorkCleanup']['token'])
        deleting=[e for e in events if e.get('phase')=='deleting']
        self.assertEqual(len({e['total'] for e in deleting}),1)
        counts=[e['processed'] for e in deleting]
        self.assertEqual(counts,sorted(counts))
        self.assertEqual(counts[-1],result['processedCount'])
        self.assertTrue(result['complete']);self.assertFalse(cache.exists())
        self.assertTrue(self.original.exists());self.assertTrue(self.export.exists());self.assertTrue(self.model.exists())
