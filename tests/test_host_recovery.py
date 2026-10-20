"""Host restart, queue finalization and model-removal locks using owned fixtures."""
import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'studio'),str(ROOT/'windows'),str(ROOT/'Resources')]
from backend import Studio
from desktop_state import read,write
from diagnostics import start
class HostRecoveryTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
  self.helper=self.root/'worker';self.helper.touch();self.app=Studio(self.root,ROOT/'Resources',helper=self.helper)
  self.video=self.root/'movie.mp4';self.video.touch();self.ident=self.app.dispatch('add',dict(paths=[str(self.video)]))['selected'];self.row=self.app.row()
  self.request=self.root/'requests/frozen.json';self.request.parent.mkdir();self.request.write_text('{"video":"saved input"}')
  self.row.update(status='running',request=str(self.request),job=str(self.root/'jobs/original'),lastError=dict(message='previous failure'))
  self.app.store.save()
 def tearDown(self):self.temp.cleanup()
 def test_only_explicit_host_recovery_unblocks_stale_row_and_retains_frozen_work(self):
  second=Studio(self.root,ROOT/'Resources',helper=self.helper)
  self.assertEqual(second.row()['status'],'running')
  with self.assertRaisesRegex(ValueError,'Pause processing'):second.dispatch('source-language',dict(id=self.ident))
  second.recover_orphans();row=second.row()
  self.assertEqual(row['status'],'paused');self.assertEqual(row['request'],str(self.request));self.assertEqual(row['job'],str(self.root/'jobs/original'))
  self.assertEqual(row['lastError']['message'],'previous failure')
  with patch('model_maintenance.removal_plan',return_value={'canRemove':True}) as removal:
   self.assertTrue(second.dispatch('model-removal-plan',dict(id='unused-model'))['canRemove']);removal.assert_called_once()
  with patch('source_language.preflight',return_value={'language':'ja'}) as check:
   self.assertEqual(second.dispatch('source-language',dict(id=self.ident))['language'],'ja');check.assert_called_once()
  self.assertEqual(self.request.read_text(),'{"video":"saved input"}')
 def test_missing_attempt_receipt_cannot_leave_ended_worker_running(self):
  self.row['attempt']={'id':'one','path':str(self.root/'attempts/missing')}
  self.row['output']=None;self.row['lastError']=None
  result=self.app.dispatch('finish',dict(id=self.ident,code=1,stderr='worker failed'))
  self.assertEqual(result['queue'][0]['status'],'attention');self.assertIn('diagnosticsWarning',self.row)
  self.assertEqual(read(self.app.store.path)['queue'][0]['status'],'attention')
 def test_existing_receipt_finalized_once_and_failure_not_replaced_by_no_output(self):
  start(self.root,self.row,'batch',self.request);self.row['status']='running'
  with patch('diagnostics.finish',wraps=__import__('diagnostics').finish) as finish:
   self.app.dispatch('finish',dict(id=self.ident,code=5,stderr='real failure'))
   self.assertEqual(finish.call_count,1)
  self.assertIn('real failure',self.row['lastError']['message']);self.assertEqual(self.row['status'],'attention')
 def test_terminal_receipt_recovers_complete_only_with_current_output(self):
  attempt=start(self.root,self.row,'batch',self.request);attempt.update(endedAt=1,exitCode=0,status='exported')
  write(Path(attempt['path'])/'attempt.json',attempt);self.row['status']='running';self.row['outputThisAttempt']=str(self.root/'new.mp4')
  self.app.store.save();self.app.recover_orphans();self.assertEqual(self.row['status'],'attention')
  self.row['status']='running';Path(self.row['outputThisAttempt']).touch();self.app.recover_orphans();self.assertEqual(self.row['status'],'complete')
 def test_preview_recovery_does_not_replace_full_job_state(self):
  self.row.update(previewAttempt=True,previousStatus='attention');self.app.recover_orphans()
  self.assertEqual(self.row['status'],'attention');self.assertEqual(self.row['job'],str(self.root/'jobs/original'))
if __name__=='__main__':unittest.main()
