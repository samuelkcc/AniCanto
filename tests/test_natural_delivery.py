import array,copy,json,math,shutil,subprocess,sys,tempfile,unittest,wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import concise_dialogue as concise,natural_delivery,fast_mode,speech_timing,normal_mode,dubbing,worker


def audio(path,seconds):
 sr=24000
 with wave.open(str(path),'wb') as f:
  f.setparams((1,2,sr,0,'NONE','not compressed'))
  f.writeframes(array.array('h',(round(3500*math.sin(i*.071)) for i in range(round(sr*seconds)))).tobytes())
 return path

class NaturalDeliveryTests(unittest.TestCase):
 def test_semantic_omission_is_rejected_and_failed_request_is_not_repeated(self):
  cue=dict(start=0,end=1,japanese='門を開けるな',english="Do not open the gate, whatever you do.")
  w=SimpleNamespace(ollama_chat=Mock(return_value='{"0":"Open the gate."}'),atomic_json=worker.atomic_json)
  with tempfile.TemporaryDirectory() as d,patch('semantic_review.audit',return_value={'0':dict(faithful=False)}):
   self.assertEqual(concise.compact(w,dict(port=1,model='m',targetLanguage='en'),d,[cue],[0],{0:4}),[])
   self.assertEqual(concise.compact(w,dict(port=1,model='m',targetLanguage='en'),d,[cue],[0],{0:4}),[])
   self.assertEqual(w.ollama_chat.call_count,1)
  self.assertTrue(cue['english'].startswith('Do not'))
 def test_numeric_and_name_loss_rejected_even_if_model_verdict_is_positive(self):
  for before,after,names in [('Bring 2 keys to Roger.','Bring keys.',[dict(english='Roger')]),('Please take Roger there.','Take him there.',[dict(english='Roger')])]:
   with self.subTest(before=before),tempfile.TemporaryDirectory() as d,patch('semantic_review.audit',return_value={'0':dict(faithful=True)}):
    c=dict(english=before,japanese='source');w=SimpleNamespace(ollama_chat=Mock(return_value=json.dumps({'0':after})),atomic_json=worker.atomic_json)
    self.assertEqual(concise.compact(w,dict(model='m',port=1,targetLanguage='en',normalNameGlossary=names),d,[c],[0],{0:3}),[])
    self.assertEqual(c['english'],before)
 def test_verified_concise_english_is_cached_and_keeps_original(self):
  original=dict(english='I would like you to come with me now.',japanese='一緒に来て',start=0,end=1)
  w=SimpleNamespace(ollama_chat=Mock(return_value='{"0":"Come with me."}'),atomic_json=worker.atomic_json)
  with tempfile.TemporaryDirectory() as d,patch('semantic_review.audit',return_value={'0':dict(faithful=True)}):
   a=copy.deepcopy(original);b=copy.deepcopy(original)
   self.assertEqual(concise.compact(w,dict(model='m',port=1,targetLanguage='en'),d,[a],[0],{0:3}),[0])
   self.assertEqual(concise.compact(w,dict(model='m',port=1,targetLanguage='en'),d,[b],[0],{0:3}),[0])
   self.assertEqual(w.ollama_chat.call_count,1);self.assertEqual(a['english'],'Come with me.')
   self.assertEqual(a['preConciseEnglish'],original['english']);self.assertEqual(a['start'],0)
 def test_next_timing_retry_uses_a_different_approved_phrasing_without_repeating_text_ai(self):
  original=dict(start=0,end=2,japanese='ついて来て',english='Please come along with me now.')
  w=SimpleNamespace(ollama_chat=Mock(return_value=json.dumps({'0':['Follow me.','Come with me.']})),atomic_json=worker.atomic_json)
  with tempfile.TemporaryDirectory() as d,patch('semantic_review.audit',return_value={'0:0':dict(faithful=True),'0:1':dict(faithful=True)}):
   a=copy.deepcopy(original);b=copy.deepcopy(original)
   self.assertEqual(concise.compact(w,dict(model='m',port=1,targetLanguage='en'),d,[a],[0],{0:3}),[0])
   self.assertEqual(concise.compact(w,dict(model='m',port=1,targetLanguage='en'),d,[b],[0],{0:3},alternative_index=1),[0])
   self.assertEqual(a['english'],'Follow me.');self.assertEqual(b['english'],'Come with me.');self.assertEqual(w.ollama_chat.call_count,1)
 def test_shortening_cannot_turn_the_affected_person_into_the_object_even_with_ai_approval(self):
  cue=dict(start=0,end=2,japanese='抵抗できない',cantonese='對媽媽嘅生命卡完全冇抵抗力')
  w=SimpleNamespace(ollama_chat=Mock(return_value=json.dumps({'0':['媽媽嘅生命卡完全冇抵抗力','對媽媽生命卡完全冇抵抗力']})),atomic_json=worker.atomic_json)
  with tempfile.TemporaryDirectory() as d,patch('semantic_review.audit',return_value={'0:0':dict(faithful=True),'0:1':dict(faithful=True)}):
   self.assertEqual(concise.compact(w,dict(model='m',port=1,targetLanguage='yue'),d,[cue],[0],{0:10}),[0])
   self.assertEqual(cue['cantonese'],'對媽媽生命卡完全冇抵抗力')
 def test_grounded_semantic_failure_gets_one_source_only_correction(self):
  cue=dict(start=0,end=2,japanese='存分に使うわ',cantonese='我會好好利用呢張卡。')
  w=SimpleNamespace(ollama_chat=Mock(side_effect=[json.dumps({'0':['呢張卡我會用盡。']}),json.dumps({'0':['我會好好用佢。']})]),atomic_json=worker.atomic_json)
  defect=dict(kind='addition',source_quote='存分に使うわ',candidate_quote='呢張卡',explanation='The own source has an unspecified object, no card.')
  with tempfile.TemporaryDirectory() as d,patch('semantic_review.audit',side_effect=[{'0:0':dict(faithful=False,groundedDefects=[defect])},{'0:feedback0':dict(faithful=True)}]):
   self.assertEqual(concise.compact(w,dict(model='m',port=1,targetLanguage='yue'),d,[cue],[0],{0:7}),[0])
   self.assertEqual(cue['cantonese'],'我會好好用佢。');self.assertEqual(w.ollama_chat.call_count,2)
   correction=json.loads(w.ollama_chat.call_args.args[2][1]['content'])['0'];self.assertNotIn('current',correction);self.assertNotIn('draft',correction)
 def test_even_positive_ai_verdict_cannot_import_the_next_standalone_name(self):
  cues=[dict(start=0,end=2,japanese='使わせてもらうわ',asrConfidence=.98,cantonese='我會好好用，蘿拉。',subtitleHint='我會好好用 羅拉'),dict(start=2,end=3,japanese='ローラ',cantonese='蘿拉。',subtitleHint='我會好好用 羅拉')]
  w=SimpleNamespace(ollama_chat=Mock(return_value=json.dumps({'0':['用盡，蘿拉。','我會好好用。']})),atomic_json=worker.atomic_json)
  with tempfile.TemporaryDirectory() as d,patch('semantic_review.audit',return_value={'0:owned':dict(faithful=True),'0:0':dict(faithful=True),'0:1':dict(faithful=True)}):
   concise.compact(w,dict(model='m',port=1,targetLanguage='yue',normalNameGlossary=[dict(source='ローラ',cantonese='蘿拉')]),d,cues,[0],{0:6})
   self.assertNotIn('蘿拉',cues[0]['cantonese']);self.assertEqual(cues[1]['cantonese'],'蘿拉。')
   sent=json.loads(w.ollama_chat.call_args.args[2][1]['content'])['0'];self.assertEqual(sent['source']['caption'],'');self.assertEqual(sent['neighbour_context_only'],[])
 def test_uncertain_source_and_genuine_repeated_name_do_not_authorize_suffix_removal(self):
  glossary=[dict(source='ローラ',cantonese='蘿拉')]
  for source,score,reasons in [('ローラ、使うわ',.98,[]),('使うわ',.4,['uncertain source'])]:
   cues=[dict(japanese=source,cantonese='我會用，蘿拉。',subtitleHint='我會用 蘿拉',asrConfidence=score,sourceReviewReasons=reasons),dict(japanese='ローラ',cantonese='蘿拉。',subtitleHint='我會用 蘿拉')]
   self.assertIsNone(concise.unowned_suffix(cues,0,cues[0]['cantonese'],glossary,'yue'))
 def test_three_alternatives_select_shortest_verified_own_turn_and_remove_added_neighbour_name(self):
  cues=[dict(start=0,end=2,japanese='存分に使わせてもらうわよ',asrConfidence=.98,cantonese='我會好好利用呢張卡，蘿拉。',subtitleHint='我會好好利用的哦 蘿拉'),dict(start=2.3,end=3,japanese='ローラ',cantonese='蘿拉。',subtitleHint='我會好好利用的哦 蘿拉')]
  w=SimpleNamespace(ollama_chat=Mock(return_value=json.dumps({'0':['用得好。','我會好好用。','我會好好利用。']})),atomic_json=worker.atomic_json)
  verdict={'0:0':dict(faithful=False),'0:1':dict(faithful=True),'0:2':dict(faithful=True)}
  with tempfile.TemporaryDirectory() as d,patch('semantic_review.audit',return_value=verdict) as audit:
   changed=concise.compact(w,dict(model='m',port=1,targetLanguage='yue',normalNameGlossary=[dict(source='ローラ',cantonese='蘿拉')]),d,cues,[0],{0:6})
   self.assertEqual(changed,[0]);self.assertEqual(cues[0]['cantonese'],'我會好好用。');self.assertEqual(cues[1]['cantonese'],'蘿拉。')
   self.assertEqual(len(audit.call_args.args[1]),4)
   self.assertEqual(json.loads((Path(d)/'concise-dialogue.json').read_text()).popitem()[1]['alternatives'][0]['accepted'],False)
 def test_empty_gap_can_be_used_without_crossing_next_line_or_opening(self):
  cues=[dict(start=0,end=.6),dict(start=1.4,end=2)]
  self.assertEqual(speech_timing.natural_window(cues[0],cues,2), (0,1.4))
  cfg=dict(opRanges=[dict(start=1.,end=1.3)],startOffset=0,duration=2)
  self.assertEqual(speech_timing.natural_window(cues[0],cues,2,cfg),(0,1.))
  overlapping=[dict(start=0,end=2),dict(start=1,end=3)]
  self.assertEqual(speech_timing.natural_window(overlapping[0],overlapping,3),(0,2))
 def test_human_editor_never_gets_automatic_wording_changes(self):
  with patch('dubbing.gsv_audio') as tts:
   self.assertEqual(natural_delivery.repair(dict(editorRender=True,automaticDurationRewrite=True),Path('.'),[],['take'],Mock(),Mock()),['take'])
   tts.assert_not_called()
 def test_first_take_preference_keeps_audible_recording_for_later_timing_recovery(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);first=audio(job/'first.wav',1.4)
   cue=dict(start=0,end=1,japanese='行こう',cantonese='出發啦。')
   cfg=dict(duration=2,automaticDurationRewrite=True,preferFirstAudibleTake=True,normalRepairPolicy='verified',productionMode='normal',targetLanguage='yue')
   with patch('dubbing.gsv_audio',side_effect=AssertionError('Unrequested rewrite')):
    self.assertEqual(natural_delivery.repair(cfg,job,[cue],[first],Mock(),Mock()),[first])
   self.assertEqual(cue['cantonese'],'出發啦。')
 @unittest.skipUnless(shutil.which('ffmpeg'),'FFmpeg required')
 def test_measured_long_line_only_is_rewritten_at_rate_one_and_resume_reuses_take(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);long=audio(job/'long.wav',1.5);short=audio(job/'short.wav',.4);healthy=audio(job/'healthy.wav',.4)
   original=[dict(start=0,end=.7,japanese='来て',cantonese='I would like you to come here.',speakerId='own-1'),dict(start=.7,end=1.5,japanese='はい',cantonese='Yes.',speakerId='own-2')]
   cfg=dict(duration=1.5,speechRatePolicy='natural',automaticDurationRewrite=True,preferFirstAudibleTake=False,normalRepairPolicy='verified',productionMode='normal',targetLanguage='en',ttsBackend='drama3',model='m',port=1,ffmpeg=shutil.which('ffmpeg'))
   calls=[]
   def run(args):calls.append(args);return subprocess.check_output([str(x) for x in args],stderr=subprocess.PIPE)
   def generate(c,folder,cues,*args):
    if len(cues)==2:return [long,healthy]
    self.assertEqual(cues[0]['speakerId'],'own-1');return [short]
   with patch('dubbing.gsv_audio',side_effect=generate) as tts,patch.object(worker,'ollama_chat',return_value='{"0":"Come here."}'),patch('semantic_review.audit',return_value={'0':dict(faithful=True)}),patch('normal_mode.repair_paths',side_effect=lambda cfg,job,cues,paths,*args:paths),patch('normal_mode.inspect',return_value={}):
    for _ in range(2):
     cues=copy.deepcopy(original);output,warnings=fast_mode.synthesize(dict(cfg),job,cues,run,Mock())
     rows=json.loads((job/'timing.json').read_text())
     self.assertEqual([r['rate'] for r in rows],[1.,1.]);self.assertEqual(cues[0]['cantonese'],'Come here.')
     self.assertEqual(cues[1],original[1]);self.assertFalse(any(r['skipped'] for r in rows))
     self.assertLessEqual(rows[0]['renderedEnd'],.7)
    self.assertEqual(tts.call_count,3,'Resume generated the edited line again')
   self.assertFalse(any('atempo=' in ' '.join(map(str,c)) for c in calls))
   self.assertAlmostEqual(natural_delivery.seconds(long,cfg,run),1.5)
 def test_many_changed_lines_share_one_engine_load_and_keep_their_own_references(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);old=[audio(job/f'old-{i}.wav',1.4) for i in range(3)];new=[audio(job/f'new-{i}.wav',.5) for i in range(3)]
   original=[dict(start=i,end=i+1,japanese='行こう',cantonese='I would like you to come here.',speakerId=f'own-{i}',reviewIndex=i+20) for i in range(3)]
   cfg=dict(duration=3,speechRatePolicy='natural',automaticDurationRewrite=True,preferFirstAudibleTake=False,normalRepairPolicy='verified',productionMode='normal',targetLanguage='en',ttsBackend='drama3',model='m',port=1)
   def generate(c,folder,rows,*args):
    self.assertEqual([r['speakerId'] for r in rows],['own-0','own-1','own-2'])
    self.assertEqual([r['reviewIndex'] for r in rows],[20,21,22]);return new
   with patch('dubbing.gsv_audio',side_effect=generate) as tts,patch.object(worker,'ollama_chat',return_value=json.dumps({str(i):'Come here.' for i in range(3)})),patch('semantic_review.audit',return_value={str(i):dict(faithful=True) for i in range(3)}),patch('normal_mode.inspect',return_value={}) as listen:
    for _ in range(2):
     cues=copy.deepcopy(original)
     self.assertEqual(natural_delivery.repair(cfg,job,cues,old,Mock(),Mock()),new)
     self.assertEqual([c['cantonese'] for c in cues],['Come here.']*3)
    self.assertEqual(tts.call_count,1,'Each changed line reloaded the engine or resume repeated synthesis')
    self.assertEqual(len(listen.call_args.args[2]),3)
 def test_wrong_language_shortened_candidate_is_not_adopted(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);old=audio(job/'old.wav',1.4);new=audio(job/'new.wav',.5)
   cue=dict(start=0,end=1,japanese='行こう',cantonese='I would like you to come here.',reviewIndex=41)
   cfg=dict(duration=1,automaticDurationRewrite=True,normalRepairPolicy='verified',productionMode='normal',targetLanguage='en',model='m',port=1)
   with patch('dubbing.gsv_audio',return_value=[new]),patch.object(worker,'ollama_chat',return_value='{"0":"Come here."}'),patch('semantic_review.audit',return_value={'0':dict(faithful=True)}),patch('normal_mode.inspect',return_value={42:dict(decision='japanese')}):
    self.assertEqual(natural_delivery.repair(cfg,job,[cue],[old],Mock(),Mock()),[old])
    self.assertEqual(cue['cantonese'],'I would like you to come here.')
 def test_incomplete_batch_is_not_misaligned_to_other_cues(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);old=[audio(job/f'old-{i}.wav',1.4) for i in range(2)];new=audio(job/'new.wav',.4)
   cues=[dict(start=i,end=i+1,japanese='行こう',cantonese='I would like you to come here.') for i in range(2)]
   cfg=dict(duration=2,automaticDurationRewrite=True,normalRepairPolicy='verified',productionMode='normal',targetLanguage='en',model='m',port=1)
   with patch('dubbing.gsv_audio',return_value=[new]),patch.object(worker,'ollama_chat',return_value='{"0":"Come here.","1":"Come here."}'),patch('semantic_review.audit',return_value={str(i):dict(faithful=True) for i in range(2)}):
    self.assertEqual(natural_delivery.repair(cfg,job,cues,old,Mock(),Mock()),old)
 def test_repaired_language_audio_is_measured_after_replacement_before_mixing(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);first=audio(job/'first.wav',.4);language_fixed=audio(job/'language.wav',1.4);shortened=audio(job/'concise.wav',.5)
   cue=dict(start=0,end=1,japanese='行こう',cantonese='Come here.')
   cfg=dict(duration=1,speechRatePolicy='natural',normalRepairPolicy='verified',productionMode='normal',targetLanguage='en',ffmpeg='ffmpeg')
   def repair(c,j,rows,paths,*a,**kw):
    self.assertEqual(paths,[language_fixed]);return [shortened]
   raw=b'\x01\x00'*12000
   with patch('dubbing.gsv_audio',return_value=[first]),patch('normal_mode.repair_paths',return_value=[language_fixed]),patch('natural_delivery.repair',side_effect=repair),patch('natural_schedule.prepare',return_value=None):
    fast_mode.synthesize(cfg,job,[cue],Mock(return_value=raw),Mock())
   row=json.loads((job/'timing.json').read_text())[0]
   self.assertEqual(row['rate'],1.);self.assertFalse(row['skipped'])
 @unittest.skipUnless(shutil.which('ffmpeg'),'FFmpeg required')
 def test_real_mixer_delivers_bounded_placement_at_rate_one_with_all_words_intact(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);long=audio(job/'long.wav',1.3);short=audio(job/'short.wav',.6)
   cues=[dict(start=0,end=1,cantonese='Hello.'),dict(start=1,end=2,cantonese='Yes.')]
   cfg=dict(duration=3,speechRatePolicy='natural',normalRepairPolicy='verified',productionMode='normal',targetLanguage='en',ffmpeg=shutil.which('ffmpeg'))
   calls=[]
   def run(args):calls.append(args);return subprocess.check_output([str(a) for a in args],stderr=subprocess.PIPE)
   with patch('dubbing.gsv_audio',return_value=[long,short]),patch('normal_mode.repair_paths',side_effect=lambda c,j,cs,ps,*args:ps),patch('natural_delivery.repair',side_effect=lambda c,j,cs,ps,*args,**kwargs:ps),patch('natural_schedule.scene_boundaries',return_value=dict(status='detected',cuts=[])):
    output,warnings=fast_mode.synthesize(cfg,job,cues,run,Mock())
   rows=json.loads((job/'timing.json').read_text())
   self.assertFalse(warnings);self.assertTrue(all(not r['skipped'] for r in rows))
   self.assertEqual([r['rate'] for r in rows],[1.,1.]);self.assertGreater(rows[1]['timingShiftSeconds'],0)
   self.assertAlmostEqual(rows[0]['renderedSeconds'],1.3);self.assertAlmostEqual(rows[1]['renderedSeconds'],.6)
   self.assertLessEqual(rows[0]['renderedEnd'],rows[1]['renderedStart'])
   self.assertFalse(any('atempo=' in ' '.join(map(str,c)) for c in calls))
 def test_interruption_recovers_finished_batch_audio_without_restarting_model(self):
  from track_control import UserSkipped
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);old=audio(job/'old.wav',1.5)
   cue=dict(start=0,end=1,japanese='来て',cantonese='I would like you to come here.',speakerId='own')
   cfg=dict(duration=1,automaticDurationRewrite=True,preferFirstAudibleTake=False,normalRepairPolicy='verified',productionMode='normal',targetLanguage='en',ttsBackend='drama3',model='m',port=1)
   def interrupted(c,folder,rows,*args):
    target=audio(folder/'completed.wav',.4)
    worker.atomic_json(folder/'audio-preview.json',dict(engine='drama3',language='en',rows=[dict(rows[0],audio=str(target))]))
    raise UserSkipped('Pause')
   with patch('dubbing.gsv_audio',side_effect=interrupted) as tts,patch.object(worker,'ollama_chat',return_value='{"0":"Come here."}'),patch('semantic_review.audit',return_value={'0':dict(faithful=True)}),patch('normal_mode.inspect',return_value={}):
    with self.assertRaises(UserSkipped):natural_delivery.repair(cfg,job,[dict(cue)],[old],Mock(),Mock())
    result=natural_delivery.repair(cfg,job,[dict(cue)],[old],Mock(),Mock())
    self.assertEqual(tts.call_count,1);self.assertEqual(result[0].name,'completed.wav')
 def test_confirmed_later_rewrite_clears_stale_language_failure_without_hiding_history(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);old=audio(job/'old.wav',1.4);new=audio(job/'new.wav',.5)
   cue=dict(start=0,end=1,japanese='行こう',cantonese='I would like you to come here.')
   cfg=dict(duration=1,automaticDurationRewrite=True,preferFirstAudibleTake=False,normalRepairPolicy='verified',productionMode='normal',targetLanguage='en',model='m',port=1)
   worker.atomic_json(job/'normal-checks.json',dict(unresolved=[1],repairs=[dict(index=1,repaired=False)]))
   worker.atomic_json(job/'segment-issues.json',[dict(index=1,kind='normal-unresolved',message='Japanese')])
   with patch('dubbing.gsv_audio',return_value=[new]),patch.object(worker,'ollama_chat',return_value='{"0":"Come here."}'),patch('semantic_review.audit',return_value={'0':dict(faithful=True)}),patch('normal_mode.inspect',return_value={1:dict(decision='english',contentFailure=False)}):
    natural_delivery.repair(cfg,job,[cue],[old],Mock(),Mock())
   self.assertEqual(json.loads((job/'normal-checks.json').read_text())['unresolved'],[])
   self.assertEqual(json.loads((job/'segment-issues.json').read_text()),[])
   self.assertEqual(json.loads((job/'resolved-segment-issues.json').read_text())[0]['status'],'repaired')
 @unittest.skipUnless(shutil.which('ffmpeg'),'FFmpeg required')
 def test_longer_cantonese_and_english_use_empty_gap_without_rewrite_shift_or_acceleration(self):
  for language,text in [('yue','我哋一齊出發啦。'),('en','Let us go together.')]:
   with self.subTest(language=language),tempfile.TemporaryDirectory() as d:
    job=Path(d);long=audio(job/'long.wav',4.);short=audio(job/'short.wav',.4)
    cues=[dict(start=0,end=2,japanese='行こう',cantonese=text),dict(start=5,end=6,japanese='はい',cantonese='Yes.' if language=='en' else '係呀。')]
    cfg=dict(duration=6,speechRatePolicy='natural',automaticDurationRewrite=True,normalRepairPolicy='verified',productionMode='normal',targetLanguage=language,ffmpeg=shutil.which('ffmpeg'))
    before=copy.deepcopy(cues);calls=[]
    def run(args):calls.append(args);return subprocess.check_output([str(a) for a in args],stderr=subprocess.PIPE)
    with patch('dubbing.gsv_audio',return_value=[long,short]) as generate,patch('normal_mode.repair_paths',side_effect=lambda c,j,cs,ps,*a:ps),patch.object(worker,'ollama_chat',side_effect=AssertionError('Unnecessary rewrite of a line that fits the following gap')),patch('natural_schedule.scene_boundaries',side_effect=AssertionError('Unnecessary cut scan of a line that fits')):
     output,warnings=fast_mode.synthesize(cfg,job,cues,run,Mock())
    rows=json.loads((job/'timing.json').read_text())
    self.assertFalse(warnings);self.assertEqual(generate.call_count,1);self.assertEqual(cues,before)
    self.assertFalse(rows[0]['skipped']);self.assertEqual(rows[0]['rate'],1.)
    self.assertAlmostEqual(rows[0]['renderedSeconds'],4.);self.assertAlmostEqual(rows[0]['slot'],5.)
    self.assertEqual(rows[0]['timingShiftSeconds'],0.);self.assertLessEqual(rows[0]['renderedEnd'],rows[1]['renderedStart'])
    self.assertFalse(any('atempo=' in ' '.join(map(str,c)) for c in calls))
 def test_japanese_and_mandarin_decisions_do_not_reject_names_or_nonverbal_noise(self):
  self.assertEqual(normal_mode.language_decision('出發啦','それじゃ行こう','Japanese'),'japanese')
  self.assertEqual(normal_mode.language_decision('Come with me.','一緒に来て','Japanese','en'),'japanese')
  self.assertEqual(normal_mode.language_decision('Roger','Roger','Japanese','en'),'unconfirmed')
  self.assertEqual(normal_mode.language_decision('雷德','雷德','Chinese'),'unconfirmed')
  self.assertEqual(normal_mode.language_decision('Come here.','Come here','English','en'),'english')
