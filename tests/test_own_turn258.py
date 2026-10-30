import copy,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows')]
import own_turn
from worker import atomic_json
from primary_source import REVISION

def cue(text,start=0,index=0,kind='embedded',**extra):
 d=dict(start=start,end=start+1,reviewIndex=index,enabled=True,primarySource=dict(revision=REVISION,kind=kind,text=text));d.update(extra);return d

def config(**extra):
 c=dict(basicFlowRevision=__import__('basic_flow').REVISION,deliveryPolicyRevision=__import__('delivery_policy').REVISION,ownTurnGateRevision=own_turn.REVISION,sourcePolicyRevision=REVISION,sourceLanguage='ja',model='fixture',port=1,aiAutoFix=False,limitSpeechDuration=False,repairExcessiveAudibleOverlap=False);c.update(extra);return c

def worker(response='{"text":"下集ONEPIECE"}'):
 return SimpleNamespace(atomic_json=atomic_json,emit=Mock(),traditional_cantonese=lambda c,t:t,ollama_chat=Mock(return_value=response))

class Ownership(unittest.TestCase):
 def test_partial_next_title(self):
  f=own_turn.findings('下集ONEPIECE布魯克救出大作戰','次回ONEPIECE',[dict(turn=414,source='四皇翻身布魯克救出大作戰')]);self.assertEqual(f,[dict(turn=414,clause='布魯克救')])
 def test_normalization_simplified_traditional(self):
  convert=lambda s:s.translate(str.maketrans('鲁战','魯戰'))
  self.assertTrue(own_turn.findings('布魯克救出大作戰','次回ONEPIECE',[dict(turn=2,source='布鲁克救出大作战')],convert))
 def test_own_clause_is_not_leak(self):
  self.assertEqual(own_turn.findings('布魯克救出大作戰','布魯克救出大作戰',[dict(turn=2,source='布魯克救出大作戰')]),[])
 def test_rolling_and_real_repetition(self):
  self.assertEqual(own_turn.findings('布魯克救出大作戰','次回ONEPIECE',[dict(turn=2,source='布魯克救出大作戰'),dict(turn=3,source='布魯克救出大作戰')]),[])
 def test_short_names_do_not_trigger(self):
  self.assertEqual(own_turn.findings('路飛快走','下一集',[dict(turn=2,source='路飛')]),[])
 def test_english_unique_span(self):
  self.assertTrue(own_turn.findings('Next episode rescue mission','Next episode',[dict(turn=2,source='The rescue mission')]))
 def test_three_distinct_owners_max(self):
  w=[dict(turn=i,source='abc'+str(i)+'xyz') for i in range(6)];self.assertEqual(len(own_turn.findings(''.join(r['source'] for r in w),'own',w)),3)
 def test_invalid_conversion_is_explicit(self):
  with self.assertRaises(ValueError):own_turn.findings('test','own',[dict(turn=2,source='test')],lambda _: 'wrong')

