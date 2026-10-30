"""Cached Windows cloud files and interrupted provider reads use distinct paths."""
import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import source_preparation as prep
class Cloud274(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.source=self.root/'Google Drive/movie.mkv';self.source.parent.mkdir();self.source.write_bytes(b'abcd'*800000)
 def request(self):return dict(source=str(self.source),identity=prep.identity(self.source),progress=str(self.root/'progress.json'),result=str(self.root/'result.json'))
 def test_cached_regular_windows_file_in_cloud_folder_skips_hydration(self):
  ctx=prep.Preparation(self.root/'app',self.source)
  with patch.object(prep,'windows_attributes',return_value=0x20),patch.object(ctx,'capture',side_effect=AssertionError('No cloud read for local data')):ctx.ensure_local()
  self.assertEqual(ctx.state['sourceReadPolicy'],'local-data');self.assertEqual(self.source.stat().st_size,3200000)
 def test_recall_flags_override_a_pinned_user_preference(self):
  for flag in [0x1000,0x40000,0x400000]:
   with patch.object(prep,'windows_attributes',return_value=flag|0x80000):self.assertTrue(prep.requires_hydration(self.source))
 def test_unknown_provider_state_keeps_the_full_read(self):
  with patch.object(prep,'windows_attributes',return_value=None):self.assertTrue(prep.requires_hydration(self.source))
 def test_halfway_eof_or_read_error_resumes_without_duplicate_bytes(self):
  for fails in ['eof','error']:
   request=self.request();calls=[0];pauses=[]
   class Stream:
    def __init__(inner):inner.file=self.source.open('rb')
    def seek(inner,n):inner.file.seek(n)
    def close(inner):inner.file.close()
    def read(inner,n):
     calls[0]+=1
     if calls[0]==2:
      if fails=='error':raise OSError('fixture provider temporarily unavailable')
      return b''
     return inner.file.read(n)
   prep.read_source(request,opener=Stream,pause=lambda seconds:pauses.append(seconds))
   value=json.loads(Path(request['result']).read_text());self.assertEqual(value['bytesRead'],3200000);self.assertEqual(value['sha256'],hashlib.sha256(self.source.read_bytes()).hexdigest());self.assertTrue(pauses)
 def test_download_can_progress_for_longer_than_the_idle_limit(self):
  request=self.request();calls=[0];elapsed=[0]
  class Stream:
   def __init__(inner):inner.file=self.source.open('rb')
   def seek(inner,n):inner.file.seek(n)
   def close(inner):inner.file.close()
   def read(inner,n):
    calls[0]+=1
    return b'' if calls[0] in [2,4] else inner.file.read(n)
  def pause(seconds):elapsed[0]+=70
  prep.read_source(request,opener=Stream,pause=pause,clock=lambda:elapsed[0],max_idle=120)
  self.assertGreater(elapsed[0],120);self.assertEqual(json.loads(Path(request['result']).read_text())['bytesRead'],3200000)
 def test_source_change_during_a_stall_still_fails(self):
  request=self.request()
  class Stream:
   def seek(inner,n):pass
   def close(inner):pass
   def read(inner,n):self.source.write_bytes(b'changed');return b''
  with self.assertRaisesRegex(RuntimeError,'changed'):prep.read_source(request,opener=Stream,pause=lambda _:None)
  self.assertFalse(Path(request['result']).exists())
 def test_local_probe_failure_is_failed_not_cloud_waiting(self):
  ctx=prep.Preparation(self.root/'app',self.source);ctx.fail(RuntimeError('invalid media'));self.assertEqual(ctx.state['state'],'failed')
if __name__=='__main__':unittest.main()
