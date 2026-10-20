import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import ai_result_repair as ai
import role_voice_fallback as role
import test_ai_result_repair as fixture
from test_ai_result_repair import write,wav

class RoleVoiceFallbackTests(unittest.TestCase):
 def test_card_choice_survives_failed_original_without_changing_card(self):
  profile=dict(id='actor',name='角色',reference='/missing-original.wav',promptText='日本語',language='ja',naturalVoices={'yue':'yue-low'},engineReferences={'cosyvoice3:yue':dict(enabled=True,reference='/also-missing.wav')})
  cfg=dict(voiceProfiles=[profile],ttsBackend='cosyvoice3',targetLanguage='yue',voiceStyleMode='clone')
  before=copy.deepcopy(cfg);settings,chosen=role.settings_for(cfg,dict(speakerId='actor'))
  self.assertEqual(chosen['naturalReferenceId'],'yue-low');self.assertTrue(Path(chosen['reference']).is_file())
  self.assertEqual(chosen['id'],'actor');self.assertEqual(chosen['language'],'yue')
  self.assertEqual(settings['ttsBackend'],'cosyvoice3');self.assertEqual(cfg,before)
  self.assertFalse(settings['aiAutoFix']);self.assertFalse(settings['fallbackToRoleVoice'])

 def test_reference_variation_keeps_engine_role_language_and_explicit_card_choice(self):
  cfg=dict(voiceProfiles=[dict(id='actor',name='角色',naturalVoices={'yue':'yue-low'})],ttsBackend='drama3',targetLanguage='yue')
  with self.assertRaisesRegex(ValueError,'指定後備聲線'):role.settings_for(cfg,dict(speakerId='actor'),variant=1)
  cfg['voiceProfiles'][0]['naturalVoices']={};before=copy.deepcopy(cfg)
  first=role.settings_for(cfg,dict(speakerId='actor'))[1]
  settings,other=role.settings_for(cfg,dict(speakerId='actor'),variant=1)
  self.assertNotEqual(first['naturalReferenceId'],other['naturalReferenceId'])
  self.assertEqual(other['id'],'actor');self.assertEqual(other['language'],'yue');self.assertEqual(settings['ttsBackend'],'drama3');self.assertEqual(cfg,before)

 def test_role_analysis_failure_keeps_every_line_clock_and_stable_card(self):
  cfg=dict(fallbackToRoleVoice=True,targetLanguage='yue',voiceProfiles=[dict(id='actor',name='人物',naturalVoices={'yue':'yue-low'})])
  cues=[dict(start=1.,end=2.,japanese='行こう',cantonese='出發啦',speakerId='actor'),dict(start=4.,end=5.,japanese='帰ろう',cantonese='返去啦',speakerId='actor')]
  before=copy.deepcopy(cues);result=role.assign(cfg,cues,ValueError('人物模型失敗'),Mock())
  self.assertEqual([(c['start'],c['end'],c['cantonese'],c['speakerId']) for c in result],[(c['start'],c['end'],c['cantonese'],c['speakerId']) for c in before])
  self.assertEqual(len(cfg['voiceProfiles']),1);self.assertEqual(cfg['voiceProfiles'][0]['naturalReferenceId'],'yue-low')

 def test_full_export_recovers_reference_failure_or_refuses_missing_delivery(self):
  import shutil,subprocess
  from types import SimpleNamespace
  import multitrack,worker
  ffmpeg=shutil.which('ffmpeg');ffprobe=shutil.which('ffprobe')
  if not ffmpeg or not ffprobe:self.skipTest('FFmpeg unavailable')
  def run(args):return subprocess.check_output([str(x) for x in args],stderr=subprocess.PIPE)
  for recovered in (True,False):
   with self.subTest(recovered=recovered),tempfile.TemporaryDirectory() as d:
    root=Path(d);audio=wav(root/'voice.wav',seconds=2.);video=root/'source.mp4'
    run([ffmpeg,'-v','error','-y','-f','lavfi','-i','color=s=64x64:r=10:d=2','-i',audio,'-c:v','libx264','-c:a','aac','-t','2',video])
    cfg=dict(storage=str(root/'storage'),video=str(video),duration=2.,ffmpeg=ffmpeg,ffprobe=ffprobe,selectedEngines=['cosyvoice3'],ttsBackend='cosyvoice3',cosyModel='cosy-0.5b-8bit',dubLanguages=['yue'],subtitleOutput='yue',includeOriginal=True,aiAutoFix=False,fallbackToRoleVoice=True,requireCompleteDubbing=True)
    cue=dict(start=0.,end=1.,text='出発しよう',japanese='出発しよう',cantonese='出發啦',speakerId='actor')
    review=root/'review.json';write(review,dict(config=cfg,cues=[cue],meta=dict(streams=[dict(codec_type='video'),dict(codec_type='audio')])))
    w=SimpleNamespace(run=run,atomic_json=write,emit=Mock(),render_review=Mock(side_effect=ValueError('角色參考未符合要求')),ollama_chat=Mock(),parse_srt=worker.parse_srt,save_srt=worker.save_srt)
    with patch.object(ai,'retake',side_effect=self.donor if recovered else ValueError('後備生成失敗')):
     if recovered:multitrack.render(w,dict(review=str(review)))
     else:
      with self.assertRaisesRegex(ValueError,'未交付不完整成品'):multitrack.render(w,dict(review=str(review)))
    w.ollama_chat.assert_not_called()
    if recovered:
     report=json.loads((root/'report.json').read_text())
     self.assertEqual(report['failedEngines'],{});self.assertIn('cosyvoice3',report['originalFailedEngines'])
     self.assertEqual(report['dialogueDelivery']['status'],'audio-present')
     self.assertEqual(report['aiAutoFix']['repaired'],1)
     self.assertFalse([c for c in w.emit.call_args_list if c.args[0]=='完成'][-1].kwargs['partial'])
    else:
     self.assertFalse(any(c.args[0]=='完成' for c in w.emit.call_args_list))
     self.assertEqual(json.loads((root/'dialogue-delivery-audit.json').read_text())['status'],'missing-dialogue')

 def setup_track(self,root):
  helper=fixture.ResultRepairTests();track=helper.track(root);worker=helper.worker({})
  track['report']['failureReason']='角色參考未符合要求'
  return track,worker

 def donor(self,w,cfg,track,row,folder):
  folder.mkdir(parents=True,exist_ok=True);audio=wav(folder/'good.wav')
  write(folder/'timing.json',[dict(index=row['index'],start=0.,end=1.,renderedAudio=str(audio),renderedSeconds=.8,text=row['approvedText'],speakerId='actor')])
  write(folder/'validation.json',{})
  write(folder/'final-speech-check.json',dict(rows=[dict(index=1,textMatches=True,requiresReview=False,languageMismatch=False,languageUnverified=False)]))
  import hashlib
  return dict(engine=track['engine'],language=track['language'],folder=folder,id=track['id'],report={},audioSHA=hashlib.sha256(audio.read_bytes()).hexdigest(),roleVoiceFallback='yue-low')

 def test_reference_failure_uses_card_without_qwen_and_reuses_verified_result(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);track,worker=self.setup_track(root);before=(track['folder']/'review.json').read_bytes()
   with patch.object(ai,'retake',side_effect=self.donor) as generate:
    cfg=dict(duration=2.,fallbackToRoleVoice=True)
    donors,result=ai.run(worker,cfg,root,[track]);again,result2=ai.run(worker,cfg,root,[track])
   generate.assert_called_once();worker.ollama_chat.assert_not_called()
   self.assertEqual(generate.call_args.args[3]['action'],'role-voice')
   self.assertEqual(result['rows'][0]['status'],'verified');self.assertEqual(result2['rows'][0]['status'],'verified')
   self.assertEqual(donors[0]['engine'],track['engine']);self.assertEqual(len(again),1)
   self.assertEqual((track['folder']/'review.json').read_bytes(),before)

 def test_failing_fallback_is_not_silence_success_or_an_infinite_retry(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);track,worker=self.setup_track(root)
   with patch.object(ai,'retake',side_effect=ValueError('後備台詞驗證失敗')) as generate:
    for i in range(2):
     donors,result=ai.run(worker,dict(duration=2.,fallbackToRoleVoice=True),root,[track])
     self.assertEqual(donors,[]);self.assertEqual(result['rows'][0]['status'],'unresolved')
   generate.assert_called_once()

 def test_missing_line_uses_distinct_bounded_seeds_and_resumes_without_regeneration(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);track,worker=self.setup_track(root)
   attempts=[]
   def recover(w,cfg,track,row,folder):
    attempts.append(row.get('recoveryAttempt',0))
    if row.get('recoveryAttempt',0)<3:raise ValueError('重錄未通過同稿及目標語言核對，未採用。')
    return self.donor(w,cfg,track,row,folder)
   with patch.object(ai,'retake',side_effect=recover):
    donors,result=ai.run(worker,dict(duration=2.,fallbackToRoleVoice=True),root,[track])
    again,resumed=ai.run(worker,dict(duration=2.,fallbackToRoleVoice=True),root,[track])
   self.assertEqual(attempts,[0,1,2,3]);self.assertEqual(len(donors),1);self.assertEqual(len(again),1)
   self.assertEqual(result['rows'][0]['status'],'verified');self.assertEqual(resumed['rows'][0]['status'],'verified')
   worker.ollama_chat.assert_not_called()

 def test_six_rejected_generations_are_recorded_once_and_never_faked_as_success(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);track,worker=self.setup_track(root)
   with patch.object(ai,'retake',side_effect=ValueError('重錄未通過同稿及目標語言核對，未採用。')) as generate:
    for _ in range(2):
     donors,result=ai.run(worker,dict(duration=2.,fallbackToRoleVoice=True),root,[track])
     self.assertEqual(donors,[]);self.assertEqual(result['rows'][0]['status'],'unresolved')
   self.assertEqual(generate.call_count,6)

 def test_drama_cap_recovery_reaches_distinct_whole_turn_strategy_and_reuses_verified_work(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);track,worker=self.setup_track(root);track['engine']='drama3';track['id']='drama3'
   seen=[]
   def recover(w,cfg,track,row,folder):
    seen.append((row['recoveryAttempt'],row.get('fallbackStyle'),row.get('referenceVariant')))
    if row.get('fallbackStyle')!='plain-whole':raise ValueError('generation-limit')
    return self.donor(w,cfg,track,row,folder)
   with patch.object(ai,'retake',side_effect=recover):
    first,result=ai.run(worker,dict(duration=2.,fallbackToRoleVoice=True),root,[track])
    second,resumed=ai.run(worker,dict(duration=2.,fallbackToRoleVoice=True),root,[track])
   self.assertEqual(len(seen),7);self.assertEqual(seen[-1],(6,'plain-whole',0))
   self.assertEqual(len(first),1);self.assertEqual(len(second),1)
   self.assertEqual(result['rows'][0]['status'],'verified');self.assertEqual(resumed['rows'][0]['status'],'verified')
   worker.ollama_chat.assert_not_called()

 def test_check_unavailable_is_a_summary_warning_without_model_decision(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);helper=fixture.ResultRepairTests();track=helper.track(root);worker=helper.worker({})
   audio=wav(track['folder']/'healthy.wav')
   write(track['folder']/'timing.json',[dict(index=1,start=0.,end=1.,renderedSeconds=.8,renderedAudio=str(audio))])
   write(track['folder']/'validation.json',dict(verificationError='ASR unavailable',voiceReviewIndices=[1],levelReviewIndices=[1]))
   with patch.object(ai,'retake') as generate:_,result=ai.run(worker,dict(duration=2.),root,[track])
   result=ai.finish(worker,root,[track],result)
   generate.assert_not_called();worker.ollama_chat.assert_not_called()
   self.assertEqual(result['warnings'],1);self.assertEqual(result['unresolved'],0)

 def test_locale_rules_apply_to_writing_and_edits_without_touching_input(self):
  from hong_kong_dialogue import RULES,localize_messages
  original=[dict(role='system',content='改成自然廣東話口語。'),dict(role='user',content='廣東話是一項資料')]
  before=copy.deepcopy(original);result=localize_messages(original)
  self.assertIn('yue-HK',result[0]['content']);self.assertIn('角色感',result[0]['content'])
  self.assertEqual(result[1],original[1]);self.assertEqual(original,before)
  self.assertEqual(localize_messages(result),result)
  english=[dict(role='system',content='Translate into natural English.')]
  self.assertEqual(localize_messages(english),english)

 def test_optional_model_unavailable_does_not_make_network_request(self):
  worker=fixture.ResultRepairTests().worker({})
  with tempfile.TemporaryDirectory() as d:
   row=dict(index=1,allowedActions=['keep','retry'])
   result=ai.decisions(worker,dict(aiDecisionUnavailable=True),Path(d),[row],'log')
  worker.ollama_chat.assert_not_called();self.assertTrue(result[0]['analysisFailed'])

 def test_delivered_fallback_uses_local_slot_but_keeps_source_timing(self):
  import subprocess,wave
  from types import SimpleNamespace
  ffmpeg=Path(__file__).parents[1]/'dist/AniCanto.app/Contents/Resources/bin/ffmpeg'
  if not ffmpeg.is_file():self.skipTest('Bundled FFmpeg unavailable')
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);helper=fixture.ResultRepairTests();track=helper.track(root)
   review=json.loads((track['folder']/'review.json').read_text());cue=review['cues'][0]
   cue.update(start=100.,end=104.,speechStart=101.,speechEnd=102.)
   review['config'].update(duration=1400.,ffmpeg=str(ffmpeg),voiceStyleMode='clone',voiceProfiles=[dict(id='actor',name='角色',reference='/missing.wav',promptText='日本語',language='ja',naturalVoices={'yue':'yue-low'})])
   write(track['folder']/'review.json',review)
   def synthesize(cfg,job,cues,run,emit):
    self.assertEqual(cfg['duration'],1.);self.assertEqual(cues[0]['start'],0.)
    self.assertTrue(cfg['strictSpeechTiming'])
    self.assertFalse(cfg['autoFit']);self.assertEqual(cues[0]['cantonese'],'出發啦')
    audio=wav(job/'cantonese.wav',seconds=1.)
    write(job/'timing.json',[dict(audio=str(audio),renderedSeconds=1.)])
   def run(command):return subprocess.check_output([str(x) for x in command],stderr=subprocess.PIPE)
   w=SimpleNamespace(run=run,emit=Mock(),atomic_json=write)
   check=dict(textMatches=True,requiresReview=False,languageMismatch=False,languageUnverified=False)
   with patch('dubbing.synthesize',side_effect=synthesize),patch('speechcheck.inspect',return_value=[check]):
    donor=ai.retake(w,dict(duration=1400.),track,dict(index=1,action='role-voice'),root/'fallback')
   timed=json.loads((donor['folder']/'timing.json').read_text())[0]
   self.assertEqual(timed['start'],100.);self.assertEqual(timed['end'],104.)
   self.assertEqual(timed['renderedStart'],101.);self.assertEqual(timed['renderedSeconds'],1.)
   self.assertEqual(donor['roleVoiceFallback'],'yue-low')

