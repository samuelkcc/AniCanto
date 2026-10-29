"""Production scopes use real settings RPCs and immutable submitted requests."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'studio'),str(ROOT/'windows'),str(ROOT/'Resources')]
from backend import Studio
from desktop_state import Store,read
import production_scope
class ScopeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.app=Studio(self.root,ROOT/'Resources',platform='darwin',helper=self.root/'helper')
  self.rows=[]
  for n in range(3):
   p=self.root/f'video-{n}.mkv';p.write_bytes(b'isolated fixture source')
   self.app.store.add([str(p)]);self.rows.append(self.app.store.queue[-1])
  self.app.store.mode='expert';self.app.store.selected=self.rows[0]['id'];self.app.store.settings.update(dubLanguages=['yue'],subtitleModes=['yue'],ttsBackend='drama3',selectedEngines=['drama3'])
  self.app.store.save()
 def tearDown(self):self.tmp.cleanup()
 def change_scope(self,row,global_value):return self.app.dispatch('configure',dict(scope='video',id=row['id'],useGlobalSettings=global_value,settings={}))
 def patch(self,row,**settings):return self.app.dispatch('configure',dict(scope='video',id=row['id'],settings=settings))
 def test_existing_rows_default_to_global_and_all_follow_global_edits(self):
  self.app.dispatch('configure',dict(settings=dict(dubLanguages=['zh'])))
  for row in self.rows:self.assertFalse(production_scope.individual(row));self.assertEqual(self.app.store.settings_for(row)['dubLanguages'],['zh'])
 def test_individual_snapshot_stays_independent_when_global_changes(self):
  row=self.rows[0];self.change_scope(row,False);self.patch(row,dubLanguages=['en'],limitSpeechDuration=True)
  self.app.dispatch('configure',dict(settings=dict(dubLanguages=['zh'],limitSpeechDuration=False)))
  self.assertEqual(self.app.store.settings_for(row)['dubLanguages'],['en']);self.assertTrue(self.app.store.settings_for(row)['limitSpeechDuration'])
  for other in self.rows[1:]:self.assertEqual(self.app.store.settings_for(other)['dubLanguages'],['zh'])
 def test_turning_global_back_on_discards_local_override(self):
  row=self.rows[0];self.change_scope(row,False);self.patch(row,dubLanguages=['en']);self.change_scope(row,True)
  self.assertNotIn('productionSettings',row);self.assertEqual(self.app.store.settings_for(row)['dubLanguages'],['yue'])
 def test_language_engine_and_repair_choices_are_frozen_per_actual_submission(self):
  self.change_scope(self.rows[0],False);self.patch(self.rows[0],dubLanguages=['en'],limitSpeechDuration=True,aiAutoFix=True)
  paths=[self.app.store.submit(r) for r in self.rows]
  requests=[read(p) for p in paths]
  self.assertEqual([r['dubLanguages'] for r in requests],[['en'],['yue'],['yue']])
  self.assertTrue(requests[0]['limitSpeechDuration']);self.assertFalse(requests[1]['limitSpeechDuration'])
  self.assertTrue(requests[0]['aiAutoFix']);self.assertFalse(requests[1]['aiAutoFix'])
  self.assertEqual([r['video'] for r in requests],[r['video'] for r in self.rows])
  self.assertTrue(all(r.get('repairPermissionsRevision')==__import__('repair_permissions').REVISION for r in requests))
 def test_resume_keeps_the_submitted_file_after_scope_and_global_changes(self):
  row=self.rows[0];self.change_scope(row,False);self.patch(row,dubLanguages=['en']);p=self.app.store.submit(row);before=p.read_bytes();row['status']='paused'
  self.change_scope(row,True);self.app.dispatch('configure',dict(settings=dict(dubLanguages=['zh'])))
  self.assertEqual(self.app.store.submit(row),p);self.assertEqual(p.read_bytes(),before)
 def test_individual_settings_survive_store_reload_and_selection_change(self):
  row=self.rows[0];self.change_scope(row,False);self.patch(row,dubLanguages=['en'])
  restored=Studio(self.root,ROOT/'Resources',platform='darwin',helper=self.root/'helper').store;self.assertEqual(restored.settings_for(restored.queue[0])['dubLanguages'],['en'])
  self.app.store.selected=self.rows[1]['id'];self.assertEqual(self.app.state()['productionSettings']['dubLanguages'],['yue'])
  self.app.store.selected=row['id'];self.assertEqual(self.app.state()['productionSettings']['dubLanguages'],['en'])
 def test_changing_global_cannot_mutate_the_saved_individual_snapshot(self):
  row=self.rows[0];self.change_scope(row,False);before=copy.deepcopy(row['productionSettings'])
  self.app.dispatch('configure',dict(settings=dict(dubLanguages=['zh'],fullAIReview=True)))
  self.assertEqual(row['productionSettings'],before)
 def test_preferences_remain_global_and_are_not_captured_in_snapshot(self):
  row=self.rows[0];self.change_scope(row,False)
  self.app.dispatch('configure',dict(settings=dict(appearance='dark')))
  self.assertEqual(self.app.store.settings_for(row)['appearance'],'dark');self.assertNotIn('appearance',row['productionSettings'])
  with self.assertRaises(ValueError):self.patch(row,appearance='light')
 def test_individual_source_priority_defaults_do_not_drift_with_preferences(self):
  row=self.rows[0];self.change_scope(row,False)
  self.app.dispatch('configure',dict(settings=dict(defaultSubtitleWorkflow='speech-subtitles',defaultOCRWorkflow='speech-ocr')))
  self.assertEqual(self.app.store.settings_for(row)['defaultSubtitleWorkflow'],'subtitles-speech')
  self.assertEqual(self.app.store.settings_for(row)['defaultOCRWorkflow'],'ocr-speech')
  self.assertEqual(self.app.store.settings_for(self.rows[1])['defaultSubtitleWorkflow'],'speech-subtitles')
 def test_cannot_implicitly_edit_global_row_through_video_scope(self):
  with self.assertRaises(ValueError):self.patch(self.rows[0],dubLanguages=['en'])
 def test_bad_scope_is_atomic(self):
  before=copy.deepcopy(self.app.store.queue)
  for value in ['false',None,0]:
   with self.assertRaises(ValueError):self.change_scope(self.rows[0],value)
  self.assertEqual(self.app.store.queue,before)
 def test_running_row_cannot_change_scope_or_local_settings(self):
  row=self.rows[0];self.change_scope(row,False);before=copy.deepcopy(row);row['status']='running'
  with self.assertRaises(ValueError):self.change_scope(row,True)
  with self.assertRaises(ValueError):self.patch(row,dubLanguages=['en'])
  self.assertEqual(row['productionSettings'],before['productionSettings'])
class GuideTests(unittest.TestCase):
 def test_four_language_shared_warning_is_a_generated_consumer_not_a_copy(self):
  import hashlib
  src=ROOT/'docs/WORKFLOW-CONTROLS-GUIDE.json';data=json.loads(src.read_text());items={i['id']:i for i in data['items']}
  self.assertIn('repairCostWarning',items)
  for lang in ('en','zh-HK','zh-CN','ja'):self.assertTrue(items['repairCostWarning']['body'][lang])
  self.assertEqual((ROOT/'studio/web/assets/workflow-controls-guide.json').read_bytes(),src.read_bytes())
  self.assertIn(hashlib.sha256(src.read_bytes()).hexdigest(),(ROOT/'studio/web/assets/workflow-controls-guide.js').read_text())
  self.assertIn("import {WORKFLOW_GUIDE}",(ROOT/'studio/web/help.js').read_text())
if __name__=='__main__':unittest.main()
