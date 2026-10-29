"""Measured delivery contract, exercised through real production entry points."""
import array,copy,hashlib,json,math,sys,tempfile,unittest,wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import worker,normal_mode,concise_dialogue,generic_delivery,natural_delivery,delivery_policy,source_workflow


def audio(path,seconds):
 with wave.open(str(path),'wb') as f:
  f.setparams((1,2,24000,0,'NONE','not compressed'))
  f.writeframes(array.array('h',(round(3000*math.sin(i*.071)) for i in range(round(24000*seconds)))).tobytes())
 return path


class MeasuredDraftTests(unittest.TestCase):
 def config(self,**kw):return dict(deliveryPolicyRevision=delivery_policy.LEGACY_REVISION,model='m',port=1,targetLanguage='yue',sourceLanguage='ja',dubLanguages=['yue'],subtitleModes=['yue'],**kw)
 def test_complete_first_draft_has_no_duration_budget_or_preemptive_compaction(self):
  text='甚平同娜美喺城堡入面周圍走。';cues=[dict(start=0,end=1.96,japanese='ジンベエとナミが城を走り回る',subtitleHint='甚平与娜美在城堡内到处奔走',cantonese='')]
  with tempfile.TemporaryDirectory() as d:
   chat=Mock(return_value=json.dumps({'0':text}));w=SimpleNamespace(emit=Mock(),atomic_json=worker.atomic_json,ollama_chat=chat,traditional_cantonese=lambda cfg,s:s)
   with patch('normal_mode.glossary',return_value=[]),patch('script_gap_recovery.compact_drafts') as compact,patch('translation_brevity.review'):
    normal_mode.translate(w,self.config(),Path(d),cues)
   self.assertEqual(cues[0]['cantonese'],text);compact.assert_not_called()
   payload=json.loads(chat.call_args.args[2][1]['content']);serialized=json.dumps(payload)
   self.assertNotIn('targetCharacters',serialized);self.assertNotIn('targetWords',serialized)
   self.assertIn('There is no character/word budget',chat.call_args.args[2][0]['content'])
 def test_estimates_or_underlimit_audio_cannot_authorize_shared_compaction(self):
  with tempfile.TemporaryDirectory() as d:
   w=SimpleNamespace(ollama_chat=Mock(),atomic_json=worker.atomic_json);cue=dict(cantonese='甚平同娜美喺城堡入面周圍走。',japanese='source')
   for records in [{},{'0':dict(seconds=1.5,availableSeconds=2)},{'0':dict(seconds=2,availableSeconds=2)},{'0':dict(seconds='3',availableSeconds=2)}]:
    self.assertEqual(concise_dialogue.compact(w,dict(self.config(),_measuredOverruns=records),d,[cue],[0],{0:4}),[])
   w.ollama_chat.assert_not_called();self.assertIn('周圍走',cue['cantonese'])
 def test_real_overrun_rejects_telegraphic_grammar_even_with_matching_keywords(self):
  for natural,expected in [(False,[]),(True,[0])]:
   with self.subTest(natural=natural),tempfile.TemporaryDirectory() as d:
    cue=dict(cantonese='甚平同娜美喺城堡入面到處奔走。',japanese='甚平與娜美在城堡到處跑')
    result='甚平娜美城堡奔' if not natural else '甚平同娜美喺城堡周圍跑。'
    w=SimpleNamespace(ollama_chat=Mock(return_value=json.dumps({'0':result})),atomic_json=worker.atomic_json)
    cfg=dict(self.config(),_measuredOverruns={'0':dict(seconds=3.5,availableSeconds=2)})
    with patch('semantic_review.audit',return_value={'0':dict(faithful=True,naturalSpoken=natural)}) as audit:
     self.assertEqual(concise_dialogue.compact(w,cfg,d,[cue],[0],{0:8}),expected)
    self.assertTrue(audit.call_args.args[0]['_requireNaturalSpoken'])
    if natural:self.assertEqual(cue['cantonese'],result)
    else:self.assertIn('到處奔走',cue['cantonese'])


