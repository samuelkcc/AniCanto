import contextlib,hashlib,io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'Resources')]
import model_maintenance as m

class MaintenanceTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.contents={'shared':'shared bytes','voice':'voice bytes'}
  self.row=dict(id='model-test',title='Test model',category='voice',engine='drama3',legacy='models/test',repo='test/model',revision='pinned',files=[dict(path=k,size=len(v.encode()),sha=hashlib.sha256(v.encode()).hexdigest()) for k,v in self.contents.items()])
  self.mock=patch.object(m,'catalog_paths',return_value=([self.row],lambda root,row:root/row['legacy']));self.mock.start()
  self.base=self.root/'models/test';self.base.mkdir(parents=True)
  for k,v in self.contents.items():(self.base/k).write_text(v)
  self.calls=[]
 def tearDown(self):self.mock.stop();self.tmp.cleanup()
 def download(self,url,target,digest,size):
  self.calls.append(str(target));target.parent.mkdir(parents=True,exist_ok=True);target.write_text(self.contents[target.name])
 def run_task(self,mode='repair'):
  with patch('model_download.download',side_effect=self.download),patch.object(m.shutil,'disk_usage',return_value=type('Space',(),{'free':10**12})()),contextlib.redirect_stdout(io.StringIO()):return m.maintain(self.root,'model-test',mode)
 def test_repair_only_downloads_missing_file_and_preserves_selection(self):
  (self.base/'voice').unlink();selection=self.root/'model-selections.json';selection.write_text('{"drama3":"other"}');before=selection.read_bytes()
  result=self.run_task();self.assertEqual(result['reused'],1);self.assertEqual(result['downloaded'],1)
  self.assertEqual(len(self.calls),1);self.assertEqual(selection.read_bytes(),before)
  self.assertTrue(json.loads((self.root/'model-ready/model-test.json').read_text())['sha256Verified'])
 def test_same_size_checksum_corruption_is_repaired(self):
  (self.base/'voice').write_bytes(b'x'*len(self.contents['voice']))
  result=self.run_task();self.assertEqual(result['downloaded'],1);self.assertEqual((self.base/'voice').read_text(),self.contents['voice'])
 def test_redownload_verifies_all_before_replacing_any_current_file(self):
  before={k:(self.base/k).read_bytes() for k in self.contents}
  def fail_second(url,target,digest,size):
   self.assertEqual({k:(self.base/k).read_bytes() for k in before},before)
   if target.name=='voice':raise RuntimeError('network lost')
   self.download(url,target,digest,size)
  with patch('model_download.download',side_effect=fail_second),contextlib.redirect_stdout(io.StringIO()):
   with self.assertRaisesRegex(RuntimeError,'network lost'):m.maintain(self.root,'model-test','redownload')
  self.assertEqual({k:(self.base/k).read_bytes() for k in before},before)
  record=json.loads(next((self.root/'studio/model-maintenance').glob('*.json')).read_text());self.assertEqual(record['status'],'failed')
  result=self.run_task('redownload');self.assertEqual(result['status'],'complete');self.assertEqual(result['downloaded'],2)
 def test_complete_repair_does_not_download(self):self.assertEqual(self.run_task()['downloaded'],0);self.assertEqual(self.calls,[])
 def test_batch_download_keeps_successes_and_reports_other_failures(self):
  other=dict(self.row,id='other',title='Other voice model',legacy='models/other',files=[self.row['files'][1]])
  self.mock.stop();self.mock=patch.object(m,'catalog_paths',return_value=([self.row,other],lambda root,row:root/row['legacy']));self.mock.start()
  (self.base/'voice').unlink()
  def selective_download(url,target,digest,size):
   if 'other' in str(target):raise RuntimeError('second model unavailable')
   self.download(url,target,digest,size)
  with patch('model_download.download',side_effect=selective_download),patch.object(m.shutil,'disk_usage',return_value=type('Space',(),{'free':10**12})()),contextlib.redirect_stdout(io.StringIO()):
   failures=m.maintain_many(self.root,['model-test','other'])
  self.assertTrue((self.base/'voice').is_file())
  self.assertEqual([r['id'] for r in failures],['other'])
  self.assertTrue((self.root/'model-ready/model-test.json').is_file())
  self.assertFalse((self.root/'model-ready/other.json').exists())
  with self.assertRaises(ValueError):m.maintain_many(self.root,['model-test','model-test'])
 def test_licence_block_allows_local_verification_but_no_repair_download(self):
  self.row['licenseReviewRequired']=True
  self.assertEqual(self.run_task()['downloaded'],0)
  (self.base/'voice').unlink()
  with self.assertRaisesRegex(ValueError,'licence review'):self.run_task()
  self.assertEqual(self.calls,[]);self.assertTrue((self.base/'shared').exists())
 def test_invalid_id_mode_and_escape_never_write(self):
  with self.assertRaises(ValueError):m.model(self.root,'other')
  self.row['files'][0]['path']='../../outside'
  with self.assertRaises(ValueError):m.model(self.root,'model-test')
  with self.assertRaises(ValueError):m.maintain(self.root,'model-test','delete')
 def test_inline_metadata_verifies_without_network(self):
  for f in self.row['files']:f['content']=self.contents[f['path']]
  (self.base/'voice').unlink();self.assertEqual(self.run_task()['status'],'complete');self.assertEqual(self.calls,[])
 def test_explicit_removal_protects_current_and_pending_models(self):
  with self.assertRaisesRegex(ValueError,'Switch model first'):m.remove_model(self.root,self.row['id'],selected_ids=[self.row['id']])
  from model_switch import write
  write(self.root/'studio/desktop-state.json',dict(queue=[dict(status='paused',asrModel=self.row['id'])]))
  with self.assertRaisesRegex(ValueError,'pending job'):m.remove_model(self.root,self.row['id'])
  self.assertTrue((self.base/'voice').exists())
 def test_paused_drama_job_does_not_lock_unused_cosy_preferences(self):
  from model_switch import write,pending_models
  request=self.root/'request.json'
  write(request,dict(ttsBackend='drama3',selectedEngines=['drama3'],drama3Model='real-drama',cosyModel=self.row['id'],deploymentModels={'voice':self.row['id']},asrModel='real-asr'))
  write(self.root/'studio/desktop-state.json',dict(queue=[dict(status='paused',request=str(request))]))
  self.assertNotIn(self.row['id'],pending_models(self.root));self.assertIn('real-drama',pending_models(self.root));self.assertIn('real-asr',pending_models(self.root))
  self.assertTrue(m.removal_plan(self.root,self.row['id'])['canRemove'])
  write(request,dict(ttsBackend='drama3',selectedEngines=['drama3','cosyvoice3'],cosyModel=self.row['id']))
  self.assertFalse(m.removal_plan(self.root,self.row['id'])['canRemove'])
 def test_removal_preserves_shared_files_and_unpins_only_requested_model(self):
  other=dict(self.row,id='other',files=[self.row['files'][0]])
  self.mock.stop();self.mock=patch.object(m,'catalog_paths',return_value=([self.row,other],lambda root,row:root/row['legacy']));self.mock.start()
  from model_switch import write,read
  write(self.root/'studio/model-pins.json',[self.row['id'],'other'])
  result=m.remove_model(self.root,self.row['id'])
  self.assertTrue((self.base/'shared').exists());self.assertFalse((self.base/'voice').exists())
  self.assertEqual(result['freedBytes'],len(self.contents['voice']));self.assertEqual(read(self.root/'studio/model-pins.json',[]),['other'])
 def test_two_removed_variants_release_the_last_common_file(self):
  other=dict(self.row,id='other',title='Other variant',files=[self.row['files'][0],dict(path='other-voice',size=4,sha='0'*64)])
  self.mock.stop();self.mock=patch.object(m,'catalog_paths',return_value=([self.row,other],lambda root,row:root/row['legacy']));self.mock.start()
  # Exact regression: both unique voice weights were already removed; only the
  # same shared encoder remains, so both used to say removed / zero bytes.
  (self.base/'voice').unlink()
  first=m.remove_model(self.root,self.row['id']);self.assertEqual(first['freedBytes'],0)
  self.assertEqual(first['sharedBytesRetained'],len(self.contents['shared']));self.assertEqual(first['sharedModels'][0]['id'],'other')
  from model_ownership import removed_ids
  self.assertEqual(removed_ids(self.root,[self.row,other]),{self.row['id']})
  second=m.remove_model(self.root,'other');self.assertEqual(second['freedBytes'],len(self.contents['shared']))
  self.assertFalse((self.base/'shared').exists());self.assertEqual(removed_ids(self.root,[self.row,other]),{self.row['id'],'other'})
 def test_selected_owner_keeps_shared_files_after_other_variant_is_removed(self):
  other=dict(self.row,id='selected',files=[self.row['files'][0]])
  self.mock.stop();self.mock=patch.object(m,'catalog_paths',return_value=([self.row,other],lambda root,row:root/row['legacy']));self.mock.start()
  result=m.remove_model(self.root,self.row['id'],selected_ids=['selected'])
  self.assertEqual(result['sharedBytesRetained'],len(self.contents['shared']));self.assertTrue((self.base/'shared').is_file())
  with self.assertRaisesRegex(ValueError,'Switch model first'):m.remove_model(self.root,'selected',selected_ids=['selected'])
 def test_successful_repair_restores_explicitly_removed_variant(self):
  from model_ownership import mark_removed,removed_ids
  mark_removed(self.root,self.row);self.assertIn(self.row['id'],removed_ids(self.root,[self.row]))
  self.run_task();self.assertNotIn(self.row['id'],removed_ids(self.root,[self.row]))
 def test_removal_rejects_symlink_before_deleting_any_file(self):
  (self.base/'voice').unlink();(self.base/'voice').symlink_to(self.base/'shared')
  with self.assertRaisesRegex(ValueError,'symlink'):m.remove_model(self.root,self.row['id'])
  self.assertTrue((self.base/'shared').exists())
if __name__=='__main__':unittest.main()
