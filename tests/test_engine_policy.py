import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Resources'))
import engine_policy
import multitrack

class EnginePolicyTests(unittest.TestCase):
    def test_old_qwen_only_frozen_job_gets_active_engine_and_audit(self):
        cfg=dict(ttsBackend='qwen-tts',defaultAudioEngine='qwen-tts',selectedEngines=['qwen-tts'],model='mlx:qwen-text',asrModel='asr-1.7b-8bit',qwenModel='qwen-1.7b-8bit')
        emit=Mock()
        self.assertTrue(engine_policy.migrate(cfg,emit))
        self.assertEqual(cfg['ttsBackend'],'cosyvoice3')
        self.assertEqual(cfg['defaultAudioEngine'],'cosyvoice3')
        self.assertEqual(cfg['selectedEngines'],['cosyvoice3'])
        self.assertEqual(cfg['model'],'mlx:qwen-text')
        self.assertEqual(cfg['asrModel'],'asr-1.7b-8bit')
        self.assertEqual(cfg['qwenModel'],'qwen-1.7b-8bit')
        self.assertEqual(cfg['engineSelectionRecovery'][0]['previous'],['qwen-tts'])
        emit.assert_called_once()
        self.assertFalse(engine_policy.migrate(cfg,emit))
        emit.assert_called_once()
    def test_two_languages_produce_four_dub_tracks_without_mutating_old_selection(self):
        cfg=dict(ttsBackend='gpt-sovits',selectedEngines=['cosyvoice3','gpt-sovits','qwen-tts'],dubLanguages=['yue','en'])
        old=copy.deepcopy(cfg)
        selected=multitrack.selected(cfg)
        self.assertEqual(selected,['cosyvoice3','gpt-sovits'])
        self.assertEqual(len([(language,engine) for language in cfg['dubLanguages'] for engine in selected]),4)
        self.assertEqual(cfg,old)
    def test_retirement_does_not_mask_unknown_engine(self):
        with self.assertRaises(ValueError):multitrack.selected(dict(selectedEngines=['../../invalid','qwen-tts']))
    def test_v3_retirement_preserves_other_engines_and_old_configuration_fields(self):
        cfg=dict(ttsBackend='gpt-sovits-v3',selectedEngines=['gpt-sovits-v3','gpt-sovits-v2','cosyvoice3'],defaultAudioEngine='gpt-sovits-v3',gsvVersion='v3')
        self.assertTrue(engine_policy.migrate(cfg))
        self.assertEqual(cfg['selectedEngines'],['gpt-sovits-v2','cosyvoice3'])
        self.assertNotEqual(cfg['ttsBackend'],'gpt-sovits-v3');self.assertEqual(cfg['gsvVersion'],'v3')
        only=dict(ttsBackend='gpt-sovits-v3',selectedEngines=['gpt-sovits-v3'])
        engine_policy.migrate(only);self.assertEqual(only['selectedEngines'],['gpt-sovits'])
    def test_active_configuration_unchanged(self):
        cfg=dict(ttsBackend='gpt-sovits',selectedEngines=['gpt-sovits'],defaultAudioEngine='gpt-sovits')
        old=copy.deepcopy(cfg)
        self.assertFalse(engine_policy.migrate(cfg))
        self.assertEqual(cfg,old)

if __name__=='__main__':unittest.main()
