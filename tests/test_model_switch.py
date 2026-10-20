import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import model_switch


class ModelSwitchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.models=[dict(id=n,files=[dict(path='weights',size=4)],legacy='models/'+n) for n in ('old','new','expert')]
        for row in self.models:
            p=self.root/row['legacy'];p.mkdir(parents=True);(p/'weights').write_bytes(b'data')
        model_switch.write(self.root/'model-selections.json',dict(text='old'))
        self.plan=dict(canDeployModels=True,engine='drama3',roles=dict(text='new'))
    def tearDown(self):self.tmp.cleanup()
    def folder(self,root,row):return root/row['legacy']
    def ready(self):
        model_switch.write(self.root/'model-selections.json',dict(text='new'))
        model_switch.write(self.root/'first-run-deployment.json',dict(status='complete',plan=self.plan))
    def begin(self,expert=False):return model_switch.begin(self.root,self.plan,dict(text='new'),True,expert)
    def finish(self,token):return model_switch.finish(self.root,token,self.models,self.folder)
    def test_no_old_file_is_removed_before_new_load_receipt_and_verified_selection(self):
        token=self.begin()
        with self.assertRaises(ValueError):self.finish(token)
        self.assertTrue((self.root/'models/old/weights').is_file())
        self.ready();result=self.finish(token)
        self.assertFalse((self.root/'models/old/weights').exists())
        self.assertTrue((self.root/'models/new/weights').exists())
        self.assertTrue((self.root/'models/expert/weights').exists())
        self.assertEqual(self.finish(token),result)
    def test_pending_frozen_request_protects_previous_weights(self):
        token=self.begin();self.ready()
        request=self.root/'requests/paused.json';model_switch.write(request,dict(model='old'))
        model_switch.write(self.root/'studio/desktop-state.json',dict(queue=[dict(status='paused',request=str(request))]))
        result=self.finish(token);self.assertTrue((self.root/'models/old/weights').exists())
        self.assertEqual(result['kept'],[dict(id='old',reason='in-use-or-pinned')])
    def test_shared_files_and_expert_pins_are_retained(self):
        self.models[2]['legacy']='models/old'
        token=self.begin();self.ready();self.finish(token)
        self.assertTrue((self.root/'models/old/weights').exists())
        model_switch.write(self.root/'model-selections.json',dict(text='old'))
        model_switch.write(self.root/'studio/model-pins.json',['old'])
        token=self.begin();self.ready();self.finish(token)
        self.assertTrue((self.root/'models/old/weights').exists())
    def test_expert_download_keeps_additional_models(self):
        token=self.begin(expert=True);self.ready();self.finish(token)
        self.assertTrue((self.root/'models/old/weights').exists())
        self.assertIn('new',model_switch.read(self.root/'studio/model-pins.json',[]))
    def test_interrupted_windows_download_restores_old_selection_and_ready_receipt(self):
        model_switch.write(self.root/'native-ready.json',dict(modelLoadPassed=True,roles=dict(text='old')))
        token=self.begin();model_switch.write(self.root/'model-selections.json',dict(text='new'))
        model_switch.write(self.root/'setup-invalidated.json',dict(reason='setup-in-progress'))
        result=model_switch.finish(self.root,token,self.models,self.folder,success=False)
        self.assertEqual(result['status'],'incomplete')
        self.assertEqual(model_switch.read(self.root/'model-selections.json',{})['text'],'old')
        self.assertFalse((self.root/'setup-invalidated.json').exists())
    def test_catalog_path_escape_cannot_delete_external_files(self):
        token=self.begin();self.ready();self.models[0]['legacy']='../external'
        with self.assertRaises(ValueError):self.finish(token)
        self.assertTrue((self.root/'models/old/weights').exists())


if __name__=='__main__':unittest.main()
