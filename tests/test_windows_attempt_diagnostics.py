"""Protect actionable failure evidence across batch summaries and app restarts."""
import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'windows'))
from desktop_state import Store,read,write
from diagnostics import start,finish,exit_failure
class AttemptDiagnosticsTests(unittest.TestCase):
 def test_zero_exit_batch_summary_cannot_hide_error(self):
  with tempfile.TemporaryDirectory() as d:
   store=Store(d);store.add([Path(d)/'日本語.mp4']);row=store.row();request=store.submit(row);attempt=start(d,row,'batch',request)
   store.event(row,dict(stage='批量錯誤',message='CUDA out of memory',batchStatus='需要處理'))
   store.event(row,dict(stage='批量進度',message='已處理 1 集'))
   store.event(row,dict(stage='批量完成',message='全部完成'))
   store.finish(row,0)
   restored=Store(d).row();self.assertEqual(restored['status'],'attention');self.assertEqual(restored['lastError']['message'],'CUDA out of memory')
   self.assertEqual(read(Path(attempt['path'])/'attempt.json')['status'],'failed')
 def test_old_movie_does_not_make_a_failed_new_attempt_successful(self):
  with tempfile.TemporaryDirectory() as d:
   store=Store(d);store.add([Path(d)/'episode.mp4']);row=store.row();movie=Path(d)/'old.mp4';movie.write_bytes(b'old movie');row['output']=str(movie)
   start(d,row,'batch',store.submit(row));store.finish(row,0)
   self.assertEqual(row['status'],'attention');self.assertEqual(row['lastError']['code'],'no-output');self.assertEqual(movie.read_bytes(),b'old movie')
 def test_audition_and_subtitle_operations_do_not_require_movie(self):
  with tempfile.TemporaryDirectory() as d:
   row=dict(id='fixture',video='movie.mp4');attempt=start(d,row,'render-project','request')
   self.assertIsNone(finish(d,row,0,success_without_movie=True));self.assertEqual(read(Path(attempt['path'])/'attempt.json')['status'],'finished')
 def test_native_dll_crash_has_persistent_specific_reason(self):
  with tempfile.TemporaryDirectory() as d:
   row=dict(id='fixture',video='movie.mp4');attempt=start(d,row,'batch','request')
   error=finish(d,row,-1073741515,stderr='Missing cudart64.dll')
   self.assertEqual(error['code'],'missing-dll');self.assertIn('cudart64.dll',read(Path(attempt['path'])/'attempt.json')['error']['message'])
 def test_pause_is_not_generation_failure_and_retry_preserves_old_attempt(self):
  with tempfile.TemporaryDirectory() as d:
   row=dict(id='fixture',video='movie.mp4');old=start(d,row,'batch','first');self.assertIsNone(finish(d,row,9,paused=True))
   new=start(d,row,'batch','second');self.assertNotEqual(old['path'],new['path']);self.assertEqual(read(Path(old['path'])/'attempt.json')['status'],'paused')
 def test_new_output_is_complete_and_custom_export_folder_is_retained(self):
  with tempfile.TemporaryDirectory() as d:
   store=Store(d);store.add([Path(d)/'movie.mp4']);row=store.row();store.settings['exportFolder']=str(Path(d)/'chosen')
   request=store.submit(row);self.assertEqual(read(request)['exportFolder'],str(Path(d)/'chosen'))
   start(d,row,'batch',request);output=Path(d)/'new.mp4';output.write_bytes(b'new movie');store.event(row,dict(stage='輸出',output=str(output)));store.finish(row,0)
   self.assertEqual(row['status'],'complete');self.assertEqual(row['progress'],1);self.assertIsNone(row.get('lastError'))
if __name__=='__main__':unittest.main()
