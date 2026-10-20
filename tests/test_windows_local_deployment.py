"""Actual shared planner; no download, user-data writes or inference claims."""
import json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows')]
import native_setup,voice_models,studio_core
class WindowsLocalDeploymentTests(unittest.TestCase):
 def test_each_retained_official_voice_can_be_planned_and_resolves_same_folder(self):
  rows=native_setup.catalog();hardware=dict(platform='windows',architecture='x86_64',nativeWorkflowVersion=1,backend='cuda',memoryGB=64,acceleratorMemoryGB=24)
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   for engine,variants in [('voxcpm2',['voxcpm2-2b-bf16']),('wsyue',['wsyue-cosy2-base','wsyue-cosy2-zjg'])]:
    for ident in variants:
     with self.subTest(ident=ident):
      plan=studio_core.call('deployment',hardware=hardware,models=rows,engine=engine,installedModels=[],selectedModels={},requestedModels={'voice':ident},singleModelPerCategory=True)
      self.assertEqual(plan['blockers'],[]);self.assertEqual(plan['engine'],engine);self.assertEqual(plan['roles']['voice'],ident)
      row=next(r for r in rows if r['id']==ident)
      self.assertEqual(row['nativeFormat'],'pytorch')
      self.assertEqual(native_setup.folder(root,row),voice_models.folder(root,voice_models.choice(engine,ident)))
 def test_one_engine_probe_does_not_certify_another_engine(self):
  from native_models import missing_setup
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);marker=root/'local-windows-ready.json'
   state=dict(modelLoadPassed=True,speechInferencePassed=True,engines=['voxcpm2','wsyue'],verifiedEngines=['wsyue'])
   marker.write_text(json.dumps(state))
   self.assertEqual(missing_setup(root,['wsyue']),[])
   self.assertEqual(missing_setup(root,['voxcpm2','wsyue']),['voxcpm2'])
 def test_other_native_engines_are_not_removed(self):
  active={x['id'] for x in studio_core.catalog()['engines']}
  self.assertTrue({'drama3','cosyvoice3','voxcpm2','wsyue'}.issubset(active))
if __name__=='__main__':unittest.main()
