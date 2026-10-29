import copy,json,sys,tempfile,unittest,wave,subprocess,shutil
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch,Mock
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows')]
import source_fragment_repair as fragments,caption_alignment as captions,natural_schedule as schedule
import normal_voice_fallback,failed_voice_policy,fast_mode

def row(a,b,text,prob=.9):return dict(start=a,end=b,text=text,words=[dict(start=a,end=b,word=text,probability=prob)])
def wav(path,seconds=1):
 with wave.open(str(path),'wb') as w:w.setparams((1,2,24000,0,'NONE','not compressed'));w.writeframes(b'\0\x10'*round(24000*seconds))
 return path
class SourceClockTests(unittest.TestCase):
 def test_latin_japanese_suspect_only(self):self.assertTrue(fragments.suspect(row(1,2,'dj')));self.assertFalse(fragments.suspect(row(1,2,'DJ'),'en'))
 def test_short_genuine_response_is_reheard_not_discarded(self):self.assertTrue(fragments.suspect(row(1,1.06,'え')))
 def test_grouped_context_not_per_bad_letter(self):
  windows,wanted=fragments.windows([row(5+i*.2,5.2+i*.2,'d') for i in range(4)],30);self.assertEqual(len(windows),1);self.assertEqual(len(wanted),4);self.assertLessEqual(windows[0]['end']-windows[0]['start'],26)
 def test_listening_context_does_not_cut_good_adjacent_turn(self):
  old=[row(1,5,'前の文'),row(7,7.2,'dj'),row(10,13,'次の文')];groups,_=fragments.windows(old,30);self.assertLess(groups[0]['start'],1);self.assertGreater(groups[0]['end'],13);self.assertLessEqual(groups[0]['end']-groups[0]['start'],26)
 def test_paired_local_recovers_greeting_before_old_fragment(self):
  old=[row(1,2,'前の文'),row(6,6.3,'d'),row(6.3,6.4,'j'),row(9,10,'次の文')];w=dict(start=3,end=9,indices=[1,2]);new=[row(4,6.2,'いらっしゃいませ')];before=copy.deepcopy(old)
  chosen=fragments.select(old,new,w,'いらっしゃいませ');out=fragments.apply(old,chosen,[1,2]);self.assertTrue(any(x['text']=='いらっしゃいませ' for x in out));self.assertIn(old[0],out);self.assertIn(old[3],out);self.assertEqual(old,before)
 def test_no_caption_clock_can_be_added(self):
  old=[row(2,2.1,'d')];new=[row(50,51,'こんにちは')];self.assertEqual(fragments.select(old,new,dict(start=0,end=5,indices=[0]),'こんにちは'),[])
 def test_no_neighbour_borrow(self):
  old=[row(2,2.1,'d'),row(3,5,'今回の件')];self.assertEqual(fragments.select(old,[row(2,4,'今回の件')],dict(start=0,end=5,indices=[0]),'今回の件'),[])
 def test_unconfirmed_source_preserved_without_new_word_clock(self):
  old=[row(1,2,'dj')];out=fragments.apply(old,[],[0]);self.assertTrue(out[0]['sourceClockUnconfirmed']);self.assertEqual(out[0]['words'],old[0]['words'])
 def test_independent_text_required(self):self.assertEqual(fragments.select([row(1,2,'dj')],[row(1,2,'こんにちは')],dict(start=0,end=3,indices=[0]),''),[])
 def test_bad_candidate_rejected(self):self.assertEqual(fragments.select([row(1,2,'dj')],[row(1,2,'dj')],dict(start=0,end=3,indices=[0]),'dj'),[])
 def test_stretched_word_cannot_create_an_early_speech_start(self):
  bad=row(1,6.2,'なんだ');self.assertEqual(fragments.select([row(4,5,'dj')],[bad],dict(start=0,end=10,indices=[0]),'なんだ'),[])
 def test_source_locked_start_never_moves(self):
  cues=[dict(start=1,end=2),dict(start=2,end=3)];out=schedule.plan(dict(duration=4),cues,[1.4,.6]);self.assertFalse(out[0]['fit']);self.assertEqual([x['start'] for x in out],[1,2]);self.assertEqual([x['shift'] for x in out],[0,0])
 def test_normal_configuration_migrates_implicit_microshift(self):self.assertEqual(fast_mode.configure(dict(productionMode='normal',naturalTimingPolicy='micro-shift'))['naturalTimingPolicy'],'source-locked')
