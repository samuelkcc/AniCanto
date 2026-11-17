"""Test source ownership through the actual desktop reference producer."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'windows'), str(ROOT / 'Resources')]
import independent_voices as iv
from desktop_state import Store, read


class OwnedReferenceWindow(unittest.TestCase):
    def test_confirmed_clock_keeps_context_inside_cue(self):
        cfg = dict(voiceReferenceWindowRevision=iv.WINDOW_REVISION)
        for cue, expected in [
            (dict(start=1, end=2, speechStart=1.2, speechEnd=1.7), (1.14, 1.8, True)),
            (dict(start=1, end=2, speechStart=1.01, speechEnd=1.99), (1, 2, True)),
            (dict(start=3, end=4, speechStart=3.3, speechEnd=3.6), (3.24, 3.7, True)),
        ]:
            with self.subTest(cue=cue):
                a, b, confirmed = iv.reference_window(cfg, cue, 20)
                self.assertAlmostEqual(a, expected[0])
                self.assertAlmostEqual(b, expected[1])
                self.assertEqual(confirmed, expected[2])

    def test_invalid_or_unknown_hints_use_the_own_cue(self):
        cfg = dict(voiceReferenceWindowRevision=iv.WINDOW_REVISION)
        for hints in [dict(), dict(speechStart=None, speechEnd=None),
                      dict(speechStart=3, speechEnd=4), dict(speechStart=-1, speechEnd=.5),
                      dict(speechStart=.8, speechEnd=.2), dict(speechStart=float('nan'), speechEnd=.8),
                      dict(speechStart=.1, speechEnd=float('inf')),
                      dict(speechStart=.2, speechEnd=.8, sourceClockUnconfirmed=True)]:
            with self.subTest(hints=hints):
                self.assertEqual(iv.reference_window(cfg, dict(start=0, end=1, **hints), 10), (0, 1, False))

    def test_actual_pcm_does_not_read_a_different_adjacent_interval(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sr = 16000
            t = np.arange(4 * sr) / sr
            audio = np.where(t < 1, .2*np.sin(2*np.pi*220*t), .2*np.sin(2*np.pi*110*t)).astype('float32')
            source = root/'source.wav'
            sf.write(source, audio, sr, subtype='FLOAT')
            cues = [dict(id='first', start=0, end=1, speechStart=1.2, speechEnd=1.8)]
            before = copy.deepcopy(cues)
            cfg = dict(audio=str(source), job=str(root), storage=str(root), cues=cues,
                       productionMode='normal', voiceReferencePaddingRevision=iv.PADDING_REVISION342,
                       voiceReferenceIdentityRevision=iv.IDENTITY_REVISION379,
                       voiceReferenceWindowRevision=iv.WINDOW_REVISION)
            with patch('reference_padding.pad', side_effect=AssertionError('Do not borrow external audio')):
                iv.prepare(cfg, Mock())
            profile = read(root/'independent-voices.json')['profiles'][0]
            pcm, rate = sf.read(profile['reference'], dtype='float32')
            np.testing.assert_allclose(pcm[:sr], audio[:sr], atol=1/32768)
            self.assertTrue(np.all(pcm[sr:] == 0))
            self.assertEqual(rate, sr)
            receipt = read(Path(profile['reference']).with_name('source.json'))
            self.assertEqual(receipt['range'], [0, 1])
            self.assertEqual(receipt['cueID'], 'first')
            self.assertFalse(receipt['usesSpeechClock'])
            self.assertEqual(receipt['sourceSHA256'], hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(receipt['referenceSHA256'], profile['referenceSHA256'])
            self.assertEqual(cues, before)

    def test_absent_policy_retains_legacy_ranges_and_separate_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root/'source.wav'
            sf.write(source, np.ones(4*16000, dtype='float32')*.1, 16000)
            cfg = dict(audio=str(source), job=str(root), storage=str(root),
                       cues=[dict(start=0, end=1, speechStart=1.2, speechEnd=1.8)],
                       productionMode='normal', voiceReferencePaddingRevision=iv.PADDING_REVISION342)
            iv.prepare(cfg, Mock())
            old = read(root/'independent-voices.json')['profiles'][0]
            self.assertAlmostEqual(old['referenceRanges'][0][0], 1.2)
            cfg['voiceReferenceWindowRevision'] = iv.WINDOW_REVISION
            iv.prepare(cfg, Mock())
            new = read(root/'independent-voices.json')['profiles'][0]
            self.assertEqual(new['referenceRanges'], [[0, 1]])
            self.assertNotEqual(new['reference'], old['reference'])

    def test_new_request_freezes_policy_and_resume_preserves_old_bytes(self):
        for mode in ['basic', 'expert']:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source = root/'fixture.mkv'
                source.write_bytes(b'isolated fixture')
                store = Store(root)
                store.mode = mode
                store.add([source])
                row = store.queue[0]
                path = store.submit(row)
                current = read(path)
                self.assertEqual(current['voiceReferenceWindowRevision'], iv.WINDOW_REVISION)
                current.pop('voiceReferenceWindowRevision')
                current.update(recoverySpentSeconds=49, testAttempts={'reference': 2})
                path.write_text(json.dumps(current))
                before = path.read_bytes()
                row['status'] = 'paused'
                self.assertEqual(store.submit(row), path)
                self.assertEqual(path.read_bytes(), before)

    def test_child_request_and_cache_include_clock_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root/'source.wav'
            sf.write(source, np.ones(4*16000, dtype='float32')*.1, 16000)
            cues = [dict(start=0, end=1, speechStart=.2, speechEnd=.7, japanese='こんにちは。')]
            cfg = dict(storage=str(root), dialoguePath=str(source), productionMode='normal',
                       voiceReferenceWindowRevision=iv.WINDOW_REVISION,
                       voiceReferencePaddingRevision=iv.PADDING_REVISION342,
                       voiceReferenceIdentityRevision=iv.IDENTITY_REVISION379)
            requests = []
            def child(parent, action, request, emit):
                self.assertEqual(action, 'independent-voices')
                self.assertEqual(request['voiceReferenceWindowRevision'], iv.WINDOW_REVISION)
                requests.append(copy.deepcopy(request))
                iv.prepare(request, emit)
            def transcribe(parent, job, profiles, model, emit):
                for profile in profiles:
                    profile['promptText'] = 'こんにちは。'
            with patch('dubbing.model_job', side_effect=child), patch('speakers.transcribe_profiles', side_effect=transcribe), patch('model_catalog.selected', return_value='whisper-small'):
                iv.assign(cfg, root, cues, Mock())
                first = read(root/'independent-voices.json')['profiles'][0]
                iv.assign(cfg, root, cues, Mock())
                self.assertEqual(len(requests), 1)
                cues[0]['sourceClockUnconfirmed'] = True
                iv.assign(cfg, root, cues, Mock())
                last = read(root/'independent-voices.json')['profiles'][0]
                self.assertEqual(len(requests), 2)
                self.assertNotEqual(first['reference'], last['reference'])
                self.assertEqual(last['referenceRanges'], [[0, 1]])


if __name__ == '__main__':
    unittest.main()
