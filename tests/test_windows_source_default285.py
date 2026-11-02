"""Standard mode picks the content flow from the subtitles that really exist.

Samuel reported a Windows standard-mode job that did not use 字幕 > 語音 for a video
with embedded subtitles. This test freezes the rule and the notice the app shows, so
the chosen flow is never invisible again.
"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'Resources'), str(ROOT / 'windows'), str(ROOT / 'studio')]

import source_workflow
import subtitle_preference
import workflow_localization


def track(index, codec='mov_text', language=None):
    return dict(index=index, codec_type='subtitle', codec_name=codec,
                tags=dict(language=language) if language else {})


def basic_cfg(**extra):
    # A stored speech-first preference must not override the standard-mode rule.
    cfg = dict(sourceWorkflowRevision=source_workflow.SUBTITLE_REVISION,
               sourceSelectionRevision='basic-source-defaults-231', interfaceMode='basic',
               sourceWorkflow='auto', defaultSubtitleWorkflow='speech-subtitles',
               defaultOCRWorkflow='ocr-speech', subtitleLanguage=None, subtitleTitle=None)
    cfg.update(extra)
    return cfg


def run(cfg, streams, select=None):
    notes = []
    source_workflow.configure(cfg, dict(streams=streams),
                              select or (lambda rows, language=None, title=None, target=None:
                                         subtitle_preference.pick(rows, language, title, target)),
                              emit=lambda stage, message, **extra: notes.append((stage, message)))
    return notes


class StandardFlowChoice(unittest.TestCase):
    def test_readable_embedded_subtitle_selects_subtitles_first(self):
        cfg = basic_cfg()
        notes = run(cfg, [track(1, 'subrip', 'eng'), track(2, 'mov_text', 'yue')])
        self.assertEqual(cfg['sourceWorkflowEffective'], 'subtitles-speech')
        self.assertFalse(cfg['ocr'])
        self.assertEqual(cfg['sourceFlow']['flow'], 'subtitles-speech')
        self.assertEqual(cfg['sourceFlow']['label'], '字幕 > 語音')
        self.assertIn('內置字幕軌 2', cfg['sourceFlow']['reason'])
        # The chosen track already states the dub language, so the notice says that plainly.
        self.assertIn('跟返配音語言 廣東話', cfg['sourceFlow']['reason'])
        self.assertTrue(cfg['sourceWorkflowResolution']['trackInTargetLanguage'])
        self.assertEqual(cfg['sourceWorkflowResolution']['targetLanguage'], 'yue')
        self.assertEqual(notes, [('來源流程',
                                  '字幕 > 語音 · 偵測到文字字幕（內置字幕軌 2；跟返配音語言 廣東話） · 自動偵測')])

    def test_image_only_subtitle_selects_speech_first_with_ocr(self):
        cfg = basic_cfg()
        run(cfg, [track(4, 'hdmv_pgo_subtitle'), track(5, 'pgs_subtitle')])
        self.assertEqual(cfg['sourceWorkflowEffective'], 'speech-ocr')
        self.assertTrue(cfg['ocr'])
        self.assertEqual(cfg['sourceFlow']['label'], '語音 > OCR')
        self.assertIn('hdmv_pgo_subtitle', cfg['sourceFlow']['reason'])
        self.assertEqual(cfg['sourceWorkflowResolution']['imageSubtitleCodecs'], ['hdmv_pgo_subtitle', 'pgs_subtitle'])

    def test_a_video_without_subtitle_tracks_states_that_fact(self):
        cfg = basic_cfg()
        run(cfg, [])
        self.assertEqual(cfg['sourceWorkflowEffective'], 'speech-ocr')
        self.assertEqual(cfg['sourceFlow']['reason'], '冇任何字幕軌')

    def test_external_sidecar_is_reported_as_an_external_subtitle(self):
        with tempfile.TemporaryDirectory() as folder:
            sidecar = Path(folder) / 'episode.zh-Hant.srt'
            sidecar.write_text('1\n00:00:00,000 --> 00:00:02,000\n測試\n', encoding='utf-8')
            cfg = basic_cfg(subtitle=str(sidecar))
            run(cfg, [track(2, 'mov_text', 'jpn')])
            self.assertEqual(cfg['sourceWorkflowEffective'], 'subtitles-speech')
            self.assertEqual(cfg['subtitleSource'], 'external')
            self.assertEqual(cfg['sourceFlow']['reason'], '偵測到文字字幕（外掛字幕檔案）')

    def test_expert_manual_choice_is_labelled_as_manual(self):
        cfg = basic_cfg(interfaceMode='expert', sourceWorkflow='speech-subtitles')
        notes = run(cfg, [track(1, 'subrip', 'eng')])
        self.assertEqual(cfg['sourceWorkflowEffective'], 'speech-subtitles')
        self.assertTrue(cfg['sourceFlow']['manual'])
        self.assertIn('專家模式手動選擇', notes[0][1])

    def test_every_flow_notice_part_localizes_without_a_fallback(self):
        cases = [[track(2, 'mov_text', 'yue')], [track(4, 'hdmv_pgo_subtitle')], [],
                 [track(1, 'ass', 'zho')], [track(3, 'ass', 'eng')]]
        for streams in cases:
            with self.subTest(streams=streams):
                cfg = basic_cfg()
                for stage, message in run(cfg, streams):
                    parts = [stage] + message.split(' · ')
                    for part in parts:
                        english, known = workflow_localization.english(part, stage=part == stage)
                        self.assertTrue(known, part)
                        self.assertNotIn('Worker diagnostic', english)
                        self.assertNotIn('Processing', english)

    def test_audio_only_source_still_reports_its_flow(self):
        cfg = basic_cfg(translationSource='audio-only')
        notes = run(cfg, [track(1, 'mov_text', 'yue')])
        self.assertEqual(cfg['sourceWorkflowEffective'], 'speech-only')
        self.assertEqual(notes[0][0], '來源流程')


class DesktopRowNotice(unittest.TestCase):
    """The saved desktop row carries the flow so the panel can show it after a restart."""

    def setUp(self):
        from desktop_state import Store
        self.root = Path(tempfile.mkdtemp(prefix='source-flow-285-'))
        self.video = self.root / 'episode.mkv'
        self.video.write_bytes(b'fixture-video')
        self.store = Store(self.root)
        self.store.mode = 'basic'
        self.store.queue.append(dict(id='row-1', video=str(self.video), status='waiting', progress=0))
        self.store.selected = 'row-1'

    def test_submit_clears_an_older_notice_and_an_event_records_the_new_one(self):
        from desktop_state import read
        from output_delivery import presentation
        row = self.store.row('row-1')
        row['sourceFlow'] = dict(flow='speech-ocr', label='語音 > OCR', reason='冇任何字幕軌', manual=False, automatic=True, track=None)
        self.store.submit(row)
        self.assertNotIn('sourceFlow', row)
        self.assertEqual(read(self.store.row('row-1')['request'])['sourceWorkflow'], 'auto')
        self.assertEqual(read(self.store.row('row-1')['request'])['sourceSelectionRevision'], 'basic-source-defaults-231')
        self.store.event(row, dict(stage='來源流程', message='字幕 > 語音 · 偵測到文字字幕（內置字幕軌 2） · 自動偵測',
                                   sourceFlow=dict(flow='subtitles-speech', label='字幕 > 語音', reason='偵測到文字字幕（內置字幕軌 2）', manual=False, automatic=True, track=2)))
        shown = presentation(self.root, self.store.row('row-1'))
        self.assertEqual(shown['sourceFlow']['flow'], 'subtitles-speech')
        self.assertEqual(shown['sourceFlow']['track'], 2)
        self.store.event(row, dict(stage='準備'))
        self.assertEqual(self.store.row('row-1')['sourceFlow']['flow'], 'subtitles-speech')


if __name__ == '__main__':
    unittest.main()
