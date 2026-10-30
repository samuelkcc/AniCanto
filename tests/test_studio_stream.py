"""Source playback integration: audio choice, clocks, cache, access and teardown."""
import concurrent.futures,hashlib,json,math,os,signal,subprocess,sys,tempfile,time,unittest,urllib.request,urllib.error
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'Resources'));import studio_preview,studio_stream
FF=str(R/'dist/AniCanto.app/Contents/Resources/bin/ffmpeg');PROBE=str(R/'dist/AniCanto.app/Contents/Resources/bin/ffprobe');W=None
class Playback(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  global W
  cls.scratch=tempfile.TemporaryDirectory(prefix='anicanto-source-player-');W=Path(cls.scratch.name)
  if not Path(FF).is_file():raise unittest.SkipTest('Packaged FFmpeg is unavailable.')
  subprocess.run([FF,'-v','error','-y','-f','lavfi','-i','testsrc2=s=320x180:r=24:d=20','-f','lavfi','-i','sine=frequency=440:duration=20','-f','lavfi','-i','sine=frequency=880:duration=20','-map','0:v','-map','1:a','-map','2:a','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',str(W/'日本語 source.mkv')],check=True)
 @classmethod
 def tearDownClass(cls):cls.scratch.cleanup()
 def test_source_selection_and_no_movie_cache(self):
  source=W/'日本語 source.mkv';before=hashlib.sha256(source.read_bytes()).hexdigest()
  for track in [1,2]:
   m=studio_preview.prepare(W/'unused-root',source,dict(ffmpeg=FF,ffprobe=PROBE),'darwin',audio_stream=track);self.assertEqual(m['path'],str(source.resolve()));self.assertEqual(m['selectedAudioStream'],track);self.assertEqual(m['mode'],'demand');self.assertFalse((W/'unused-root').exists())
  self.assertEqual(before,hashlib.sha256(source.read_bytes()).hexdigest())
  for invalid in [-1,0,99,'1',True]:
   with self.assertRaises(ValueError):studio_preview.source_playback(source,dict(ffmpeg=FF,ffprobe=PROBE),invalid)
 def test_lru_exact_clock_and_selected_audio(self):
  import numpy as np
  media=studio_stream.Media(dict(source=str(W/'日本語 source.mkv'),duration=20,ffmpeg=FF,audioStream=2))
  for n in range(4):
   data=media.segment(n);path=W/f'boundary-{n}.ts';path.write_bytes(data)
   meta=json.loads(subprocess.check_output([PROBE,'-v','error','-show_format','-of','json',str(path)]))['format'];start=float(meta['start_time']);length=float(meta['duration']);self.assertLess(abs(start-n*6),.06);self.assertLess(abs(length-min(6,20-n*6)),.08)
   audio=subprocess.check_output([FF,'-v','error','-i',str(path),'-vn','-f','f32le','-ac','1','-ar','16000','pipe:1']);x=np.frombuffer(audio,dtype=np.float32);frequency=np.fft.rfftfreq(len(x),1/16000)[np.argmax(abs(np.fft.rfft(x)))];self.assertLess(abs(frequency-880),3)
  same=media.segment(2);self.assertIs(same,media.cache[2]);self.assertLessEqual(sum(map(len,media.cache.values())),studio_stream.MAX_BYTES)
  with self.assertRaises(ValueError):media.segment(4)
 def test_nonzero_source_timestamp_and_last_interval(self):
  source=W/'offset.mkv'
  subprocess.run([FF,'-v','error','-y','-i',str(W/'日本語 source.mkv'),'-t','12','-map','0:v','-map','0:a:0','-c','copy','-output_ts_offset','5',str(source)],check=True)
  value=studio_preview.source_playback(source,dict(ffmpeg=FF,ffprobe=PROBE))
  self.assertLess(abs(value['duration']-12),.15)
  m=studio_stream.Media(value['streamConfig']);data=m.segment(1);path=W/'offset-segment.ts';path.write_bytes(data)
  meta=json.loads(subprocess.check_output([PROBE,'-v','error','-show_format','-of','json',str(path)]))['format']
  self.assertLess(abs(float(meta['start_time'])-6),.06)
  self.assertLess(abs(float(meta['duration'])-6),.15)
 def test_auth_and_teardown(self):
  config=dict(source=str(W/'日本語 source.mkv'),duration=20,ffmpeg=FF,audioStream=1,owner=os.getpid())
  p=subprocess.Popen([sys.executable,str(R/'Resources/studio_stream.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,start_new_session=True);p.stdin.write(json.dumps(config)+'\n');p.stdin.close();v=json.loads(p.stdout.readline())
  try:
   playlist=urllib.request.urlopen(v['url']).read().decode();self.assertIn('#EXT-X-ENDLIST',playlist);self.assertIn('#EXTINF:2.000000',playlist)
   with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(v['url'].replace(v['streamID'],'bad-token'))
   with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(v['url'].replace('index.m3u8','../movie'))
   req=urllib.request.Request(v['url'],headers={'Host':'foreign.example'})
   with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(req)
  finally:os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=3);p.stdout.close()
 def test_parent_exit_stops_active_decoder(self):
  import shlex,threading
  fake=W/'slow-ffmpeg';pidfile=W/'decoder.pid'
  fake.write_text('#!/bin/sh\necho $$ > '+shlex.quote(str(pidfile))+'\nexec /bin/sleep 30\n');fake.chmod(0o700)
  owner=subprocess.Popen(['/bin/sleep','30']);cfg=dict(source='unused.mkv',duration=20,ffmpeg=str(fake),audioStream=1,owner=owner.pid)
  process=subprocess.Popen([sys.executable,str(R/'Resources/studio_stream.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,start_new_session=True);process.stdin.write(json.dumps(cfg)+'\n');process.stdin.close();value=json.loads(process.stdout.readline())
  def request():
   try:urllib.request.urlopen(value['url'].replace('index.m3u8','0.ts'),timeout=8).read()
   except (OSError,urllib.error.URLError):pass
  reader=threading.Thread(target=request,daemon=True);reader.start()
  try:
   deadline=time.monotonic()+4
   while not pidfile.exists() and time.monotonic()<deadline:time.sleep(.05)
   self.assertTrue(pidfile.exists());decoder=int(pidfile.read_text());owner.terminate();owner.wait();process.wait(timeout=5);reader.join(timeout=2)
   state=subprocess.run(['/bin/ps','-o','stat=','-p',str(decoder)],capture_output=True,text=True).stdout.strip()
   self.assertTrue(not state or state.startswith('Z'),state)
  finally:
   if owner.poll() is None:owner.terminate();owner.wait()
   if process.poll() is None:os.killpg(process.pid,signal.SIGTERM);process.wait()
   process.stdout.close()
 def test_parent_exit_stops_reader_group(self):
  # The owner is a synthetic process, never the user's app.
  owner=subprocess.Popen(['/bin/sleep','30']);cfg=dict(source=str(W/'日本語 source.mkv'),duration=20,ffmpeg=FF,audioStream=1,owner=owner.pid)
  p=subprocess.Popen([sys.executable,str(R/'Resources/studio_stream.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,start_new_session=True);p.stdin.write(json.dumps(cfg)+'\n');p.stdin.close();v=json.loads(p.stdout.readline());owner.terminate();owner.wait()
  try:p.wait(timeout=5);self.assertIsNotNone(p.returncode)
  finally:
   if p.poll() is None:os.killpg(p.pid,signal.SIGTERM);p.wait()
   p.stdout.close()
if __name__=='__main__':unittest.main()
