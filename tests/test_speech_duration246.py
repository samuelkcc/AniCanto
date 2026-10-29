"""Measured duration, intentional overlap, and independent switch acceptance."""
import array,copy,json,math,shutil,sys,tempfile,unittest,wave
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows')]
import speech_duration as policy,speech_timing,work_modes,fast_mode,natural_delivery,natural_schedule
import delivery_policy,worker,delivery,source_mora,script_fit
FF=shutil.which('ffmpeg') or str(ROOT/'dist/AniCanto.app/Contents/Resources/bin/ffmpeg')
def cfg(strict=False,**extra):
 result=dict(speechDurationRevision=policy.REVISION,limitSpeechDuration=strict,workModeRevision=work_modes.REVISION,
  workMode='performance',duration=6.,speechRatePolicy='natural',productionMode='fast',targetLanguage='yue',
  ffmpeg=FF,aiAutoFix=False,fullAIReview=False,autoFit=True,autoValidate=False,failedVoicePolicy='first-take')
 result.update(extra);return work_modes.configure(result)
def wav(path,body=1.,lead=0.,tail=0.,quiet=False,stereo=False):
 sr=24000;channels=2 if stereo else 1;raw=array.array('h',[0])*round(lead*sr)*channels
 for n in range(round(body*sr)):
  value=(1 if n%2 else -1) if quiet else round(4500*math.sin(2*math.pi*240*n/sr))
  raw.extend([value,-value] if stereo else [value])
 raw.extend([0]*round(tail*sr)*channels)
 with wave.open(str(path),'wb') as f:f.setparams((channels,2,sr,0,'NONE','not compressed'));f.writeframes(raw.tobytes())
 return path
class SwitchTests(unittest.TestCase):
 def test_all_switch_combinations_survive_worker_initialization(self):
  for full in [False,True]:
   for repair in [False,True]:
    for strict in [False,True]:
     with self.subTest(full=full,repair=repair,strict=strict):
      c=cfg(strict,fullAIReview=full,aiAutoFix=repair,roleAnalysisMode='independent',automaticAlternateVoice=True,automaticSystemVoice=True)
      fast_mode.configure(c)
      self.assertEqual(c['aiAutoFix'],repair)
      self.assertTrue(c['automaticAlternateVoice']);self.assertTrue(c['automaticSystemVoice'])
      self.assertEqual(c['autoContentRepair'],repair)
      self.assertEqual(c['autoVoiceRepair'],repair)
      self.assertEqual(c['automaticDurationRewrite'],strict)
      self.assertEqual(c['allowCrossEngineRepair'],repair)
      self.assertEqual(c['maximumTimingRewritePasses'],int(strict))
 def test_legacy_saved_job_retains_its_old_semantics(self):
  c=dict(workModeRevision=work_modes.REVISION,workMode='performance',aiAutoFix=True,fullAIReview=False)
  work_modes.configure(c);self.assertFalse(policy.enabled(c));fast_mode.configure(c)
  self.assertFalse(c['aiAutoFix']);self.assertFalse(c['automaticDurationRewrite'])
 def test_no_mora_or_estimated_prefit_for_new_jobs(self):
  c=cfg(True);self.assertFalse(source_mora.active(c));w=Mock()
  with tempfile.TemporaryDirectory() as d:script_fit.fit(w,c,Path(d),[dict(start=0,end=1,cantonese='A long draft.')],Mock())
  w.ollama_chat.assert_not_called()
 def test_setting_rejects_non_boolean(self):
  import workflow_settings
  with self.assertRaises(ValueError):workflow_settings.validated(dict(limitSpeechDuration='false'))
 def test_defaults_are_unrestricted_for_new_work(self):
  from desktop_state import defaults
  c=defaults();self.assertEqual(c['speechDurationRevision'],policy.REVISION);self.assertFalse(c['limitSpeechDuration'])
class ClockTests(unittest.TestCase):
 def setUp(self):self.cues=[dict(start=0.,end=2.5,speechStart=0.,speechEnd=1.5,cantonese='First'),dict(start=1.7,end=3.,cantonese='Next')]
 def test_off_allows_crossing_next_dialogue_without_moving_start(self):
  self.assertEqual(speech_timing.natural_window(self.cues[0],self.cues,6.,cfg()),(0.,6.))
 def test_on_uses_source_speech_not_caption_tail(self):
  self.assertEqual(speech_timing.natural_window(self.cues[0],self.cues,6.,cfg(True)),(0.,1.5))
 def test_off_still_protects_manual_source_and_opening(self):
  self.cues[1]['preserveOriginalSpeech']=True
  self.assertEqual(speech_timing.natural_window(self.cues[0],self.cues,6.,cfg()),(0.,1.7))
  with patch('opening.local_ranges',return_value=[dict(start=1.,end=1.2)]):
   self.assertEqual(speech_timing.natural_window(self.cues[0],self.cues,6.,cfg()),(0.,1.))
 def test_original_simultaneous_speech_keeps_its_clock(self):
  self.cues[0].update(speechEnd=2.);self.assertEqual(speech_timing.natural_window(self.cues[0],self.cues,6.,cfg(True)),(0.,2.))