class BoundedGuard(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.job=Path(self.tmp.name);self.cues=[cue('次回ONEPIECE'),cue('四皇翻身布魯克救出大作戰',2,1)];self.first='下集ONEPIECE，布魯克救出大作戰！'
 def test_one_retry_off_controls_and_history(self):
  w=worker();before=copy.deepcopy(self.cues);out=own_turn.guard(w,config(),self.job,self.cues,0,'yue',self.first);self.assertEqual(out,'下集ONEPIECE');self.assertEqual(w.ollama_chat.call_count,1);self.assertEqual(w.ollama_chat.call_args.kwargs['max_attempts'],1)
  self.assertEqual(self.cues[0]['start'],before[0]['start']);self.assertEqual(self.cues[0]['primarySource'],before[0]['primarySource']);self.assertEqual(self.cues[0]['ownTurnDraftHistory'][0]['text'],self.first)
 def test_resume_reuses_accepted_without_model(self):
  w=worker();a=own_turn.guard(w,config(),self.job,self.cues,0,'yue',self.first);b=own_turn.guard(w,config(),self.job,self.cues,0,'yue',self.first);self.assertEqual(a,b);self.assertEqual(w.ollama_chat.call_count,1)
 def test_resume_keeps_saved_resolution_even_when_replayed_first_reply_changes(self):
  w=worker();a=own_turn.guard(w,config(),self.job,self.cues,0,'yue',self.first)
  b=own_turn.guard(w,config(),self.job,self.cues,0,'yue','下集ONEPIECE呀')
  self.assertEqual(a,b);self.assertEqual(w.ollama_chat.call_count,1)
 def test_speech_priority_does_not_retranslate_from_auxiliary_caption(self):
  w=worker();before=copy.deepcopy(self.cues)
  self.assertEqual(own_turn.guard(w,config(sourceContentPriority='speech',sourceWorkflowRevision=__import__('source_workflow').REVISION),self.job,self.cues,0,'yue',self.first),self.first)
  w.ollama_chat.assert_not_called();self.assertEqual(before,self.cues)
 def test_invalid_retry_retains_first_and_does_not_retry_again(self):
  w=worker('{"text":""}');self.assertEqual(own_turn.guard(w,config(),self.job,self.cues,0,'yue',self.first),self.first);self.assertEqual(own_turn.guard(w,config(),self.job,self.cues,0,'yue',self.first+'呀'),self.first);self.assertEqual(w.ollama_chat.call_count,1);self.assertTrue(self.cues[0]['translationWarnings'])
 def test_still_leaking_retry_retains_first(self):
  w=worker(json.dumps(dict(text=self.first)));self.assertEqual(own_turn.guard(w,config(),self.job,self.cues,0,'yue',self.first),self.first)
 def test_crash_after_reservation_never_refunds(self):
  from workflow_policy import reserve
  self.assertTrue(reserve(self.job,'own-turn-caption',['yue',0],1));w=worker();self.assertEqual(own_turn.guard(w,config(),self.job,self.cues,0,'yue',self.first),self.first);w.ollama_chat.assert_not_called()
 def test_malformed_reply_keeps_original_and_spent_limit(self):
  for raw in ['[]','null','17','{"text":null}','{"text":123}','not JSON']:
   with self.subTest(raw=raw),tempfile.TemporaryDirectory() as d:
    w=worker(raw);cs=copy.deepcopy(self.cues)
    self.assertEqual(own_turn.guard(w,config(),Path(d),cs,0,'yue',self.first),self.first)
    self.assertEqual(own_turn.guard(w,config(),Path(d),cs,0,'yue',self.first),self.first)
    self.assertEqual(w.ollama_chat.call_count,1);self.assertTrue(cs[0]['translationWarnings'])
 def test_model_error_is_nonfatal(self):
  w=worker();w.ollama_chat.side_effect=RuntimeError('fixture');self.assertEqual(own_turn.guard(w,config(),self.job,self.cues,0,'yue',self.first),self.first)
 def test_user_skip_propagates(self):
  from track_control import UserSkipped
  w=worker();w.ollama_chat.side_effect=UserSkipped()
  with self.assertRaises(UserSkipped):own_turn.guard(w,config(),self.job,self.cues,0,'yue',self.first)
 def test_saved_script_or_audio_is_never_changed(self):
  for patch_values in [dict(cantonese='已保存'),dict(preserveOriginalSpeech=True),dict(opEdKind='opening'),dict(enabled=False),dict(primarySource=dict(revision=REVISION,kind='speech',text='source'))]:
   cs=copy.deepcopy(self.cues);cs[0].update(patch_values);before=copy.deepcopy(cs);w=worker();self.assertEqual(own_turn.guard(w,config(),self.job,cs,0,'yue',self.first),self.first);self.assertEqual(before,cs);w.ollama_chat.assert_not_called()
 def test_legacy_request_is_not_restamped(self):
  w=worker();self.assertEqual(own_turn.guard(w,{},self.job,self.cues,0,'yue',self.first),self.first);w.ollama_chat.assert_not_called()
 def test_window_excludes_far_caption(self):
  self.cues[1].update(start=100,end=101);w=worker();self.assertEqual(own_turn.guard(w,config(),self.job,self.cues,0,'yue',self.first),self.first);w.ollama_chat.assert_not_called()
 def test_actual_native_hans_hant_conversion(self):
  exe=ROOT/'dist/AniCanto.app/Contents/MacOS/AniCanto-worker'
  if not exe.exists():self.skipTest('Mac converter is unavailable')
  self.cues[1]['primarySource']['text']='四皇翻身布鲁克救出大作战';w=worker();self.assertEqual(own_turn.guard(w,config(executable=str(exe)),self.job,self.cues,0,'yue',self.first),'下集ONEPIECE')
 def test_fast_translation_hook_runs_before_selected_text_saved(self):
  import fast_mode
  cs=copy.deepcopy(self.cues);w=worker(json.dumps({'0':self.first,'1':'四皇翻身，布魯克救出大作戰！'}));w.ollama_chat.side_effect=[w.ollama_chat.return_value,'{"text":"下集ONEPIECE"}'];w.traditional_cantonese=lambda c,t:t
  with patch('script_fit.fit'),patch('draft_length.apply'),patch('draft_length.instruction',return_value=''):
   fast_mode.translate(w,dict(config(),productionMode='fast',dubLanguages=['yue'],subtitleModes=['yue']),self.job,cs)
  self.assertEqual(cs[0]['cantonese'],'下集ONEPIECE');self.assertEqual(w.ollama_chat.call_count,2)

if __name__=='__main__':unittest.main()

class EntryPoints(unittest.TestCase):
 def test_normal_initial_draft_correction_is_saved_once(self):
  import normal_mode
  with tempfile.TemporaryDirectory() as d:
   cs=[cue('次回ONEPIECE'),cue('四皇翻身布魯克救出大作戰',2,1)]
   w=worker();w.ollama_chat.side_effect=[json.dumps({'0':'下集ONEPIECE，布魯克救出大作戰！','1':'四皇翻身，布魯克救出大作戰！'}),'{"text":"下集ONEPIECE"}']
   with patch.object(normal_mode,'glossary',return_value=[]),patch('draft_length.apply'),patch('draft_length.instruction',return_value=''):
    normal_mode.translate(w,config(dubLanguages=['yue'],subtitleModes=[]),Path(d),cs)
   self.assertEqual(cs[0]['cantonese'],'下集ONEPIECE');self.assertEqual(w.ollama_chat.call_count,2)
 def test_add_language_cache_reuses_corrected_take_script(self):
  import dub_languages
  for language in ['en','zh']:
   with self.subTest(language=language),tempfile.TemporaryDirectory() as d:
    if language=='en':
     cs=[cue('Next episode'),cue('Brook rescue mission',2,1)];first={'0':'Next episode Brook rescue mission','1':'Brook rescue mission'};correct='Next episode';field='english';fn=dub_languages.english_script
    else:
     cs=[cue('下集ONEPIECE'),cue('布鲁克救出大作战',2,1)];first={'0':'下集ONEPIECE，布鲁克救出大作战','1':'布鲁克救出大作战'};correct='下集ONEPIECE';field='mandarin';fn=dub_languages.mandarin_script
    w=worker();w.ollama_chat.side_effect=[json.dumps(first),json.dumps({'text':correct})]
    with patch('draft_length.apply'),patch('draft_length.instruction',return_value=''),patch('output_language.simplified',side_effect=lambda c,t:t),patch('english_overlap.repair'):
     fn(w,config(),Path(d),cs);self.assertEqual(cs[0][field],correct);self.assertEqual(w.ollama_chat.call_count,2)
     fn(w,config(),Path(d),cs);self.assertEqual(w.ollama_chat.call_count,2)
 def test_all_languages_report_warning_without_changing_export_success(self):
  import fast_mode
  for language,tag in [('yue','yue'),('en','eng'),('zh','zho')]:
   with self.subTest(language=language),tempfile.TemporaryDirectory() as d:
    cs=[cue('source',translationWarnings=[dict(stage='own-turn-caption')])];meta=dict(format=dict(duration='1.0'),streams=[dict(codec_type='video'),dict(codec_type='audio',tags=dict(language=tag)),dict(codec_type='subtitle')]);run=Mock(side_effect=[json.dumps(meta),''])
    result=fast_mode.validation(config(targetLanguage=language,productionMode='fast',ffprobe='fixture',ffmpeg='fixture',duration=1),Path(d),cs,'output',run,Mock())
    self.assertEqual(result['structuralStatus'],'passed');self.assertEqual(result['scriptReviewIndices'],[1]);self.assertEqual(run.call_count,2)