class ContentDeliveryFallbackTests(unittest.TestCase):
 def test_present_but_clearly_wrong_speech_uses_role_fallback_without_qwen_veto(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);helper=fixture.ResultRepairTests();track=helper.track(root);w=helper.worker({})
   review=json.loads((track['folder']/'review.json').read_text());cue=review['cues'][0];cue['cantonese']='我哋一齊出發去東京'
   write(track['folder']/'review.json',review);path=wav(track['folder']/'wrong.wav')
   write(track['folder']/'timing.json',[dict(index=1,start=0.,end=1.,renderedSeconds=.8,renderedAudio=str(path),text=cue['cantonese'],speakerId='actor')])
   write(track['folder']/'final-speech-check.json',dict(rows=[dict(index=1,expected=cue['cantonese'],heard='別の日本語',similarity=.1,languageMismatch=True,languageUnverified=False,requiresReview=True,textMatches=False,detectedLanguage='japanese',cantoneseReviewPolicy=__import__('cantonese_review').REVISION,confirmedContentFailure=True,independentCheck=dict(heard='別の日本語',detectedLanguage='japanese'))]))
   rows=ai.collect(track,[track]);self.assertFalse(rows[0]['missing']);self.assertTrue(rows[0]['contentFailure'])
   calls=[];donor_helper=RoleVoiceFallbackTests()
   def retake(worker,cfg,t,row,folder):
    calls.append(row['action'])
    if row['action']!='role-voice':raise ValueError('原聲模仿仍係錯誤語言')
    return donor_helper.donor(worker,cfg,t,row,folder)
   with patch.object(ai,'retake',side_effect=retake):
    donors,result=ai.run(w,dict(duration=2.,fallbackToRoleVoice=True,aiDecisionUnavailable=True),root,[track],missing_only=True)
    again,result2=ai.run(w,dict(duration=2.,fallbackToRoleVoice=True,aiDecisionUnavailable=True),root,[track],missing_only=True)
   self.assertEqual(calls,['retry','role-voice']);self.assertEqual(len(donors),1);self.assertEqual(len(again),1)
   self.assertTrue(result['rows'][0]['contentFailure']);self.assertEqual(result['rows'][0]['status'],'verified')
   w.ollama_chat.assert_not_called()
 def test_short_name_language_label_alone_does_not_force_role_replacement(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);helper=fixture.ResultRepairTests();track=helper.track(root)
   path=wav(track['folder']/'short.wav')
   write(track['folder']/'timing.json',[dict(index=1,start=0.,end=1.,renderedSeconds=.8,renderedAudio=str(path))])
   write(track['folder']/'validation.json',dict(languageReviewIndices=[1]))
   write(track['folder']/'final-speech-check.json',dict(rows=[dict(index=1,expected='出發啦',heard='ジャパ',similarity=.1,languageMismatch=True,requiresReview=True)]))
   row=ai.collect(track,[track])[0];self.assertFalse(row['contentFailure']);self.assertFalse(row['missing'])