class ResumePolicyTests(unittest.TestCase):
 def test_frozen_policy_identity_survives_update(self):
  cfg=fast_mode.configure(dict(productionMode='normal',normalPolicyRevision='frozen-previous'))
  self.assertEqual(cfg['normalPolicyRevision'],'frozen-previous');self.assertEqual(cfg['naturalTimingPolicy'],'source-locked')
 def test_delivery_start_policy_keeps_same_source_checkpoint(self):
  import job_identity
  with tempfile.TemporaryDirectory() as d:
   original=dict(video='/fixture/video.mp4',normalPolicyRevision='frozen',sourceStat=[123,456]);a=job_identity.resolve(d,original);(a/'cues.json').write_text('[]');b=job_identity.resolve(d,dict(original,naturalTimingPolicy='source-locked'));self.assertEqual(a,b)
class FragmentPersistenceTests(unittest.TestCase):
 def test_paired_result_saved_and_resume_does_not_regenerate(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);old=[row(5,5.2,'dj')];cfg=dict(duration=12,storage=d,sourceLanguage='ja');model=Mock();word=NS(start=3,end=4.2,word='こんにちは',probability=.95);model.transcribe.return_value=([NS(words=[word])],None)
   def secondary(cfg,action,request,emit):
    cues=request['cues'];self.assertTrue(all(c['text'] for c in cues));Path(request['job'],'asr-verification.json').write_text(json.dumps(dict(identity=[[c['start'],c['end'],True] for c in cues],rows=[dict(text='こんにちは') for c in cues])))
   with patch('dubbing.model_job',side_effect=secondary) as second,patch('track_control.check'):
    first=fragments.repair(model,[0]*200000,old,cfg,p,Mock());again=fragments.repair(model,[0]*200000,old,cfg,p,Mock())
   self.assertEqual(first,again);self.assertEqual(first[0]['text'],'こんにちは');self.assertEqual(second.call_count,1);self.assertEqual(model.transcribe.call_count,1)
 def test_missing_secondary_model_preserves_original_and_attempt_budget(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);old=[row(5,5.2,'dj')];model=Mock();model.transcribe.return_value=([],None);cfg=dict(duration=12,storage=d)
   with patch('dubbing.model_job',side_effect=RuntimeError('not deployed')) as second,patch('track_control.check'):
    a=fragments.repair(model,[0]*200000,old,cfg,p,Mock());fragments.repair(model,[0]*200000,old,cfg,p,Mock())
   self.assertEqual(second.call_count,1);self.assertTrue(a[0]['sourceClockUnconfirmed']);self.assertEqual(json.loads((p/'source-fragment-report.json').read_text())['independentError'],'not deployed')
 def test_unbounded_suspect_never_launches_empty_secondary_batch(self):
  with tempfile.TemporaryDirectory() as d:
   with patch('dubbing.model_job') as second:
    a=fragments.repair(Mock(),[],[row(1,40,'dj')],dict(duration=60,storage=d),d,Mock())
   second.assert_not_called();self.assertTrue(a[0]['sourceClockUnconfirmed'])
class CaptionTests(unittest.TestCase):
 def test_no_source_loss_when_partitioning(self):
  cues=[dict(japanese='字'*1200) for i in range(20)];groups=list(captions.batches(cues));self.assertEqual([i for a,b in groups for i in range(a,b)],list(range(20)));self.assertTrue(all(b-a<=8 for a,b in groups))
 def test_long_silence_splits_scene_and_excludes_distant_context(self):
  cues=[dict(start=0,end=1,japanese='前'),dict(start=20,end=21,japanese='後')];self.assertEqual(list(captions.batches(cues)),[(0,1),(1,2)]);payload=captions.payload({'1':{}},cues,1,2,[]);self.assertEqual([c['id'] for c in payload['readOnlyContext']],['1'])
 def test_candidate_clocks_are_only_evidence(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'subtitle-context.json').write_text(json.dumps([dict(start=2,end=4,text='歡迎光臨')]))
   c=[dict(start=1,end=2,japanese='いらっしゃいませ')];captions.prepare({},p,c);self.assertEqual((c[0]['start'],c[0]['end']),(1,2));self.assertEqual(c[0]['captionCandidates'][0]['id'],1);self.assertFalse(c[0]['captionAlignment']['clocksChanged'])
 def test_audio_only_has_no_caption_leak(self):
  from translation_source import remove_caption_evidence
  c=[dict(captionCandidates=[dict(text='secret')],captionAlignment={})];remove_caption_evidence(dict(translationSource='audio-only'),c);self.assertNotIn('captionCandidates',c[0]);self.assertNotIn('captionAlignment',c[0])
 def test_missing_and_partial_batch_reported_honestly(self):
  with tempfile.TemporaryDirectory() as d:
   w=NS(atomic_json=lambda p,v:Path(p).write_text(json.dumps(v)));captions.record_batch(w,d,'yue',{'1':{},'2':{}},{'1':'你好'});v=json.loads((Path(d)/'caption-batches.json').read_text());self.assertEqual(next(iter(v['batches'].values()))['status'],'partial')
