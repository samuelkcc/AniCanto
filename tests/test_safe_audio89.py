import hashlib,json,sys,tempfile,unittest,wave
from pathlib import Path
from unittest.mock import Mock,patch
import numpy as np,soundfile as sf
sys.path[:0]=[str(Path(__file__).parents[1]/'Resources')]
import safe_audio_endpoint as endpoint,delivery_policy as policy,repair_limits as limits,worker,secondary_speech,work_modes

def audio(path,voice=3,total=8,noise=.0008,weak=None,sr=24000):
 rng=np.random.default_rng(17);t=np.arange(round(sr*total))/sr;x=rng.normal(0,noise,len(t));active=t<voice;x[active]+=.3*np.sin(t[active]*2*np.pi*180)
 if weak:
  a,b,level=weak;span=(t>=a)&(t<b);x[span]+=level*np.sin(t[span]*2*np.pi*230)
 sf.write(path,x,sr,subtype='PCM_16');return Path(path)
def cue(index=0,**kw):return dict(start=0,end=3.5,reviewIndex=index,cantonese='Bring the key.',japanese='鍵を持って',speakerId='r',enabled=True,**kw)
def config(root,mode='balanced',**kw):return dict(deliveryPolicyRevision=policy.REVISION,workModeRevision=work_modes.REVISION,workMode=mode,productionMode='normal',duration=3.5,ttsBackend='drama3',targetLanguage='en',storage=str(root/'runtime'),failedVoicePolicy='first-take',automaticSystemVoice=False,**kw)
def proof(heard='Bring the key.',end=2.9):return dict(method=secondary_speech.ENDPOINT_REVISION,conditioning='No expected text, prompt or vocabulary supplied',heard=heard,language='en',words=[dict(word=heard,start=.02,end=end,probability=.95)])

