import array,copy,json,math,sys,tempfile,unittest,wave
from pathlib import Path
from unittest.mock import Mock,patch
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import normal_recovery as recovery,worker

def wav(path,seconds=1.,edge=0):
 sr=24000;voice=array.array('h',(round(4000*math.sin(i*.1)) for i in range(round(sr*seconds))))
 raw=array.array('h',[0])*round(sr*edge);raw.extend(voice);raw.extend(array.array('h',[0])*round(sr*edge))
 with wave.open(str(path),'wb') as f:f.setparams((1,2,sr,0,'NONE','not compressed'));f.writeframes(raw.tobytes())
 return path

class RecoveryDirectorTests(unittest.TestCase):
 def cfg(self,**kw):return dict(dict(productionMode='normal',duration=1.,targetLanguage='en',ttsBackend='drama3',model='selected-qwen-9b',port=1),**kw)
 def cue(self):return dict(start=0,end=1,japanese='来て',text='来て',cantonese='Come here.',speakerId='own')
 def placement(self,seconds=1.4):return [dict(start=0,deadline=1,seconds=seconds,fit=False)]
 def test_ai_cannot_invent_commands_or_actions_and_uses_selected_model(self):
  w=SimpleNamespace(ollama_chat=Mock(return_value='{"1":{"action":"execute-shell","reason":"rm files"}}'))
  rows=[dict(key='k',index=1,position=0,allowedActions=['retry-clauses','retain'])]
  result=recovery.decisions(w,self.cfg(),rows)
  self.assertEqual(result['k']['action'],'retry-clauses');self.assertEqual(result['k']['decisionSource'],'deterministic-fallback')
  self.assertEqual(w.ollama_chat.call_args.args[1],'selected-qwen-9b');self.assertTrue(w.ollama_chat.call_args.kwargs['strict_model'])
 def test_overlong_recording_never_receives_a_lengthening_instruction(self):
  w=SimpleNamespace(ollama_chat=Mock(return_value='{"1":{"action":"retry-clauses","reason":"Draft is too short; lengthen it to 9.43s"}}'))
  rows=[dict(key='k',index=1,position=0,reason='timing',seconds=9.43,availableSeconds=8.34,allowedActions=['retry-clauses','retain'])]
  reason=recovery.decisions(w,self.cfg(),rows)['k']['reason'];self.assertIn('9.43s / 8.34s',reason);self.assertIn('never lengthen',reason);self.assertNotIn('Draft is too short',reason)
 def test_unavailable_ai_uses_a_concrete_available_mechanism(self):
  w=SimpleNamespace(ollama_chat=Mock(side_effect=RuntimeError('model unavailable')))
  rows=[dict(key='k',index=1,position=0,allowedActions=['trim-padding','retain'])]
  self.assertEqual(recovery.decisions(w,self.cfg(),rows)['k']['action'],'trim-padding')
 def test_full_natural_recording_can_be_recovered_and_resume_does_not_generate_again(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);old=wav(job/'old.wav',1.4);new=wav(job/'new.wav',.7);cfg=self.cfg();cue=self.cue();before=old.read_bytes()
   with patch.object(worker,'ollama_chat',return_value='{"1":{"action":"retry-clauses","reason":"Try a complete natural rendition"}}'),patch('dubbing.gsv_audio',return_value=[new]) as tts,patch('normal_mode.inspect',return_value={1:dict(decision='english',heard='Come here.',contentFailure=False)}):
    for _ in range(2):
     paths,placement=recovery.recover(cfg,job,[dict(cue)],[old],Mock(),Mock(),self.placement())
     self.assertEqual(paths,[new]);self.assertTrue(placement[0]['fit'])
    self.assertEqual(tts.call_count,1)
   self.assertEqual(old.read_bytes(),before)
   data=json.loads((job/'automatic-recovery.json').read_text());self.assertFalse(data['qualityCertified'])
 def test_wrong_language_candidate_is_never_reported_as_a_repair(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);old=wav(job/'old.wav',1.4);new=wav(job/'new.wav',.5)
   with patch.object(worker,'ollama_chat',return_value='{"1":{"action":"retry-clauses","reason":"Retry"}}'),patch('dubbing.gsv_audio',return_value=[new]),patch('normal_mode.inspect',return_value={1:dict(decision='japanese',heard='来てください')}):
    paths,_=recovery.recover(self.cfg(),job,[self.cue()],[old],Mock(),Mock(),self.placement())
   self.assertEqual(paths,[old]);self.assertTrue(all(not r.get('selectedAudio') for r in json.loads((job/'automatic-recovery.json').read_text())['rows'].values()))
 def test_retries_are_persistent_and_never_repeat_the_same_mechanism(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);old=wav(job/'old.wav',1.4);cue=self.cue();cfg=self.cfg()
   with patch.object(worker,'ollama_chat',return_value='{}'),patch('dubbing.gsv_audio',side_effect=RuntimeError('decoder failed')) as tts:
    for _ in range(3):recovery.recover(cfg,job,[dict(cue)],[old],Mock(),Mock(),self.placement())
   entries=list(json.loads((job/'automatic-recovery.json').read_text())['rows'].values());actions=[a['action'] for a in entries[0]['attempts']]
   self.assertLessEqual(len(actions),2);self.assertEqual(len(actions),len(set(actions)));self.assertLessEqual(tts.call_count,1)
 def test_near_silent_padding_is_removed_without_tts_or_touching_original_voice(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);old=wav(job/'padded.wav',.6,edge=.3);before=old.read_bytes();cue=self.cue();cfg=self.cfg(port=None)
   with patch('dubbing.gsv_audio') as tts,patch('normal_mode.inspect') as listen:
    paths,placement=recovery.recover(cfg,job,[cue],[old],Mock(),Mock(),self.placement(1.2))
   self.assertNotEqual(paths,[old]);self.assertTrue(placement[0]['fit']);self.assertEqual(old.read_bytes(),before)
   tts.assert_not_called();listen.assert_not_called()
 def test_unverified_retranslation_does_not_reach_tts(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);old=wav(job/'old.wav',1.4);cue=self.cue()
   answers=['{"1":{"action":"adapt-source","reason":"Verbose draft"}}','{"1":"Go away."}','{}']
   with patch.object(worker,'ollama_chat',side_effect=answers),patch('semantic_review.audit',return_value={'1':dict(faithful=False)}),patch('dubbing.gsv_audio',side_effect=RuntimeError('failed')) as tts:
    paths,_=recovery.recover(self.cfg(),job,[cue],[old],Mock(),Mock(),self.placement())
   self.assertEqual(paths,[old]);self.assertEqual(cue['cantonese'],'Come here.');self.assertLessEqual(tts.call_count,1)
 def test_manual_editor_recordings_are_protected(self):
  with tempfile.TemporaryDirectory() as d,patch.object(worker,'ollama_chat') as ai:
   paths,placement=recovery.recover(self.cfg(editorRender=True),d,[self.cue()],['old'],Mock(),Mock(),self.placement())
   self.assertEqual(paths,['old']);ai.assert_not_called()

 def test_finished_take_survives_interruption_without_restarting_tts_and_restores_captions(self):
  from track_control import UserSkipped
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);old=wav(job/'old.wav',1.4);cfg=self.cfg();cue=self.cue()
   def interrupted(c,folder,rows,*args):
    path=wav(folder/'finished.wav',.7)
    worker.atomic_json(folder/'audio-preview.json',dict(rows=[dict(rows[0],audio=str(path))]))
    raise UserSkipped('pause')
   with patch.object(worker,'ollama_chat',return_value='{"1":{"action":"retry-clauses","reason":"Retake"}}'),patch('dubbing.gsv_audio',side_effect=interrupted) as tts,patch('normal_mode.inspect',return_value={1:dict(decision='english',heard='Come here.')}):
    with self.assertRaises(UserSkipped):recovery.recover(cfg,job,[dict(cue)],[old],Mock(),Mock(),self.placement())
    resumed=dict(cue);paths,placement=recovery.recover(cfg,job,[resumed],[old],Mock(),Mock(),self.placement())
    self.assertEqual(tts.call_count,1);self.assertEqual(paths[0].name,'finished.wav');self.assertTrue(placement[0]['fit'])
    self.assertEqual(resumed['english'],'Come here.');self.assertEqual(resumed['captionText'],'Come here.')

 def test_unavailable_ai_is_not_called_for_every_batch_and_uses_no_text_retry(self):
  w=SimpleNamespace(ollama_chat=Mock(side_effect=TimeoutError('stopped responding')))
  rows=[dict(key=str(i),index=i,position=i,allowedActions=['adapt-source','retry-clauses','retain']) for i in range(20)]
  result=recovery.decisions(w,self.cfg(),rows)
  self.assertEqual(w.ollama_chat.call_count,1)
  self.assertTrue(all(r['action']=='retry-clauses' for r in result.values()))
  self.assertEqual(w.ollama_chat.call_args.kwargs['max_attempts'],1)
  self.assertLessEqual(w.ollama_chat.call_args.kwargs['request_timeout'],90)
 def test_whole_director_text_budget_stops_before_another_request(self):
  cfg=self.cfg(_recoveryAIDeadline=10)
  with patch('normal_recovery.time.monotonic',return_value=11):
   with self.assertRaises(TimeoutError):recovery.request_options(cfg)
 def test_missing_script_original_fallback_is_retranslated_without_overwriting_intentional_original(self):
  with tempfile.TemporaryDirectory() as d:
   cue=dict(self.cue(),cantonese='',missingScript=True,preserveOriginalSpeech=True,originalSpeechReason='missing-script')
   rows=recovery.collect(self.cfg(),Path(d),[cue],[Path(d)/'absent.wav'],self.placement(),{})
   self.assertEqual(rows[0]['reason'],'missing-script');self.assertIn('adapt-source',rows[0]['allowedActions'])
   cue['originalSpeechReason']='user-choice'
   self.assertEqual(recovery.collect(self.cfg(),Path(d),[cue],[Path(d)/'absent.wav'],self.placement(),{}),[])

 def test_worker_respects_one_attempt_timeout_without_background_retries(self):
  with patch('worker.urllib.request.urlopen',side_effect=TimeoutError('busy')) as http,patch('worker.time.sleep') as sleep:
   with self.assertRaises(RuntimeError):worker.ollama_chat(1,'qwen',[],request_timeout=4,max_attempts=1,max_tokens=512)
   self.assertEqual(http.call_count,1);self.assertEqual(http.call_args.kwargs['timeout'],4);sleep.assert_not_called()
   self.assertEqual(json.loads(http.call_args.args[0].data)['options']['num_predict'],512)
 def test_semantic_rewrite_check_shares_the_same_remaining_ai_budget(self):
  cfg=self.cfg(_recoveryAIDeadline=100)
  rows=[dict(key='k',index=1,position=0,source='来て',caption='',draft='Come here.',availableSeconds=1)]
  w=SimpleNamespace(ollama_chat=Mock(return_value='{"1":"Come."}'))
  with patch('normal_recovery.time.monotonic',return_value=98),patch('semantic_review.audit',return_value={'1':dict(faithful=True)}) as audit:
   self.assertEqual(recovery.adapt(w,cfg,[self.cue()],rows),{'k':'Come.'})
   self.assertEqual(w.ollama_chat.call_args.kwargs['request_timeout'],2)
   self.assertEqual(audit.call_args.kwargs['request_options']['request_timeout'],2)
