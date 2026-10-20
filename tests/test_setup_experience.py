import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'windows'),str(ROOT/'Resources')]
import setup_inventory,native_setup,native_models,studio_core

class SetupExperienceTests(unittest.TestCase):
 def test_laptop_16gb_vram_uses_gpt_instead_of_retired_small(self):
  hardware=dict(platform='windows',architecture='x86_64',memoryGB=32,acceleratorMemoryGB=16,backend='cuda',nativeWorkflowVersion=1,nativeDramaSmallCPU=True)
  plan=studio_core.call('deployment',hardware=hardware,models=native_setup.catalog(),engine='drama3')
  self.assertEqual(plan['engine'],'gpt-sovits-v2');self.assertEqual(plan['voice']['id'],'v2ProPlus')
  self.assertNotIn('native-drama-small-cpu-fallback',plan['warnings'])
 def test_inadequate_memory_does_not_force_small_model(self):
  hardware=dict(platform='windows',architecture='x86_64',memoryGB=8,acceleratorMemoryGB=16,backend='cuda',nativeWorkflowVersion=1,nativeDramaSmallCPU=True)
  plan=studio_core.call('deployment',hardware=hardware,models=native_setup.catalog(),engine='drama3')
  self.assertNotEqual((plan['voice'] or {}).get('id'),'drama3-small-iq3')
 def test_old_small_cuda_plugin_never_proves_full_drama_support(self):
  hardware=dict(platform='windows',architecture='x86_64',memoryGB=32,acceleratorMemoryGB=16,backend='cuda',nativeWorkflowVersion=1,nativeDramaSmallCPU=True,nativeDramaSmallCUDA=True)
  plan=studio_core.call('deployment',hardware=hardware,models=native_setup.catalog(),engine='drama3')
  self.assertEqual(plan['engine'],'gpt-sovits-v2');self.assertEqual(plan['voice']['id'],'v2ProPlus');self.assertEqual(plan['voiceBackend'],'cuda')
  self.assertNotIn('native-drama-small-cuda-planned',plan['warnings'])
 def test_verified_cuda_model_is_not_silently_replaced_with_cpu_or_gpt(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'drama3-windows-ready.json').write_text(json.dumps(dict(variant='drama3-small-iq3',backend='cuda',modelLoadPassed=True,speechInferencePassed=True)))
   cfg=dict(storage=folder,selectedEngines=['drama3'],ttsBackend='drama3',drama3Model='drama3-small-iq3')
   native_models.recover(cfg,lambda *a,**k:None)
   self.assertEqual(cfg['selectedEngines'],['drama3']);self.assertEqual(cfg['drama3Backend'],'cuda');self.assertFalse(cfg['nativeDramaCPU'])
 def test_old_small_receipt_never_overrides_a_new_request(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'drama3-windows-ready.json').write_text(json.dumps(dict(variant='drama3-small-iq3',backend='cuda',modelLoadPassed=True,speechInferencePassed=True)))
   (root/'gpt-windows-ready.json').write_text(json.dumps(dict(modelLoadPassed=True,speechInferencePassed=True,speechVersions=['v2ProPlus'])))
   cfg=dict(storage=d,selectedEngines=['drama3'],ttsBackend='drama3')
   native_models.recover(cfg,lambda *a,**k:None)
   self.assertEqual(cfg['ttsBackend'],'gpt-sovits-v2');self.assertNotEqual(cfg['drama3Model'],'drama3-small-iq3')
 def test_explicit_cpu_choice_does_not_plan_cuda_downloads(self):
  import gpu
  hardware=dict(platform='windows',architecture='x86_64',memoryGB=32,acceleratorMemoryGB=16,backend='cuda',nativeWorkflowVersion=1)
  with tempfile.TemporaryDirectory() as d,patch.object(native_setup,'data_root',return_value=Path(d)),patch.object(gpu,'planning_hardware',return_value=hardware):
   plan=native_setup.plan(backend='cpu')
  self.assertEqual(plan['voiceBackend'],'cpu');self.assertEqual(plan['tools'],[])
 def test_verified_small_model_is_kept_in_production_and_missing_setup(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'drama3-windows-ready.json').write_text(json.dumps(dict(variant='drama3-small-iq3',modelLoadPassed=True,speechInferencePassed=True)))
   cfg=dict(storage=folder,selectedEngines=['drama3'],ttsBackend='drama3',drama3Model='drama3-small-iq3')
   native_models.recover(cfg,lambda *a,**k:None)
   self.assertEqual(cfg['selectedEngines'],['drama3']);self.assertEqual(cfg['drama3Model'],'drama3-small-iq3')
   self.assertEqual(native_models.missing_setup(root,['drama3']),[])
 def test_old_gpt_fallback_does_not_satisfy_a_new_drama_selection(self):
  with tempfile.TemporaryDirectory() as d,patch('drama_cuda.capable',return_value=True):
   root=Path(d);(root/'gpt-windows-ready.json').write_text(json.dumps(dict(modelLoadPassed=True,speechInferencePassed=True,speechVersions=['v2ProPlus'])))
   self.assertEqual(native_models.missing_setup(root,['drama3']),['drama3'])
   self.assertEqual(native_models.missing_setup(root,['gpt-sovits-v2']),[])
 def test_upgrade_restores_requested_drama_once_and_keeps_submitted_jobs(self):
  from desktop_state import Store,restore_requested_drama
  with tempfile.TemporaryDirectory() as d:
   store=Store(d);store.settings.update(ttsBackend='gpt-sovits-v2',selectedEngines=['gpt-sovits-v2'],defaultAudioEngine='gpt-sovits-v2');store.queue=[dict(id='old',request='immutable-old-request.json',status='paused')]
   queued=json.dumps(store.queue,sort_keys=True);ready=dict(requestedEngine='drama3',engine='gpt-sovits-v2')
   self.assertTrue(restore_requested_drama(store,ready,True));self.assertEqual(store.settings['ttsBackend'],'drama3');self.assertEqual(json.dumps(store.queue,sort_keys=True),queued)
   store.settings.update(ttsBackend='gpt-sovits-v2',selectedEngines=['gpt-sovits-v2'])
   self.assertFalse(restore_requested_drama(store,ready,True));self.assertEqual(store.settings['ttsBackend'],'gpt-sovits-v2')
 def test_upgrade_does_not_change_a_different_user_engine_selection(self):
  from desktop_state import Store,restore_requested_drama
  with tempfile.TemporaryDirectory() as d:
   store=Store(d);store.settings.update(ttsBackend='cosyvoice3',selectedEngines=['cosyvoice3'])
   self.assertFalse(restore_requested_drama(store,dict(requestedEngine='drama3',engine='gpt-sovits-v2'),True))
   self.assertEqual(store.settings['ttsBackend'],'cosyvoice3')
 def row(self,ident='one',files=None):return dict(id=ident,title=ident,nativeFormat='gguf',legacy='models/shared',files=files or [dict(path=ident,size=4)],bytes=4)
 def test_remove_only_catalog_owned_model_files_and_preserve_shared_and_projects(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'models/shared').mkdir(parents=True);(root/'jobs').mkdir();(root/'jobs/project.json').write_text('project');(root/'export.mp4').write_text('movie')
   for name in ['shared','one','two']:(root/'models/shared'/name).write_bytes(b'data')
   shared=dict(path='shared',size=4)
   rows=[self.row('one',[shared,dict(path='one',size=4)]),self.row('two',[shared,dict(path='two',size=4)])]
   setup_inventory.remove(root,'model','one',rows)
   self.assertFalse((root/'models/shared/one').exists());self.assertTrue((root/'models/shared/shared').exists());self.assertTrue((root/'models/shared/two').exists())
   self.assertEqual((root/'jobs/project.json').read_text(),'project');self.assertEqual((root/'export.mp4').read_text(),'movie')
   self.assertEqual(native_models.missing_setup(root,['drama3']),['drama3'])
 def test_runtime_ui_and_external_paths_are_protected(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder)
   with self.assertRaises(ValueError):setup_inventory.remove(root,'runtime','ui',[])
   with self.assertRaises(ValueError):setup_inventory.safe_path(root,'../outside')
   self.assertFalse((root/'setup-invalidated.json').exists())
 def test_warning_is_readable_and_bilingual(self):
  code='native-drama-small-cpu-fallback'
  self.assertIn('CPU',setup_inventory.warning(code,'en'));self.assertIn('廣東話',setup_inventory.warning(code,'zh-HK'))

if __name__=='__main__':unittest.main()