class SourceEntryTests(unittest.TestCase):
 class ReachedSeparation(Exception):pass
 def test_real_normal_and_fast_entry_resolve_before_freeze_and_persist_four_paths(self):
  for mode in ['normal','fast','full-ai']:
   for workflow in source_workflow.TEXT_CHOICES+source_workflow.OCR_CHOICES:
    with self.subTest(mode=mode,workflow=workflow),tempfile.TemporaryDirectory() as d:
     root=Path(d);video=root/'video.mkv';video.write_bytes(b'fixture')
     streams=[dict(index=0,codec_type='video'),dict(index=1,codec_type='audio',tags=dict(language='jpn'))]
     if workflow in source_workflow.TEXT_CHOICES:streams.append(dict(index=2,codec_type='subtitle',codec_name='subrip',tags=dict(language='chi')))
     cfg=dict(video=str(video),storage=d,ffprobe='fixture-probe',productionMode=mode,separateBackground=True,ttsBackend='drama3',speechRatePolicy='natural',sourceLanguage='ja',model='m',port=1,sourceWorkflowRevision=source_workflow.REVISION,sourceWorkflow=workflow,interfaceMode='expert',deliveryPolicyRevision=delivery_policy.LEGACY_REVISION)
     captured=[]
     def freeze(c):captured.append(copy.deepcopy(c))
     with patch.object(worker,'run',return_value=json.dumps(dict(format=dict(duration='10'),streams=streams))),patch.object(worker,'emit'),patch('engine_policy.migrate'),patch('studio_core.freeze',side_effect=freeze),patch('model_recovery.recover'),patch('source_language.supported',return_value=True),patch('opening.prepare'),patch('dubbing.separate',side_effect=self.ReachedSeparation):
      with self.assertRaises(self.ReachedSeparation):worker.convert(cfg)
     self.assertTrue(captured);self.assertTrue(all(c.get('sourceWorkflowEffective')==workflow for c in captured))
     saved=list((root/'jobs').glob('*/source-workflow.json'));self.assertEqual(len(saved),1)
     self.assertEqual(json.loads(saved[0].read_text())['effective'],workflow)
 def test_basic_ignores_expert_override_and_resolves_factory_or_preference_defaults(self):
  for has_text,default in [(True,'subtitles-speech'),(False,'ocr-speech'),(True,'speech-subtitles'),(False,'speech-ocr')]:
   cfg=dict(sourceWorkflowRevision=source_workflow.REVISION,interfaceMode='basic',sourceWorkflow='speech-subtitles',defaultSubtitleWorkflow=default if has_text else 'subtitles-speech',defaultOCRWorkflow=default if not has_text else 'ocr-speech')
   source_workflow.configure(cfg,dict(streams=[dict(index=2,codec_type='subtitle',codec_name='subrip')] if has_text else []),lambda tracks,*a:tracks[0] if tracks else None)
   self.assertEqual(cfg['sourceWorkflowEffective'],default)