class MeasurementTests(unittest.TestCase):
 def test_count_file_and_trimmed_lengths_but_preserve_internal_pause_and_original(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);original=wav(job/'padded.wav',1.,.4,.7);before=original.read_bytes()
   # An internal pause must remain part of the performance duration.
   with wave.open(str(original)) as f:params=f.getparams();raw=array.array('h');raw.frombytes(f.readframes(params.nframes))
   for n in range(round(.8*24000),round(.95*24000)):raw[n]=0
   with wave.open(str(original),'wb') as f:f.setparams(params);f.writeframes(raw.tobytes())
   before=original.read_bytes();selected=policy.prepare(cfg(True),job,[dict(start=0,end=1.3,cantonese='Test')],[original])
   self.assertEqual(original.read_bytes(),before)
   self.assertAlmostEqual(natural_delivery.seconds(selected[0],{},None),1.16,places=2)
   with wave.open(str(selected[0])) as f:x=array.array('h');x.frombytes(f.readframes(f.getnframes()))
   self.assertGreater(sum(v==0 for v in x),round(.15*24000))
   row=json.loads((job/'speech-duration-measure.json').read_text())['rows'][0]
   self.assertAlmostEqual(row['fileSeconds'],2.1);self.assertTrue(row['internalPausesRetained'])
 def test_quiet_and_phase_inverted_stereo_voice_is_not_removed(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);p=wav(job/'quiet.wav',1.,.5,.5,quiet=True,stereo=True)
   target=policy.trim(cfg(True),job,p)
   self.assertAlmostEqual(natural_delivery.seconds(target,{},None),1.16,places=2)
   with wave.open(str(target)) as f:self.assertEqual(f.getnchannels(),2)
 def test_padding_alone_does_not_trigger_a_rewrite(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);p=wav(job/'padding.wav',1.,.6,.8);cues=[dict(start=0.,end=1.3,cantonese='Test')];c=cfg(True,automaticDurationRewrite=True,preferFirstAudibleTake=False)
   with patch('concise_dialogue.compact') as compact:
    paths=natural_delivery.repair(c,job,cues,[p],Mock(),Mock())
   compact.assert_not_called();self.assertLess(natural_delivery.seconds(paths[0],{},None),1.3)
class RewriteTests(unittest.TestCase):
 def test_true_measured_overrun_gets_one_shorter_take_and_keeps_authored_subtitle(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);long=wav(job/'long.wav',2.);short=wav(job/'short.wav',.9,.3,.5)
   cues=[dict(start=0.,end=1.4,speechEnd=1.4,cantonese='The complete old script',subtitleHint='Authored subtitle',japanese='Source sentence',speakerId='R01')]
   c=cfg(True,automaticDurationRewrite=True,preferFirstAudibleTake=False,_maximumTimingOperations=1,_durationFitRequired=True)
   def compact(w,cfg,job,drafts,pending,targets,**kw):
    self.assertGreater(cfg['_measuredOverruns']['0']['seconds'],cfg['_measuredOverruns']['0']['availableSeconds'])
    drafts[0]['cantonese']='Shorter script';return [0]
   with patch('concise_dialogue.compact',side_effect=compact) as edit,patch('dubbing.gsv_audio',return_value=[short]) as generate:
    result=natural_delivery.repair(c,job,cues,[long],Mock(),Mock())
   self.assertEqual(edit.call_count,1);self.assertEqual(generate.call_count,1)
   self.assertEqual(cues[0]['subtitleHint'],'Authored subtitle');self.assertEqual(cues[0]['cantonese'],'Shorter script')
   self.assertLess(natural_delivery.seconds(result[0],{},None),1.4)
 def test_off_never_shortens_even_with_an_overlong_recording(self):
  with patch('concise_dialogue.compact') as compact:
   self.assertEqual(natural_delivery.repair(cfg(),Path('/unused'),[],[],Mock(),Mock()),[])
  compact.assert_not_called()
class RenderingTests(unittest.TestCase):
 def test_real_mixer_keeps_intentional_overlap_and_reports_target_audio_present(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);first=wav(job/'first.wav',1.8);second=wav(job/'second.wav',.6)
   cues=[dict(start=0.,end=1.,cantonese='First'),dict(start=1.,end=2.,cantonese='Second')]
   c=cfg(False,duration=4.)
   with patch('source_counting.repair',return_value=[]):
    output,warnings=fast_mode.synthesize(c,job,cues,worker.run,Mock(),generated_paths=[first,second])
   rows=json.loads((job/'timing.json').read_text());self.assertTrue(output.is_file())
   self.assertFalse(rows[0]['skipped']);self.assertTrue(rows[0]['intentionalOverlap'])
   self.assertAlmostEqual(rows[0]['renderedSeconds'],1.8,places=2);self.assertAlmostEqual(rows[0]['overlapSeconds'],.8,places=2)
   self.assertFalse(rows[0]['requiresTimingReview']);self.assertFalse(rows[1]['skipped'])
