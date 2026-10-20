import concurrent.futures,json,shutil,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import studio_preview
ROOT=Path(__file__).resolve().parents[1]
FF=shutil.which('ffmpeg') or str(ROOT/'dist/AniCanto.app/Contents/Resources/bin/ffmpeg')
PROBE=shutil.which('ffprobe') or str(ROOT/'dist/AniCanto.app/Contents/Resources/bin/ffprobe')
TOOLS=dict(ffmpeg=FF,ffprobe=PROBE)
class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.source=self.root/'日本語.mkv'
        subprocess.run([FF,'-v','error','-y','-f','lavfi','-i','testsrc2=s=320x180:r=12:d=2','-c:v','libx264','-pix_fmt','yuv420p',str(self.source)],check=True)
    def tearDown(self):self.tmp.cleanup()
    def test_h264_mkv_is_remuxed_and_concurrent_requests_share_one_preparation(self):
        original=subprocess.run;calls=[]
        def run(*a,**k):
            if a[0][0]==FF:calls.append(a[0]);time.sleep(.1)
            return original(*a,**k)
        with patch.object(studio_preview.subprocess,'run',side_effect=run):
            with concurrent.futures.ThreadPoolExecutor(2) as pool:
                results=list(pool.map(lambda _:studio_preview.prepare(self.root,self.source,TOOLS,'win32'),range(2)))
        self.assertEqual(len(calls),1);self.assertEqual(results[0]['path'],results[1]['path']);self.assertEqual(results[0]['mode'],'remux')
        self.assertIn('copy',calls[0]);self.assertNotIn('libx264',calls[0]);self.assertTrue(Path(results[0]['path']).is_file())
        self.assertEqual(studio_preview.status(self.root,self.source)['progress'],1)
        self.assertFalse(list(Path(results[0]['path']).parent.glob('*.partial.mp4')))
    def test_hevc_mac_uses_hvc1_remux_but_compatibility_fallback_is_h264(self):
        hevc=self.root/'hevc.mkv'
        subprocess.run([FF,'-v','error','-y','-i',str(self.source),'-c:v','libx265','-x265-params','pools=1:frame-threads=1:log-level=error',str(hevc)],check=True,stderr=subprocess.DEVNULL)
        m=studio_preview.prepare(self.root,hevc,TOOLS,'darwin');self.assertEqual(m['mode'],'remux');self.assertTrue(m['fallbackAvailable'])
        meta=json.loads(subprocess.check_output([PROBE,'-v','error','-show_streams','-of','json',m['path']]))
        self.assertEqual(meta['streams'][0]['codec_tag_string'],'hvc1')
        safe=studio_preview.prepare(self.root,hevc,TOOLS,'darwin',True);self.assertEqual(safe['mode'],'encode');self.assertFalse(safe['fallbackAvailable'])
        meta=json.loads(subprocess.check_output([PROBE,'-v','error','-show_streams','-of','json',safe['path']]))
        self.assertEqual(meta['streams'][0]['codec_name'],'h264')
    def test_progress_is_readable_while_other_request_holds_lock(self):
        d=studio_preview.folder(self.root,self.source);d.mkdir(parents=True)
        (d/'status.json').write_text(json.dumps(dict(stage='encode',duration=100)))
        (d/'progress.txt').write_text('out_time_us=35000000\nprogress=continue\n')
        with studio_preview.exclusive(d/'prepare.lock'):
            self.assertEqual(studio_preview.status(self.root,self.source)['progress'],.35)

if __name__=='__main__':unittest.main()
