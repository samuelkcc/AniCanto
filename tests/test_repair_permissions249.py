"""Execution boundaries for the frozen final-fallback choice and AI permissions."""
import copy,itertools,json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from test_speech_duration246 import cfg as duration_cfg,wav
import repair_permissions as permissions,recovery_coordinator as coordinator
import delivery_policy,failed_voice_policy,normal_voice_fallback,normal_engine_fallback,system_voice

def config(choice='first-take',review=False,repair=False,strict=False,**extra):
 c=duration_cfg(strict,repairPermissionsRevision=permissions.REVISION,failedVoicePolicy=choice,fullAIReview=review,aiAutoFix=repair,
  automaticAlternateVoice=True,automaticSystemVoice=True,deliveryPolicyRevision=delivery_policy.REVISION,
  forcedDubbingRevision=delivery_policy.FORCED_TTS_REVISION,ttsBackend='drama3')
 c.update(extra);return c

class PermissionTests(unittest.TestCase):
 def test_coordinator_executes_the_three_choice_switch_matrix(self):
  for choice,review,repair,strict in itertools.product(['generic','first-take','source'],[False,True],[False,True],[False,True]):
   with self.subTest(choice=choice,review=review,repair=repair,strict=strict),tempfile.TemporaryDirectory() as d:
    job=Path(d);c=config(choice,review,repair,strict);cue=dict(start=0.,end=1.5,cantonese='Test',reviewIndex=0)
    path=wav(job/'first.wav',1.);paths=[path];placement=[dict(index=1,fit=False,start=0.,deadline=1.5,seconds=2.)]
    with patch('safe_vocal_capacity.configure'),patch('recovery_plan.prepare'),patch('production_progress.phase'),patch('normal_policy.finish_requested',return_value=False),patch('natural_finish.finish',return_value=(paths,placement)),patch.object(coordinator,'physical',return_value=paths) as missing,patch.object(coordinator,'actor',return_value=paths) as actor,patch.object(coordinator,'fallback',return_value=paths) as generic,patch('normal_engine_fallback.repair',return_value=paths) as alternate,patch('system_voice.repair',return_value=paths) as native:
     coordinator.recover(c,job,[cue],paths,Mock(),Mock())
    self.assertEqual(missing.call_count,1)
    self.assertEqual(actor.call_count,int(strict))
    self.assertEqual(generic.call_count,int(choice=='generic'))
    self.assertEqual(alternate.call_count,int(repair))
    # The coordinator itself must not even enter a disallowed native stage.
    self.assertEqual(native.call_count,int(choice=='generic' and repair))
 def test_generator_entries_reject_disallowed_calls_before_inference(self):
  for choice,repair in itertools.product(['generic','first-take','source'],[False,True]):
   c=config(choice,repair=repair);paths=['missing.wav'];placement=[dict(fit=False)]
   with tempfile.TemporaryDirectory() as d,patch('dubbing.gsv_audio') as generate,patch('system_voice.installed') as voices:
    if choice!='generic':self.assertEqual(normal_voice_fallback.repair(c,Path(d),[],paths,placement,Mock(),Mock()),paths)
    if not repair or choice!='generic':self.assertEqual(system_voice.repair(c,Path(d),[],paths,placement,Mock(),Mock()),paths)
    if not repair:self.assertEqual(normal_engine_fallback.repair(c,Path(d),[],paths,placement,Mock(),Mock()),paths)
    elif choice!='generic':self.assertEqual(normal_engine_fallback.repair(dict(c,_genericTargetVoice=True),Path(d),[],paths,placement,Mock(),Mock()),paths)
    generate.assert_not_called();voices.assert_not_called()
 def test_review_without_repair_does_not_reject_an_audible_take(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);path=wav(job/'original.wav',1.);c=config(review=True);cue=dict(start=0.,end=1.5,cantonese='Test')
   (job/'normal-checks.json').write_text(json.dumps(dict(unresolved=[1],repairs=[dict(index=1,check=dict(contentFailure=True))])))
   self.assertEqual(delivery_policy.confirmed_indices(c,job),set())
   self.assertEqual(failed_voice_policy.choose(c,job,[cue],[path]),([path],set()))
 def test_first_take_is_saved_once_and_survives_failed_later_take(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);first=wav(job/'first.wav',1.);later=wav(job/'later.wav',2.);c=config(strict=True);cue=dict(start=0.,end=1.5,cantonese='Test')
   permissions.capture(c,job,[cue],[first]);before=(job/'first-audible-takes.json').read_bytes();permissions.capture(c,job,[cue],[later])
   self.assertEqual((job/'first-audible-takes.json').read_bytes(),before)
   self.assertEqual(failed_voice_policy.choose(c,job,[cue],[later]),([first],set()))
 def test_strict_overrun_cannot_resurrect_first_take_but_overlap_can(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);p=wav(job/'long.wav',2.);cue=dict(start=0.,end=1.5,cantonese='Test');c=config(strict=True)
   permissions.capture(c,job,[cue],[p]);self.assertEqual(failed_voice_policy.choose(c,job,[cue],[p])[1],{0})
   c['limitSpeechDuration']=False
   self.assertEqual(failed_voice_policy.choose(c,job,[cue],[p])[1],set())
 def test_identity_and_hash_prevent_stale_recording_reuse(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);p=wav(job/'first.wav',1.);cue=dict(start=0.,end=1.5,cantonese='Test');c=config()
   permissions.capture(c,job,[cue],[p]);self.assertIsNone(permissions.first(c,job,dict(cue,cantonese='Changed')))
   wav(p,1.1);self.assertIsNone(permissions.first(c,job,cue))
 def test_old_job_is_not_restamped_by_initializers_or_child_execution(self):
  import work_modes,fast_mode
  c=duration_cfg();work_modes.configure(c);fast_mode.configure(c);delivery_policy.new_execution(c,'unused')
  self.assertNotIn('repairPermissionsRevision',c)
 def test_disabled_parent_repair_never_creates_ledgers(self):
  import ai_result_repair
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);self.assertEqual(ai_result_repair.run(Mock(),config(),job,[]),([],None));self.assertEqual(list(job.iterdir()),[])
 def test_resume_does_not_refill_existing_recovery_plan(self):
  import recovery_plan
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);marker=job/'repair-time-budget.json';original=dict(plan=dict(phaseLimits=dict(ai=0,native=0,listening=0)),phases=dict(ai=dict(spentSeconds=60)))
   marker.write_text(json.dumps(original));before=marker.read_bytes();recovery_plan.prepare(config('generic',repair=True),job,[],[]);self.assertEqual(marker.read_bytes(),before)
 def test_native_budget_only_reserved_with_both_permissions(self):
  import recovery_plan
  for choice,repair in itertools.product(['generic','first-take','source'],[False,True]):
   with tempfile.TemporaryDirectory() as d:
    job=Path(d);recovery_plan.prepare(config(choice,repair=repair),job,[],[])
    plan=json.loads((job/'repair-time-budget.json').read_text())['plan'];self.assertEqual(plan['phaseLimits']['native']>0,choice=='generic' and repair)