class ReviewOnlyTests(unittest.TestCase):
 def test_full_review_with_repair_off_does_not_generate_content_retake(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);p=wav(job/'take.wav');generate=Mock(side_effect=AssertionError('Unexpected retake'))
   c=cfg(fullAIReview=True,aiAutoFix=False)
   proof=dict(requiresReview=True,heard='Different words',languageUnverified=False)
   with patch('speechcheck.inspect',return_value=[proof]),patch('cantonese_review.needs_repair',return_value=True):
    self.assertEqual(delivery.check_content(c,job,[dict(start=0,end=2,cantonese='Expected words')],[p],generate,Mock(),Mock()),[p])
   generate.assert_not_called()

class CoordinatorTests(unittest.TestCase):
 def test_real_delivery_pipeline_retains_overlap_and_does_not_call_the_text_model(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);first=wav(job/'first.wav',1.8,.3,.5);second=wav(job/'second.wav',.6)
   cues=[dict(start=0.,end=1.,cantonese='First',japanese='First source'),dict(start=1.,end=2.,cantonese='Second',japanese='Second source')]
   c=cfg(False,duration=4.,deliveryPolicyRevision=delivery_policy.REVISION,forcedDubbingRevision=delivery_policy.FORCED_TTS_REVISION)
   with patch('worker.ollama_chat',side_effect=AssertionError('No timing rewrite permitted')),patch('source_counting.repair',return_value=[]):
    output,warnings=fast_mode.synthesize(c,job,cues,worker.run,Mock(),generated_paths=[first,second])
   rows=json.loads((job/'timing.json').read_text());self.assertTrue(output.is_file())
   self.assertTrue(rows[0]['intentionalOverlap']);self.assertFalse(rows[0]['skipped']);self.assertFalse(rows[1]['skipped'])
   self.assertAlmostEqual(rows[0]['renderedSeconds'],1.96,places=2)
 def test_strict_pipeline_rewrites_only_measured_overrun_once_and_keeps_budget_on_resume(self):
  import recovery_coordinator
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);long=wav(job/'long.wav',2.);short=wav(job/'short.wav',.8,.3,.4)
   cues=[dict(start=0.,end=1.3,speechEnd=1.3,cantonese='Complete original draft',japanese='Source sentence')]
   c=cfg(True,deliveryPolicyRevision=delivery_policy.REVISION,forcedDubbingRevision=delivery_policy.FORCED_TTS_REVISION,failedVoicePolicy='source')
   def compact(w,settings,folder,drafts,pending,targets,**kw):drafts[0]['cantonese']='Short draft';return [0]
   with patch('concise_dialogue.compact',side_effect=compact) as edit,patch('dubbing.gsv_audio',return_value=[short]) as generate:
    paths,plan=recovery_coordinator.recover(c,job,cues,[long],worker.run,Mock())
    frozen_plan=json.loads((job/'repair-time-budget.json').read_text())['plan']
    again,plan2=recovery_coordinator.recover(c,job,cues,paths,worker.run,Mock())
    self.assertEqual(json.loads((job/'repair-time-budget.json').read_text())['plan'],frozen_plan)
   self.assertEqual(edit.call_count,1);self.assertEqual(generate.call_count,1)
   self.assertTrue(plan[0]['fit']);self.assertTrue(plan2[0]['fit'])
   self.assertTrue((job/'repair-time-budget.json').is_file())
   self.assertLess(natural_delivery.seconds(paths[0],{},None),1.3)

class InspectionRetentionTests(unittest.TestCase):
 def test_unconfirmed_short_audible_take_is_not_quarantined_when_repair_is_off(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);p=wav(job/'short.wav',.48);generate=Mock(side_effect=AssertionError('Unexpected retake'))
   c=cfg(fullAIReview=True,aiAutoFix=False)
   proof=dict(requiresReview=True,heard='',languageUnverified=True)
   with patch('speechcheck.inspect',return_value=[proof]),patch('cantonese_review.needs_repair',return_value=True):
    result=delivery.check_content(c,job,[dict(start=0,end=2,cantonese='Expected complete words')],[p],generate,Mock(),Mock())
   self.assertEqual(result,[p]);self.assertFalse(list(job.glob('skipped-*')));generate.assert_not_called()
   self.assertFalse(json.loads((job/'speech-check.json').read_text())['automaticRepairEnabled'])

class VoiceReviewRetentionTests(unittest.TestCase):
 def test_voice_inspection_does_not_regenerate_when_repair_is_off(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);(job/'speakers-ready.json').write_text('{}');p=wav(job/'take.wav')
   c=cfg(fullAIReview=True,aiAutoFix=False,storage=str(job),roleAnalysisMode='audio')
   generate=Mock(side_effect=AssertionError('Unexpected voice retake'))
   mismatch=dict(index=0,anchor=0,similarity=.1)
   with patch('voicecheck.embeddings',return_value=[None]),patch('voicecheck.inconsistent_takes',return_value=[mismatch]):
    self.assertEqual(delivery.stabilize_voices(c,job,[dict(start=0,end=2,cantonese='Expected words')],[p],generate,Mock(),Mock()),[p])
   generate.assert_not_called();self.assertEqual(json.loads((job/'voice-consistency.json').read_text())['repairs'],[])

if __name__=='__main__':unittest.main()