class SafeEndpointTests(unittest.TestCase):
 def test_stationary_noise_is_suspect_but_weak_late_signal_protected(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);p=audio(r/'noise.wav');a=endpoint.analyze(p);self.assertEqual(a['status'],'tail-suspect');self.assertAlmostEqual(a['activityEnd'],3,delta=.08)
   # Last word/signal is quiet enough to miss the old fixed .003 RMS rule.
   quiet=audio(r/'quiet.wav',voice=2.5,total=8,weak=(2.7,3.4,.0019));b=endpoint.analyze(quiet)
   self.assertTrue(b['status']!='tail-suspect' or b['activityEnd']>=3.35)
 def test_complete_words_and_tail_agreement_required(self):
  a=dict(status='tail-suspect',activityEnd=3,fileSeconds=8,vocalEvidenceAvailable=True,vocalEnd=3)
  self.assertEqual(endpoint.verdict('Bring the key.',proof(),a)['status'],'trim-candidate')
  for p in [None,proof('Bring.'),dict(proof(),words=[]),dict(proof(),conditioning='expected prompt supplied'),dict(proof(),words=[dict(word='Bring the key.',start=0,end=7.8,probability=.95)])]:
   self.assertNotEqual(endpoint.verdict('Bring the key.',p,a)['status'],'trim-candidate')
 def test_incomplete_or_wrong_last_word_never_licensed_by_short_energy(self):
  a=dict(status='tail-suspect',activityEnd=.7,fileSeconds=8,vocalEvidenceAvailable=True,vocalEnd=.7)
  self.assertFalse(endpoint.verdict('而且，亂馬有個麻煩之源',proof('而且',.65),a)['rewriteAllowed'])
  for p in [proof('Bring the key.',.1),dict(proof(),words=[dict(word='Bring the key.',start=0,end=2.9,probability=.5)])]:
   self.assertNotEqual(endpoint.verdict('Bring the key.',p,a)['status'],'trim-candidate')
 def test_real_pcm_candidate_saved_native_rate_raw_and_neighbour_unchanged_resume_cached(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);p=audio(r/'raw.wav',sr=44100);good=audio(r/'good.wav',voice=.8,total=1,noise=0,sr=44100);before={x:x.read_bytes() for x in [p,good]};cs=[dict(cue(),end=3.5),dict(cue(1),start=3.5,end=5)];c=dict(config(r),duration=5)
   with patch('secondary_speech.transcribe_batch',return_value=[proof()]) as infer,patch.object(endpoint,'vocal_end',return_value=dict(vocalEvidenceAvailable=True,vocalEnd=3)):
    selected=endpoint.apply(c,r,cs,[p,good],Mock(),Mock());again=endpoint.apply(c,r,cs,[p,good],Mock(),Mock())
   self.assertEqual(selected,again);self.assertNotEqual(selected[0],p);self.assertEqual(selected[1],good);self.assertEqual(infer.call_count,1)
   info=sf.info(selected[0]);self.assertEqual(info.samplerate,44100);self.assertEqual(info.subtype,'PCM_16');self.assertGreater(info.duration,3);self.assertLess(info.duration,3.5)
   self.assertTrue(all(x.read_bytes()==raw for x,raw in before.items()))
 def test_word_uncertainty_keeps_full_audio_and_blocks_shrinking_no_repeat(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);p=audio(r/'raw.wav');c=config(r)
   with patch('secondary_speech.transcribe_batch',return_value=[proof('Bring.')]) as infer:
    self.assertEqual(endpoint.apply(c,r,[cue()],[p],Mock(),Mock()),[p]);self.assertEqual(endpoint.apply(c,r,[cue()],[p],Mock(),Mock()),[p])
   self.assertEqual(infer.call_count,1);self.assertFalse(endpoint.rewrite_allowed(c,r,cue(),p))
 def test_missing_model_timeout_and_cancel_not_misreported(self):
  for error in [ValueError('model not installed'),RuntimeError('timeout')]:
   with self.subTest(error=error),tempfile.TemporaryDirectory() as d:
    r=Path(d);p=audio(r/'raw.wav');c=config(r)
    with patch('secondary_speech.transcribe_batch',side_effect=error):self.assertEqual(endpoint.apply(c,r,[cue()],[p],Mock(),Mock()),[p])
    self.assertFalse(endpoint.rewrite_allowed(c,r,cue(),p));self.assertFalse(limits.read(r/'safe-audio-endpoints.json')['qualityCertified'])
 def test_performance_manual_and_legacy_never_start_endpoint_asr(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);p=audio(r/'raw.wav')
   for c in [config(r,'performance'),dict(config(r),editorRender=True),dict(config(r),deliveryPolicyRevision=policy.REPAIR_FIRST_REVISION)]:
    with patch('secondary_speech.transcribe_batch',side_effect=AssertionError('unwanted ASR')):self.assertEqual(endpoint.apply(c,r,[cue()],[p],Mock(),Mock()),[p])
 def test_fitting_gap_uses_complete_recording_without_new_asr(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);p=audio(r/'raw.wav',voice=3,total=4,noise=0);c=dict(config(r),duration=6)
   with patch('secondary_speech.transcribe_batch',side_effect=AssertionError('fits following gap')):self.assertEqual(endpoint.apply(c,r,[dict(cue(),end=2)],[p],Mock(),Mock()),[p])
 def test_full_voice_overrun_remains_rewrite_eligible(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);p=audio(r/'long.wav',voice=4,total=4,noise=0);c=config(r)
   with patch('secondary_speech.transcribe_batch',side_effect=AssertionError('no suspect tail')):self.assertEqual(endpoint.apply(c,r,[cue()],[p],Mock(),Mock()),[p])
   self.assertTrue(endpoint.rewrite_allowed(c,r,cue(),p))
 def test_unverifiable_cached_trim_not_reused_or_licensed_for_rewrite(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);p=audio(r/'raw.wav');c=config(r)
   with patch('secondary_speech.transcribe_batch',return_value=[proof()]),patch.object(endpoint,'vocal_end',return_value=dict(vocalEvidenceAvailable=True,vocalEnd=3)):
    selected=endpoint.apply(c,r,[cue()],[p],Mock(),Mock())
   selected[0].unlink()
   with patch('secondary_speech.transcribe_batch',side_effect=AssertionError('must not repeat')):self.assertEqual(endpoint.apply(c,r,[cue()],[p],Mock(),Mock()),[p])
   self.assertFalse(endpoint.rewrite_allowed(c,r,cue(),p))
 def test_uncertain_tail_cannot_enter_ai_shortening(self):
  import natural_delivery
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);p=audio(r/'raw.wav');c=dict(config(r),preferFirstAudibleTake=False,automaticDurationRewrite=True,_maximumTimingOperations=1)
   with patch('secondary_speech.transcribe_batch',return_value=[proof('Bring.')]),patch('concise_dialogue.compact',side_effect=AssertionError('uncertain tail cannot shorten words')),patch('natural_schedule.prepare',return_value=[dict(fit=False,start=0,deadline=3.5)]):
    result=natural_delivery.repair(c,r,[cue()],[p],Mock(),Mock(),placement=[dict(fit=False,start=0,deadline=3.5)])
   self.assertEqual(result,[p])
 def test_exhausted_endpoint_clock_reuses_candidate_but_never_missing_candidate(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);p=audio(r/'raw.wav');c=config(r)
   with patch('secondary_speech.transcribe_batch',return_value=[proof()]),patch.object(endpoint,'vocal_end',return_value=dict(vocalEvidenceAvailable=True,vocalEnd=3)):
    selected=endpoint.apply(c,r,[cue()],[p],Mock(),Mock())
   marker=r/'repair-time-budget.json';saved=limits.read(marker);saved['phases']['endpoint']['spentSeconds']=60;worker.atomic_json(marker,saved)
   with patch('secondary_speech.transcribe_batch',side_effect=AssertionError('clock exhausted')):
    self.assertEqual(endpoint.apply(c,r,[cue()],[p],Mock(),Mock()),selected)
    selected[0].unlink();self.assertEqual(endpoint.apply(c,r,[cue()],[p],Mock(),Mock()),[p])
   self.assertFalse(endpoint.rewrite_allowed(c,r,cue(),p))
 def test_native_words_objects_and_mlx_dicts_normalized(self):
  from types import SimpleNamespace as S
  a=secondary_speech.endpoint_words([{'words':[dict(word='Hi',start=0,end=1,probability=.9)]}]);b=secondary_speech.endpoint_words([S(words=[S(word='Hi',start=0,end=1,probability=.9)])]);self.assertEqual(a,b)
  self.assertEqual(secondary_speech.endpoint_words([{'words':[dict(word='bad',start=0,end=float('nan'))]}]),[])

