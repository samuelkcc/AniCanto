import json,sys,tempfile,unittest,wave,math,struct
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import recovery_coordinator as rc,system_voice as native,delivery_policy as policy,worker

def wav(path,seconds=.3):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 with wave.open(str(path),'wb') as f:
  f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(b''.join(struct.pack('<h',int(5000*math.sin(n*.2))) for n in range(round(seconds*24000))))
 return path

def cfg(root,mode='balanced',**kw):return dict(deliveryPolicyRevision=policy.POOLED_REVISION,workMode=mode,duration=10,productionMode='normal',normalRepairPolicy='missing-only',automaticSystemVoice=True,targetLanguage='yue',storage=str(root/'runtime'),**kw)
def cue():return dict(start=0,end=2,reviewIndex=0,cantonese='你好呀',japanese='こんにちは',speakerId='r',enabled=True)
def plan():return [dict(fit=False,start=0,deadline=2,seconds=None,shift=0,method='source-clock')]

class CoordinatorTests(unittest.TestCase):
 def test_initial_attempt_caps_and_healthy_stops_in_all_modes(self):
  for mode,retries in [('performance',0),('balanced',0),('quality',2)]:
   with self.subTest(mode=mode),tempfile.TemporaryDirectory() as d:
    r=Path(d);bad=r/'skipped-bad.wav';good=wav(r/'good.wav');fn=Mock(side_effect=[[bad],[good]])
    with patch('dubbing.gsv_audio',fn),patch('normal_mode.inspect',return_value={}),patch('project_store.record_issue'):
     result=rc.initial(cfg(r,mode),r,[cue()],[bad],Mock(),Mock());self.assertEqual(fn.call_count,retries)
     self.assertEqual(result,[good] if retries else [bad])
     rc.initial(cfg(r,mode),r,[cue()],[good],Mock(),Mock());self.assertEqual(fn.call_count,retries)
 def test_confirmed_healthy_error_does_not_repeat_initial_generation(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);good=wav(r/'first.wav')
   with patch('dubbing.gsv_audio') as generate,patch('normal_mode.inspect',return_value={1:dict(languageFailure='japanese')}):rc.initial(cfg(r,'quality'),r,[cue()],[good],Mock(),Mock())
   generate.assert_not_called();self.assertEqual(policy.confirmed_indices({},r),{1})
 def test_pipeline_exception_still_reaches_native_and_final_timing(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);bad=r/'skipped.wav';target=wav(r/'native.wav');calls=[]
   with patch.object(rc,'initial',side_effect=RuntimeError('AI unavailable')),patch.object(rc,'fallback',side_effect=RuntimeError('bank unavailable')),patch('natural_finish.finish',side_effect=lambda c,j,cs,ps,*a,**k:(ps,plan())),patch('system_voice.repair',side_effect=lambda *a:(calls.append('native') or [target])):
    paths,_=rc.recover(cfg(r,failedVoicePolicy='generic'),r,[cue()],[bad],Mock(),Mock())
   self.assertEqual(paths,[target]);self.assertEqual(calls,['native']);self.assertEqual(len(json.loads((r/'recovery-warnings.json').read_text())['warnings']),2)
 def test_performance_skips_actor_timing_and_generic_compact(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);bad=r/'skipped.wav';c=cfg(r,'performance',failedVoicePolicy='first-take')
   with patch.object(rc,'initial',return_value=[bad]),patch.object(rc,'actor') as actor,patch('natural_finish.finish',side_effect=lambda c,j,cs,ps,*a,**k:(ps,plan())),patch('normal_voice_fallback.repair',side_effect=lambda c,j,cs,ps,*a:ps) as generic,patch('generic_delivery.repair') as compact,patch('normal_engine_fallback.repair',side_effect=lambda c,j,cs,ps,*a:ps) as alternate,patch('system_voice.repair',return_value=[bad]):rc.recover(c,r,[cue()],[bad],Mock(),Mock())
   actor.assert_not_called();compact.assert_not_called();self.assertEqual(generic.call_count,1);self.assertEqual(alternate.call_count,1)
 def test_native_two_attempts_per_cue_survive_restart_in_every_mode(self):
  for mode in ['performance','balanced','quality']:
   with self.subTest(mode=mode),tempfile.TemporaryDirectory() as d:
    r=Path(d);bad=r/'skipped.wav'
    with patch.object(native,'installed',return_value=[dict(name='HK',locale='zh-HK')]),patch.object(native,'synthesize',side_effect=RuntimeError('voice failed')) as generate:
     native.repair(cfg(r,mode),r,[cue()],[bad],plan(),Mock(),Mock());native.repair(cfg(r,mode),r,[cue()],[bad],plan(),Mock(),Mock())
    self.assertEqual(generate.call_count,2)
 def test_native_adoption_protects_neighbour_and_clears_confirmed_without_asr(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);bad=r/'skipped.wav';target=wav(r/'native.wav');worker.atomic_json(r/'normal-checks.json',dict(unresolved=[1],repairs=[dict(index=1,check=dict(contentFailure=True))]))
   with patch.object(native,'installed',return_value=[dict(name='HK',locale='zh-HK')]),patch.object(native,'synthesize',return_value=target),patch('natural_schedule.prepare',return_value=[dict(fit=True,start=0,deadline=2)]),patch('normal_mode.inspect',side_effect=AssertionError('native must not ASR')):
    self.assertEqual(native.repair(cfg(r),r,[cue()],[bad],plan(),Mock(),Mock()),[target])
   self.assertEqual(policy.confirmed_indices({},r),set());record=next(iter(json.loads((r/'system-voice-fallback.json').read_text())['records'].values()));self.assertFalse(record['qualityCertified'])

if __name__=='__main__':unittest.main()
