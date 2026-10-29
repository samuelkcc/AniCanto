import json,math,struct,sys,tempfile,unittest,wave
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import delivery_policy as policy,work_modes,recovery_coordinator as rc

def wav(path,seconds=.3):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 with wave.open(str(path),'wb') as f:
  f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(b''.join(struct.pack('<h',int(5000*math.sin(n*.2))) for n in range(round(seconds*24000))))
 return path

def cue():return dict(start=0,end=2,reviewIndex=0,cantonese='你好呀',japanese='こんにちは',speakerId='r',enabled=True)

def cfg(root,mode='performance',forced=None,**kw):
 # Build 244 froze these rules on work-modes revision 1. Revision 2 is covered by
 # tests/test_standard_mode245.py and must not re-read these frozen expectations.
 c=dict(deliveryPolicyRevision=policy.REVISION,workModeRevision=work_modes.REVISION_1,workMode=mode,
  duration=10,productionMode='normal',automaticAlternateVoice=True,automaticSystemVoice=True,
  targetLanguage='yue',storage=str(root/'runtime'),failedVoicePolicy='generic',**kw)
 if forced is not None:c['forcedDubbingRevision']=forced
 return c

class ForcedDesktopTests(unittest.TestCase):
 def test_new_execution_stamps_forced_revision_and_gates_by_mode(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);c=policy.new_execution(cfg(r,'performance',forced='stale'),r/'job')
   self.assertEqual(c['forcedDubbingRevision'],policy.FORCED_TTS_REVISION)
   self.assertTrue(policy.forced_tts(c));work_modes.configure(c)
   self.assertFalse(c['automaticAlternateVoice']);self.assertFalse(c['automaticSystemVoice'])
   self.assertEqual(c['maximumMissingRepairAttempts'],2);self.assertEqual(c['maximumTimingRewritePasses'],0)
   self.assertFalse(c['automaticDurationRewrite'])
   b=policy.new_execution(cfg(r,'balanced',forced='stale'),r/'job2');work_modes.configure(b)
   self.assertTrue(policy.forced_tts(b) is False)
   self.assertTrue(b['automaticAlternateVoice']);self.assertTrue(b['automaticSystemVoice'])
 def test_jobs_without_the_stamp_keep_previous_frozen_behaviour(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);c=cfg(r,'performance')  # no forcedDubbingRevision
   work_modes.configure(c)
   self.assertTrue(c['automaticAlternateVoice']);self.assertTrue(c['automaticSystemVoice'])
   self.assertEqual(c['maximumMissingRepairAttempts'],0)
  self.assertFalse(policy.forced_tts(dict(deliveryPolicyRevision=policy.REVISION,workModeRevision=work_modes.REVISION_1,workMode='performance',forcedDubbingRevision='forced-tts-dubbing-always-export-189')))
 def test_initial_and_physical_re_record_only_missing_in_forced_performance(self):
  for forced,retries in [(policy.FORCED_TTS_REVISION,2),(None,0)]:
   with self.subTest(forced=bool(forced)),tempfile.TemporaryDirectory() as d:
    r=Path(d);bad=r/'skipped-missing-result-1.wav';quiet=wav(r/'quiet.wav',seconds=0);good=wav(r/'good.wav');fn=Mock(side_effect=[[quiet],[good]])
    c=cfg(r,'performance',forced=forced);work_modes.configure(c)
    with patch('dubbing.gsv_audio',fn),patch('normal_mode.inspect',return_value={}),patch('project_store.record_issue'):
     rc.initial(c,r,[cue()],[bad],Mock(),Mock())
     self.assertEqual(fn.call_count,retries)
    with tempfile.TemporaryDirectory() as e:
     r2=Path(e);bad2=r2/'skipped-missing-result-1.wav';good2=wav(r2/'good.wav');fn2=Mock(side_effect=[[bad2],[good2]])
     c2=cfg(r2,'performance',forced=forced);work_modes.configure(c2)
     with patch('dubbing.gsv_audio',fn2),patch('project_store.record_issue'):
      selected=rc.physical(c2,r2,[cue()],[bad2],Mock(),Mock())
      self.assertEqual(fn2.call_count,retries)
      self.assertEqual(selected,[good2] if retries else [bad2])
 def test_forced_performance_delivery_freezes_alternate_and_native_gates(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);bad=r/'skipped.wav';c=cfg(r,'performance',forced=policy.FORCED_TTS_REVISION);work_modes.configure(c)
   seen=[]
   def alternate(cc,*a):seen.append(cc);return list(a[2])
   with patch.object(rc,'initial',return_value=[bad]),patch('natural_finish.finish',side_effect=lambda cc,j,cs,ps,*a,**k:(ps,[dict(fit=False,start=0,deadline=2,seconds=None,shift=0,method='source-clock')])),patch('normal_voice_fallback.repair',side_effect=lambda cc,j,cs,ps,*a:ps) as generic,patch('generic_delivery.repair') as compact,patch('normal_engine_fallback.repair',side_effect=alternate):
    paths,_=rc.recover(c,r,[cue()],[bad],Mock(),Mock())
   generic.assert_called();compact.assert_not_called()
   self.assertTrue(seen and all(x['automaticAlternateVoice'] is False for x in seen))
   # Unpatched system_voice.repair must no-op on the frozen gate and keep the take.
   self.assertEqual(paths,[bad])
   self.assertFalse((r/'system-voice-fallback.json').exists())

if __name__=='__main__':unittest.main()
