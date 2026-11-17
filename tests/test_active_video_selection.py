"""Check the Mac and Windows RPC selection boundary during owned work."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'studio'), str(ROOT/'windows'), str(ROOT/'Resources')]
from backend import Studio


class ActiveVideoSelection(unittest.TestCase):
    def test_active_selection_rejects_other_videos_without_changing_work(self):
        for platform in ['darwin', 'win32']:
            with self.subTest(platform=platform), tempfile.TemporaryDirectory() as tmp:
                app = Studio(Path(tmp), ROOT/'Resources', platform=platform)
                rows = [dict(id='a', video='a.mkv', status='running', progress=.42,
                             request='frozen-a', recoverySpentSeconds=49),
                        dict(id='b', video='b.mkv', status='complete', output='b.mp4')]
                app.store.queue = copy.deepcopy(rows)
                app.store.selected = 'a'
                app.store.save()
                before = app.store.path.read_bytes()
                with self.assertRaisesRegex(ValueError, 'Pause and save'):
                    app.dispatch('select', dict(id='b'))
                self.assertEqual(app.store.path.read_bytes(), before)
                self.assertEqual(app.store.queue, rows)
                self.assertEqual(app.dispatch('select', dict(id='a'))['selected'], 'a')

    def test_pause_and_saved_final_state_allow_selection(self):
        for status in ['paused', 'complete', 'attention']:
            with self.subTest(status=status), tempfile.TemporaryDirectory() as tmp:
                app = Studio(Path(tmp), ROOT/'Resources')
                app.store.queue = [dict(id='a', video='a.mkv', status=status, request='saved'),
                                   dict(id='b', video='b.mkv', status='waiting')]
                app.store.selected = 'a'
                app.store.save()
                before = copy.deepcopy(app.store.queue)
                self.assertEqual(app.dispatch('select', dict(id='b'))['selected'], 'b')
                self.assertEqual(app.store.queue, before)

    def test_state_recovers_visible_selection_to_the_running_video(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = Studio(Path(tmp), ROOT/'Resources')
            app.store.queue = [dict(id='a', video='a.mkv', status='waiting'),
                               dict(id='b', video='b.mkv', status='running', progress=.6)]
            app.store.selected = 'a'
            app.store.save()
            before = copy.deepcopy(app.store.queue)
            self.assertEqual(app.dispatch('state', {})['selected'], 'b')
            self.assertEqual(app.store.selected, 'b')
            self.assertEqual(app.store.queue, before)


if __name__ == '__main__':
    unittest.main()
