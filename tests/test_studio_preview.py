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
    def test_windows_mkv_opens_source_without_full_movie_preparation(self):
        with patch.object(studio_preview.subprocess,'run',wraps=subprocess.run) as run:
            with concurrent.futures.ThreadPoolExecutor(2) as pool:
                results=list(pool.map(lambda _:studio_preview.prepare(self.root,self.source,TOOLS,'win32'),range(2)))
        self.assertFalse(any(c.args[0][0]==FF for c in run.call_args_list))
        self.assertTrue(all(r['path']==str(self.source.resolve()) and r['mode']=='demand' and not r['fullMovieCopy'] for r in results))
        self.assertFalse((self.root/'cache').exists())
    def test_mac_mkv_uses_source_reader_and_does_not_create_movie_cache(self):
        m=studio_preview.prepare(self.root,self.source,TOOLS,'darwin')
        self.assertEqual(m['mode'],'demand');self.assertEqual(m['path'],str(self.source.resolve()));self.assertFalse(m['fullMovieCopy'])
        self.assertEqual(m['streamConfig']['source'],str(self.source.resolve()))
        self.assertFalse((self.root/'cache').exists())
        safe=studio_preview.prepare(self.root,self.source,TOOLS,'darwin',True)
        self.assertEqual(safe['mode'],'demand');self.assertFalse((self.root/'cache').exists())
    def test_progress_is_readable_while_other_request_holds_lock(self):
        d=studio_preview.folder(self.root,self.source);d.mkdir(parents=True)
        (d/'status.json').write_text(json.dumps(dict(stage='encode',duration=100)))
        (d/'progress.txt').write_text('out_time_us=35000000\nprogress=continue\n')
        with studio_preview.exclusive(d/'prepare.lock'):
            self.assertEqual(studio_preview.status(self.root,self.source)['progress'],.35)

if __name__=='__main__':unittest.main()
