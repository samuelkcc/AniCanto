"""Real WAVs + deterministic costs: repair gets first use, not an ASR race."""
import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
from test_coordinator86 import wav,cue
import delivery_policy as policy,repair_limits as limits,recovery_coordinator as rc,recovery_plan as plan,worker

def cfg(root,mode='balanced',**kw):
 return dict(deliveryPolicyRevision=policy.REPAIR_FIRST_REVISION,workMode=mode,duration=1000,workModeRevision='desktop-work-modes-1',ttsBackend='drama3',targetLanguage='yue',storage=str(root/'runtime'),normalRepairPolicy='missing-only',failedVoicePolicy='first-take',automaticSystemVoice=False,automaticMicroTempo=False,**kw)

class Recovery88Tests(unittest.TestCase):
 def test_plan_measured_pending_and_generation_speed_not_text_shortening(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);a=wav(r/'long.wav',5);good=wav(r/'good.wav',1);cues=[dict(cue(),end=2),dict(cue(),start=4,end=6,reviewIndex=1)]
   c=cfg(r,_observedGenerationSecondsPerCue=100)
   before=[dict(x) for x in cues];plan.prepare(c,r,cues,[a,good]);saved=limits.read(r/'repair-time-budget.json')['plan']
   self.assertEqual(saved['pendingIndices'],[1]);self.assertEqual(saved['observedGenerationSecondsPerCue'],100);self.assertEqual(saved['phaseLimits']['native'],0);self.assertEqual(saved['phaseLimits']['listening'],60);self.assertEqual(cues,before)
   many=[dict(cue(),reviewIndex=i,start=i*4,end=i*4+2) for i in range(80)]
   plan.prepare(dict(c,workMode='quality'),r,many,[a]*80)
   self.assertEqual(limits.read(r/'repair-time-budget.json')['plan'],saved,'Resume must not resize frozen clocks')
 def test_mode_caps_and_native_consent(self):
  for mode,cap,listen in [('performance',300,0),('balanced',900,60),('quality',1800,180)]:
   with self.subTest(mode=mode),tempfile.TemporaryDirectory() as d:
    r=Path(d);cs=[dict(cue(),reviewIndex=i,start=i*4,end=i*4+2) for i in range(100)]
    plan.prepare(dict(cfg(r,mode,_observedGenerationSecondsPerCue=90),automaticSystemVoice=True),r,cs,[r/'skipped.wav']*100)
    p=limits.read(r/'repair-time-budget.json')['plan'];self.assertEqual(p['repairSeconds'],cap);self.assertEqual(p['phaseLimits']['native'],cap*.25);self.assertEqual(p['listeningSeconds'],listen)
 def test_listening_cannot_spend_repair_or_refill_across_resume(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);now=[0.];calls=[];c=cfg(r,_repairBudgetSeconds=10)
   @limits.bounded('listen',phase='listening')
   def listen(c,j,cs,ps):now[0]+=61;limits.check();return ps
   @limits.bounded('repair')
   def repair(c,j,cs,ps):calls.append(1);now[0]+=6;return ['new']
   with patch('repair_limits.time.monotonic',side_effect=lambda:now[0]):
    listen(c,r,[],['old']);self.assertEqual(repair(c,r,[],['old']),['new']);repair(c,r,[],['old']);repair(dict(c,workMode='quality'),r,[],['kept'])
   self.assertEqual(len(calls),2);p=limits.read(r/'repair-time-budget.json');self.assertEqual(p['phases']['listening']['spentSeconds'],61);self.assertEqual(p['phases']['ai']['spentSeconds'],12)
 def test_balanced_first_take_repairs_before_listening_and_no_asr_inside_repair(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);long=wav(r/'long.wav',3);fixed=wav(r/'fixed.wav',1);order=[]
   def finish(c,j,cs,ps,*a,**k):return ps,[dict(fit=str(p)==str(fixed),start=0,deadline=2,seconds=1 if p==fixed else 3) for p in ps]
   def actor(c,j,cs,ps,*a,**k):
    order.append('actor');self.assertFalse(c['preferFirstAudibleTake']);self.assertEqual(c['_maximumTimingOperations'],1);self.assertTrue(c['_durationFitRequired']);self.assertTrue(c['_deferContentReadback']);return [fixed]
   with patch.object(rc,'physical',side_effect=lambda c,j,cs,ps,*a:ps),patch.object(rc,'actor',side_effect=actor),patch.object(rc,'fallback',side_effect=lambda c,j,cs,ps,*a:(order.append('fallback') or ps)),patch('system_voice.repair',side_effect=lambda c,j,cs,ps,*a:ps),patch.object(rc,'listen',side_effect=lambda c,j,cs,ps,*a:(order.append('listen') or ps)),patch('natural_finish.finish',side_effect=finish):
    got,_=rc.recover(cfg(r),r,[cue()],[long],Mock(),Mock())
   self.assertEqual(got,[fixed]);self.assertEqual(order,['actor','fallback','listen']);self.assertEqual(limits.read(r/'recovery-summary.json')['unresolvedCount'],0)
 def test_confirmed_listening_failure_uses_same_remaining_repair_and_one_more_disposition(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);good=wav(r/'good.wav');order=[]
   def listen(c,j,cs,ps,*a):
    order.append('listen');worker.atomic_json(r/'normal-checks.json',dict(unresolved=[1],repairs=[dict(index=1,check=dict(contentFailure=True))]));return ps
   with patch.object(rc,'physical',side_effect=lambda c,j,cs,ps,*a:ps),patch.object(rc,'actor',side_effect=lambda c,j,cs,ps,*a:ps),patch.object(rc,'fallback',side_effect=lambda c,j,cs,ps,*a:(order.append('fallback') or ps)),patch.object(rc,'listen',side_effect=listen),patch('system_voice.repair',side_effect=lambda c,j,cs,ps,*a:ps),patch('natural_finish.finish',side_effect=lambda c,j,cs,ps,*a,**k:(ps,[dict(fit=True,start=0,deadline=2)])):
    rc.recover(cfg(r),r,[cue()],[good],Mock(),Mock())
   self.assertEqual(order,['fallback','listen','fallback']);self.assertEqual(limits.read(r/'recovery-summary.json')['unresolvedIndices'],[1])
 def test_balanced_listens_suspects_only_max24_quality_broader(self):
  for mode,count in [('balanced',24),('quality',32),('balanced',0)]:
   with self.subTest(mode=mode,count=count),tempfile.TemporaryDirectory() as d:
    r=Path(d);p=wav(r/'healthy.wav',1);cs=[dict(cue(),reviewIndex=i,start=2*i,end=2*i+2) for i in range(32)]
    if count:cs=[dict(c,translationWarnings=['suspect']) for c in cs]
    with patch('normal_mode.inspect',return_value={}) as inspect:
     rc.listen(cfg(r,mode),r,cs,[p]*len(cs),Mock(),Mock())
    self.assertEqual(len(inspect.call_args.args[2]) if inspect.called else 0,count)
    self.assertFalse(limits.read(r/'normal-checks.json')['qualityCertified'])
 def test_audio_fingerprint_prevents_old_confirmed_error_reinfecting_new_take(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);old=wav(r/'old.wav',1);new=wav(r/'new.wav',1.1)
   worker.atomic_json(r/'normal-checks.json',dict(unresolved=[1],repairs=[dict(index=1,audioSHA256=hashlib.sha256(old.read_bytes()).hexdigest(),check=dict(contentFailure=True))]))
   with patch('normal_mode.inspect',return_value={}):rc.listen(cfg(r),r,[cue()],[new],Mock(),Mock())
   self.assertEqual(policy.confirmed_indices(cfg(r),r),set())
 def test_generic_reference_sha_is_real_and_enters_measured_compact(self):
  from normal_voice_fallback import repair
  from generic_delivery import repair as compact
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);source=wav(r/'source.wav',3);candidate=wav(r/'candidate.wav',3);ref=wav(r/'ref.wav',4)
   c=dict(cfg(r,productionMode='normal',_sourceVoiceRepairsExhausted=True,preferFirstAudibleTake=False,_deferContentReadback=True),duration=2)
   profile=dict(id='r',language='ja',reference=str(source));bank=dict(profile,reference=str(ref),language='yue',naturalReferenceId='test')
   place=[dict(fit=False,seconds=3,start=0,deadline=2)]
   with patch('dubbing.profile_for',return_value=profile),patch('natural_voices.resolve',return_value=bank),patch('dubbing.gsv_audio',return_value=[candidate]),patch('normal_mode.inspect',return_value={}),patch('natural_finish.bounded_tempo',return_value=None):repair(c,r,[cue()],[source],place,Mock(),Mock())
   record=next(iter(limits.read(r/'target-reference-recovery.json').values()));self.assertEqual(record['referenceSHA256'],hashlib.sha256(ref.read_bytes()).hexdigest());self.assertEqual(record['status'],'timing-not-fit')
   cs=[cue()]
   with patch('dubbing.profile_for',return_value=profile),patch('natural_voices.resolve',return_value=bank),patch('natural_schedule.prepare',return_value=place),patch('natural_delivery.repair',side_effect=lambda c,j,cs,ps,*a,**k:ps) as revoice,patch('natural_finish.finish',side_effect=lambda c,j,cs,ps,*a,**k:(ps,place)),patch('normal_mode.inspect',return_value={}):compact(dict(c,failedVoicePolicy='generic',_skipAlternate=True),r,cs,[source],place,Mock(),Mock())
   self.assertEqual(revoice.call_count,1,'A real SHA must permit measured bank compaction')
 def test_real_same_actor_measured_retake_only_once_and_neighbour_unchanged(self):
  import natural_delivery
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);long=wav(r/'long.wav',3);fixed=wav(r/'fixed.wav',1);neighbour=wav(r/'neighbour.wav',1);before=neighbour.read_bytes()
   cs=[dict(cue(),cantonese='我哋而家一齊即刻去幫佢啦'),dict(cue(),start=2,end=4,reviewIndex=1,cantonese='好呀')]
   placement=[dict(fit=False,start=0,deadline=2,seconds=3),dict(fit=True,start=2,deadline=4,seconds=1)]
   def compact(w,c,j,cs,indices,targets,**kw):
    self.assertEqual(indices,[0]);self.assertGreater(c['_measuredOverruns']['0']['seconds'],c['_measuredOverruns']['0']['availableSeconds']);cs[0]['cantonese']='即刻去幫佢啦';return [0]
   c=dict(cfg(r,productionMode='normal',_deferContentReadback=True),preferFirstAudibleTake=False,automaticDurationRewrite=True,_maximumTimingOperations=1,_durationFitRequired=True)
   with patch('concise_dialogue.compact',side_effect=compact),patch('natural_schedule.prepare',return_value=placement),patch('dubbing.gsv_audio',return_value=[fixed]) as generate,patch('normal_mode.inspect',side_effect=AssertionError('repair cannot spend listening allowance')):
    got=natural_delivery.repair(c,r,cs,[long,neighbour],Mock(),Mock(),placement=placement)
    self.assertEqual(got,[fixed,neighbour]);natural_delivery.repair(c,r,cs,[long,neighbour],Mock(),Mock(),placement=placement)
   self.assertEqual(generate.call_count,1);self.assertEqual(neighbour.read_bytes(),before);self.assertEqual(limits.read(r/'recovery-operation-counts.json')['actor-timing:1'],1)
 def test_fifty_pending_target_repairs_happen_before_a_full_listener_clock(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);short=wav(r/'target.wav',1);paths=[r/('skipped-'+str(i)+'.wav') for i in range(50)];cs=[dict(cue(),reviewIndex=i,start=i*2,end=i*2+2) for i in range(50)];now=[0.];events=[]
   @limits.bounded('fixture-target')
   def repair(c,j,cs,ps,*args):
    limits.check();events.append('target');now[0]+=100;return [short]*50
   @limits.bounded('fixture-listen',phase='listening')
   def listen(c,j,cs,ps,*args):
    events.append('listen');now[0]+=61;limits.check();return ps
   def finish(c,j,cs,ps,*a,**k):return ps,[dict(fit=p==short,start=i*2,deadline=i*2+2) for i,p in enumerate(ps)]
   with patch('repair_limits.time.monotonic',side_effect=lambda:now[0]),patch.object(rc,'physical',side_effect=lambda c,j,cs,ps,*a:ps),patch.object(rc,'actor',side_effect=lambda c,j,cs,ps,*a:ps),patch.object(rc,'fallback',side_effect=repair),patch.object(rc,'listen',side_effect=listen),patch('system_voice.repair',side_effect=lambda c,j,cs,ps,*a:ps),patch('natural_finish.finish',side_effect=finish):
    selected,_=rc.recover(cfg(r,_observedGenerationSecondsPerCue=8),r,cs,paths,Mock(),Mock())
   self.assertEqual(events,['target','listen']);self.assertEqual(selected,[short]*50)
   saved=limits.read(r/'repair-time-budget.json');self.assertEqual(saved['plan']['pendingCount'],50);self.assertEqual(saved['phases']['ai']['spentSeconds'],100);self.assertEqual(saved['phases']['listening']['spentSeconds'],61)
 def test_cantonese_now_substitution_preserves_appear_compounds(self):
  for text in ['救命恩人蕾玖突然出現喺佢面前','佢重現喺畫面','畫面呈現喺眼前']:
   self.assertEqual(worker.spoken_cantonese(text),text)
   self.assertFalse(any('written Mandarin' in e for e in worker.dubbing_script_issues(text,100)))
  self.assertEqual(worker.spoken_cantonese('現喺我哋走啦'),'而家我哋走啦')
 def test_confirmed_bad_generic_cache_is_not_readopted_or_marked_fixed(self):
  from normal_voice_fallback import repair
  from failed_voice_policy import choose
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);source=wav(r/'source.wav',3);candidate=wav(r/'candidate.wav',1);ref=wav(r/'ref.wav',4);p=dict(id='r',reference=str(ref),language='yue')
   c=dict(cfg(r,productionMode='normal',_sourceVoiceRepairsExhausted=True,preferFirstAudibleTake=False,_deferContentReadback=True),duration=2)
   place=[dict(fit=False,seconds=3,start=0,deadline=2)];cs=[cue()]
   with patch('dubbing.profile_for',return_value=p),patch('natural_voices.resolve',return_value=p),patch('dubbing.gsv_audio',return_value=[candidate]) as generate:
    selected=repair(c,r,cs,[source],place,Mock(),Mock());self.assertEqual(selected,[candidate])
    worker.atomic_json(r/'normal-checks.json',dict(unresolved=[1],repairs=[dict(index=1,originalAudio=str(candidate),audioSHA256=hashlib.sha256(candidate.read_bytes()).hexdigest(),check=dict(contentFailure=True))]))
    repair(c,r,cs,selected,[dict(fit=True,seconds=1,start=0,deadline=2)],Mock(),Mock())
   self.assertEqual(generate.call_count,1);self.assertEqual(policy.confirmed_indices(c,r),{1})
   self.assertEqual(next(iter(limits.read(r/'target-reference-recovery.json').values()))['status'],'not-verified')
   self.assertEqual(choose(dict(c,failedVoicePolicy='first-take'),r,cs,selected)[1],{0})
 def test_native_cannot_revive_confirmed_bad_bytes_or_refill_on_changed_text(self):
  import system_voice
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);candidate=wav(r/'native.wav',1);c=dict(cfg(r),automaticSystemVoice=True);place=[dict(fit=True,seconds=1,start=0,deadline=2)]
   with patch.object(system_voice,'installed',return_value=[dict(name='HK',locale='zh-HK')]),patch.object(system_voice,'synthesize',return_value=candidate) as generate,patch('natural_schedule.prepare',return_value=place),patch('project_store.record_issue'):
    system_voice.repair(c,r,[cue()],[r/'skipped.wav'],place,Mock(),Mock())
    worker.atomic_json(r/'normal-checks.json',dict(unresolved=[1],repairs=[dict(index=1,audioSHA256=hashlib.sha256(candidate.read_bytes()).hexdigest(),check=dict(contentFailure=True))]))
    system_voice.repair(c,r,[cue()],[candidate],place,Mock(),Mock())
    system_voice.repair(c,r,[dict(cue(),cantonese='改咗個稿')],[r/'skipped.wav'],place,Mock(),Mock())
   self.assertEqual(generate.call_count,2);self.assertEqual(policy.confirmed_indices(c,r),{1})
   self.assertEqual(limits.read(r/'recovery-operation-counts.json')['native-generation:1'],2)
 def test_report_distinguishes_missing_target_from_audible_source_fallback(self):
  from dialogue_delivery import summary
  track=dict(deliveryPolicyRevision=policy.REPAIR_FIRST_REVISION,language='yue',engine='drama3',available=194,required=244,missing=50,causes={'timing-overrun':43},rows=[dict(available=False,fallbackStage='original-source') for _ in range(50)])
  text=summary(dict(tracks=[track]));self.assertIn('目標配音 194/244',text);self.assertIn('原聲後備 50',text);self.assertNotIn('缺聲 50',text)
 def test_fallback_selector_matrix_preserves_healthy_and_rejects_confirmed_bad_first(self):
  from failed_voice_policy import choose
  for mode in ['performance','balanced','quality']:
   for option in ['generic','first-take','source']:
    with self.subTest(mode=mode,option=option),tempfile.TemporaryDirectory() as d:
     r=Path(d);actor=wav(r/'actor.wav',1);bank=wav(r/'bank.wav',.9);c=dict(cfg(r,mode),failedVoicePolicy=option)
     worker.atomic_json(r/'natural-placement.json',dict(rows=[dict(index=1,fit=True)]))
     worker.atomic_json(r/'normal-checks.json',dict(unresolved=[1],repairs=[dict(index=1,originalAudio=str(actor),check=dict(decision='unconfirmed'))]))
     self.assertEqual(choose(c,r,[cue()],[actor]),([actor],set()),'Uncertain does not discard a usable first take')
     worker.atomic_json(r/'normal-checks.json',dict(unresolved=[1],repairs=[dict(index=1,originalAudio=str(actor),check=dict(contentFailure=True))]))
     self.assertEqual(choose(c,r,[cue()],[actor])[1],{0},'Confirmed bad first cannot be revived without a target fallback')
     worker.atomic_json(r/'target-reference-recovery.json',dict(trial=dict(index=1,status='selected-unverified',selectedAudio=str(bank))))
     selected,source=choose(c,r,[cue()],[bank]);self.assertEqual(selected,[bank]);self.assertEqual(source,{0} if option=='source' else set())
 def test_actual_first_generation_events_supply_cost_without_model_inference(self):
  import fast_mode
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);good=wav(r/'good.wav');captured=[]
   def generate(c,j,cs,run,emit):
    for value in [2,8,20]:emit('配音','test',.5,workID='tts',seconds=value)
    return [good]
   def recover(c,*a):captured.append(c);raise StopIteration('fixture stops before mux')
   with patch('source_counting.repair',return_value=[]),patch('dubbing.gsv_audio',side_effect=generate),patch.object(rc,'recover',side_effect=recover):
    with self.assertRaises(StopIteration):fast_mode.synthesize(cfg(r),r,[cue()],Mock(),Mock())
   self.assertEqual(captured[0]['_observedGenerationSecondsPerCue'],8)
   self.assertEqual(limits.read(r/'generation-cost.json')['samples'],3)
 def test_legacy_v2_calls_original_frozen_flow(self):
  with patch.object(rc,'recover_v2',return_value=('old','plan')) as legacy:
   self.assertEqual(rc.recover(dict(deliveryPolicyRevision=policy.POOLED_REVISION),'/unused',[],[],Mock(),Mock()),('old','plan'));legacy.assert_called_once()
 def test_generic_count_survives_script_change(self):
  from normal_voice_fallback import repair
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);src=wav(r/'source.wav',3);ref=wav(r/'ref.wav',4);p=dict(id='r',reference=str(ref),language='yue')
   c=cfg(r,productionMode='normal',_sourceVoiceRepairsExhausted=True,preferFirstAudibleTake=False,_deferContentReadback=True)
   place=[dict(fit=False,seconds=3,start=0,deadline=2)]
   with patch('dubbing.profile_for',return_value=p),patch('natural_voices.resolve',return_value=p),patch('dubbing.gsv_audio',side_effect=RuntimeError('failed')) as generate:
    repair(c,r,[cue()],[src],place,Mock(),Mock());repair(c,r,[dict(cue(),cantonese='新嘅講法')],[src],place,Mock(),Mock())
   self.assertEqual(generate.call_count,1)

if __name__=='__main__':unittest.main()
