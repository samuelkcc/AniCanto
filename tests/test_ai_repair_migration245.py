import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'windows'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
from desktop_state import Store,write,read

class AiRepairMigrationTests(unittest.TestCase):
 def test_stored_forced_value_turns_off_only_once(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   write(root/'desktop-state.json',dict(language='en',mode='expert',settings=dict(aiAutoFix=True),queue=[],selected=None,ui={}))
   store=Store(root,recover_running=False)
   self.assertFalse(store.settings['aiAutoFix'])
   marker=root/'migrations/ai-repair-default-off-v1.json'
   self.assertTrue(marker.exists())
   self.assertEqual(read(marker)['previous'],True)
   self.assertFalse(read(root/'desktop-state.json')['settings']['aiAutoFix'])
   # A later user choice must survive the one-time migration.
   store.settings['aiAutoFix']=True;store.save()
   self.assertTrue(Store(root,recover_running=False).settings['aiAutoFix'])
 def test_no_marker_when_the_stored_value_is_already_off(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   write(root/'desktop-state.json',dict(language='en',mode='expert',settings=dict(aiAutoFix=False),queue=[],selected=None,ui={}))
   store=Store(root,recover_running=False)
   self.assertFalse(store.settings['aiAutoFix'])
   self.assertFalse((root/'migrations/ai-repair-default-off-v1.json').exists())
 def test_missing_stored_settings_leave_the_default_off(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   store=Store(root,recover_running=False)
   self.assertFalse(store.settings['aiAutoFix'])
   self.assertFalse((root/'migrations/ai-repair-default-off-v1.json').exists())

if __name__=='__main__':unittest.main()
