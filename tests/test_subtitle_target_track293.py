"""The dub output language decides which subtitle track the automatic choice takes.

Samuel reported an iPhone dub where Japanese captions and Cantonese speech both
reached the finished film. This module freezes the import-time rule on the shared
module: with a Cantonese or Mandarin dub, take a Chinese track; with an English dub,
take an English track; never prefer a foreign-language track over an untagged one.
"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'Resources'), str(ROOT / 'studio')]

import source_workflow
import subtitle_preference
import worker
import workflow_localization


def track(index, language=None, title=None):
    return dict(index=index, codec_type='subtitle', codec_name='mov_text',
                tags=dict(language=language) if language else {})


def cfg_for(target, **extra):
    cfg = dict(sourceWorkflowRevision=source_workflow.REVISION,
               sourceSelectionRevision='basic-source-defaults-231', interfaceMode='basic',
               sourceWorkflow='auto', defaultSubtitleWorkflow='subtitles-speech',
               defaultOCRWorkflow='ocr-speech', subtitleLanguage=None, subtitleTitle=None,
               targetLanguage=target)
    cfg.update(extra)
    return cfg


class TargetOrder(unittest.TestCase):
    def test_revision_names_the_target_language_rule(self):
        self.assertEqual(subtitle_preference.REVISION, 'subtitle-track-preference-2-target-language')

    def test_cantonese_dub_prefers_the_chinese_tracks_over_japanese(self):
        tracks = [track(1, 'jpn'), track(2, 'und'), track(3, 'zh-hant')]
        self.assertEqual(subtitle_preference.pick(tracks, target='yue')['index'], 3)

    def test_an_untagged_track_outranks_a_foreign_track_for_cantonese(self):
        # The old fixed order put a tagged Japanese track above an untagged one.
        tracks = [track(1, 'jpn'), track(2, 'und')]
        self.assertEqual(subtitle_preference.pick(tracks, target='yue')['index'], 2)
        self.assertEqual(subtitle_preference.pick([track(2, 'und'), track(1, 'jpn')], target='yue')['index'], 2)

    def test_mandarin_dub_prefers_simplified_then_traditional(self):
        self.assertEqual(subtitle_preference.pick([track(1, 'zh-hant'), track(2, 'zh-hans')],
                                                  target='zh')['index'], 2)
        self.assertEqual(subtitle_preference.pick([track(1, 'jpn'), track(2, 'zh-hant')],
                                                  target='zh')['index'], 2)

    def test_english_dub_prefers_the_english_track(self):
        self.assertEqual(subtitle_preference.pick([track(1, 'jpn'), track(2, 'eng')],
                                                  target='en')['index'], 2)
        self.assertEqual(subtitle_preference.pick([track(1, 'zh-hant'), track(2, 'eng')],
                                                  target='en')['index'], 2)

    def test_an_explicit_request_still_outranks_the_target_order(self):
        tracks = [track(1, 'zh-hant'), track(2, 'jpn')]
        self.assertEqual(subtitle_preference.pick(tracks, 'jpn', target='yue')['index'], 2)

    def test_no_target_keeps_the_previous_order(self):
        self.assertEqual(subtitle_preference.pick([track(1, 'und'), track(2, 'jpn')])['index'], 2)

    def test_target_script_flag_states_when_the_track_already_is_the_dub_language(self):
        self.assertTrue(subtitle_preference.in_target_script(track(1, 'yue'), 'yue'))
        self.assertTrue(subtitle_preference.in_target_script(track(1, 'eng'), 'en'))
        self.assertFalse(subtitle_preference.in_target_script(track(1, 'zh-hant'), 'yue'))
        self.assertEqual(subtitle_preference.target_label('zh'), '普通話')
        self.assertEqual(subtitle_preference.target_label('nonsense'), '')


class SidecarChoice(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='sidecar293-'))
        self.video = self.root / 'movie.mkv'
        self.video.write_bytes(b'fixture-video')

    def test_english_dub_takes_the_english_sidecar(self):
        (self.root / 'movie.zh-Hant.srt').write_text('hant', encoding='utf-8')
        (self.root / 'movie.eng.srt').write_text('eng', encoding='utf-8')
        self.assertEqual(worker.select_sidecar_subtitle(self.video, 'en').name, 'movie.eng.srt')

    def test_cantonese_dub_still_takes_the_chinese_sidecar(self):
        (self.root / 'movie.eng.srt').write_text('eng', encoding='utf-8')
        (self.root / 'movie.zh-Hant.srt').write_text('hant', encoding='utf-8')
        self.assertEqual(worker.select_sidecar_subtitle(self.video, 'yue').name, 'movie.zh-Hant.srt')


class FrozenRequest(unittest.TestCase):
    def configure(self, target, streams, **extra):
        notes = []
        cfg = cfg_for(target, **extra)
        source_workflow.configure(cfg, dict(streams=streams), worker.select_batch_subtitle,
                                  emit=lambda stage, message, **more: notes.append(message))
        return cfg, notes

    def test_japanese_and_untagged_tracks_never_win_a_cantonese_job(self):
        cfg, notes = self.configure('yue', [track(1, 'jpn'), track(2, 'und')])
        self.assertEqual(cfg['subtitleStream'], 2)
        self.assertFalse(cfg['sourceWorkflowResolution']['trackInTargetLanguage'])
        self.assertIn('未標示語言優先', cfg['sourceFlow']['reason'])
        self.assertIn('配音語言 廣東話', cfg['sourceFlow']['reason'])

    def test_english_job_records_the_english_target(self):
        cfg, notes = self.configure('en', [track(1, 'jpn'), track(2, 'eng')])
        self.assertEqual(cfg['subtitleStream'], 2)
        self.assertEqual(cfg['sourceWorkflowResolution']['targetLanguage'], 'en')
        self.assertTrue(cfg['sourceWorkflowResolution']['trackInTargetLanguage'])
        self.assertIn('跟返配音語言 英文', cfg['sourceFlow']['reason'])

    def test_dub_language_falls_back_to_the_first_requested_track(self):
        self.assertEqual(source_workflow.dub_language(dict(dubLanguages=['en', 'yue'])), 'en')
        self.assertEqual(source_workflow.dub_language(dict(targetLanguage='zh')), 'zh')
        self.assertEqual(source_workflow.dub_language(dict(targetLanguage='klingon')), 'yue')
        self.assertEqual(source_workflow.dub_language({}), 'yue')


class LocalizedNotice(unittest.TestCase):
    """The English interface must translate each new notice instead of hiding it."""

    def test_new_notices_localize_without_a_fallback(self):
        cases = [
            '偵測到文字字幕（內置字幕軌 2；跟返配音語言 廣東話）',
            '偵測到文字字幕（內置字幕軌 3；跟返配音語言 英文）',
            '偵測到文字字幕（內置字幕軌 2；配音語言 廣東話；未標示語言優先）',
            '自動選擇本集字幕軌 5（yue；配音語言 廣東話；cantonese 優先）。',
        ]
        for text in cases:
            with self.subTest(text=text):
                english, known = workflow_localization.english(text)
                self.assertTrue(known, english)
                self.assertNotIn('Worker diagnostic', english)


if __name__ == '__main__':
    unittest.main()
