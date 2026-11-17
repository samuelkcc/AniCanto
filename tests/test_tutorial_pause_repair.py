"""Verify that tutorial pause edits retain speech and chapter reading time."""
from pathlib import Path
from fractions import Fraction
import array
import importlib.util
import math
import tempfile
import unittest
import wave

SPEC = importlib.util.spec_from_file_location(
    'tutorial_pauses', Path(__file__).resolve().parents[1] / 'mobile/DemoFilm/repair_tutorial_pauses.py')
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class TutorialPauseProtection(unittest.TestCase):
    def test_only_internal_quiet_is_shortened_and_clocks_stay_common(self):
        rate = 44100
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'different-narration.wav'
            signal = array.array('h')
            for length, amplitude in [(1, .1), (3, 0), (1, .1), (2, 0), (1, .1)]:
                signal.extend(round(32767 * amplitude * math.sin(2 * math.pi * 211 * n / rate))
                              for n in range(round(length * rate)))
            with wave.open(str(path), 'wb') as target:
                target.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
                target.writeframes(signal.tobytes())
            found = MOD.quiet_intervals(path)
            cuts = MOD.plan_cuts(found, [(0, 5, 'First chapter'), (7, 8, 'Second chapter')], 24, rate)
            self.assertEqual(len(cuts), 1)
            self.assertGreaterEqual(cuts[0]['start'], 1.3)
            self.assertLessEqual(cuts[0]['end'], 3.7)
            for cut in cuts:
                for frame in [cut['firstFrame'], cut['lastFrame']]:
                    self.assertEqual((Fraction(frame, 24) * rate).denominator, 1)
            self.assertAlmostEqual(MOD.map_time(7, cuts) - MOD.map_time(5, cuts), 2)

    def test_low_level_voiced_audio_is_not_a_quiet_candidate(self):
        rate = 16000
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'quiet-voiced.wav'
            signal = array.array('h', (round(32767 * .012 * math.sin(2 * math.pi * 193 * n / rate))
                                      for n in range(3 * rate)))
            with wave.open(str(path), 'wb') as target:
                target.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
                target.writeframes(signal.tobytes())
            self.assertEqual(MOD.quiet_intervals(path), [])

    def test_edge_and_short_pauses_remain_unchanged(self):
        self.assertEqual(MOD.plan_cuts([(0, 2), (3, 4.2), (7.5, 10)],
                                      [(0, 10, 'A full chapter')], 24, 44100), [])


if __name__ == '__main__':
    unittest.main()
