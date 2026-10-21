import json,sys,tempfile,unittest,wave,shutil,subprocess
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
from normal_voice_fallback import repair

def audio(p,seconds=1):
 with wave.open(str(p),'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(b'\x00\x10'*round(24000*seconds))
 return p

class TargetReferenceTests(unittest.TestCase):
 def trial(self,root,proof=None,duration=1,manual=False):
  (root/'normal-checks.json').write_text(json.dumps(dict(unresolved=[1])))
  source=audio(root/'source.wav');candidate=audio(root/'candidate.wav',duration);reference=audio(root/'reference.wav',4)
  cues=[dict(start=0,end=2,cantonese='你究竟想點呀？',speakerId='r',editorAudio=str(source) if manual else None)]
  cfg=dict(productionMode='normal',preferFirstAudibleTake=False,targetLanguage='yue',duration=2,ttsBackend='drama3')
  placement=[dict(fit=False,seconds=3,start=0,deadline=2)]
  profile=dict(id='r',language='ja',reference=str(source));bank=dict(profile,reference=str(reference),language='yue',naturalReferenceId='yue-mid')
  proof=proof if proof is not None else dict(decision='cantonese',heard='你究竟想點呀？')
  return cfg,cues,placement,source,candidate,profile,bank,proof
 def test_verified_fitting_take_adopted_without_new_engine_and_prior_audio_unchanged(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cfg,cues,place,source,candidate,p,bank,proof=self.trial(root);before=source.read_bytes()
   with patch('dubbing.profile_for',return_value=p),patch('natural_voices.resolve',return_value=bank),patch('dubbing.gsv_audio',return_value=[candidate]) as generate,patch('normal_mode.inspect',return_value={1:proof}):
    self.assertEqual(repair(cfg,root,cues,[source],place,Mock(),Mock()),[candidate])
    used=generate.call_args.args[0];self.assertEqual(used['ttsBackend'],'drama3');self.assertEqual(used['voiceProfiles'][0]['language'],'yue')
    self.assertEqual(source.read_bytes(),before);ledger=json.loads((root/'target-reference-recovery.json').read_text());self.assertFalse(next(iter(ledger.values()))['voiceSimilarityCertified'])
    repair(cfg,root,cues,[source],place,Mock(),Mock());self.assertEqual(generate.call_count,1,'Resume must reuse generated audio')
 def test_exhausted_actor_timing_can_try_verified_cantonese_before_source_japanese(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cfg,cues,place,source,candidate,p,bank,proof=self.trial(root)
   (root/'normal-checks.json').write_text(json.dumps(dict(unresolved=[])))
   cfg['_sourceVoiceRepairsExhausted']=True;before=source.read_bytes()
   with patch('dubbing.profile_for',return_value=p),patch('natural_voices.resolve',return_value=bank),patch('dubbing.gsv_audio',return_value=[candidate]),patch('normal_mode.inspect',return_value={1:proof}):
    self.assertEqual(repair(cfg,root,cues,[source],place,Mock(),Mock()),[candidate])
   self.assertEqual(source.read_bytes(),before)
   record=next(iter(json.loads((root/'target-reference-recovery.json').read_text()).values()))
   self.assertEqual(record['reason'],'timing-after-source-voice-repairs');self.assertEqual(record['status'],'adopted');self.assertFalse(record['voiceSimilarityCertified'])
 def test_fitting_actor_stays_unchanged_even_at_the_final_fallback_boundary(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cfg,cues,place,source,*_=self.trial(root)
   (root/'normal-checks.json').write_text(json.dumps(dict(unresolved=[])))
   cfg['_sourceVoiceRepairsExhausted']=True;place[0]['fit']=True
   with patch('dubbing.gsv_audio') as generate,patch('dubbing.profile_for') as profile:
    self.assertEqual(repair(cfg,root,cues,[source],place,Mock(),Mock()),[source])
   generate.assert_not_called();profile.assert_not_called()
 def test_wrong_language_and_overlong_take_are_not_adopted_or_retried_forever(self):
  for proof,duration in [(dict(decision='japanese',heard='日本語です'),1),(dict(decision='cantonese',heard='你究竟想點呀？'),3)]:
   with self.subTest(proof=proof),tempfile.TemporaryDirectory() as d:
    root=Path(d);cfg,cues,place,source,candidate,p,bank,_=self.trial(root,duration=duration)
    with patch('dubbing.profile_for',return_value=p),patch('natural_voices.resolve',return_value=bank),patch('dubbing.gsv_audio',return_value=[candidate]) as generate,patch('normal_mode.inspect',return_value={1:proof}):
     for _ in range(3):self.assertEqual(repair(cfg,root,cues,[source],place,Mock(),Mock()),[source])
     self.assertEqual(generate.call_count,1)
 def test_manual_audio_never_changes(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cfg,cues,place,source,*_=self.trial(root,manual=True)
   with patch('dubbing.gsv_audio') as generate:self.assertEqual(repair(cfg,root,cues,[source],place,Mock(),Mock()),[source]);generate.assert_not_called()
 def test_repeated_interruptions_are_bounded_even_without_output(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cfg,cues,place,source,candidate,p,bank,proof=self.trial(root)
   with patch('dubbing.profile_for',return_value=p),patch('natural_voices.resolve',return_value=bank),patch('dubbing.gsv_audio',side_effect=KeyboardInterrupt) as generate:
    for _ in range(2):
     with self.assertRaises(KeyboardInterrupt):repair(cfg,root,cues,[source],place,Mock(),Mock())
    self.assertEqual(repair(cfg,root,cues,[source],place,Mock(),Mock()),[source]);self.assertEqual(generate.call_count,2)

 def test_uncertain_but_audible_fitting_take_is_preview_only_not_a_quality_pass(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cfg,cues,place,source,candidate,p,bank,_=self.trial(root)
   with patch('dubbing.profile_for',return_value=p),patch('natural_voices.resolve',return_value=bank),patch('dubbing.gsv_audio',return_value=[candidate]),patch('normal_mode.inspect',return_value={1:dict(decision='unconfirmed',heard='點呀？')}):
    self.assertEqual(repair(cfg,root,cues,[source],place,Mock(),Mock()),[candidate])
   self.assertEqual(json.loads((root/'normal-checks.json').read_text())['unresolved'],[1])
   self.assertEqual(next(iter(json.loads((root/'target-reference-recovery.json').read_text()).values()))['status'],'selected-unverified')

 @unittest.skipUnless(shutil.which('ffmpeg'),'FFmpeg required')
 def test_verified_seven_millisecond_overrun_is_measured_before_rejection_and_reuses_audio(self):
  from natural_delivery import seconds
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cfg,cues,place,source,candidate,p,bank,proof=self.trial(root,duration=2.647075)
   cfg.update(duration=2.64,ffmpeg=shutil.which('ffmpeg'),_sourceVoiceRepairsExhausted=True);cues[0]['end']=2.64;place[0]['deadline']=2.64
   original=candidate.read_bytes();source_before=source.read_bytes()
   run=lambda args:subprocess.check_output([str(x) for x in args],stderr=subprocess.PIPE)
   with patch('dubbing.profile_for',return_value=p),patch('natural_voices.resolve',return_value=bank),patch('dubbing.gsv_audio',return_value=[candidate]) as generate,patch('normal_mode.inspect',return_value={1:proof}):
    paths=repair(cfg,root,cues,[source],place,run,Mock())
    self.assertNotEqual(paths,[source]);self.assertLessEqual(seconds(paths[0],cfg,run),2.64)
    record=next(iter(json.loads((root/'target-reference-recovery.json').read_text()).values()))
    self.assertEqual(record['status'],'adopted');self.assertLessEqual(record['tempoRate'],1.05)
    self.assertEqual(candidate.read_bytes(),original);self.assertEqual(source.read_bytes(),source_before)
    # A previously cached timing rejection is reevaluated under the fixed
    # admission policy without downloading or synthesising the candidate again.
    ledger=json.loads((root/'target-reference-recovery.json').read_text());old=next(iter(ledger.values()));old['status']='timing-not-fit';old.pop('timingAdmissionRevision')
    (root/'target-reference-recovery.json').write_text(json.dumps(ledger))
    self.assertEqual(repair(cfg,root,cues,[source],place,run,Mock()),paths);self.assertEqual(generate.call_count,1)