class GenericTests(unittest.TestCase):
 def test_missing_only_reaches_bank_after_timing_exhaustion_and_reuses(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);actor=wav(p/'actor.wav',4);candidate=wav(p/'candidate.wav',1);bank=wav(p/'bank.wav',4);cue=dict(start=0,end=2,cantonese='你好呀',speakerId='R1');cfg=dict(duration=2,productionMode='normal',targetLanguage='yue',ttsBackend='drama3',_sourceVoiceRepairsExhausted=True,_objectiveFallbackOnly=True);place=[dict(fit=False,seconds=4,start=0,deadline=2)];profile=dict(id='R1',reference=str(bank),language='yue',naturalReferenceId='yue-mid');before=actor.read_bytes()
   with patch('dubbing.profile_for',return_value=profile),patch('natural_voices.resolve',return_value=profile),patch('dubbing.gsv_audio',return_value=[candidate]) as generate,patch('normal_mode.inspect',return_value={1:dict(decision='cantonese',heard='你好呀')}) as inspect:
    result=normal_voice_fallback.repair(cfg,p,[cue],[actor],place,Mock(),Mock());self.assertEqual(result,[candidate]);self.assertTrue(inspect.call_args.args[0]['_forceIndependentListening']);normal_voice_fallback.repair(cfg,p,[cue],[actor],place,Mock(),Mock());self.assertEqual(generate.call_count,1)
   self.assertEqual(actor.read_bytes(),before);record=next(iter(json.loads((p/'target-reference-recovery.json').read_text()).values()));self.assertEqual(record['maximumAttempts'],1)
 def test_policy_includes_objective_overrun_not_only_missing_audio(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);a=wav(p/'voice.wav');(p/'natural-placement.json').write_text(json.dumps(dict(rows=[dict(index=1,fit=False,seconds=4)])));selected,source=failed_voice_policy.choose(dict(failedVoicePolicy='generic'),p,[dict(start=0,end=1,cantonese='你好')],[a]);self.assertEqual(source,{0});self.assertEqual(selected,[a])
 def test_foreign_script_only_fallback_is_not_selected_as_uncertain(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);a=wav(p/'actor.wav',4);v=wav(p/'candidate.wav');bank=wav(p/'bank.wav',4);profile=dict(id='R1',reference=str(bank),language='yue',naturalReferenceId='yue-mid');cue=dict(start=0,end=2,cantonese='咁黑嘅',speakerId='R1');cfg=dict(duration=2,productionMode='normal',targetLanguage='yue',ttsBackend='drama3',_sourceVoiceRepairsExhausted=True,_objectiveFallbackOnly=True)
   with patch('dubbing.profile_for',return_value=profile),patch('natural_voices.resolve',return_value=profile),patch('dubbing.gsv_audio',return_value=[v]),patch('normal_mode.inspect',return_value={1:dict(decision='unconfirmed',heard='कम्हा के',independent=dict(heard='깜하게'))}):
    self.assertEqual(normal_voice_fallback.repair(cfg,p,[cue],[a],[dict(fit=False,seconds=4,start=0,deadline=2)],Mock(),Mock()),[a])
   self.assertEqual(next(iter(json.loads((p/'target-reference-recovery.json').read_text()).values()))['status'],'not-verified')
 def test_normal_success_does_not_trigger_generic(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);a=wav(p/'good.wav');cue=dict(start=0,end=2,cantonese='你好');cfg=dict(productionMode='normal',duration=2,_objectiveFallbackOnly=True,_sourceVoiceRepairsExhausted=True)
   with patch('dubbing.gsv_audio') as generate:self.assertEqual(normal_voice_fallback.repair(cfg,p,[cue],[a],[dict(fit=True)],Mock(),Mock()),[a]);generate.assert_not_called()
if __name__=='__main__':unittest.main()