class NestedClockTests(unittest.TestCase):
 def test_endpoint_does_not_spend_parent_ai_or_drop_nested_ledger(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);now=[0.];c=config(r,_repairBudgetSeconds=10)
   @limits.bounded('endpoint',phase='endpoint')
   def child(c,j,cs,ps):now[0]+=6;return ps
   @limits.bounded('AI')
   def parent(c,j,cs,ps):now[0]+=2;child(c,j,cs,ps);now[0]+=3;limits.check();return ['new']
   with patch('repair_limits.time.monotonic',side_effect=lambda:now[0]),patch('recovery_clock.time.monotonic',side_effect=lambda:now[0]):
    self.assertEqual(parent(c,r,[],['old']),['new'])
   saved=limits.read(r/'repair-time-budget.json');self.assertEqual(saved['phases']['ai']['spentSeconds'],5);self.assertEqual(saved['phases']['endpoint']['spentSeconds'],6);self.assertEqual(len(saved['stages']),2)
 def test_nested_failure_settles_each_clock_and_restores_parent(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);now=[0.]
   @limits.bounded('failed-endpoint',phase='endpoint')
   def child(c,j,cs,ps):now[0]+=7;raise RuntimeError('owned ASR failed')
   @limits.bounded('repair')
   def parent(c,j,cs,ps):
    now[0]+=2
    try:child(c,j,cs,ps)
    except RuntimeError:pass
    now[0]+=1;return ps
   with patch('recovery_clock.time.monotonic',side_effect=lambda:now[0]):parent(config(r,_repairBudgetSeconds=10),r,[],[])
   saved=limits.read(r/'repair-time-budget.json');self.assertEqual(saved['phases']['ai']['spentSeconds'],3);self.assertEqual(saved['phases']['endpoint']['spentSeconds'],7);self.assertIsNone(limits._active.get());self.assertTrue(all('activeSince' not in row for row in saved['phases'].values()))
 def test_active_clock_charged_after_crash_without_refunding_other_phase(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);c=config(r,_repairBudgetSeconds=10);__import__('recovery_plan').prepare(c,r,[],[])
   p=r/'repair-time-budget.json';saved=limits.read(p);saved['phases']=dict(ai=dict(spentSeconds=9),endpoint=dict(spentSeconds=2,activeSince=1));worker.atomic_json(p,saved)
   wrapped=limits.bounded('endpoint',phase='endpoint')(Mock(side_effect=AssertionError('expired')))
   with patch('recovery_clock.time.time',return_value=100):self.assertEqual(wrapped(c,r,[],['kept']),['kept'])
   row=limits.read(p);self.assertEqual(row['phases']['ai']['spentSeconds'],9);self.assertTrue(row['phases']['endpoint']['recoveredActiveClock'])

