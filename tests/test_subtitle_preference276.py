"""Automatic subtitle track and sidecar preference (Samuel, 2026-10-31)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / 'Resources'))

import subtitle_preference
import worker


def track(index, language=None, title=None, **extra):
    tags = {}
    if language is not None:
        tags['language'] = language
    if title is not None:
        tags['title'] = title
    return dict(index=index, codec_type='subtitle', codec_name='ass', tags=tags, **extra)


class SubtitleTrackPreference(unittest.TestCase):
    def test_traditional_beats_simplified_beats_other_language(self):
        tracks = [track(1, 'eng'), track(2, 'zho'), track(3, 'zh-hans'), track(4, 'zh-hant')]
        self.assertEqual(subtitle_preference.pick(tracks)['index'], 4)
        remaining = [t for t in tracks if t['index'] != 4]
        self.assertEqual(subtitle_preference.pick(remaining)['index'], 3)
        remaining = [t for t in remaining if t['index'] != 3]
        self.assertEqual(subtitle_preference.pick(remaining)['index'], 2)

    def test_cantonese_leads_and_simplified_beats_plain_chinese(self):
        tracks = [track(1, 'zho'), track(2, 'zh-hans'), track(3, 'yue')]
        self.assertEqual(subtitle_preference.pick(tracks)['index'], 3)
        self.assertEqual(subtitle_preference.pick([track(1, 'zho'), track(2, 'zh-hans')])['index'], 2)

    def test_title_states_the_script_when_the_tag_is_plain(self):
        tracks = [track(1, 'zho', '简体'), track(2, 'zho', '繁體')]
        self.assertEqual(subtitle_preference.pick(tracks)['index'], 2)

    def test_other_language_is_used_when_no_chinese_track_exists(self):
        tracks = [track(1, 'eng'), track(2, 'jpn')]
        self.assertEqual(subtitle_preference.pick(tracks)['index'], 1)
        self.assertEqual(subtitle_preference.pick([track(1, 'eng'), track(2)])['index'], 1)
        self.assertEqual(subtitle_preference.pick([track(1), track(2, 'eng')])['index'], 2)

    def test_explicit_choice_outranks_the_automatic_order(self):
        tracks = [track(1, 'zh-hant'), track(2, 'jpn')]
        self.assertEqual(subtitle_preference.pick(tracks, 'jpn')['index'], 2)
        self.assertEqual(subtitle_preference.pick(tracks, 'chi', 'Main')['index'], 1)

    def test_ui_placeholder_language_is_not_a_filter(self):
        self.assertEqual(subtitle_preference.pick([track(1), track(2, 'eng')], '未標示語言')['index'], 2)
        self.assertIsNone(subtitle_preference.pick([]))


class SidecarPreference(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='sidecar276-'))
        self.video = self.root / 'episode.mkv'
        self.video.write_bytes(b'fixture-video')

    def names(self):
        return sorted(p.name for p in self.root.iterdir() if p.suffix != '.mkv')

    def test_chinese_sidecar_beats_a_plain_sidecar(self):
        (self.root / 'episode.srt').write_text('plain', encoding='utf-8')
        (self.root / 'episode.zh-Hant.srt').write_text('hant', encoding='utf-8')
        (self.root / 'episode.zh-Hans.srt').write_text('hans', encoding='utf-8')
        self.assertEqual(worker.select_sidecar_subtitle(self.video).name, 'episode.zh-Hant.srt')

    def test_plain_sidecar_beats_a_foreign_sidecar(self):
        (self.root / 'episode.srt').write_text('plain', encoding='utf-8')
        (self.root / 'episode.eng.srt').write_text('english', encoding='utf-8')
        self.assertEqual(worker.select_sidecar_subtitle(self.video).name, 'episode.srt')

    def test_only_the_plain_sidecar_still_works(self):
        (self.root / 'episode.ass').write_text('plain', encoding='utf-8')
        self.assertEqual(worker.select_sidecar_subtitle(self.video).name, 'episode.ass')
        (self.root / 'episode.ass').unlink()
        self.assertIsNone(worker.select_sidecar_subtitle(self.video))

    def test_a_different_title_sidecar_is_not_matched(self):
        (self.root / 'other.srt').write_text('other', encoding='utf-8')
        self.assertIsNone(worker.select_sidecar_subtitle(self.video))


class ResolutionRecord(unittest.TestCase):
    def test_resolution_states_the_chosen_track_family(self):
        import source_workflow
        cfg = dict(sourceWorkflowRevision=source_workflow.REVISION, interfaceMode='basic',
                   sourceWorkflow='auto', defaultSubtitleWorkflow='subtitles-speech',
                   defaultOCRWorkflow='speech-ocr', subtitleLanguage=None, subtitleTitle=None)
        meta = dict(streams=[track(1, 'eng'), track(2, 'zh-hans'), track(3, 'zh-hant')])
        source_workflow.configure(cfg, meta, worker.select_batch_subtitle)
        self.assertEqual(cfg['sourceWorkflowEffective'], 'subtitles-speech')
        self.assertEqual(cfg['sourceContentPriority'], 'subtitles')
        self.assertEqual(cfg['subtitleStream'], 3)
        self.assertEqual(cfg['sourceWorkflowResolution']['trackFamily'], 'traditional')
        self.assertEqual(cfg['sourceWorkflowResolution']['trackPreferenceRevision'],
                         subtitle_preference.REVISION)

    def test_no_text_subtitle_keeps_speech_primary_without_implicit_ocr(self):
        import source_workflow
        cfg = dict(sourceWorkflowRevision=source_workflow.REVISION, interfaceMode='basic',
                   sourceWorkflow='auto', defaultSubtitleWorkflow='subtitles-speech',
                   defaultOCRWorkflow='speech-ocr', subtitleLanguage=None, subtitleTitle=None)
        source_workflow.configure(cfg, dict(streams=[dict(index=9, codec_type='subtitle',
                                                          codec_name='pgssub', tags={})]),
                                  worker.select_batch_subtitle)
        self.assertEqual(cfg['sourceWorkflowEffective'], 'speech-subtitles')
        self.assertEqual(cfg['sourceContentPriority'], 'speech')
        self.assertFalse(cfg['ocr'])


if __name__ == '__main__':
    unittest.main()
