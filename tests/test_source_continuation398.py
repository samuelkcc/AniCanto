"""Exercise actual desktop recovery and cue producers beyond the old mobile cap."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Resources'))
import dialogue
import source_clock_recovery as clock


class DesktopContinuation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.job = Path(self.temp.name)
        self.calls = 0
        self.row = dict(start=0, end=330, text='bad clock',
                        words=[dict(start=0, end=330, word='bad clock', probability=.1)])
        self.cfg = dict(sourceClockRecoveryRevision=clock.REVISION,
                        duration=330, sourceLanguage='ja')

    def run_recovery(self):
        def failed_decode(*args, **kwargs):
            self.calls += 1
            raise RuntimeError('Injected bounded recognition failure')
        return clock.repair(SimpleNamespace(transcribe=failed_decode), [], [self.row],
                            self.cfg, self.job, lambda *args: None)

    def test_unknown_windows_continue_and_keep_original_cues(self):
        rows = self.run_recovery()
        self.assertEqual(len(rows), 42)
        self.assertEqual(self.calls, clock.MAX_WINDOWS)
        self.assertEqual(sum(r['end'] - r['start'] for r in rows), 330)
        cues = dialogue.build_cues(rows, [], [], 330)
        self.assertEqual(len(cues), 42)
        self.assertTrue(all(c['preserveOriginalSpeech'] and c['sourceClockUnconfirmed'] for c in cues))
        self.assertTrue(all(c['japanese'] == '' and c['cantonese'] == '' for c in cues))

    def test_cached_resume_preserves_spent_ledger_and_adds_no_call(self):
        first = self.run_recovery()
        path = self.job / 'source-clock-recovery.json'
        before = path.read_bytes()
        self.assertEqual(self.run_recovery(), first)
        self.assertEqual(self.calls, clock.MAX_WINDOWS)
        self.assertEqual(path.read_bytes(), before)

    def test_missing_result_with_spent_budget_does_not_restart(self):
        self.run_recovery()
        path = self.job / 'source-clock-recovery.json'
        ledger = json.loads(path.read_text())
        ledger['windows'].pop(next(iter(ledger['windows'])))
        path.write_text(json.dumps(ledger))
        before = path.read_bytes()
        rows = self.run_recovery()
        self.assertEqual(len(rows), 42)
        self.assertEqual(self.calls, clock.MAX_WINDOWS)
        self.assertEqual(path.read_bytes(), before)
        self.assertTrue(all(r['sourceClockUnconfirmed'] for r in rows))


if __name__ == '__main__':
    unittest.main()