class EndpointASRContractTests(unittest.TestCase):
 def test_word_request_has_no_expected_prompt_and_different_cache_from_readback(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);clip=audio(r/'clip.wav');items=[(r/'witness',clip)];calls=[]
   def batch(cfg,args,python,emit):
    req=limits.read(args);calls.append(req);self.assertNotIn('expected',json.dumps(req));self.assertNotIn('prompt',json.dumps(req))
    for row in req['items']:worker.atomic_json(row['cache'],dict(key=row['key'],status='completed',heard='Bring the key.',language='en',**(dict(words=proof()['words']) if req.get('wordTimestamps') else {})))
    return dict(attempted={r['key'] for r in req['items']},failure=None)
   from types import SimpleNamespace as S
   selected=dict(backend='cpu',id='test',path='/isolated/model',revision='pinned',runtime='runtime')
   with patch.object(secondary_speech,'backend',return_value=selected),patch.object(secondary_speech,'run_batch',side_effect=batch),patch('runtime_paths.python_for',return_value='python'):
    c=dict(storage=str(r));a=secondary_speech.transcribe_batch(S(atomic_json=worker.atomic_json),dict(c,_endpointWordTimestamps=True),items,True)
    b=secondary_speech.transcribe_batch(S(atomic_json=worker.atomic_json),c,items,True)
   self.assertTrue(calls[0]['wordTimestamps']);self.assertNotIn('wordTimestamps',calls[1]);self.assertNotEqual(a[0]['key'],b[0]['key'])
 def test_faster_whisper_word_flags_no_text_conditioning(self):
  from types import SimpleNamespace as S
  model=Mock();model.transcribe.return_value=([S(text='Hi',words=[S(word='Hi',start=0,end=1,probability=.9)])],S(language='en'))
  with patch('faster_whisper.WhisperModel',return_value=model),patch.object(secondary_speech,'whisper_pcm',return_value=np.zeros(16000,dtype='float32')):
   infer=secondary_speech.load_transcriber(dict(backend='cpu',model='/isolated/model',wordTimestamps=True));p=infer('clip.wav')
  self.assertTrue(model.transcribe.call_args.kwargs['word_timestamps']);self.assertFalse(model.transcribe.call_args.kwargs['condition_on_previous_text']);self.assertNotIn('initial_prompt',model.transcribe.call_args.kwargs);self.assertEqual(len(p['words']),1)
 def test_worker_without_onnx_can_use_installed_acoustic_runtime(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);p=audio(r/'voice.wav',voice=1,total=2)
   runtime=Path.home()/'Library/Application Support/SamCantoSync/runtime/bin/python'
   with patch.object(endpoint,'vocal_end',side_effect=ImportError('onnx absent in worker')),patch('runtime_paths.python_for',return_value=runtime) as resolve,patch('sys.platform','win32'):
    result=endpoint.vocal_witness(dict(storage=str(r)),r,p)
   self.assertTrue(result['vocalEvidenceAvailable']);self.assertEqual(resolve.call_args.args[1],'speech-runtime')

