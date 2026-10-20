"""Windows rename-denied regression, without needing a GPU or user library."""
import contextlib,io,json,sys,tempfile,unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import atomic_files,processing_time,production_progress,worker

class AtomicFilesTests(unittest.TestCase):
 def test_short_windows_lock_retries_and_closes_temporary_handle(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'record.json';path.write_text('{"old":true}')
   replace=atomic_files.os.replace;calls=[]
   def locked(source,target):
    calls.append(source)
    if len(calls)<3:raise PermissionError(13,'Access is denied')
    replace(source,target)
   with patch.object(atomic_files.os,'replace',side_effect=locked),patch.object(atomic_files.time,'sleep') as wait:
    worker.atomic_json(path,{'new':'廣東話'})
   self.assertEqual(json.loads(path.read_text()),{'new':'廣東話'});self.assertEqual(wait.call_count,2)
   self.assertFalse(list(Path(folder).glob('*.tmp')))
 def test_persistent_failure_keeps_last_good_data_and_critical_error(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'script.json';original=b'{"saved":"original"}';path.write_bytes(original)
   with patch.object(atomic_files.os,'replace',side_effect=PermissionError(13,'denied')),patch.object(atomic_files.time,'sleep'):
    with self.assertRaises(PermissionError):worker.atomic_json(path,{'saved':'changed'})
   self.assertEqual(path.read_bytes(),original);self.assertFalse(list(Path(folder).glob('*.tmp')))
 def test_concurrent_writers_never_share_temporary_file_or_truncate_json(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'record.json'
   with ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(lambda n:atomic_files.write_json(path,{'index':n,'payload':'聲'*5000}),range(60)))
   data=json.loads(path.read_text());self.assertIn(data['index'],range(60));self.assertEqual(data['payload'],'聲'*5000)
   self.assertFalse(list(Path(folder).glob('*.tmp')))
 def test_timing_access_denied_does_not_abort_worker_events_or_export(self):
  with tempfile.TemporaryDirectory() as folder:
   job=Path(folder);(job/'processing-time.json').write_text('{"seconds":12}')
   output=job/'finished.mp4';report=job/'report.json';events=[]
   @processing_time.measured
   def convert(request):
    production_progress.phase(job,'recognition')
    for i in range(5):worker.emit('日語原聲',str(i),job=str(job));events.append(i)
    output.write_bytes(b'completed movie');report.write_text(json.dumps({'output':str(output)}))
    production_progress.phase(job,'export');production_progress.finish(exported=True)
    return 'finished'
   stream=io.StringIO()
   with patch.object(atomic_files.os,'replace',side_effect=PermissionError(13,'Access is denied')),patch.object(atomic_files.time,'sleep'),contextlib.redirect_stdout(stream):
    self.assertEqual(convert({}),'finished')
   self.assertEqual(events,list(range(5)));self.assertTrue(output.is_file())
   self.assertEqual(json.loads((job/'processing-time.json').read_text())['seconds'],12)
   warnings=[json.loads(line) for line in stream.getvalue().splitlines() if '未能儲存時間紀錄' in line]
   self.assertEqual(len(warnings),3) # checkpoint, report and portable sidecar; once per file.
   self.assertIsNone(processing_time._active)
 def test_original_exception_is_not_masked_by_final_timing_write(self):
  with tempfile.TemporaryDirectory() as folder:
   @processing_time.measured
   def convert(request):
    processing_time.checkpoint(folder);raise RuntimeError('real model failure')
   with patch.object(atomic_files.os,'replace',side_effect=PermissionError(13,'denied')),patch.object(atomic_files.time,'sleep'),contextlib.redirect_stdout(io.StringIO()):
    with self.assertRaisesRegex(RuntimeError,'real model failure'):convert({})
   self.assertIsNone(processing_time._active)
if __name__=='__main__':unittest.main()
