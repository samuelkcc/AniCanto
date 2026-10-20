import json
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'Resources'))
from normal_engine_fallback import repair, installed


def audio(path, seconds=1):
    with wave.open(str(path), 'wb') as f:
        f.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
        f.writeframes(b'\x00\x10' * round(24000 * seconds))
    return path


class AlternateEngineTests(unittest.TestCase):
    def trial(self, root, proof=None):
        (root / 'normal-checks.json').write_text(json.dumps(dict(unresolved=[1])))
        source = audio(root / 'source.wav')
        candidate = audio(root / 'candidate.wav')
        cues = [dict(start=0, end=2, cantonese='你究竟想點呀？', speakerId='r')]
        cfg = dict(productionMode='normal', targetLanguage='yue', duration=2, ttsBackend='drama3', storage=str(root), voiceProfiles=[dict(id='r', name='角色', reference=str(source), promptText='參考對白')])
        placement = [dict(fit=False, seconds=3, start=0, deadline=2)]
        proof = proof or dict(decision='cantonese', heard='你究竟想點呀？')
        return cfg, cues, placement, source, candidate, proof

    def test_verified_alternate_replaces_only_failed_line_and_keeps_prior_recording(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            cfg, cues, placement, source, candidate, proof = self.trial(root)
            before = source.read_bytes()
            with patch('normal_engine_fallback.installed', return_value=[('gpt-sovits-v2', 'v2ProPlus')]), patch('dubbing.gsv_audio', return_value=[candidate]) as generate, patch('normal_mode.inspect', return_value={1: proof}):
                self.assertEqual(repair(cfg, root, cues, [source], placement, Mock(), Mock()), [candidate])
                self.assertEqual(generate.call_args.args[0]['ttsBackend'], 'gpt-sovits-v2')
                self.assertEqual(generate.call_count, 1)
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(json.loads((root / 'normal-checks.json').read_text())['unresolved'], [])
            record = next(iter(json.loads((root / 'alternate-engine-recovery.json').read_text()).values()))
            self.assertEqual(record['status'], 'adopted')
            self.assertEqual(record['engine'], 'gpt-sovits-v2')

    def test_wrong_language_is_kept_for_review_but_not_adopted_or_repeated(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            cfg, cues, placement, source, candidate, _ = self.trial(root)
            proof = dict(decision='japanese', heard='日本語です', languageFailure=True)
            with patch('normal_engine_fallback.installed', return_value=[('gpt-sovits-v2', 'v2ProPlus')]), patch('dubbing.gsv_audio', return_value=[candidate]) as generate, patch('normal_mode.inspect', return_value={1: proof}):
                for _ in range(2):
                    self.assertEqual(repair(cfg, root, cues, [source], placement, Mock(), Mock()), [source])
            self.assertEqual(generate.call_count, 1)
            record = next(iter(json.loads((root / 'alternate-engine-recovery.json').read_text()).values()))
            self.assertEqual(record['status'], 'not-verified')
            self.assertTrue(Path(record['audio']).is_file())

    def test_switch_can_be_disabled(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            cfg, cues, placement, source, *_ = self.trial(root)
            cfg['automaticAlternateVoice'] = False
            with patch('normal_engine_fallback.installed') as installed:
                self.assertEqual(repair(cfg, root, cues, [source], placement, Mock(), Mock()), [source])
                installed.assert_not_called()

    def test_downloaded_weights_without_runtime_are_not_treated_as_usable(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            cfg = dict(storage=str(root), ttsBackend='drama3', targetLanguage='yue')
            row = dict(id='v2ProPlus', engine='gpt-sovits-v2', category='voice', estimatedMemoryGB=8)
            with patch('model_catalog.catalog', return_value=[row]), patch('model_catalog.resolve', return_value=root):
                self.assertEqual(installed(cfg), [])
                (root / 'gsv-ready.json').write_text('{}')
                self.assertEqual(installed(cfg), [], 'A different GPT runtime version is insufficient')
                (root / 'gsv-v2ProPlus-ready.json').write_text('{}')
                self.assertIn(('gpt-sovits-v2', 'v2ProPlus'), installed(cfg))


if __name__ == '__main__':
    unittest.main()
