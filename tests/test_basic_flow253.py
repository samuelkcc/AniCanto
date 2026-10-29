"""Execution-boundary tests for the opt-in new basic flow; fixtures only."""
import array,copy,hashlib,json,math,shutil,sys,tempfile,unittest,wave
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows')]
import basic_flow,draft_length,audible_overlap,repair_permissions,generation_guard,fast_mode,speech_duration,delivery_policy,work_modes
FF=str(ROOT/'dist/AniCanto.app/Contents/Resources/bin/ffmpeg')
def wav(path,duration=1.,silence=False):
 path.parent.mkdir(parents=True,exist_ok=True);sr=24000;raw=array.array('h',(0 if silence else round(3500*math.sin(n*2*math.pi*250/sr)) for n in range(round(sr*duration))))
 with wave.open(str(path),'wb') as f:f.setparams((1,2,sr,0,'NONE','not compressed'));f.writeframes(raw.tobytes())
 return path

def cfg(**extra):
 c=dict(basicFlowRevision=basic_flow.REVISION,repairPermissionsRevision=repair_permissions.REVISION,speechDurationRevision=speech_duration.REVISION,deliveryPolicyRevision=delivery_policy.REVISION,workModeRevision=work_modes.REVISION,workMode='performance',productionMode='fast',targetLanguage='yue',ttsBackend='drama3',duration=3.,ffmpeg=FF,ffprobe=str(Path(FF).with_name('ffprobe')),storage='/nonexistent-fixture',contentChecks=0,repairExcessiveAudibleOverlap=False,limitSpeechDuration=False,aiAutoFix=False,fullAIReview=False,speechRatePolicy='natural',autoFit=True,continueOnError=True,preferFirstAudibleTake=True,failedVoicePolicy='first-take',normalRepairPolicy='missing-only',autoSkipOP=False,preserveNonverbal=False)
 c.update(extra);return c