class GenericDeliveryTests(unittest.TestCase):
 def trial(self,root):
  old=audio(root/'actor.wav',3);bank=audio(root/'bank-long.wav',2.8);other=audio(root/'neighbour.wav',.5);ref=audio(root/'bank-reference.wav',4)
  cues=[dict(start=0,end=2,reviewIndex=9,japanese='こっちへ来て',cantonese='你而家過嚟呢邊啦。',speakerId='r'),dict(start=3,end=4,reviewIndex=10,japanese='はい',cantonese='係呀。',speakerId='r',editorAudio=str(other))]
  profile=dict(id='bank',reference=str(ref),language='yue',promptText='香港廣東話參考。')
  record=dict(index=10,status='timing-not-fit',audio=str(bank),referenceSHA256=hashlib.sha256(ref.read_bytes()).hexdigest())
  worker.atomic_json(root/'target-reference-recovery.json',{'trial':record});worker.atomic_json(root/'review.json',dict(cues=copy.deepcopy(cues)))
  cfg=dict(deliveryPolicyRevision=delivery_policy.LEGACY_REVISION,productionMode='normal',failedVoicePolicy='generic',duration=4,speechRatePolicy='natural',naturalTimingPolicy='source-locked',preferFirstAudibleTake=True,automaticDurationRewrite=True,model='m',port=1,targetLanguage='yue',ttsBackend='drama3')
  place=[dict(fit=False,seconds=3,start=0,deadline=2),dict(fit=True,seconds=.5,start=3,deadline=4)]
  return cfg,cues,[old,other],place,profile
 def test_bank_overrun_is_measured_then_rewritten_and_saved_without_touching_good_neighbour(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cfg,cues,paths,place,profile=self.trial(root);new=audio(root/'generic-short.wav',1.5);before=paths[1].read_bytes()
   def repair(local,folder,drafts,trials,*a,**kw):
    self.assertEqual(trials[0],root/'bank-long.wav');self.assertEqual(local['voiceProfiles'],[profile]);self.assertEqual(drafts[1]['editorAudio'],str(paths[1]));drafts[0]['cantonese']='你過嚟呢邊啦。';return [new,paths[1]]
   def finish(local,folder,drafts,selected,*a,**kw):return selected,[dict(place[0],fit=selected[0]==new),place[1]]
   with patch('dubbing.profile_for',side_effect=ValueError('actor missing')),patch('natural_voices.resolve',return_value=profile),patch('natural_schedule.prepare',return_value=place),patch('natural_delivery.repair',side_effect=repair),patch('natural_finish.finish',side_effect=finish),patch('normal_mode.inspect',return_value={10:dict(decision='cantonese',heard='你過嚟呢邊啦。')}),patch('normal_engine_fallback.repair') as alternate:
    result=generic_delivery.repair(cfg,root,cues,paths,place,Mock(),Mock())
   self.assertEqual(result,[new,paths[1]]);self.assertEqual(paths[1].read_bytes(),before);alternate.assert_not_called()
   record=json.loads((root/'target-reference-recovery.json').read_text())['trial'];self.assertEqual(record['status'],'adopted');self.assertFalse(record['qualityCertified'])
   self.assertEqual(json.loads((root/'review.json').read_text())['cues'][0]['cantonese'],'你過嚟呢邊啦。')
 def test_wrong_language_bank_candidate_not_adopted_and_only_one_target_bank_alternate_allowed(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cfg,cues,paths,place,profile=self.trial(root);new=audio(root/'bad-short.wav',1)
   with patch('dubbing.profile_for',return_value=profile),patch('natural_voices.resolve',return_value=profile),patch('natural_schedule.prepare',return_value=place),patch('natural_delivery.repair',return_value=[new,paths[1]]),patch('natural_finish.finish',side_effect=lambda c,j,cs,ps,*a,**kw:(ps,place)),patch('normal_mode.inspect',return_value={10:dict(decision='japanese',heard='日本語')}),patch('normal_engine_fallback.repair',side_effect=lambda c,j,cs,ps,*a:ps) as alternate:
    result=generic_delivery.repair(cfg,root,cues,paths,place,Mock(),Mock())
   self.assertEqual(result,paths);self.assertEqual(alternate.call_count,1)
   self.assertTrue(alternate.call_args.args[0]['_genericTargetVoice']);self.assertEqual(alternate.call_args.args[0]['_maximumAlternateEngines'],1)
   self.assertEqual(json.loads((root/'target-reference-recovery.json').read_text())['trial']['status'],'timing-not-fit')
 def test_legacy_jobs_and_finish_request_do_not_start_additional_work(self):
  with tempfile.TemporaryDirectory() as d,patch('normal_mode.inspect') as listen:
   root=Path(d);cfg,cues,paths,place,_=self.trial(root)
   for local in [dict(cfg,deliveryPolicyRevision=None),dict(cfg,failedVoicePolicy='source'),dict(cfg,editorRender=True)]:self.assertEqual(generic_delivery.repair(local,root,cues,paths,place,Mock(),Mock()),paths)
   with patch('normal_policy.finish_requested',return_value=True):self.assertEqual(generic_delivery.repair(cfg,root,cues,paths,place,Mock(),Mock()),paths)
   listen.assert_not_called()
 def test_final_policy_recognizes_verified_generic_alternate_instead_of_japanese(self):
  from failed_voice_policy import choose
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cfg,cues,paths,place,_=self.trial(root)
   worker.atomic_json(root/'normal-checks.json',dict(unresolved=[10]));worker.atomic_json(root/'alternate-engine-recovery.json',{'x':dict(index=10,genericTargetReference=True,status='adopted',selectedAudio=str(paths[0]))})
   _,source=choose(cfg,root,cues,paths);self.assertEqual(source,set())
   self.assertEqual(json.loads((root/'failed-voice-choices.json').read_text())['decisions'][0]['action'],'generic-target-language-take')

class RealWaveformDeliveryTests(unittest.TestCase):
 def test_actual_measured_repair_keeps_generic_reference_manifest_and_neighbour(self):
  import shutil,subprocess
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);fixture=GenericDeliveryTests();cfg,cues,paths,place,profile=fixture.trial(root)
   cues[1].update(start=2,end=3);place[1].update(start=2,deadline=3);cfg['duration']=3
   cfg.update(ffmpeg=shutil.which('ffmpeg'),ffprobe=shutil.which('ffprobe'),automaticMicroTempo=False,_voiceManifest={'r':'original-actor-hash'})
   new=audio(root/'short.wav',1.25);before=paths[1].read_bytes()
   def generate(c,folder,rows,*a):
    self.assertEqual(c['_voiceManifest'][profile['id']],hashlib.sha256(Path(profile['reference']).read_bytes()).hexdigest())
    self.assertEqual(len(rows),1);self.assertEqual(rows[0]['speakerId'],profile['id']);return [new]
   def chat(*a,**kw):return json.dumps({'0':'你過嚟啦。'})
   run=lambda args:subprocess.check_output(list(map(str,args)),stderr=subprocess.PIPE)
   with patch('dubbing.profile_for',return_value=profile),patch('natural_voices.resolve',return_value=profile),patch('dubbing.gsv_audio',side_effect=generate) as tts,patch.object(worker,'ollama_chat',side_effect=chat),patch('semantic_review.audit',return_value={'0':dict(faithful=True,naturalSpoken=True)}),patch('normal_mode.inspect',return_value={10:dict(decision='cantonese',heard='你過嚟啦。')}),patch('normal_engine_fallback.installed',return_value=[]):
    output=generic_delivery.repair(cfg,root,cues,paths,place,run,Mock())
   self.assertNotEqual(output[0],paths[0]);self.assertLess(natural_delivery.seconds(output[0],cfg,run),2)
   self.assertEqual(cues[0]['cantonese'],'你過嚟啦。');self.assertEqual(paths[1].read_bytes(),before);self.assertEqual(tts.call_count,1)
   record=json.loads((root/'target-reference-recovery.json').read_text())['trial'];self.assertEqual(record['status'],'adopted')
   # Reusing the repaired text and saved trial cannot synthesize again.
   with patch('dubbing.gsv_audio') as tts,patch('normal_engine_fallback.installed',return_value=[]):
    generic_delivery.repair(cfg,root,cues,output,[dict(place[0],fit=True),place[1]],run,Mock())
   tts.assert_not_called()

if __name__=='__main__':unittest.main()
