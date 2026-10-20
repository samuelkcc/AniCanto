import sys,json,tempfile,unittest
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'Resources')]
import project_cache as cache

class CacheTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.job=self.root/'jobs/completed';self.job.mkdir(parents=True)
  self.rows=[dict(video=str(self.root/'source.mkv'),status='complete',job=str(self.job),output=str(self.job/'output.mp4'))]
  for name in ['frames-pts/001.jpg','ocr-discovery/001.jpg','output.mp4','drama3.raw.wav','failed.wav','review.json','timing.json']:
   p=self.job/name;p.parent.mkdir(exist_ok=True);p.write_bytes(b'test')
  self.preview=self.root/'cache/studio-preview/test';self.preview.mkdir(parents=True)
  (self.preview/'status.json').write_text(json.dumps(dict(stage='ready')));(self.preview/'preview.mp4').write_bytes(b'proxy')
 def tearDown(self):self.tmp.cleanup()
 def test_safe_cleanup_preserves_exports_recordings_and_state(self):
  plan=cache.plan(self.root,self.rows);self.assertGreater(plan['bytes'],0)
  result=cache.execute(self.root,self.rows,plan['token']);self.assertTrue(result['complete'])
  self.assertFalse((self.job/'frames-pts/001.jpg').exists());self.assertFalse((self.preview/'preview.mp4').exists())
  for name in ['output.mp4','drama3.raw.wav','failed.wav','review.json','timing.json']:self.assertTrue((self.job/name).exists())
 def test_paused_jobs_and_busy_preview_are_not_swept(self):
  self.rows[0]['status']='paused';(self.preview/'status.json').write_text(json.dumps(dict(stage='encode')))
  with cache.preview_lock(self.preview):self.assertEqual(cache.plan(self.root,self.rows)['bytes'],0)
 def test_stale_token_does_not_remove_anything(self):
  plan=cache.plan(self.root,self.rows);(self.job/'frames-pts/001.jpg').write_bytes(b'changed')
  with self.assertRaisesRegex(ValueError,'changed'):cache.execute(self.root,self.rows,plan['token'])
  self.assertTrue((self.preview/'preview.mp4').exists())
 def test_symlink_and_source_inside_cache_are_kept(self):
  outside=self.root/'outside';outside.mkdir();(outside/'x.jpg').write_bytes(b'keep')
  (self.job/'frames-pts/link').symlink_to(outside,target_is_directory=True)
  self.rows[0]['video']=str(self.job/'frames-pts/001.jpg')
  plan=cache.plan(self.root,self.rows);cache.execute(self.root,self.rows,plan['token'])
  self.assertTrue((outside/'x.jpg').exists());self.assertTrue((self.job/'frames-pts/001.jpg').exists())
 def test_legacy_preview_without_any_status_is_found(self):
  legacy=self.root/'cache/studio-preview'/('a'*24);legacy.mkdir();(legacy/'preview.mp4').write_bytes(b'legacy')
  plan=cache.plan(self.root,[]);self.assertIn('cache/studio-preview/'+('a'*24)+'/preview.mp4',[f['path'] for f in plan['files']])
  cache.execute(self.root,[],plan['token']);self.assertFalse((legacy/'preview.mp4').exists())
 def test_crash_status_without_live_lock_is_recoverable(self):
  (self.preview/'status.json').write_text(json.dumps(dict(stage='encode')))
  plan=cache.plan(self.root,[]);self.assertIn('video-preview',plan['groups'])
 def test_unlinked_recordings_are_separate_and_require_selection(self):
  plan=cache.plan(self.root,[]);self.assertEqual(len(plan['orphanWork']),1)
  cache.execute(self.root,[],plan['token']);self.assertTrue((self.job/'failed.wav').exists())
  plan=cache.plan(self.root,[]);cache.execute(self.root,[],plan['token'],[self.job.name])
  self.assertFalse((self.job/'failed.wav').exists());self.assertTrue((self.job/'output.mp4').exists())
 def test_saved_database_project_is_not_abandoned(self):
  import sqlite3
  with sqlite3.connect(self.root/'projects.sqlite3') as db:
   db.execute('create table projects(review text)');db.execute('insert into projects values(?)',(str(self.job/'review.json'),))
  self.assertEqual(cache.plan(self.root,[])['orphanWork'],[])
 def test_failed_database_check_protects_work_data(self):
  (self.root/'projects.sqlite3').write_bytes(b'broken index')
  plan=cache.plan(self.root,[]);self.assertFalse(plan['orphanWork'][0]['canRemove'])
  with self.assertRaisesRegex(ValueError,'cannot be checked'):cache.execute(self.root,[],plan['token'],[self.job.name])
  self.assertTrue((self.job/'failed.wav').exists())
 def test_current_reference_and_paused_request_protect_whole_folder(self):
  settings=dict(voiceProfiles=[dict(reference=str(self.job/'failed.wav'))])
  self.assertEqual(cache.plan(self.root,[],settings)['orphanWork'],[])
  request=self.root/'request.json';request.write_text(json.dumps(dict(job=str(self.job))))
  self.assertEqual(cache.plan(self.root,[dict(status='paused',request=str(request))])['orphanWork'],[])
 def test_hardlinked_runtime_is_not_counted_as_reclaimed_or_removed(self):
  import os
  runtime=self.root/'runtime/model.so';runtime.parent.mkdir();runtime.write_bytes(b'runtime')
  cached=self.root/'cache/uv/archive/model.so';cached.parent.mkdir(parents=True);os.link(runtime,cached)
  plan=cache.plan(self.root,self.rows);item=next(f for f in plan['files'] if f['path'].endswith('model.so'))
  self.assertEqual(cache.footprint([item]),0);cache.execute(self.root,self.rows,plan['token']);self.assertEqual(runtime.read_bytes(),b'runtime');self.assertFalse(cached.exists())
 def test_unknown_selection_and_changed_job_are_rejected(self):
  plan=cache.plan(self.root,[])
  with self.assertRaises(ValueError):cache.execute(self.root,[],plan['token'],['../outside'])
  (self.job/'failed.wav').write_bytes(b'changed')
  with self.assertRaises(ValueError):cache.execute(self.root,[],plan['token'],[self.job.name])
 def test_real_progress_counts_and_final_receipt(self):
  from unittest.mock import patch
  events=[];plan=cache.plan(self.root,self.rows)
  original=cache.execute
  def execute(*args):
   callback=args[-1]
   def record(**event):events.append(dict(event));callback(**event)
   return original(*args[:-1],progress=record)
  with patch.object(cache,'execute',side_effect=execute):
   result=cache.tracked_execute(self.root,self.rows,plan['token'],operation_id='test-operation')
  self.assertEqual(events[0]['phase'],'checking')
  deleting=[e for e in events if e['phase']=='deleting']
  self.assertEqual(deleting[-1]['processed'],plan['count'])
  self.assertEqual(result['removedCount'],plan['count']);self.assertEqual(result['failedCount'],0)
  receipt=cache.cleanup_status(self.root,'test-operation')
  self.assertEqual(receipt['phase'],'complete');self.assertEqual(receipt['freedBytes'],result['freedBytes'])
  self.assertIsNone(cache.cleanup_status(self.root,'another-operation'))
  self.assertNotIn(str(self.root),(self.root/'project-cache-progress.json').read_text())
 def test_progress_reports_partial_failure_and_stale_plan(self):
  from unittest.mock import patch
  plan=cache.plan(self.root,self.rows);unlink=Path.unlink
  def fail_one(path,*args,**kw):
   if path.resolve()==(self.preview/'preview.mp4').resolve():raise PermissionError('locked')
   return unlink(path,*args,**kw)
  with patch.object(Path,'unlink',fail_one):result=cache.tracked_execute(self.root,self.rows,plan['token'],operation_id='partial')
  self.assertFalse(result['complete']);self.assertEqual(result['failedCount'],1)
  self.assertEqual(cache.cleanup_status(self.root,'partial')['phase'],'partial')
  self.assertTrue((self.preview/'preview.mp4').exists())
  with self.assertRaises(ValueError):cache.tracked_execute(self.root,self.rows,'stale',operation_id='stale')
  self.assertEqual(cache.cleanup_status(self.root,'stale')['phase'],'failed')
 def test_bad_operation_id_cannot_delete_files_or_overwrite_receipt(self):
  plan=cache.plan(self.root,self.rows)
  for ident in ('../escape',None,'x'*81):
   with self.assertRaises(ValueError):cache.tracked_execute(self.root,self.rows,plan['token'],operation_id=ident)
  self.assertTrue((self.preview/'preview.mp4').exists())
  self.assertFalse((self.root/'project-cache-progress.json').exists())
if __name__=='__main__':unittest.main()
