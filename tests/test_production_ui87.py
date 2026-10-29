"""Paused request isolation and the single standard mode at the desktop boundary."""
import json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'studio'),str(ROOT/'windows'),str(ROOT/'Resources')]
import test_shared_studio as shared
from desktop_state import write,read
import work_modes

class ProductionSettingsTests(unittest.TestCase):
 setUp=shared.SharedStudioTests.setUp
 tearDown=shared.SharedStudioTests.tearDown
 add=shared.SharedStudioTests.add
 def test_paused_elsewhere_does_not_lock_new_defaults_or_rewrite_request(self):
  ident=self.add();row=self.app.row(ident);saved=self.root/'requests/paused.json';write(saved,dict(workMode='performance',fullAIReview=True,video=str(self.video),sourceWorkflowRevision='frozen'))
  row.update(status='paused',request=str(saved));self.app.store.save();before=saved.read_bytes()
  result=self.app.dispatch('configure',dict(settings=dict(fullAIReview=False,automaticSystemVoice=False,autoSkipOP=False,translateOPED=True)))
  self.assertEqual(result['settings']['workMode'],'performance');self.assertFalse(result['settings']['fullAIReview']);self.assertTrue(result['settings']['translateOPED']);self.assertEqual(saved.read_bytes(),before)
  self.assertEqual(self.app.store.submit(row),saved);self.assertEqual(saved.read_bytes(),before)
 def test_one_work_mode_in_both_interface_views(self):
  expert=self.app.dispatch('configure',dict(mode='expert',settings={}))
  self.assertEqual(expert['settings']['workMode'],'performance')
  self.assertEqual(expert['settings']['workModeRevision'],work_modes.REVISION)
  state=self.app.dispatch('configure',dict(mode='basic',settings={}))
  self.assertEqual(state['settings']['workMode'],'performance');self.assertEqual(state['settings']['productionMode'],'fast')
  ident=self.add();request=self.app.store.submit(self.app.row(ident));self.assertEqual(read(request)['workMode'],'performance')
  self.assertEqual(read(request)['workModeRevision'],work_modes.REVISION)
  self.assertEqual(read(request)['productionMode'],'fast')
 def test_legacy_speed_values_cannot_be_selected(self):
  self.app.dispatch('configure',dict(mode='basic',settings=dict(workMode='quality')))
  ident=self.add();request=self.app.store.submit(self.app.row(ident));submitted=read(request)
  self.assertEqual(submitted['workMode'],'performance');self.assertEqual(submitted['workModeRevision'],work_modes.REVISION)
  self.assertFalse(submitted['automaticDurationRewrite']);self.assertEqual(submitted['maximumTimingRewritePasses'],0)
 def test_ai_repair_switch_is_off_until_the_user_turns_it_on(self):
  self.assertFalse(self.app.dispatch('configure',dict(settings={}))['settings']['aiAutoFix'])
  on=self.app.dispatch('configure',dict(settings=dict(aiAutoFix=True)))['settings']
  self.assertTrue(on['aiAutoFix'])
  off=self.app.dispatch('configure',dict(settings=dict(aiAutoFix=False)))['settings']
  self.assertFalse(off['aiAutoFix']);self.assertFalse(off['automaticAlternateVoice']);self.assertFalse(off['automaticSystemVoice'])
 def test_mode_and_full_ai_remain_locked_while_actually_running(self):
  ident=self.add();self.app.row(ident).update(status='running',request='active.json')
  for settings in [dict(fullAIReview=True),dict(aiAutoFix=True)]:
   with self.assertRaisesRegex(ValueError,'locked'):self.app.dispatch('configure',dict(settings=settings))

if __name__=='__main__':unittest.main()