class EvidenceTests(unittest.TestCase):
 def test_empty_transcripts_remain_advisory_even_with_ai_repair(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);p=wav(job/'voiced.wav',1.);check=dict(contentFailure=True,confirmedContentFailure=True,heard='',independent=dict(heard=''))
   (job/'normal-checks.json').write_text(json.dumps(dict(unresolved=[1],repairs=[dict(index=1,check=check)])))
   self.assertEqual(delivery_policy.confirmed_indices(config(repair=True),job),set())
   self.assertFalse(permissions.advisory(check)['confirmedContentFailure'])
 def test_old_bad_hash_does_not_reject_a_new_good_take(self):
  import hashlib
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);old=wav(job/'bad.wav',.8);new=wav(job/'good.wav',1.);cue=dict(start=0,end=1.5,cantonese='Test')
   (job/'normal-checks.json').write_text(json.dumps(dict(unresolved=[1],repairs=[dict(index=1,audioSHA256=hashlib.sha256(old.read_bytes()).hexdigest(),check=dict(contentFailure=True,heard='Wrong words'))])))
   selected,source=failed_voice_policy.choose(config(repair=True),job,[cue],[new]);self.assertEqual(selected,[new]);self.assertFalse(source)

class GenerationCountTests(unittest.TestCase):
 def test_generic_selected_engine_runs_once_across_resume(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);reference=wav(job/'reference.wav',1.);candidate=wav(job/'generic.wav',1.)
   cue=dict(start=0.,end=1.5,cantonese='Test',speakerId='R01',reviewIndex=0)
   c=config('generic',repair=False);paths=[job/'missing.wav'];placement=[dict(index=1,fit=False,start=0.,deadline=6.,seconds=None)]
   profile=dict(id='generic-test',reference=str(reference),language='yue',naturalReferenceId='test')
   with patch('dubbing.profile_for',return_value=profile),patch('natural_voices.resolve',return_value=profile),patch('dubbing.gsv_audio',return_value=[candidate]) as generate:
    result=coordinator.fallback(c,job,[cue],paths,Mock(),Mock(),placement)
    resumed=coordinator.fallback(c,job,[cue],paths,Mock(),Mock(),placement)
   self.assertEqual(result,[candidate]);self.assertEqual(resumed,[candidate]);self.assertEqual(generate.call_count,1)
   counts=json.loads((job/'recovery-operation-counts.json').read_text());self.assertTrue(counts)
 def test_missing_fill_is_two_calls_total_across_resume(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);cue=dict(start=0.,end=1.5,cantonese='Test',speakerId='R01',reviewIndex=0);paths=[job/'missing.wav'];c=config()
   with patch('dubbing.gsv_audio',return_value=[job/'failed.wav']) as generate:
    coordinator.physical(c,job,[cue],paths,Mock(),Mock())
    coordinator.physical(c,job,[cue],paths,Mock(),Mock())
   self.assertEqual(generate.call_count,2)
