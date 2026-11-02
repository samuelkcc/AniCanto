"""Reference wording is reused, saved per line, and never restarts at line one.

A Windows job (attempt 7ba77b0e, app 0.25.25, 2,561 cues) spent about two hours in
「角色參考」 although the episode already carried readable captions. The pass called
Whisper once per line, kept no per-line answer, and reported no work count, so the
bar stayed at 34% and every pause or retry began again at line 1. That reads to the
user as an endless translation loop. The flow default itself was correct and stays
pinned by tests/test_windows_source_default285.py; these cases freeze the four rules
that remove the stall.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Resources'))

import independent_voices
import production_progress
import speakers
import whisper_accel

MODEL = 'whisper-large-v3'
NOTHING = lambda *a, **k: None


def reference(folder):
    """One real PCM clip: the transcriber only ever receives a resampled waveform."""
    path = Path(folder) / 'reference.wav'
    tone = .2 * np.sin(np.arange(16000)) * .08
    sf.write(path, tone.astype('float32'), 16000)
    return path


def line(folder, name):
    return dict(id=name, name=name, reference=str(reference(folder)), promptText='',
                referenceRanges=[], referenceCandidates=[], language='ja')


def settings(**extra):
    cfg = dict(independentVoiceMapping=True, continueOnError=True, sourceLanguage='ja',
               speechModel=MODEL, referenceSpeechModel=MODEL, speechAcceleration='auto')
    cfg.update(extra)
    return cfg


class NoModel(unittest.TestCase):
    """Any call below that reaches a model is a regression, so loading one fails the test."""

    def load(self, *args, **kwargs):
        raise AssertionError('the reference pass must not load a model here')


class ReusedWording(NoModel):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.job = self.root / 'job'
        self.job.mkdir()
        self.addCleanup(self.temporary.cleanup)

    def test_saved_answer_for_this_clip_is_reused_without_any_inference(self):
        clip_folder = self.job / 'line-references' / 'a1b2c3'
        clip_folder.mkdir(parents=True)
        entry = line(clip_folder, '第 1 句原聲')
        speakers.write_line_transcript(entry, 'こんにちは。', 'ja', settings())
        with patch('whisper_accel.load', side_effect=self.load):
            speakers.transcribe_profiles(settings(), self.job, [entry], self.job, NOTHING)
        self.assertEqual(entry['promptText'], 'こんにちは。')
        self.assertEqual(entry['transcriptSource'], 'saved-line-transcript')

    def test_wording_the_caller_already_attached_is_never_retranscribed(self):
        entry = line(self.job, '第 2 句原聲')
        entry.update(promptText='さようなら。', transcriptSource='cue-source-wording')
        with patch('whisper_accel.load', side_effect=self.load):
            speakers.transcribe_profiles(settings(), self.job, [entry], self.job, NOTHING)
        self.assertEqual(entry['promptText'], 'さようなら。')
        self.assertEqual(entry['transcriptSource'], 'cue-source-wording')

    def test_a_saved_answer_is_not_reused_for_another_model_or_language(self):
        entry = line(self.job, '第 3 句原聲')
        speakers.write_line_transcript(entry, 'こんにちは。', 'ja', settings())
        self.assertEqual(speakers.read_line_transcript(entry, settings(referenceSpeechModel='whisper-medium'), 'ja'), '')
        self.assertEqual(speakers.read_line_transcript(entry, settings(), 'zh'), '')
        self.assertEqual(speakers.read_line_transcript(entry, settings(), 'ja'), 'こんにちは。')

    def test_a_sidecar_needs_an_absolute_reference_inside_an_existing_folder(self):
        self.assertIsNone(speakers.line_transcript_path(dict(reference='relative.wav')))
        self.assertIsNone(speakers.line_transcript_path(dict(reference=str(self.job / 'gone' / 'reference.wav'))))
        self.assertEqual(speakers.line_transcript_path(line(self.job, 'x')), self.job / 'transcript.json')


class ResumeInsideOnePass(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.job = self.root / 'job'
        self.job.mkdir()
        self.addCleanup(self.temporary.cleanup)

    def clips(self, *keys):
        rows = []
        for key in keys:
            folder = self.job / 'line-references' / key
            folder.mkdir(parents=True, exist_ok=True)
            rows.append(line(folder, f'第 {key} 句原聲'))
        return rows

    def test_each_answer_is_saved_before_the_next_line_starts(self):
        class Interrupted(Exception):
            pass

        heard = []

        def transcribe(audio, **options):
            heard.append(1)
            if len(heard) > 1:
                raise Interrupted('the worker stopped while line 2 was in flight')
            return iter([SimpleNamespace(text='こんにちは。')]), None

        model = SimpleNamespace(transcribe=transcribe)
        with patch('whisper_accel.load', return_value=model):
            with self.assertRaises(Interrupted):
                speakers.transcribe_profiles(settings(), self.job, self.clips('aaa', 'bbb'), self.job, NOTHING)
        # Line 1 finished, so its answer must already be on disk before anything else ran.
        saved = json.loads((self.job / 'line-references' / 'aaa' / 'transcript.json').read_text())
        self.assertEqual(saved['text'], 'こんにちは。')
        self.assertEqual(saved['revision'], speakers.LINE_CACHE)
        self.assertEqual(saved['model'], MODEL)

        # A retry of the same attempt must start at line 2, not at line 1.
        retry = self.clips('aaa', 'bbb')
        heard.clear()
        with patch('whisper_accel.load', return_value=model):
            speakers.transcribe_profiles(settings(), self.job, retry, self.job, NOTHING)
        self.assertEqual(retry[0]['promptText'], 'こんにちは。')
        self.assertEqual(retry[0]['transcriptSource'], 'saved-line-transcript')
        self.assertEqual(len(heard), 1)
        self.assertEqual(retry[1]['promptText'], 'こんにちは。')
        self.assertEqual(retry[1]['transcriptSource'], 'line-transcription')

    def test_a_short_reference_reaches_the_model_only_once(self):
        rows = self.clips('ccc')
        seen = []

        def transcribe(audio, **options):
            if not isinstance(audio, np.ndarray):
                raise TypeError("open() got an unexpected keyword argument 'metadata_errors'")
            seen.append(audio.shape)
            return iter([SimpleNamespace(text='テスト。')]), None

        notes = []
        emit = lambda stage, message, progress=None, **extra: notes.append((stage, message, extra))
        with patch('whisper_accel.load', return_value=SimpleNamespace(transcribe=transcribe)):
            speakers.transcribe_profiles(settings(), self.job, rows, self.job, emit)
        self.assertEqual(seen, [(16000,)])
        self.assertEqual(rows[0]['promptText'], 'テスト。')

    def test_the_pass_reports_work_counts_and_moves_the_running_bar(self):
        rows = self.clips('d', 'e', 'f')
        production_progress.reset()
        production_progress.begin(self.job)
        production_progress.phase(self.job, 'recognition', cached=True)
        production_progress.phase(self.job, 'roles', skipped=True)
        production_progress.phase(self.job, 'translation')
        self.addCleanup(production_progress.reset)
        before = production_progress.snapshot()['progress']
        notes = []
        emit = lambda stage, message, progress=None, **extra: notes.append((stage, message, extra))
        model = SimpleNamespace(transcribe=lambda audio, **options: (iter([SimpleNamespace(text='テスト。')]), None))
        with patch('whisper_accel.load', return_value=model):
            speakers.transcribe_profiles(settings(), self.job, rows, self.job, emit)
        after = production_progress.snapshot()['progress']
        self.assertGreater(after, before)
        work = [extra for _, _, extra in notes if extra.get('workID') == 'reference-transcript']
        self.assertTrue(work)
        self.assertEqual({row['workTotal'] for row in work}, {3})
        self.assertEqual(max(row['workCompleted'] for row in work), 3)
        self.assertTrue(any('原聲參考整理完成' in message for _, message, _extra in notes))


class CueOwnsItsWording(unittest.TestCase):
    def cue(self, **extra):
        row = dict(start=1, end=2, speechStart=1, speechEnd=2, japanese='こんにちは。',
                   primarySource=dict(text='こんにちは。'))
        row.update(extra)
        return row

    def test_a_reference_that_covers_the_cue_window_uses_that_cue_text(self):
        self.assertEqual(independent_voices.cue_wording(self.cue(), dict(originalReferenceSeconds=1.0), 'ja'), 'こんにちは。')

    def test_chinese_wording_is_not_treated_as_spoken_Japanese(self):
        row = self.cue(japanese='今天很好。', primarySource=dict(text='今天很好。'))
        self.assertEqual(independent_voices.cue_wording(row, dict(originalReferenceSeconds=1.0), 'ja'), '')
        self.assertEqual(independent_voices.cue_wording(row, dict(originalReferenceSeconds=1.0), 'zh'), '今天很好。')

    def test_a_reference_shorter_than_the_cue_window_is_refused(self):
        self.assertEqual(independent_voices.cue_wording(self.cue(), dict(originalReferenceSeconds=.4), 'ja'), '')
        self.assertEqual(independent_voices.cue_wording(self.cue(), dict(originalReferenceSeconds=.96), 'ja'), 'こんにちは。')

    def test_text_already_set_aside_by_source_policy_is_refused(self):
        for key in ('captionOnly', 'subtitleContentOnlyGap', 'sourcePolicyBlocked', 'sourceClockUnconfirmed'):
            self.assertEqual(independent_voices.cue_wording(self.cue(**{key: True}), dict(originalReferenceSeconds=1.0), 'ja'), '')

    def test_a_caption_owned_job_costs_no_reference_inference_at_all(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            rate = 44100
            time_axis = np.arange(rate * 6) / rate
            source = folder / 'dialogue.wav'
            sf.write(source, (.15 * np.sin(2 * np.pi * 180 * time_axis)).astype('float32'), rate, subtype='FLOAT')
            cues = [dict(start=0, end=.6, speechStart=.1, speechEnd=.5, japanese='こんにちは。'),
                    dict(start=3, end=4, speechStart=3.2, speechEnd=3.6, japanese='さようなら。')]
            cfg = dict(storage=str(folder), job=str(folder), audio=str(source), dialoguePath=str(source),
                       cues=cues, roleAnalysisMode='independent', sourceLanguage='ja', continueOnError=True)

            def child(config, action, request, emit):
                self.assertEqual(action, 'independent-voices')
                independent_voices.prepare(request, NOTHING)

            notes = []
            with patch('dubbing.model_job', side_effect=child), \
                    patch('model_catalog.selected', return_value=MODEL), \
                    patch('model_catalog.choice', return_value=None), \
                    patch('model_catalog.folder', return_value=folder), \
                    patch('whisper_accel.load', side_effect=AssertionError('captions own every line; no model may load')):
                independent_voices.assign(cfg, folder, cues, lambda stage, message, *a, **k: notes.append((stage, message)))
            profiles = json.loads((folder / 'independent-voices.json').read_text())['profiles']
            self.assertEqual([p['promptText'] for p in profiles], ['こんにちは。', 'さようなら。'])
            self.assertEqual({p['transcriptSource'] for p in profiles}, {'cue-source-wording'})
            self.assertTrue(any('直接用返本句時段嘅原文' in message for stage, message in notes))


class NamedGpuFailureIsRemembered(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.job = self.root / 'job'
        self.job.mkdir()
        self.addCleanup(self.temporary.cleanup)

    def test_the_notice_names_the_library_the_loader_asked_for(self):
        runner = object.__new__(whisper_accel.AcceleratedWhisper)
        runner.cfg = dict(speechModel=MODEL, storage=str(self.root))
        runner.chosen = {}
        runner.cpu = None
        runner.job = self.job
        runner.close = lambda: None
        notes = []
        runner.emit = lambda stage, message, **extra: notes.append((stage, message))
        with patch.object(whisper_accel, 'cpu_model', return_value=None):
            runner.fallback(ValueError('Library cublas64_12.dll is not found or cannot be loaded'))
        self.assertTrue(any('cublas64_12.dll' in message for _, message in notes))
        self.assertTrue(any('唔會由第 1 句重新聽' in message for _, message in notes))
        saved = json.loads((self.job / 'whisper-compute.json').read_text())
        self.assertEqual(saved['state'], 'fallback')
        self.assertEqual(saved['id'], MODEL)

    def test_a_proven_fallback_is_recalled_for_the_same_model(self):
        self.assertFalse(whisper_accel.prior_cpu_fallback(self.job, MODEL))
        (self.job / 'whisper-compute.json').write_text(json.dumps(dict(state='fallback', id=MODEL)))
        self.assertTrue(whisper_accel.prior_cpu_fallback(self.job, MODEL))
        self.assertFalse(whisper_accel.prior_cpu_fallback(self.job, 'whisper-medium'))
        (self.job / 'whisper-compute.json').write_text(json.dumps(dict(state='inference-passed', id=MODEL)))
        self.assertFalse(whisper_accel.prior_cpu_fallback(self.job, MODEL))

    def test_the_reference_pass_stays_on_cpu_once_cuda_has_already_failed(self):
        seen = []
        loader = lambda options, path, emit: seen.append(options)
        (self.job / 'whisper-compute.json').write_text(json.dumps(dict(state='fallback', id=MODEL)))
        with patch('whisper_accel.load', side_effect=loader):
            speakers.load_reference_model(settings(), self.job, NOTHING)
        self.assertEqual(seen[0]['speechAcceleration'], 'cpu')
        self.assertEqual(seen[0]['speechModel'], MODEL)

    def test_a_fresh_job_still_offers_the_gpu_path_once(self):
        seen = []
        loader = lambda options, path, emit: seen.append(options)
        with patch('whisper_accel.load', side_effect=loader):
            speakers.load_reference_model(settings(), self.job, NOTHING)
        self.assertEqual(seen[0]['speechAcceleration'], 'auto')

    def test_every_present_cuda_folder_is_offered_once(self):
        site = self.root / 'site-packages'
        torch_folder = site / 'torch'
        (torch_folder / 'lib').mkdir(parents=True)
        cublas = site / 'nvidia' / 'cublas' / 'lib'
        cublas.mkdir(parents=True)
        tools = self.root / 'storage' / 'tools'
        cuda13 = tools / 'drama-full-cudart13'
        cuda13.mkdir(parents=True)
        found = [str(path) for path in whisper_accel.cuda_library_folders(torch_folder / '__init__.py', self.root / 'storage')]
        self.assertIn(str(torch_folder / 'lib'), found)
        self.assertIn(str(cublas), found)
        self.assertIn(str(cuda13), found)
        self.assertNotIn(str(tools / 'drama-full-cudart12'), found)
        self.assertNotIn(str(site / 'nvidia' / 'cudnn' / 'lib'), found)
        self.assertEqual(len(found), len(set(found)))


if __name__ == '__main__':
    unittest.main()