class VocalCapacityTests(unittest.TestCase):
 def test_only_proven_background_gap_borrowable_next_vocal_protected(self):
  from safe_vocal_capacity import configure
  from speech_timing import natural_window
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);stem=r/'stem.wav';x=np.zeros(24000*7,dtype='float32');x[5*24000:]=.1;sf.write(stem,x,24000,subtype='PCM_16')
   cs=[dict(cue(),end=1),dict(cue(1),start=1,end=5,japanese='',preserveOriginalSpeech=True,originalSpeechReason='subtitle-content-only-gap'),dict(cue(2),start=5,end=7)]
   c=dict(config(r),duration=7,dialoguePath=str(stem));configure(c,r,cs)
   self.assertEqual(natural_window(cs[0],cs,7,c),(0,5));self.assertTrue(cs[1]['preserveOriginalSpeech'])
   # Flag-only / absent waveform proof retains a barrier.
   self.assertEqual(natural_window(cs[0],cs,7,config(r)),(0,1))
 def test_micro_shift_plan_uses_same_verified_gap_barriers_as_source_locked(self):
  from safe_vocal_capacity import configure
  from natural_schedule import plan
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);stem=r/'stem.wav';sf.write(stem,np.zeros(24000*7),24000,subtype='PCM_16')
   cs=[dict(cue(),end=1),dict(cue(1),start=1,end=5,japanese='',cantonese='',preserveOriginalSpeech=True,originalSpeechReason='subtitle-content-only-gap'),dict(cue(2),start=5,end=7)]
   c=dict(config(r),duration=7,dialoguePath=str(stem),naturalTimingPolicy='micro-shift');configure(c,r,cs)
   rows=plan(c,cs,[3,None,1]);self.assertTrue(rows[0]['fit']);self.assertEqual(rows[0]['start'],0);self.assertEqual(rows[2]['start'],5);self.assertTrue(rows[1]['originalSource'])
 def test_changed_cue_content_cannot_reuse_prior_quiet_gap_flag(self):
  from safe_vocal_capacity import configure,is_barrier
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);stem=r/'stem.wav';sf.write(stem,np.zeros(24000*5),24000,subtype='PCM_16')
   cs=[dict(cue(1),start=1,end=5,japanese='',cantonese='',preserveOriginalSpeech=True,originalSpeechReason='subtitle-content-only-gap')];c=dict(config(r),duration=5,dialoguePath=str(stem));configure(c,r,cs);self.assertFalse(is_barrier(cs[0],cs,c))
   cs[0]['japanese']='こんにちは';self.assertTrue(is_barrier(cs[0],cs,c));configure(c,r,cs);self.assertEqual(c['_nonVocalCueIDs'],[])
 def test_original_words_manual_performance_and_faint_vocal_are_barriers(self):
  from safe_vocal_capacity import configure
  from speech_timing import natural_window
  for text,reason,level in [('日語','subtitle-content-only-gap',0),('','manual-preserve',0),('','subtitle-content-only-gap',.0003)]:
   with self.subTest(text=text,reason=reason,level=level),tempfile.TemporaryDirectory() as d:
    r=Path(d);stem=r/'stem.wav';sf.write(stem,np.ones(24000*5)*level,24000,subtype='PCM_16')
    cs=[dict(cue(),end=1),dict(cue(1),start=1,end=5,japanese=text,preserveOriginalSpeech=True,originalSpeechReason=reason)]
    c=dict(config(r),duration=5,dialoguePath=str(stem));configure(c,r,cs);self.assertEqual(natural_window(cs[0],cs,5,c),(0,1))

if __name__=='__main__':unittest.main()
