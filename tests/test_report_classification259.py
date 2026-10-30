"""Current report grouping with isolated audio. No model or user film runs."""
import array,copy,json,math,os,sys,tempfile,unittest,wave
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows'),str(ROOT/'studio')]
import review_report,review_workbench,review_classification

class Classification(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.audio=self.root/'voice.wav';self.wav(self.audio)
  self.review=dict(config=dict(ttsBackend='gpt-sovits',targetLanguage='yue',dubLanguages=['yue'],selectedEngines=['gpt-sovits'],duration=2,voiceProfiles=[]),cues=[dict(start=0,end=1,cantonese='你好',japanese='こんにちは',enabled=True)])
  self.save('review.json',self.review);self.timing=dict(index=1,start=0,end=1,audio=str(self.audio),renderedAudio=str(self.audio),renderedSeconds=.2,text='你好',renderedStart=0,renderedEnd=.2);self.save('timing.json',[self.timing])
 def save(self,name,data):
  p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,ensure_ascii=False))
 def wav(self,path,silent=False):
  data=array.array('h',[0 if silent else round(2000*math.sin(i*2*math.pi*440/24000)) for i in range(4800)])
  with wave.open(str(path),'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(data.tobytes())
 def result(self,status='complete'):
  return review_report.project(self.root,self.review,dict(status=status))
 def group(self):return self.result()['reportRows'][0]['reportGroup']
 def test_audible_without_optional_audit_is_available_not_quality_pass(self):
  p=self.result();self.assertEqual(p['reportRows'][0]['reportGroup'],'reportAvailable');self.assertEqual(p['reviewState']['pending'],0);self.assertFalse(p['reviewState']['qualityChecked']);self.assertFalse(p['reportRows'][0]['qualityCertified'])
 def test_first_audible_retained_is_not_pending(self):
  self.save('normal-checks.json',dict(advisories=[dict(index=1,reason='uncertain-or-usable')]))
  p=review_workbench.project(self.root,self.result());self.assertEqual(p['reportRows'][0]['reportGroup'],'reportAvailable');self.assertEqual(p['workbench']['pending'],0)
 def test_missing_silent_and_damaged_are_primary(self):
  for kind in ['missing','silent','damaged']:
   with self.subTest(kind=kind):
    if kind=='missing':self.audio.unlink(missing_ok=True)
    elif kind=='silent':self.wav(self.audio,True)
    else:self.audio.write_bytes(b'corrupt')
    p=self.result();self.assertEqual(p['reportRows'][0]['reportGroup'],'reportMissing');self.assertEqual(p['reviewState']['needsDubbing'],1)
 def test_stale_missing_failure_cannot_override_repaired_current_take(self):
  self.save('segment-issues.json',[dict(index=1,kind='missing-audio')]);self.save('resolved-segment-issues.json',[dict(index=1,kind='missing-audio')])
  p=self.result();self.assertEqual(p['reportRows'][0]['reportGroup'],'reportAvailable');self.assertEqual(p['reviewState']['pending'],0);self.assertEqual(p['reviewState']['repaired'],1);self.assertEqual(len(p['reportHistory']),1)
 def test_current_content_finding_is_preserved_as_advisory(self):
  self.save('segment-issues.json',[dict(index=1,kind='targeted-language-or-integrity',check=dict(contentFailure=True))]);p=self.result();self.assertEqual(p['reportRows'][0]['reportGroup'],'reportAdvisory');self.assertEqual(p['reviewState']['pending'],0);self.assertEqual(len(p['issues']),1)
 def test_silence_after_historical_repair_still_needs_dubbing(self):
  self.save('resolved-segment-issues.json',[dict(index=1,kind='missing-audio')]);self.wav(self.audio,True);p=self.result();self.assertEqual(p['reportRows'][0]['reportGroup'],'reportMissing');self.assertEqual(p['reviewState']['repaired'],0)
 def test_unplanned_original_fallback_is_missing_target_not_total_silence(self):
  self.timing['originalFallback']=True;self.save('timing.json',[self.timing]);self.assertEqual(self.group(),'reportMissing')
 def test_deliberate_original_choice_is_preserved_not_missing(self):
  self.save('editor-draft-studio.json',dict(segments=[dict(sources=[0],reviewDecisions={'yue:gpt-sovits':dict(action='original')})]));self.assertEqual(self.group(),'reportPreserved')
 def test_saved_recording_choice_is_available_even_if_export_pending(self):
  self.timing.update(originalFallback=True);self.save('timing.json',[self.timing]);self.save('editor-draft-studio.json',dict(segments=[dict(sources=[0],reviewDecisions={'yue:gpt-sovits':dict(action='recording',audio=str(self.audio))})]));p=self.result();self.assertEqual(p['reportRows'][0]['reportGroup'],'reportAvailable');self.assertTrue(p['reportRows'][0]['pendingExport'])
 def test_protected_performance_and_disabled_line_are_preserved(self):
  for change in [dict(enabled=False),dict(opEdKind='opening'),dict(preserveOriginalSpeech=True,originalSpeechReason='confirmed-nonlexical-performance')]:
   with self.subTest(change=change):
    before=copy.deepcopy(self.review['cues'][0]);self.review['cues'][0].update(change);self.assertEqual(self.group(),'reportPreserved');self.review['cues'][0]=before
 def test_generic_selected_target_is_available(self):
  self.save('target-reference-recovery.json',{'1':dict(index=1,status='selected-unverified',audio=str(self.audio))});self.assertEqual(self.group(),'reportAvailable')
 def test_real_long_file_is_advisory_not_missing(self):
  self.timing['renderedEnd']=4;self.save('timing.json',[self.timing]);self.assertEqual(self.group(),'reportAdvisory')
 def test_translation_warning_is_advisory_not_missing(self):
  self.review['cues'][0]['translationWarnings']=[dict(stage='own-turn-caption')];self.assertEqual(self.group(),'reportAdvisory')
 def test_hash_changed_is_not_available(self):
  self.timing['audioSHA256']='0'*64;self.save('timing.json',[self.timing]);self.assertEqual(self.group(),'reportMissing')
 def test_live_generation_unknown_is_checking_not_failed(self):
  (self.root/'timing.json').unlink();p=self.result('running');self.assertEqual(p['reportRows'][0]['reportGroup'],'checking');self.assertEqual(p['reviewState']['pending'],0)
 def test_only_optional_cache_file_is_written(self):
  before={str(p):p.read_bytes() for p in self.root.glob('*.json')};self.result();self.assertTrue(all(Path(p).read_bytes()==b for p,b in before.items()));self.assertEqual(set(p.name for p in self.root.glob('*.json'))-set(Path(p).name for p in before),{'review-audio-evidence.json'})
 def test_cache_reuses_sha_and_detects_changed_audio(self):
  self.result()
  with patch('review_classification.hashlib.sha256',side_effect=AssertionError('Cache should reuse same recording SHA')):self.assertEqual(self.group(),'reportAvailable')
  self.wav(self.audio,True);self.assertEqual(self.group(),'reportMissing')
 def test_selected_choice_uses_its_own_hash_not_old_timing_hash(self):
  import hashlib
  self.timing['audioSHA256']='0'*64;self.save('timing.json',[self.timing])
  self.save('editor-draft-studio.json',dict(segments=[dict(sources=[0],reviewDecisions={'yue:gpt-sovits':dict(action='recording',audio=str(self.audio),audioSHA256=hashlib.sha256(self.audio.read_bytes()).hexdigest())})]))
  self.assertEqual(self.group(),'reportAvailable')
 def test_coverage_header_matches_current_four_group_counts(self):
  import editing_tools
  self.save('segment-issues.json',[dict(index=1,kind='missing-audio')]);self.save('resolved-segment-issues.json',[dict(index=1,kind='missing-audio')]);result=self.result();result['review']=self.review
  coverage=editing_tools.coverage(result);self.assertEqual(coverage['tracks'][0]['missing'],[]);self.assertEqual(coverage['tracks'][0]['recordings'],1);self.assertEqual(result['reviewState']['repairEligible'],0)
 def test_covered_continuation_is_preserved_not_a_missing_tts(self):
  self.review['cues'][0].update(captionCovered=True,captionCoverageOwners=[2],enabled=False)
  self.save('segment-issues.json',[dict(index=1,kind='fast-generation-failed')])
  p=self.result();self.assertEqual(p['reviewState']['needsDubbing'],0);self.assertEqual(p['issues'][0]['kind'],'subtitle-continuation');self.assertFalse(p['issues'][0]['repairEligible']);self.assertTrue(p['reportRows'][0]['captionCovered'])
 def test_legacy_continuation_reason_does_not_imply_model_failure(self):
  self.review['cues'][0].update(preserveOriginalSpeech=True,originalSpeechReason='subtitle-continuation')
  self.save('segment-issues.json',[dict(index=1,kind='fast-generation-failed')])
  p=self.result();self.assertEqual(p['issues'][0]['kind'],'subtitle-continuation');self.assertFalse(p['issues'][0]['repairEligible'])
 def test_normalization_never_runs_inference_or_repair(self):
  with patch('worker.ollama_chat',side_effect=AssertionError('No model call')),patch('normal_mode.repair_paths',side_effect=AssertionError('No repair')):self.result()

if __name__=='__main__':unittest.main()
