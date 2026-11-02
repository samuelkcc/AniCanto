"""Verify opt-in overlay suppression, source uncertainty and persistent reservations."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'Resources'), str(ROOT / 'windows')]
import caption_speech_guard as guard
from atomic_files import write_json


class CaptionSpeechGuard300(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.caption = '本廣告由世界級品牌提供贊助，立即購買全新系列產品，享用期間限定優惠。'
        for name in ['japanese-original.wav', 'stem.wav']:
            with wave.open(str(self.root / name), 'wb') as f:
                f.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
                f.writeframes(b'\x00\x01' * 48000)
        self.cfg = dict(skipNonDialogueCaptions=True, captionSpeechGuardRevision=guard.REVISION,
                        captionOnlyRevision='caption-only-no-dialogue-270', sourceLanguage='ja',
                        targetLanguage='yue', dubLanguages=['yue'], storage=str(self.root),
                        dialoguePath=str(self.root / 'stem.wav'), duration=3, startOffset=0,
                        ffmpeg='fixture', model='selected-model', port=999, ttsBackend='drama3')
        self.cue = dict(start=.1, end=1, japanese='はい', text='はい', enabled=True,
                        captionRecords=[dict(id='one', text=self.caption, start=0, end=3)],
                        primarySource=dict(kind='embedded', text=self.caption, captionIDs=['one']),
                        cantonese=self.caption)
        self.analysis = dict(key='frozen-source', segments=[dict(start=.2, end=.8, text='はい', words=[dict(word='はい', probability=.9)])],
                             noDialogueEvidence=dict(complete=True, dualInput=True,
                                 sourceSHA256=self.sha('japanese-original.wav'), stemSHA256=self.sha('stem.wav'), startOffset=0))
        write_json(self.root / 'japanese-analysis.json', self.analysis)
        self.answer = dict(speechClear=True, relation='unrelated-overlay', captionIsOverlay=True)
        self.calls = []
        self.recognizer_calls = []
        def chat(port, model, messages, **kw):
            self.calls.append(messages)
            return json.dumps(self.answer) if kw.get('structured') else '係呀'
        self.worker = SimpleNamespace(emit=lambda *a, **kw: None, atomic_json=write_json,
                                      run=lambda *a: b'\0' * 32000, ollama_chat=chat)
        def transcribe(*a, **kw):
            self.recognizer_calls.append(kw)
            return iter([SimpleNamespace(text='はい')]), None
        self.model = SimpleNamespace(transcribe=transcribe)
        self.addCleanup(patch.stopall)
        patch('whisper_accel.load', return_value=self.model).start()
        patch('source_evidence.caption_records', return_value=self.cue['captionRecords']).start()

    def sha(self, name):
        return hashlib.sha256((self.root / name).read_bytes()).hexdigest()

    def run_guard(self, cue=None):
        cue = copy.deepcopy(self.cue if cue is None else cue)
        guard.review(self.worker, self.cfg, self.root, [cue])
        return cue

    def test_speech_is_translated_before_caption_comparison_and_voice_is_omitted(self):
        from dubbing import required_dialogue
        cue = self.run_guard()
        self.assertTrue(guard.selected(self.cfg, cue))
        self.assertEqual(cue['originalSpeechReason'], guard.REASON)
        self.assertEqual(required_dialogue(self.cfg, [cue]), [])
        self.assertEqual(cue['cantonese'], self.caption)
        self.assertEqual((cue['start'], cue['end']), (.1, 1))
        self.assertEqual(len(self.calls), 2)
        self.assertNotIn(self.caption, self.calls[0][1]['content'])
        self.assertIn(self.caption, self.calls[1][1]['content'])
        self.assertEqual(len(self.recognizer_calls), 1)

    def test_confirmed_overlay_keeps_full_caption_and_skips_spoken_length_rewrites(self):
        import script_fit, translation_editorial
        cue = self.run_guard()
        self.assertIsNone(script_fit.fit_reason(self.cfg, cue, [cue], 0))
        cfg = dict(self.cfg, repairGroupsRevision='repair-groups-263', translationTextReview=True)
        translation_editorial.review(self.worker, cfg, self.root, [cue])
        self.assertEqual(cue['cantonese'], self.caption)
        self.assertEqual(len(self.calls), 2)

    def test_related_or_uncertain_answer_keeps_normal_target(self):
        for relation, clear in [('related', True), ('uncertain', False), ('unrelated-overlay', False)]:
            with self.subTest(relation=relation, clear=clear):
                (self.root / 'caption-speech-guard.json').unlink(missing_ok=True)
                self.answer.update(relation=relation, speechClear=clear)
                self.assertNotIn('captionSpeechMismatch', self.run_guard())

    def test_no_opt_in_or_legacy_job_calls_no_model(self):
        for cfg in [dict(self.cfg, skipNonDialogueCaptions=False), dict(self.cfg, captionSpeechGuardRevision=None)]:
            guard.review(self.worker, cfg, self.root, [copy.deepcopy(self.cue)])
        self.assertEqual(self.calls, [])
        self.assertEqual(self.recognizer_calls, [])

    def test_short_matching_caption_does_not_enter_the_ai_gate(self):
        self.cue['captionRecords'][0]['text'] = '係呀'
        self.assertNotIn('captionSpeechMismatch', self.run_guard())
        self.assertEqual(self.calls, [])

    def test_disagreeing_original_and_stem_is_unconfirmed_not_wrong(self):
        self.model.transcribe = lambda *a, **k: (iter([SimpleNamespace(text='いいえ')]), None)
        self.assertNotIn('captionSpeechMismatch', self.run_guard())
        self.assertEqual(self.calls, [])
        row = next(iter(json.loads((self.root / 'caption-speech-guard.json').read_text())['rows'].values()))
        self.assertEqual(row['decision'], 'source-unconfirmed')

    def test_missing_or_low_confidence_evidence_keeps_target(self):
        for probability in [.2, float('nan'), float('inf'), -1, 2]:
            self.analysis['segments'][0]['words'][0]['probability'] = probability
            write_json(self.root / 'japanese-analysis.json', self.analysis)
            self.assertNotIn('captionSpeechMismatch', self.run_guard())
        self.assertEqual(self.recognizer_calls, [])

    def test_incomplete_proof_and_corrupt_ledger_never_authorize_suppression(self):
        cue = self.run_guard()
        cue['captionSpeechGuardEvidence']['comparison'] = {'relation': 'unrelated-overlay'}
        self.assertFalse(guard.selected(self.cfg, cue))
        for bad in [[], dict(revision=guard.REVISION, rows=[], spentSeconds=0)]:
            write_json(self.root / 'caption-speech-guard.json', bad)
            self.assertNotIn('captionSpeechMismatch', self.run_guard())
        self.assertEqual(len(self.calls), 2)

    def test_positive_activity_can_recheck_missing_asr_before_comparison(self):
        self.analysis['segments'] = []
        write_json(self.root / 'japanese-analysis.json', self.analysis)
        self.cue.update(japanese='', text='', captionSpeechRescue=True, speechRegions=[dict(start=.2, end=.8)])
        self.model.transcribe = lambda *a, **kw: (iter([SimpleNamespace(text='はい', words=[SimpleNamespace(probability=.9)])]), None)
        cue = self.run_guard()
        self.assertTrue(guard.selected(self.cfg, cue))
        self.assertEqual(cue['captionSpeechGuardEvidence']['recheckedOriginalTranscript'], 'はい')
        self.assertEqual(self.analysis['segments'], [])
        self.assertEqual(len(self.calls), 2)

    def test_missing_asr_without_positive_activity_never_runs_the_guard(self):
        self.analysis['segments'] = []
        write_json(self.root / 'japanese-analysis.json', self.analysis)
        self.assertNotIn('captionSpeechMismatch', self.run_guard())
        self.assertEqual(self.calls, [])

    def test_japanese_terminal_vowel_notation_preserves_lexical_differences(self):
        self.assertEqual(guard.normalize('すごいなぁ'), guard.normalize('すごいなー'))
        self.assertNotEqual(guard.normalize('はい'), guard.normalize('いいえ'))
        self.assertNotEqual(guard.normalize('なぃ'), guard.normalize('な'))
        self.assertEqual(guard.normalize('ファ'), 'ファ')

    def test_saved_success_reuses_proof_without_new_recognition_or_model_calls(self):
        cue = self.run_guard()
        second = self.run_guard(cue)
        self.assertTrue(guard.selected(self.cfg, second))
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(len(self.recognizer_calls), 1)

    def test_failed_call_stays_spent_on_resume(self):
        def fail(*a, **kw):
            self.calls.append('failed')
            raise RuntimeError('isolated model fault')
        self.worker.ollama_chat = fail
        cue = self.run_guard()
        self.run_guard(cue)
        self.assertEqual(self.calls, ['failed'])
        self.assertEqual(len(self.recognizer_calls), 1)
        row = next(iter(json.loads((self.root / 'caption-speech-guard.json').read_text())['rows'].values()))
        self.assertEqual(row['attempts'], 1)

    def test_interrupted_time_and_count_caps_do_not_refund(self):
        write_json(self.root / 'caption-speech-guard.json', dict(revision=guard.REVISION, rows={}, spentSeconds=599, activeSince=time.time()-5))
        self.assertNotIn('captionSpeechMismatch', self.run_guard())
        self.assertEqual(self.calls, [])
        saved = json.loads((self.root / 'caption-speech-guard.json').read_text())
        self.assertGreaterEqual(saved['spentSeconds'], 604)
        write_json(self.root / 'caption-speech-guard.json', dict(revision=guard.REVISION, rows={str(i): {} for i in range(12)}, spentSeconds=0))
        self.assertNotIn('captionSpeechMismatch', self.run_guard())
        self.assertEqual(self.calls, [])

    def test_stale_hash_restores_target_without_refunding(self):
        cue = self.run_guard()
        with (self.root / 'stem.wav').open('ab') as file:
            file.write(b'changed-fixture')
        updated = self.run_guard(cue)
        self.assertNotIn('captionSpeechMismatch', updated)
        self.assertEqual(len(self.calls), 2)

    def test_existing_target_or_manual_recording_is_not_replaced(self):
        write_json(self.root / 'timing.json', [dict(index=1, renderedSeconds=1, originalPreserved=False)])
        self.assertNotIn('captionSpeechMismatch', self.run_guard())
        (self.root / 'timing.json').unlink()
        self.cue['editorAudio'] = 'existing.wav'
        self.assertNotIn('captionSpeechMismatch', self.run_guard())
        self.assertEqual(self.calls, [])

    def test_default_upgrade_and_frozen_request_are_separate(self):
        from desktop_state import Store, defaults
        self.assertIs(defaults()['skipNonDialogueCaptions'], False)
        frozen = self.root / 'old-request.json'
        frozen.write_text('{"skipNonDialogueCaptions":true,"captionOnlyRevision":"caption-only-no-dialogue-270"}')
        original = frozen.read_bytes()
        state = self.root / 'studio'
        state.mkdir()
        write_json(state / 'desktop-state.json', dict(settings=dict(skipNonDialogueCaptions=True), queue=[dict(id='old', video='fixture', status='paused', request=str(frozen), productionSettings=dict(skipNonDialogueCaptions=True))]))
        store = Store(state)
        self.assertIs(store.settings['skipNonDialogueCaptions'], False)
        self.assertIs(store.queue[0]['productionSettings']['skipNonDialogueCaptions'], False)
        store.settings['skipNonDialogueCaptions'] = True
        store.save()
        self.assertIs(Store(state).settings['skipNonDialogueCaptions'], True)
        self.assertEqual(store.submit(store.queue[0]), frozen)
        self.assertEqual(frozen.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
