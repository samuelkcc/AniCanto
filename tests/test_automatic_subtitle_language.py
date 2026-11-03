"""Check automatic caption selection at preflight, submission and frozen resume boundaries."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows'),str(ROOT/'studio')]
import subtitle_choice
import source_modes
import subtitle_preference
from desktop_state import Store,read


def track(index,language='und'):
    return dict(index=index,codec_type='subtitle',codec_name='subrip',tags=dict(language=language))


class AutomaticSubtitleLanguage(unittest.TestCase):
    def preflight(self,video,streams,settings,row,**extra):
        with patch.object(subtitle_choice.subprocess,'check_output',return_value=json.dumps(dict(streams=streams)).encode()):
            return subtitle_choice.preflight(video,dict(ffprobe='fixture'),settings,row,**extra)

    def test_unknown_chinese_text_is_selected_without_a_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            video=Path(tmp)/'fixture.mkv';video.write_bytes(b'isolated')
            settings=dict(autoApproveSourceLanguage=True,dubLanguages=['yue'])
            with patch.object(subtitle_choice,'embedded_language',side_effect=['ja','zh']):
                result=self.preflight(video,[track(2),track(3)],settings,{})
            self.assertFalse(result['needsConfirmation'])
            self.assertEqual(result['selected']['stream'],3)
            self.assertEqual(result['selected']['languageMethod'],'bounded-subtitle-text')

    def test_known_chinese_does_not_need_a_text_probe(self):
        with tempfile.TemporaryDirectory() as tmp:
            video=Path(tmp)/'fixture.mkv';video.write_bytes(b'isolated')
            with patch.object(subtitle_choice,'embedded_language') as inspect:
                result=self.preflight(video,[track(2),track(3,'zh')],dict(autoApproveSourceLanguage=True,dubLanguages=['zh']),{})
            inspect.assert_not_called();self.assertEqual(result['selected']['stream'],3)

    def test_english_output_prefers_english_then_chinese(self):
        with tempfile.TemporaryDirectory() as tmp:
            video=Path(tmp)/'fixture.mkv';video.write_bytes(b'isolated')
            settings=dict(autoApproveSourceLanguage=True,dubLanguages=['en'])
            result=self.preflight(video,[track(2,'zh'),track(3,'en')],settings,{})
            self.assertEqual(result['selected']['stream'],3)
            with patch.object(subtitle_choice,'embedded_language',return_value='zh'):
                result=self.preflight(video,[track(2)],settings,{})
            self.assertEqual(result['selected']['stream'],2)

    def test_speech_fallback_is_frozen_and_does_not_reselect_foreign_captions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);video=root/'fixture.mkv';video.write_bytes(b'isolated')
            store=Store(root/'state');store.add([video]);store.settings.update(autoApproveSourceLanguage=True,dubLanguages=['yue'])
            row=store.queue[0];tracks=[track(2,'ja'),track(3)]
            with patch.object(subtitle_choice,'embedded_language',return_value='und'):
                result=self.preflight(video,tracks,store.settings,row)
            self.assertFalse(result['needsConfirmation']);self.assertIsNone(result['selected'])
            subtitle_choice.apply_to_row(row,result)
            # A matching but uncertain sidecar must not be rediscovered at submission.
            video.with_suffix('.srt').write_text('1\n00:00:01,000 --> 00:00:02,000\n...\n')
            request=store.submit(row);cfg=read(request)
            self.assertIsNone(cfg['subtitle']);self.assertEqual(cfg['subtitleSource'],'none')
            source_modes.configure(cfg,dict(streams=tracks),subtitle_preference.pick)
            self.assertEqual(cfg['sourceWorkflowEffective'],'speech-subtitles')
            self.assertFalse(cfg['sourceWorkflowResolution']['hasTextSubtitles']);self.assertFalse(cfg['ocr'])
            cfg['sourceProofreadBudgetSeconds']=17
            request.write_text(json.dumps(cfg))
            before=request.read_bytes();row['status']='paused';store.settings['autoApproveSourceLanguage']=False
            row['automaticSubtitleSelection']['speechOnly']=False
            self.assertEqual(store.submit(row),request);self.assertEqual(request.read_bytes(),before)
            frozen=read(request)
            self.assertEqual(frozen['sourceProofreadBudgetSeconds'],17)
            self.assertTrue(frozen['preferFirstAudibleTake'])

    def test_switch_off_retains_the_unknown_subtitle_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            video=Path(tmp)/'fixture.mkv';video.write_bytes(b'isolated')
            result=self.preflight(video,[track(2)],dict(autoApproveSourceLanguage=False,dubLanguages=['yue']),{})
            self.assertTrue(result['needsConfirmation'])

    def test_desktop_rpc_returns_audio_preflight_without_a_subtitle_prompt(self):
        from backend import Studio
        for platform in ['darwin','win32']:
            with self.subTest(platform=platform),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);video=root/'fixture.mkv';video.write_bytes(b'isolated')
                studio=Studio(root/'state',platform=platform)
                studio.store.add([video]);studio.store.settings.update(autoApproveSourceLanguage=True,dubLanguages=['yue'])
                row=studio.store.queue[0]
                metadata=dict(streams=[track(2)])
                heard=dict(kind='audio',language='ja',stream=0,supported=True,needsConfirmation=False)
                with patch.object(studio,'tools',return_value={'ffprobe':'fixture'}),patch.object(subtitle_choice.subprocess,'check_output',return_value=json.dumps(metadata).encode()),patch('source_language.preflight',return_value=heard):
                    result=studio.dispatch('source-language',dict(id=row['id']))
                self.assertFalse(result['needsConfirmation']);self.assertEqual(result['kind'],'audio')
                self.assertTrue(row['automaticSubtitleSelection']['speechOnly'])

    def test_manual_source_and_language_choice_stays_selected(self):
        with tempfile.TemporaryDirectory() as tmp:
            video=Path(tmp)/'fixture.mkv';video.write_bytes(b'isolated')
            settings=dict(autoApproveSourceLanguage=True,dubLanguages=['yue']);row={}
            result=self.preflight(video,[track(2,'ja'),track(3,'zh')],settings,row,selected='embedded:2',selected_language='ja')
            subtitle_choice.apply_to_row(row,result)
            again=self.preflight(video,[track(2,'ja'),track(3,'zh')],settings,row)
            self.assertEqual(again['selected']['stream'],2);self.assertEqual(again['selected']['language'],'ja')
            self.assertFalse(again['needsConfirmation'])

    def test_sampling_failure_and_limit_keep_the_run_automatic(self):
        with tempfile.TemporaryDirectory() as tmp:
            video=Path(tmp)/'fixture.mkv';video.write_bytes(b'isolated')
            with patch.object(subtitle_choice,'embedded_language',return_value='und') as inspect:
                result=self.preflight(video,[track(i) for i in range(2,12)],dict(autoApproveSourceLanguage=True,dubLanguages=['yue']),{})
            self.assertEqual(inspect.call_count,3)
            self.assertFalse(result['needsConfirmation']);self.assertTrue(result['automaticSelection']['speechOnly'])

    def test_real_unlabelled_embedded_chinese_reaches_the_frozen_request(self):
        ffmpeg=shutil.which('ffmpeg') or str(ROOT/'dist/AniCanto.app/Contents/Resources/bin/ffmpeg')
        if not Path(ffmpeg).is_file():self.skipTest('ffmpeg is unavailable')
        ffprobe=str(Path(ffmpeg).with_name('ffprobe'))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);sub=root/'captions.srt'
            sub.write_text('1\n00:00:00,000 --> 00:00:01,000\n你好朋友，我們一起出發吧。\n',encoding='utf-8')
            video=root/'fixture.mkv'
            subprocess.run([ffmpeg,'-v','error','-f','lavfi','-i','anullsrc=r=16000:cl=mono','-i',str(sub),'-map','0:a','-map','1:s','-t','1','-c:a','pcm_s16le','-c:s','srt',str(video)],check=True,timeout=20)
            sub.unlink()
            store=Store(root/'state');store.add([video]);store.settings.update(autoApproveSourceLanguage=True,dubLanguages=['yue'])
            row=store.queue[0]
            result=subtitle_choice.preflight(video,dict(ffmpeg=ffmpeg,ffprobe=ffprobe),store.settings,row)
            self.assertFalse(result['needsConfirmation']);self.assertEqual(result['selected']['language'],'zh')
            subtitle_choice.apply_to_row(row,result);cfg=read(store.submit(row))
            self.assertEqual(cfg['subtitleStream'],result['selected']['stream'])
            self.assertEqual(cfg['sourceCaptionLanguageSelected'],'zh')
            meta=json.loads(subprocess.check_output([ffprobe,'-v','error','-show_streams','-of','json',str(video)]))
            source_modes.configure(cfg,meta,subtitle_preference.pick)
            self.assertEqual(cfg['sourceWorkflowEffective'],'subtitles-speech')


if __name__=='__main__':unittest.main()
