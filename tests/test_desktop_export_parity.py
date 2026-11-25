import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Resources'))
import delivery_policy
import export_packages
from export_picture import PictureCoverageError
import export_retry
import fast_mode
import opening
from track_control import UserSkipped


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg tools required')
class DesktopExportTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.root = Path(self.work.name)
        self.base = self.root / 'base.mp4'
        self.source = self.root / 'source.mp4'
        self.candidate = self.root / 'packaged.mp4'
        self.cfg = dict(ffmpeg='ffmpeg', ffprobe='ffprobe', video=str(self.source),
                        duration=4, targetLanguage='yue', productionMode='fast',
                        burnOutputCaptions=True)

    def run_cli(self, args):
        result = subprocess.run(list(map(str, args)), capture_output=True, check=False)
        if result.returncode:
            raise RuntimeError(result.stderr.decode())
        return result.stdout

    def probe(self, movie):
        return json.loads(self.run_cli(['ffprobe', '-v', 'error', '-show_streams',
                                       '-show_format', '-of', 'json', movie]))

    def build_video(self, dest, picture=4, originals=False):
        cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i',
               f'color=c=purple:s=160x96:r=24:d={picture}', '-f', 'lavfi', '-i',
               'sine=f=440:d=4']
        if originals:
            cmd += ['-f','lavfi','-i','sine=f=680:d=4','-map','0:v','-map','1:a',
                    '-map','2:a','-metadata:s:a:0','language=jpn',
                    '-metadata:s:a:1','language=jpn','-metadata:s:a:0','handler_name=Japanese',
                    '-metadata:s:a:1','handler_name=Japanese']
        else:
            cmd += ['-metadata:s:a:0','language=yue']
        self.run_cli([*cmd, '-c:v', 'libx264', '-c:a', 'aac', dest])

    def test_full_audio_does_not_hide_short_picture(self):
        self.build_video(self.base, picture=2)
        self.assertAlmostEqual(float(self.probe(self.base)['format']['duration']), 4, places=2)
        with self.assertRaises(PictureCoverageError):
            fast_mode.validation(self.cfg, self.root, [], self.base, self.run_cli, Mock())
        self.build_video(self.base)
        report=fast_mode.validation(self.cfg, self.root, [], self.base, self.run_cli, Mock())
        self.assertAlmostEqual(report['pictureRange']['duration'], 4, places=2)

    def test_keep_both_same_language_originals_when_captions_fail(self):
        self.build_video(self.base)
        self.build_video(self.source, originals=True)
        streams=[s for s in self.probe(self.source)['streams'] if s['codec_type']=='audio']
        captions=self.root/'broken.srt'
        captions.write_text('invalid input')
        result, meta, original, embedded, warnings = export_packages.package(
            self.cfg,self.run_cli,Mock(),self.base,self.candidate,4,streams,
            [dict(path=captions,mode='yue',language='yue')],self.probe(self.base))
        self.assertEqual(result,self.candidate)
        self.assertEqual(len(original),2)
        self.assertEqual(embedded,[])
        self.assertEqual([w['kind'] for w in warnings],['embedded-subtitle-package'])
        audio=[s for s in meta['streams'] if s['codec_type']=='audio']
        self.assertEqual([s['tags']['language'] for s in audio],['yue','jpn','jpn'])
        self.assertEqual([s['tags']['handler_name'] for s in audio[1:]],['Japanese (1)','Japanese (2)'])
        self.assertEqual([s['disposition']['default'] for s in audio],[1,0,0])
        self.assertEqual(len(self.probe(self.base)['streams']),2)

    def test_required_track_and_user_cancel_cannot_report_success(self):
        self.build_video(self.base)
        self.build_video(self.source)
        metadata=self.probe(self.base)
        source_streams=[dict(index=999)]
        with self.assertRaises(RuntimeError):
            export_packages.package(self.cfg,self.run_cli,Mock(),self.base,self.candidate,4,
                                    source_streams,[],metadata,required=True)
        with self.assertRaises(UserSkipped):
            export_packages.package(self.cfg,Mock(side_effect=UserSkipped('stop')),Mock(),
                                    self.base,self.candidate,4,source_streams,[],metadata)
        self.assertFalse(self.candidate.exists())


class ExportRequestPolicyTests(unittest.TestCase):
    def test_picture_retry_uses_one_existing_slot(self):
        with tempfile.TemporaryDirectory() as folder, patch('video_acceleration.encode') as encode:
            cfg=dict(deliveryPolicyRevision=delivery_policy.REVISION)
            cmd=['ffmpeg','-c:v','copy','-tag:v','hvc1',str(Path(folder)/'draft.mp4')]
            validate=Mock(side_effect=[PictureCoverageError('short'),'valid'])
            self.assertEqual(export_retry.run(cfg,folder,cmd,Mock(),Mock(),validate),'valid')
            self.assertIn('copy',encode.call_args_list[0].args[1])
            self.assertIn('libx264',encode.call_args_list[1].args[1])
            self.assertNotIn('-tag:v',encode.call_args_list[1].args[1])
            with self.assertRaisesRegex(RuntimeError,'已用完'):
                export_retry.run(cfg,folder,cmd,Mock(),Mock(),Mock())
            self.assertEqual(encode.call_count,2)

    def test_opening_range_uses_distinct_cache_and_witnessed_chapters(self):
        with tempfile.TemporaryDirectory() as folder:
            video=Path(folder)/'video.mkv'
            video.touch()
            cfg=dict(video=str(video),storage=folder,ffmpeg='ffmpeg',executable='helper')
            meta={'format':{'duration':'1200'},'chapters':[
                {'tags':{'title':'Opening'},'start_time':'350','end_time':'420'},
                {'tags':{'title':'ED'},'start_time':'780','end_time':'850'}]}
            run=Mock(return_value=b'[{"start":0,"duration":1,"music":0,"singing":0,"speech":0}]')
            self.assertEqual(opening.detect(cfg,meta,run,Mock()),[])
            broad=opening.detect(dict(cfg,openingDetectionMinutes=10), meta,run,Mock())
            self.assertEqual([r['start'] for r in broad],[350,780])
            self.assertEqual(opening.detect(cfg,meta,run,Mock()),[])
            with self.assertRaises(ValueError):
                opening.detect(dict(cfg,openingDetectionMinutes=17),meta,run,Mock())
