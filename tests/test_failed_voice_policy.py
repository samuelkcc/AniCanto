import json
import sys
import tempfile
import unittest
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / 'Resources'))
sys.path.insert(0, str(Path(__file__).parents[1] / 'windows'))

from failed_voice_policy import choose
from desktop_state import defaults


def take(path):
    with wave.open(str(path), 'wb') as audio:
        audio.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
        audio.writeframes(b'\x00\x20' * 2400)
    return path


class FailedVoicePolicyTests(unittest.TestCase):
    def test_both_interface_modes_default_to_generic_target_language_voice(self):
        self.assertEqual(defaults('en')['failedVoicePolicy'], 'generic')
        self.assertEqual(defaults('zh-HK')['failedVoicePolicy'], 'generic')

    def test_generic_take_is_used_only_when_a_saved_bank_attempt_was_selected(self):
        with tempfile.TemporaryDirectory() as directory:
            job = Path(directory)
            actor = take(job / 'actor.wav')
            generic = take(job / 'generic.wav')
            (job / 'normal-checks.json').write_text(json.dumps({'unresolved': [1]}))
            cue = [dict(start=0, end=1, cantonese='你好')]
            selected, source = choose({'failedVoicePolicy': 'generic'}, job, cue, [actor])
            self.assertEqual(source, {0})
            (job / 'target-reference-recovery.json').write_text(json.dumps({
                'bank': dict(index=1, status='selected-unverified', selectedAudio=str(generic))}))
            selected, source = choose({'failedVoicePolicy': 'generic'}, job, cue, [generic])
            self.assertEqual(selected, [generic])
            self.assertEqual(source, set())
            self.assertFalse(json.loads((job / 'failed-voice-choices.json').read_text())['decisions'][0]['qualityCertified'])

    def test_first_take_and_original_source_are_distinct_choices(self):
        with tempfile.TemporaryDirectory() as directory:
            job = Path(directory)
            first = take(job / 'first.wav')
            latest = take(job / 'latest.wav')
            (job / 'normal-checks.json').write_text(json.dumps({'unresolved': [1], 'repairs': [
                dict(index=1, originalAudio=str(first), attempts=[])]}))
            cue = [dict(start=0, end=1, cantonese='你好')]
            selected, source = choose({'failedVoicePolicy': 'first-take'}, job, cue, [latest])
            self.assertEqual(selected, [first])
            self.assertEqual(source, set())
            selected, source = choose({'failedVoicePolicy': 'source'}, job, cue, [latest])
            self.assertEqual(selected, [latest])
            self.assertEqual(source, {0})

    def test_no_audible_generated_take_requests_source_instead_of_silent_output(self):
        with tempfile.TemporaryDirectory() as directory:
            job = Path(directory)
            missing = job / 'skipped-missing.wav'
            (job / 'normal-checks.json').write_text(json.dumps({'unresolved': [1], 'repairs': [
                dict(index=1, originalAudio=str(missing), attempts=[])]}))
            selected, source = choose({'failedVoicePolicy': 'first-take'}, job,
                                      [dict(start=0, end=1, cantonese='你好')], [missing])
            self.assertEqual(selected, [missing])
            self.assertEqual(source, {0})


if __name__ == '__main__':
    unittest.main()
