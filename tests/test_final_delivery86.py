import copy,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
from test_coordinator86 import wav,cue,cfg
import final_delivery_cache as cache,delivery_policy as policy,repair_limits as limits

class FinalDeliveryTests(unittest.TestCase):
 def test_saved_mix_reused_only_with_exact_script_parameters_and_audio(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);c=cfg(r);cs=[cue()];audio=wav(r/'mix.wav');cache.save(c,r,cs,audio,[dict(kind='needs-listen')]);self.assertEqual(cache.load(c,r,cs),(audio,[dict(kind='needs-listen')]))
   changed=copy.deepcopy(cs);changed[0]['cantonese']='再見啦';self.assertIsNone(cache.load(c,r,changed));self.assertIsNone(cache.load(dict(c,workMode='quality'),r,cs))
   wav(audio,.5);self.assertIsNone(cache.load(c,r,cs))
 def test_explicit_new_delivery_resets_execution_only_and_parent_ledger_stays(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);parent=r/'parent';parent.mkdir();ledger=parent/'repair-time-budget.json';ledger.write_text('{"spentSeconds":180}');c=cfg(r,_repairBudgetRoot=str(parent),_repairDeadlineUTC=1,_recoveryAIDeadline=1,finalOnly=True,exportRetries=2,sourceWorkflowRevision='frozen-v1',sourceWorkflowEffective='subtitles-speech')
   child=parent/'versions/new';child.mkdir(parents=True);policy.new_execution(c,child)
   self.assertEqual(c['_repairBudgetRoot'],str(child));self.assertNotIn('finalOnly',c);self.assertNotIn('_repairDeadlineUTC',c);self.assertEqual(c['sourceWorkflowRevision'],'frozen-v1');self.assertEqual(json.loads(ledger.read_text()),dict(spentSeconds=180));self.assertFalse((child/'repair-time-budget.json').exists())
 def test_stage_counts_do_not_refill_when_text_changes_or_on_resume(self):
  from recovery_attempts import reserve
  with tempfile.TemporaryDirectory() as d:
   self.assertTrue(reserve(d,'actor-timing',1,1));self.assertFalse(reserve(d,'actor-timing',1,1));self.assertTrue(reserve(d,'generic-compact',1,1));self.assertFalse(reserve(d,'generic-compact',1,1))
 def test_full_ai_switch_never_restarts_unbudgeted_post_export_listening(self):
  from unittest.mock import patch,Mock
  import quality
  with patch('fast_mode.validation',return_value={'validated':True}) as check,patch('quality.inspect_rendered_voice',side_effect=AssertionError('must not rerun whole film')):
   result=quality.validate_export(dict(deliveryPolicyRevision=policy.REVISION,workMode='balanced',productionMode='standard',fullAIReview=True),Path('/fixture'),[],Path('/fixture/out.mp4'),Mock(),Mock())
  self.assertEqual(result,{'validated':True});self.assertEqual(check.call_args.args[0]['productionMode'],'normal')
 def test_empty_derived_term_list_is_canonical_for_packaging_resume(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);c=cfg(r);cs=[dict(cue(),termRequirements=[])];audio=wav(r/'mix.wav');cache.save(c,r,cs,audio,[]);self.assertEqual(cache.load(c,r,[cue()]),(audio,[]))

if __name__=='__main__':unittest.main()