def cue(a=0.,b=1.,text='你好呀。',index=0):return dict(start=a,end=b,speechStart=a,speechEnd=b,cantonese=text,reviewIndex=index,speakerId='r1',enabled=True)
class Rules(unittest.TestCase):
 def test_optional_defaults_and_valid_count(self):
  from desktop_state import defaults
  from workflow_settings import validated
  s=defaults();self.assertEqual(s['contentChecks'],0);self.assertFalse(s['repairExcessiveAudibleOverlap'])
  for n in [0,1,2]:self.assertEqual(validated(dict(s,contentChecks=n))['contentChecks'],n)
  for n in [-1,3,True,'1',1.1]:
   with self.assertRaises(ValueError):validated(dict(s,contentChecks=n))
 def test_old_jobs_are_not_restamped(self):
  c=cfg();c.pop('basicFlowRevision');work_modes.configure(c);fast_mode.configure(c);self.assertFalse(basic_flow.enabled(c))
 def test_budget_covers_three_languages_without_mutating_source(self):
  with tempfile.TemporaryDirectory() as d:
   cs=[cue(b=3.)];before=copy.deepcopy(cs)
   for lang in ['yue','zh','en']:
    rows={'0':dict(seconds=8,source='same')};draft_length.apply(cfg(),Path(d),cs,rows,lang);guide=rows['0']['durationGuidance'];self.assertEqual(guide['sourceSeconds'],3);self.assertTrue(guide['preserveCompleteMeaning']);self.assertTrue(guide['suggestedRange'][1]>=guide['suggestedRange'][0]);self.assertIn('SOFT',draft_length.instruction(cfg(),lang))
   self.assertEqual(cs,before);self.assertEqual(draft_length.instruction({},'en'),'')
 def test_language_estimates_are_distinct(self):
  self.assertNotEqual(draft_length.RATES['en'],draft_length.RATES['yue']);self.assertEqual(draft_length.units("Don't add a long explanation",'en'),5)
 def test_first_audible_never_becomes_source_for_length_or_asr(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=wav(root/'long.wav',4.);c=cfg(duration=2.);cs=[cue(b=1.)]
   (root/'normal-checks.json').write_text(json.dumps(dict(unresolved=[1],repairs=[dict(index=1,check=dict(contentFailure=True))])))
   self.assertEqual(repair_permissions.choose(c,root,cs,[p]),([p],set()))
 def test_presence_guard_shared_across_references_and_resume(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);c=cfg(_generationGuardRoot=d)
   for n in range(4):
    reference=wav(root/f'ref{n}.wav');item=dict(text='你好',profile=dict(reference=str(reference),promptText='Hi'),output=str(root/f'out{n}.wav'),reviewIndex=5)
    state=generation_guard.reserve(c,dict(job=d,items=[item]));self.assertEqual(len(state[2]),int(n<3));generation_guard.finish(state,'no audio')
   ledger=json.loads((root/'presence-call-ledger.json').read_text());self.assertEqual(next(iter(ledger.values()))['calls'],3)
 def test_generic_can_only_reserve_once(self):
  with tempfile.TemporaryDirectory() as d:
   for n in range(2):
    item=dict(text='你好',profile={},output=str(Path(d)/f'o{n}.wav'),reviewIndex=0);r=generation_guard.reserve(cfg(_generationGuardRoot=d,_mandatoryPresence=True),dict(job=d,items=[item]));self.assertEqual(len(r[2]),int(n==0))
 def test_optional_timing_has_separate_presence_allowance(self):
  with tempfile.TemporaryDirectory() as d:
   item=dict(text='你好',profile={},output=str(Path(d)/'o.wav'),reviewIndex=0);generation_guard.reserve(cfg(_generationGuardRoot=d,_generationPurpose='timing'),dict(job=d,items=[item]));self.assertFalse((Path(d)/'presence-call-ledger.json').exists())
 def test_voiced_baseline_runs_no_model_no_inspection_no_overlap_detection(self):
  import dubbing,normal_mode
  with tempfile.TemporaryDirectory() as d:
   p=wav(Path(d)/'ok.wav');cs=[cue()]
   with patch.object(dubbing,'gsv_audio') as gen,patch.object(normal_mode,'inspect') as check,patch.object(audible_overlap,'detect') as vad:
    result,_=basic_flow.finish(cfg(),Path(d),cs,[p],Mock(),Mock());self.assertEqual(result,[p]);gen.assert_not_called();check.assert_not_called();vad.assert_not_called()
 def test_missing_is_retried_even_with_zero_checks(self):
  import dubbing
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);bad=wav(root/'silent.wav',silence=True);good=wav(root/'fixed.wav');cs=[cue()]
   with patch.object(dubbing,'gsv_audio',return_value=[good]) as gen:
    result,_=basic_flow.finish(cfg(),root,cs,[bad],Mock(),Mock());self.assertEqual(result,[good]);self.assertEqual(gen.call_count,1)
 def test_real_mix_preserves_overlapping_takes_and_last_tail(self):
  import subprocess,dubbing
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=wav(root/'long.wav',4.);q=wav(root/'next.wav',1.);cs=[cue(b=1.),cue(a=1.,b=2.,text='下一句。',index=1)];c=cfg()
   def run(args):return subprocess.check_output(list(map(str,args)))
   with patch.object(dubbing,'gsv_audio') as model:
    out,warnings=fast_mode.synthesize(c,root,cs,run,Mock(),generated_paths=[p,q]);model.assert_not_called()
   rows=json.loads((root/'timing.json').read_text());self.assertFalse(any(r.get('skipped') for r in rows));self.assertTrue(all(r['rate']==1 for r in rows));self.assertAlmostEqual(rows[0]['renderedEnd'],4.,places=2);self.assertEqual(c['outputDuration'],4.);self.assertFalse(any(w.get('kind')=='original-source-fallback' for w in warnings))
   with wave.open(str(out)) as f:self.assertAlmostEqual(f.getnframes()/f.getframerate(),4.,places=2)
class Overlap(unittest.TestCase):
 def test_union_excludes_empty_intervals(self):self.assertEqual(audible_overlap.union([(0,1),(.5,2),(4,4),(5,6)]),[[0,2],[5,6]])
 def test_exact_two_seconds_not_excessive(self):
  cs=[cue(b=1),cue(a=1,b=2,index=1)];self.assertEqual(audible_overlap.overlap_seconds(cs,{0:[[0,3]],1:[[0,3]]},0),2.)
 def test_silence_does_not_count_as_overlap(self):
  cs=[cue(b=1),cue(a=1,b=2,index=1)];self.assertAlmostEqual(audible_overlap.overlap_seconds(cs,{0:[[0,.2],[3,3.5]],1:[[0,.2]]},0),0.)
 def test_three_takes_do_not_double_count(self):
  cs=[cue(),cue(a=1,b=2,index=1),cue(a=1.5,b=2.5,index=2)];self.assertEqual(audible_overlap.overlap_seconds(cs,{0:[[0,4]],1:[[0,2]],2:[[0,2]]},0),2.5)
 def test_long_voice_without_next_speech_does_not_retake(self):
  import dubbing
  with tempfile.TemporaryDirectory() as d:
   p=wav(Path(d)/'voice.wav',4.)
   with patch.object(audible_overlap,'detect',return_value={0:[[0,4]]}),patch.object(dubbing,'gsv_audio') as gen:
    self.assertEqual(audible_overlap.repair(cfg(),Path(d),[cue()],[p],Mock(),Mock()),[p]);gen.assert_not_called()
 def test_unavailable_vad_retains_takes(self):
  import dubbing
  with tempfile.TemporaryDirectory() as d:
   p=wav(Path(d)/'voice.wav')
   with patch.object(audible_overlap,'detect',side_effect=ValueError('unknown')),patch.object(dubbing,'gsv_audio') as gen:
    self.assertEqual(audible_overlap.repair(cfg(),Path(d),[cue()],[p],Mock(),Mock()),[p]);gen.assert_not_called()

