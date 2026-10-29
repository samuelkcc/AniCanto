import json,sys,tempfile,unittest,wave
from pathlib import Path
from unittest.mock import Mock,patch
sys.path[:0]=[str(Path(__file__).parents[1]/'Resources'),str(Path(__file__).parents[1]/'windows')]
import work_modes,delivery_policy,worker,dubbing
import test_delivery85 as fixtures
audio=fixtures.audio
from desktop_state import Store,defaults

class WorkModeTests(unittest.TestCase):
 # Revision 1 keeps the old three-mode policy set. Revision 2 has one mode and is
 # covered by tests/test_standard_mode245.py.
 def config(self,mode='balanced',full=False):return dict(workModeRevision=work_modes.REVISION_1,workMode=mode,fullAIReview=full,deliveryPolicyRevision=delivery_policy.REVISION)
 def test_three_modes_map_to_separate_bounded_policies_and_no_visual_analysis_by_default(self):
  for mode,production,policy,passes in [('performance','fast','missing-only',0),('balanced','normal','missing-only',1),('quality','normal','verified',2)]:
   c=work_modes.configure(self.config(mode));self.assertEqual((c['productionMode'],c['normalRepairPolicy'],c['maximumTimingRewritePasses']),(production,policy,passes));self.assertTrue(c['autoApprove']);self.assertTrue(c['continueOnError']);self.assertFalse(c['visualRoleAnalysisEnabled'])
 def test_full_ai_is_independent_and_preserves_mode_budget(self):
  for mode,passes in [('performance',0),('balanced',1),('quality',2)]:
   c=work_modes.configure(self.config(mode,True));self.assertEqual(c['productionMode'],'standard');self.assertEqual(c['roleAnalysisMode'],'audiovisual');self.assertEqual(c['maximumTimingRewritePasses'],passes)
 def test_old_request_is_not_migrated_and_new_default_is_balanced(self):
  old=dict(productionMode='standard',autoApprove=False);self.assertEqual(work_modes.configure(dict(old)),old)
  self.assertEqual(defaults()['workMode'],'performance');self.assertEqual(defaults()['workModeRevision'],work_modes.REVISION);self.assertFalse(defaults()['fullAIReview'])
 def test_invalid_new_mode_or_full_ai_value_is_rejected_before_generation(self):
  for cfg in [self.config('wrong'),self.config(full='yes')]:
   with self.assertRaises(ValueError):work_modes.configure(cfg)
 def test_frozen_paused_request_is_returned_unchanged(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);s=Store(root);request=root/'saved.json';request.write_text(json.dumps(dict(productionMode='standard',video='frozen')));before=request.read_bytes();row=dict(request=str(request),status='paused');s.settings.update(workMode='balanced',fullAIReview=False)
   self.assertEqual(s.submit(row),request);self.assertEqual(request.read_bytes(),before)
 def test_performance_bank_voice_skips_listening_but_is_not_quality_certified(self):
  import normal_voice_fallback
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cfg,cues,paths,place,bank=fixtures.GenericDeliveryTests().trial(root);cfg.update(self.config('performance'));cfg.update(productionMode='normal',duration=4,_objectiveFallbackOnly=True)
   (root/'target-reference-recovery.json').unlink();candidate=audio(root/'fit.wav',1);bad=root/'skipped-failed.wav';paths[0]=bad
   with patch('dubbing.profile_for',return_value=bank),patch('natural_voices.resolve',return_value=bank),patch('dubbing.gsv_audio',return_value=[candidate]),patch('normal_mode.inspect') as listen:
    out=normal_voice_fallback.repair(cfg,root,cues,paths,place,Mock(),Mock())
   listen.assert_not_called();self.assertEqual(out[0],candidate)
   record=next(iter(json.loads((root/'target-reference-recovery.json').read_text()).values()));self.assertEqual(record['status'],'selected-unverified');self.assertFalse(record['voiceSimilarityCertified'])
 def test_zero_target_audio_can_finish_only_with_audible_documented_source_continuity(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cfg=self.config();cues=[dict(start=0,end=1,cantonese='你好呀',enabled=True)];wav=audio(root/'mix.wav',1)
   worker.atomic_json(root/'timing.json',[dict(index=1,originalFallback=True,skipped=True)])
   self.assertTrue(delivery_policy.source_only_delivery(cfg,root,cues,(wav,[]),Mock(),Mock()))
   report=json.loads((root/'source-only-delivery.json').read_text());self.assertEqual(report['translatedDialogue'],0);self.assertFalse(report['qualityCertified'])
   worker.atomic_json(root/'timing.json',[dict(index=1,skipped=True)])
   self.assertFalse(delivery_policy.source_only_delivery(cfg,root,cues,(wav,[]),Mock(),Mock()))
   self.assertFalse(delivery_policy.source_only_delivery(dict(cfg,editorRender=True),root,cues,(wav,[]),Mock(),Mock()))
 def test_automatic_missing_all_actor_references_reaches_fallback_instead_of_stopping(self):
  cue=dict(start=0,end=1,cantonese='你好呀',enabled=True,speakerId='missing')
  with patch('dubbing.profile_for',side_effect=ValueError('not available')):
   self.assertIsNone(dubbing.require_profiles(self.config(),[cue]))
   with self.assertRaises(ValueError):dubbing.require_profiles({},[cue])

if __name__=='__main__':unittest.main()

class FrozenEntryModeTests(unittest.TestCase):
 def test_all_modes_full_ai_switch_and_source_defaults_are_resolved_before_freeze(self):
  import copy,source_workflow
  class Reached(Exception):pass
  for mode in work_modes.MODES:
   for full in [False,True]:
    with self.subTest(mode=mode,full=full),tempfile.TemporaryDirectory() as d:
     root=Path(d);video=root/'video.mkv';video.write_bytes(b'fixture');cfg=dict(workModeRevision=work_modes.REVISION,workMode=mode,fullAIReview=full,deliveryPolicyRevision=delivery_policy.REVISION,sourceWorkflowRevision=source_workflow.REVISION,sourceWorkflow='auto',interfaceMode='basic',video=str(video),storage=d,ffprobe='probe',ttsBackend='drama3',sourceLanguage='ja',separateBackground=True)
     meta=dict(format=dict(duration=10),streams=[dict(index=0,codec_type='video'),dict(index=1,codec_type='audio',tags=dict(language='jpn')),dict(index=2,codec_type='subtitle',codec_name='subrip',tags=dict(language='chi'))]);seen=[]
     with patch.object(worker,'run',return_value=json.dumps(meta)),patch.object(worker,'emit'),patch('engine_policy.migrate'),patch('studio_core.freeze',side_effect=lambda c:seen.append(copy.deepcopy(c))),patch('model_recovery.recover'),patch('source_language.supported',return_value=True),patch('opening.prepare'),patch('dubbing.separate',side_effect=Reached):
      with self.assertRaises(Reached):worker.convert(cfg)
     self.assertTrue(seen);last=seen[-1];self.assertEqual(last['sourceWorkflowEffective'],'subtitles-speech');self.assertEqual(last['sourceContentPriority'],'subtitles');self.assertEqual(last['workMode'],mode);self.assertEqual(last['fullAIReview'],full);self.assertEqual(last['automaticDurationRewrite'],mode!='performance')
