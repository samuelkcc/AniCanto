import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import delivery_policy as policy,repair_limits as limits,worker

class RepairBudgetTests(unittest.TestCase):
 def config(self,**kw):return dict(deliveryPolicyRevision=policy.POOLED_REVISION,duration=1800,workMode='balanced',_repairBudgetSeconds=10,**kw)
 def test_mode_defaults_are_per_film_not_per_cue(self):
  for mode,expected in [('performance',60),('balanced',180),('quality',600)]:self.assertEqual(limits.limit(dict(duration=1800,workMode=mode)),expected)
 def test_spent_allowance_persists_and_pause_time_is_not_charged(self):
  with tempfile.TemporaryDirectory() as d:
   now=[0.];calls=[]
   @limits.bounded('test')
   def repair(cfg,job,cues,paths):calls.append(1);now[0]+=3;return ['new']
   with patch('repair_limits.time.monotonic',side_effect=lambda:now[0]):
    self.assertEqual(repair(self.config(),d,[],['old']),['new']);now[0]=1000;repair(self.config(),d,[],['old'])
   saved=json.loads((Path(d)/'repair-time-budget.json').read_text());self.assertEqual(saved['spentSeconds'],6);self.assertEqual(len(calls),2)
 def test_nested_stages_do_not_double_charge_and_all_tracks_share_budget(self):
  with tempfile.TemporaryDirectory() as d:
   now=[0.];cfg=self.config(_repairBudgetRoot=d)
   @limits.bounded('inner')
   def inner(c,j,cs,ps):now[0]+=3;return ps
   @limits.bounded('outer')
   def outer(c,j,cs,ps):return inner(c,j,cs,ps)
   with patch('repair_limits.time.monotonic',side_effect=lambda:now[0]):
    outer(cfg,Path(d)/'tracks/a',[],['a']);outer(dict(cfg,targetLanguage='en'),Path(d)/'tracks/b',[],['b'])
   saved=json.loads((Path(d)/'repair-time-budget.json').read_text());self.assertEqual(saved['spentSeconds'],6);self.assertEqual(len(saved['stages']),2)
 def test_expiry_returns_retained_paths_and_never_refills_on_resume(self):
  with tempfile.TemporaryDirectory() as d:
   now=[0.];calls=[]
   @limits.bounded('expire')
   def repair(c,j,cs,ps):calls.append(1);now[0]+=11;limits.check();raise AssertionError('not reached')
   with patch('repair_limits.time.monotonic',side_effect=lambda:now[0]):
    self.assertEqual(repair(self.config(),d,[],['kept']),['kept']);self.assertEqual(repair(self.config(),d,[],['kept']),['kept'])
   self.assertEqual(len(calls),1);self.assertEqual(json.loads((Path(d)/'repair-time-budget.json').read_text())['spentSeconds'],11)
 def test_abandoned_active_clock_is_charged_on_resume(self):
  with tempfile.TemporaryDirectory() as d:
   worker.atomic_json(Path(d)/'repair-time-budget.json',dict(limitSeconds=10,phases=dict(ai=dict(spentSeconds=1,activeSince=90))))
   fn=Mock();wrapped=limits.bounded('resume')(fn)
   with patch('repair_limits.time.time',return_value=100):self.assertEqual(wrapped(self.config(),d,[],['kept']),['kept'])
   fn.assert_not_called()
   self.assertTrue(json.loads((Path(d)/'repair-time-budget.json').read_text())['phases']['ai']['recoveredActiveClock'])
 def test_last_quarter_is_reserved_for_native_and_mode_change_never_refills(self):
  with tempfile.TemporaryDirectory() as d:
   now=[0.]
   @limits.bounded('ai')
   def ai(c,j,cs,ps):now[0]+=8;return ['ai']
   @limits.bounded('native',phase='native')
   def native(c,j,cs,ps):now[0]+=1;return ['native']
   with patch('repair_limits.time.monotonic',side_effect=lambda:now[0]):
    ai(self.config(),d,[],[]);self.assertEqual(ai(dict(self.config(),workMode='quality'),d,[],['held']),['held']);self.assertEqual(native(self.config(),d,[],[]),['native'])
   saved=json.loads((Path(d)/'repair-time-budget.json').read_text());self.assertEqual(saved['limitSeconds'],10);self.assertEqual(saved['phases']['native']['spentSeconds'],1)
 def test_legacy_job_and_manual_preview_are_not_migrated(self):
  with tempfile.TemporaryDirectory() as d:
   fn=Mock(return_value=['x']);wrapped=limits.bounded('legacy')(fn)
   for c in [dict(deliveryPolicyRevision=policy.LEGACY_REVISION),dict(self.config(),editorRender=True)]:self.assertEqual(wrapped(c,d,[],[]),['x'])
   self.assertFalse((Path(d)/'repair-time-budget.json').exists())
 def test_current_owned_tool_finishes_then_next_inference_is_blocked(self):
  with tempfile.TemporaryDirectory() as d:
   ran=[]
   @limits.bounded('tool')
   def repair(c,j,cs,ps):
    worker.run([sys.executable,'-c','import time;time.sleep(.1)']);ran.append(1);limits.check();raise AssertionError('not reached')
   result=repair(dict(self.config(),_repairBudgetSeconds=.04),d,[],['original']);self.assertEqual(result,['original']);self.assertEqual(ran,[1]);self.assertEqual(json.loads((Path(d)/'repair-time-budget.json').read_text())['phases']['ai']['status'],'exhausted')

if __name__=='__main__':unittest.main()