class OptionalExecution(unittest.TestCase):
 def test_one_overlap_retake_and_resume_reuses_accepted_audio(self):
  import concise_dialogue,dubbing
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=wav(root/'first.wav',4.);q=wav(root/'next.wav',3.);short=wav(root/'short.wav',2.5);cs=[cue(),cue(a=1,b=2,index=1)];cs[0]['cantonese']='完整但較長的原稿。';original=copy.deepcopy(cs)
   def detector(c,j,cues,paths,run):
    from natural_delivery import seconds
    return {i:[[0,seconds(path,c,None)]] for i,path in enumerate(paths)}
   def compact(w,c,j,drafts,indices,targets,**kwargs):drafts[0]['cantonese']='短句。';return [0]
   with patch.object(audible_overlap,'detect',side_effect=detector),patch.object(concise_dialogue,'compact',side_effect=compact),patch.object(dubbing,'gsv_audio',return_value=[short]) as gen:
    out=audible_overlap.repair(cfg(),root,cs,[p,q],Mock(),Mock());self.assertEqual(out,[short,q]);self.assertEqual(gen.call_count,1)
    out2=audible_overlap.repair(cfg(),root,original,[p,q],Mock(),Mock());self.assertEqual(out2,[short,q]);self.assertEqual(gen.call_count,1);self.assertEqual(original[0]['cantonese'],'短句。')
   self.assertEqual(json.loads((root/'audible-overlap-repairs.json').read_text())['1']['status'],'accepted')
 def test_unsuccessful_retake_is_not_repeated_on_resume(self):
  import concise_dialogue,dubbing
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=wav(root/'first.wav',4.);q=wav(root/'next.wav',3.);bad=wav(root/'bad.wav',silence=True);cs=[cue(),cue(a=1,b=2,index=1)]
   def compact(w,c,j,drafts,indices,targets,**kwargs):drafts[0]['cantonese']='短句。';return [0]
   with patch.object(audible_overlap,'detect',return_value={0:[[0,4]],1:[[0,3]]}),patch.object(concise_dialogue,'compact',side_effect=compact),patch.object(dubbing,'gsv_audio',return_value=[bad]) as gen:
    self.assertEqual(audible_overlap.repair(cfg(),root,cs,[p,q],Mock(),Mock()),[p,q]);self.assertEqual(audible_overlap.repair(cfg(),root,cs,[p,q],Mock(),Mock()),[p,q]);self.assertEqual(gen.call_count,1)
 def test_content_check_control_is_report_only_without_repair(self):
  import normal_mode,dubbing
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=wav(root/'voice.wav')
   with patch.object(normal_mode,'inspect',return_value={1:dict(contentFailure=True)}) as inspect,patch.object(normal_mode,'repair_paths') as repair,patch.object(dubbing,'gsv_audio') as gen:
    out,_=basic_flow.finish(cfg(contentChecks=1),root,[cue()],[p],Mock(),Mock());self.assertEqual(out,[p]);self.assertEqual(inspect.call_count,1);repair.assert_not_called();gen.assert_not_called()
 def test_strict_timing_does_not_also_run_overlap_repair(self):
  import natural_delivery
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=wav(root/'voice.wav')
   with patch.object(natural_delivery,'repair',return_value=[p]) as strict,patch.object(audible_overlap,'repair') as overlap:
    basic_flow.finish(cfg(limitSpeechDuration=True,repairExcessiveAudibleOverlap=True),root,[cue()],[p],Mock(),Mock());self.assertEqual(strict.call_count,1);overlap.assert_not_called()
 def test_failed_clone_uses_one_generic_selected_engine_fill(self):
  import dubbing,natural_voices
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);bad=wav(root/'bad.wav',silence=True);good=wav(root/'generic.wav',4.);reference=wav(root/'reference.wav')
   profile=dict(id='generic',reference=str(reference),language='yue',promptText='你好。',naturalReferenceId='fixture')
   with patch.object(dubbing,'profile_for',side_effect=ValueError('bad reference')),patch.object(natural_voices,'resolve',return_value=profile),patch.object(dubbing,'gsv_audio',side_effect=[[bad],[good]]) as gen:
    out,_=basic_flow.finish(cfg(storage=str(root/'store')),root,[cue()],[bad],Mock(),Mock());self.assertEqual(out,[good]);self.assertEqual(gen.call_count,2);self.assertEqual(gen.call_args.args[0]['ttsBackend'],'drama3')
if __name__=='__main__':unittest.main()
