"""A content-priority choice this video cannot serve is corrected, never a stop.

Samuel reported conversions that refused to start because the Expert flow choice did
not match the subtitle state. The app now switches to the matching flow, states the
swap in the flow notice, and keeps processing.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys_path_root = str(ROOT / 'Resources')
import sys
sys.path[:0] = [sys_path_root, str(ROOT / 'windows'), str(ROOT / 'studio')]

import source_workflow
import subtitle_preference
import workflow_localization

TEXT = ('speech-subtitles', 'subtitles-speech')
OCR = ('speech-ocr', 'ocr-speech')


def track(index, codec='mov_text', language=None):
    return dict(index=index, codec_type='subtitle', codec_name=codec,
                tags=dict(language=language) if language else {})


def expert_cfg(choice):
    return dict(sourceWorkflowRevision=source_workflow.SUBTITLE_REVISION,
                sourceSelectionRevision='basic-source-defaults-231', interfaceMode='expert',
                sourceWorkflow=choice, defaultSubtitleWorkflow='subtitles-speech',
                defaultOCRWorkflow='speech-ocr', subtitleLanguage=None, subtitleTitle=None)


def run(cfg, streams):
    notes = []
    source_workflow.configure(cfg, dict(streams=streams),
                              lambda rows, language=None, title=None, target=None: subtitle_preference.pick(rows, language, title, target),
                              emit=lambda stage, message, **extra: notes.append((stage, message)))
    return notes


class MismatchAutoCorrection(unittest.TestCase):
    def test_ocr_choice_on_a_subtitled_video_switches_to_the_subtitle_flow(self):
        for choice in OCR:
            with self.subTest(choice=choice):
                cfg = expert_cfg(choice)
                notes = run(cfg, [track(2, 'mov_text', 'yue')])
                self.assertEqual(cfg['sourceWorkflowEffective'], 'subtitles-speech')
                self.assertFalse(cfg['ocr'])
                self.assertEqual(cfg['subtitleStream'], 2)
                self.assertEqual(cfg['sourceFlow']['flow'], 'subtitles-speech')
                self.assertEqual(cfg['sourceFlow']['requested']['value'], choice)
                self.assertTrue(cfg['sourceWorkflowResolution']['requestedMismatch'])
                self.assertIn(source_workflow.FLOW_MISMATCH_NOTICE, notes[0][1])

    def test_subtitle_choice_on_an_unsubtitled_video_switches_to_ocr(self):
        for choice in TEXT:
            with self.subTest(choice=choice):
                cfg = expert_cfg(choice)
                notes = run(cfg, [])
                self.assertEqual(cfg['sourceWorkflowEffective'], 'speech-ocr')
                self.assertTrue(cfg['ocr'])
                self.assertIsNone(cfg['subtitle'])
                self.assertEqual(cfg['sourceFlow']['flow'], 'speech-ocr')
                self.assertIn(source_workflow.FLOW_MISMATCH_NOTICE, notes[0][1])

    def test_a_image_only_subtitle_video_treats_an_ocr_choice_as_a_match(self):
        cfg = expert_cfg('ocr-speech')
        run(cfg, [track(4, 'hdmv_pgo_subtitle')])
        self.assertEqual(cfg['sourceWorkflowEffective'], 'ocr-speech')
        self.assertNotIn('requestedMismatch', cfg['sourceWorkflowResolution'])

    def test_a_matching_choice_keeps_a_three_part_notice(self):
        cfg = expert_cfg('speech-subtitles')
        notes = run(cfg, [track(2, 'mov_text', 'eng')])
        self.assertEqual(cfg['sourceWorkflowEffective'], 'speech-subtitles')
        self.assertEqual(len(notes[0][1].split(' · ')), 3)

    def test_no_manual_choice_can_stop_a_run_on_either_subtitle_state(self):
        for streams in ([track(2, 'mov_text', 'yue')], [track(5, 'ass', 'zho')], [track(6, 'pgs_subtitle')], []):
            for choice in TEXT + OCR + ('auto',):
                with self.subTest(choice=choice, tracks=[t['codec_name'] for t in streams]):
                    cfg = expert_cfg(choice)
                    run(cfg, streams)
                    self.assertIn(cfg['sourceWorkflowEffective'], TEXT + OCR)
                    self.assertIn(cfg['translationSource'], ('audio-and-subtitles', 'audio-and-ocr'))

    def test_the_correction_line_translates_without_a_fallback(self):
        cfg = expert_cfg('speech-ocr')
        for stage, message in run(cfg, [track(2, 'mov_text', 'yue')]):
            shown = workflow_localization.present(stage, message, 'en')
            self.assertTrue(shown['localized'], message)
            self.assertIn('The Expert content-priority choice does not fit this video.', shown['message'])
            # Build 293 names the dub language in this line, so the English copy moved.
            self.assertIn('Readable text subtitles found (embedded subtitle track 2 is already '
                          'Cantonese, which is the dub language).', shown['message'])

    def test_an_unknown_workflow_value_is_still_refused_as_corrupt_settings(self):
        cfg = expert_cfg('subtitles-ocr')
        with self.assertRaises(ValueError):
            run(cfg, [track(2, 'mov_text', 'yue')])


if __name__ == '__main__':
    unittest.main()
