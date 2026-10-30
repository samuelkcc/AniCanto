import copy,importlib.util,json,sys,tempfile,unittest,wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly  # Import native modules before restoring sys.modules in a mock.
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows')]
import drama3,drama_prompt,target_delivery,dialogue_delivery,review_report,editing_tools,take_reuse

TEXT='鏡世界嘅喬巴同凱洛特，同分頭行動嘅佩德羅、娜美同甚平，成功會合。'
OLD='用香港廣東話講，唔好日文或普通話。完整讀出指定台詞，唔好加字、重複、拖長尾音或額外停頓。跟住參考錄音嘅音高起伏、速度同情緒講，唔好平讀，唔好照稿唸書'
def wav(p,seconds=1):
 sf.write(str(p),np.sin(np.arange(round(24000*seconds))*.05).astype(np.float32)*.15,24000,subtype='PCM_16');return p

def cue(**changes):
 return dict(dict(start=0.,end=2.,enabled=True,cantonese='你好呀',japanese='こんにちは',speakerId='own',captionRecords=[dict(id='c1',start=0,end=2,text='你好')],primarySource=dict(text='你好',captionIDs=['c1']),preserveOriginalSpeech=True,originalSpeechReason='uncertain-source-clock',sourceClockUnconfirmed=True),**changes)

class Prompt255Tests(unittest.TestCase):
 def test_actual_822_boundary_has_an_instruction_only_chunk(self):
  chunks=drama_prompt.splitter().split_text('['+OLD+'] '+TEXT)
  self.assertEqual(len(chunks),2);self.assertFalse(drama_prompt.spoken(chunks[0]));self.assertEqual(chunks[1],TEXT)
 def test_three_languages_short_and_long_inputs_never_submit_instruction_only(self):
  for lang,text in [('yue',TEXT),('zh','他们在镜世界成功会合。'),('en','The team has reunited in the mirror world.')]:
   for count in (1,2,12):
    plan=drama_prompt.plan(text*count,drama3.language_hint(lang,'cantonese-strict'))
    self.assertTrue(plan)
    self.assertEqual(''.join(''.join(x['text'].split()) for x in plan),''.join((text*count).split()))
    for x in plan:
     self.assertEqual(drama_prompt.splitter().split_text(x['prompt']),[x['prompt']]);self.assertTrue(drama_prompt.spoken(x['prompt']));self.assertLessEqual(len(x['prompt'].encode()),300)
 def test_rejects_instruction_only_before_neural_call(self):
  with self.assertRaisesRegex(ValueError,'instruction-only'):drama_prompt.plan('[laughing]')
  with self.assertRaises(ValueError):drama_prompt.plan('Hi','x'*300)
 def test_real_adapter_plan_preserves_text_and_sampling_with_no_extra_model_calls(self):
  with tempfile.TemporaryDirectory() as d:
   ref=wav(Path(d)/'ref.wav');calls=[]
   def generate(**kw):
    calls.append(kw)
    self.assertTrue(all(drama_prompt.spoken(x) for x in drama_prompt.splitter().split_text(kw['text'])))
    return [SimpleNamespace(audio=np.ones(500)*.1,segment_idx=0,token_count=5)]
   mx=SimpleNamespace(random=Mock());cfg=dict(targetLanguage='yue');item=dict(text=TEXT,deliveryStyle='cantonese-strict',profile=dict(reference=str(ref),promptText='原聲逐字稿'))
   with patch.dict(sys.modules,{'mlx':SimpleNamespace(core=mx),'mlx.core':mx}):drama3.generate(SimpleNamespace(generate=generate),item,cfg)
   self.assertEqual(len(calls),1);self.assertEqual(cfg['_dramaLastGeneration']['submittedText'],TEXT);self.assertFalse(drama_prompt.defects(cfg['_dramaLastGeneration']))
 def test_long_adapter_input_is_preflighted_in_full_before_inference(self):
  with tempfile.TemporaryDirectory() as d:
   ref=wav(Path(d)/'ref.wav');model=Mock();mx=SimpleNamespace(random=Mock())
   with patch.dict(sys.modules,{'mlx':SimpleNamespace(core=mx),'mlx.core':mx}):
    with self.assertRaises(ValueError):drama3.generate(model,dict(text='[laugh]',profile=dict(reference=str(ref),promptText='原文')),dict(targetLanguage='yue'))
   model.generate.assert_not_called()
 def test_windows_trace_does_not_inherit_mlx_chunk_verdict(self):
  self.assertEqual(drama_prompt.defects(dict(backend='gguf',parts=[dict(promptedText='['+OLD+'] '+TEXT)])),[])

class Clock255Tests(unittest.TestCase):
 def test_new_valid_caption_clock_guard_releases_without_changing_times_or_options(self):
  c=cue();cfg=dict(targetDeliveryRevision=target_delivery.REVISION,contentChecks=0,aiAutoFix=False);saved=copy.deepcopy(cfg)
  target_delivery.prepare(cfg,[c]);self.assertFalse(c['preserveOriginalSpeech']);self.assertTrue(c['sourceClockUnconfirmed']);self.assertEqual((c['start'],c['end']),(0,2));self.assertEqual(cfg,saved)
 def test_legacy_job_and_user_or_song_preservation_do_not_change(self):
  for cfg,c in [({},cue()),(dict(targetDeliveryRevision=target_delivery.REVISION),cue(originalSpeechReason='confirmed-source-song')),(dict(targetDeliveryRevision=target_delivery.REVISION),cue(editorAudio='manual.wav')),(dict(targetDeliveryRevision=target_delivery.REVISION),cue(sourcePolicyBlocked=True))]:
   before=copy.deepcopy(c);target_delivery.prepare(cfg,[c]);self.assertEqual(c,before)
 def test_empty_gap_or_continuation_is_not_given_duplicate_dialogue(self):
  cfg=dict(targetDeliveryRevision=target_delivery.REVISION)
  for why in ['subtitle-content-only-gap','subtitle-continuation']:
   c=cue(originalSpeechReason=why,cantonese='',primarySource=dict(text=''))
   before=copy.deepcopy(c);target_delivery.prepare(cfg,[c]);self.assertEqual(c,before)
 def test_actual_primary_stage_unblocks_before_translation_and_keeps_selected_words(self):
  import primary_source
  from atomic_files import write_json
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);write_json(job/'subtitle-context.json',[dict(start=0,end=2,text='你好')]);c=cue(cantonese='',primarySource={});cfg=dict(sourcePolicyRevision=primary_source.REVISION,sourceAllocationRevision=primary_source.ALLOCATION_REVISION,targetDeliveryRevision=target_delivery.REVISION,sourceWorkflowRevision='priority-paths-2-subtitle-content-only',sourceWorkflowEffective='subtitles-speech',subtitleSource='embedded',duration=2,sourceLanguage='ja')
   w=SimpleNamespace(atomic_json=write_json,emit=Mock())
   primary_source.prepare(w,cfg,job,[c]);self.assertFalse(c['preserveOriginalSpeech']);self.assertEqual(c['primarySource']['text'],'你好');self.assertFalse(c.get('sourcePolicyBlocked'))

class Report255Tests(unittest.TestCase):
 def project(self,root,cues,timing,items=()):
  cfg=dict(ttsBackend='drama3',targetLanguage='yue',dubLanguages=['yue'],selectedEngines=['drama3'],storage=str(root.parent),deliveryPolicyRevision='safe-capacity-delivery-4')
  review=dict(config=cfg,cues=cues);(root/'review.json').write_text(json.dumps(review));(root/'timing.json').write_text(json.dumps(timing))
  if items:(root/'drama3-request.json').write_text(json.dumps(dict(items=items)))
  report=review_report.project(root,review,dict(status='complete'));report.update(review=review,takes=[],root=str(root));return report
 def test_generated_source_is_not_reported_as_delivered_target(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);a=wav(p/'orig.wav');c=cue();t=dict(index=1,text='你好呀',renderedAudio=str(a),renderedSeconds=1,originalPreserved=True,skipped=False)
   result=self.project(p,[c],[t]);audit=result['deliveryCoverage']['tracks'][0];self.assertEqual((audit['required'],audit['available'],audit['missing']),(1,0,1));self.assertEqual(audit['sourcePreservedCount'],1)
   self.assertEqual(result['issues'][0]['kind'],'source-clock-target-missing');self.assertTrue(result['issues'][0]['repairEligible']);self.assertEqual(editing_tools.coverage(result)['tracks'][0]['recordings'],0)
 def test_old_instruction_only_recording_is_reported_read_only(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);a=wav(p/'old.wav');trace=a.with_suffix('.generation.json');trace.write_text(json.dumps(dict(backend='mlx',parts=[dict(promptedText='['+OLD+'] '+TEXT)])))
   c=cue(cantonese=TEXT,preserveOriginalSpeech=False,originalSpeechReason='');t=dict(index=1,text=TEXT,renderedAudio=str(a),renderedSeconds=1,skipped=False)
   before={f.name:f.read_bytes() for f in p.iterdir()};result=self.project(p,[c],[t],[dict(reviewIndex=0,text=TEXT,output=str(a))]);self.assertEqual(result['deliveryCoverage']['tracks'][0]['missing'],1);self.assertTrue(any(i['kind']=='generation-input' and i['repairEligible'] for i in result['issues']))
   for n,b in before.items():self.assertEqual((p/n).read_bytes(),b)
 def test_actual_selected_clean_trace_ignores_old_defect(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);a=wav(p/'good.wav');bad=p/'bad.wav';bad.with_suffix('.generation.json').write_text(json.dumps(dict(backend='mlx',parts=[dict(promptedText='['+OLD+'] '+TEXT)])));trace=a.with_suffix('.generation.json');trace.write_text(json.dumps(dict(backend='mlx',parts=[dict(promptedText='[粵語] '+TEXT)])))
   c=cue(cantonese=TEXT,preserveOriginalSpeech=False,originalSpeechReason='');t=dict(index=1,text=TEXT,renderedAudio=str(a),renderedSeconds=1,generationTrace=str(trace),skipped=False)
   result=self.project(p,[c],[t],[dict(reviewIndex=0,text=TEXT,output=str(bad))]);self.assertFalse(any(i['kind']=='generation-input' for i in result['issues']));self.assertEqual(result['deliveryCoverage']['tracks'][0]['available'],1)
 def test_continuation_and_gap_stay_explicit_source_without_fake_missing_meaning(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);cs=[cue(originalSpeechReason=w,cantonese='',primarySource=dict(text='')) for w in ('subtitle-continuation','subtitle-content-only-gap')];result=self.project(p,cs,[dict(index=i+1,originalPreserved=True) for i in range(2)]);audit=result['deliveryCoverage']['tracks'][0]
   self.assertEqual(audit['required'],0);self.assertEqual(audit['sourcePreservedCount'],2);self.assertTrue(all(x['targetDelivered'] is False for x in audit['sourcePreserved']))
 def test_original_source_is_not_advertised_as_a_generated_engine_recording(self):
  from desktop_state import job_snapshot
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);a=wav(p/'original.wav');c=cue();review=dict(config=dict(ttsBackend='drama3',targetLanguage='yue',dubLanguages=['yue'],selectedEngines=['drama3']),cues=[c]);(p/'review.json').write_text(json.dumps(review));(p/'timing.json').write_text(json.dumps([dict(index=1,renderedAudio=str(a),renderedSeconds=1,originalPreserved=True)]));(p/'audio-preview.json').write_text(json.dumps(dict(engine='drama3',language='yue',rows=[dict(index=1,audio=str(a),preserveOriginalSpeech=True)])))
   snapshot=job_snapshot(dict(job=str(p),review=str(p/'review.json'),status='complete'));self.assertEqual(snapshot['takes'],[]);self.assertEqual(snapshot['recordingCandidates'],[]);self.assertEqual(snapshot['deliveryCoverage']['tracks'][0]['missing'],1);self.assertTrue(any(e.get('originalFallback') for e in snapshot['issues'][0]['evidence']))
 def test_health_cache_invalidates_on_file_change(self):
  with tempfile.TemporaryDirectory() as d:
   a=wav(Path(d)/'voice.wav');self.assertTrue(dialogue_delivery.healthy(a));sf.write(str(a),np.zeros(24000),24000,subtype='PCM_16');self.assertFalse(dialogue_delivery.healthy(a))

class RoutingAndRetry255Tests(unittest.TestCase):
 def test_new_automatic_source_decision_ignores_old_preference_overrides(self):
  import source_workflow as f
  for mode in ('basic','expert'):
   for has_text in (True,False):
    cfg=dict(sourceWorkflowRevision=f.REVISION,sourceSelectionRevision='basic-source-defaults-231',interfaceMode=mode,sourceWorkflow='auto',defaultSubtitleWorkflow='speech-subtitles',defaultOCRWorkflow='ocr-speech')
    meta=dict(streams=[dict(index=2,codec_type='subtitle',codec_name='subrip')] if has_text else [])
    f.configure(cfg,meta,lambda rows,*a:next(iter(rows),None));self.assertEqual(cfg['sourceWorkflowEffective'],'subtitles-speech' if has_text else 'speech-ocr')
 def test_legacy_source_choices_and_expert_manual_choice_survive(self):
  import source_workflow as f
  cfg=dict(sourceWorkflowRevision=f.REVISION,interfaceMode='expert',sourceWorkflow='auto',defaultOCRWorkflow='ocr-speech')
  f.configure(cfg,dict(streams=[]),lambda *a:None);self.assertEqual(cfg['sourceWorkflowEffective'],'ocr-speech')
  cfg.update(sourceSelectionRevision='basic-source-defaults-231',sourceWorkflow='ocr-speech');f.configure(cfg,dict(streams=[]),lambda *a:None);self.assertEqual(cfg['sourceWorkflowEffective'],'ocr-speech')
 def test_explicit_performance_repair_creates_new_version_without_changing_old_request(self):
  import review_retry,multitrack,basic_flow
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=root/'jobs/test';p.mkdir(parents=True);audio=wav(p/'first.wav');path=p/'review.json';c=cue();review=dict(config=dict(productionMode='fast',basicFlowRevision=basic_flow.REVISION,contentChecks=0,aiAutoFix=False,limitSpeechDuration=False),cues=[c]);path.write_text(json.dumps(review));(p/'timing.json').write_text(json.dumps([dict(index=1,renderedAudio=str(audio),renderedStart=0,renderedEnd=1)]));before=path.read_bytes()
   snapshot=dict(issues=[dict(index=1,engine='drama3',language='yue',repairEligible=True,kind='source-clock-target-missing')])
   with patch.object(multitrack,'saved_track_reports',return_value=[dict(engine='drama3',language='yue',report=str(p/'report.json'))]):draft=review_retry.submission(root,path,snapshot)
   self.assertEqual(draft['settings']['contentChecks'],0);self.assertFalse(draft['settings']['aiAutoFix']);self.assertEqual(path.read_bytes(),before)
   cfg=dict(draft['settings'],_reviewRetry=draft['automaticReviewRetry'],_reviewRetryToken=draft['id'])
   result=review_retry.track_cues(cfg,[c],'drama3','yue');self.assertFalse(result[0]['preserveOriginalSpeech']);self.assertTrue(c['preserveOriginalSpeech'])
 def test_released_clock_reaches_missing_fill_with_zero_content_checks(self):
  import normal_mode,dubbing,basic_flow
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);good=wav(p/'new.wav');missing=p/'missing.wav';c=cue();cfg=dict(targetDeliveryRevision=target_delivery.REVISION,basicFlowRevision=basic_flow.REVISION,repairPermissionsRevision='repair-fallback-permissions-249',contentChecks=0,aiAutoFix=False,limitSpeechDuration=False,maximumMissingRepairAttempts=1,ttsBackend='drama3',targetLanguage='yue')
   target_delivery.prepare(cfg,[c])
   with patch.object(dubbing,'gsv_audio',return_value=[good]) as generate,patch.object(normal_mode,'inspect') as inspect:
    result=normal_mode.repair_missing_only(cfg,p,[c],[missing],Mock(),Mock());self.assertEqual(result,[good]);self.assertEqual(generate.call_count,1);inspect.assert_not_called()
 def test_zero_checks_prevents_hidden_readback_for_all_legacy_work_mode_labels(self):
  import normal_mode,basic_flow,dubbing
  for mode in ('performance','balanced','quality'):
   cfg=dict(basicFlowRevision=basic_flow.REVISION,workMode=mode,contentChecks=0,_forceIndependentListening=True,_allowBasicContentCheck=True)
   with patch.object(dubbing,'model_job',side_effect=AssertionError('Unrequested readback')) as model:
    self.assertEqual(normal_mode.inspect(cfg,Path('/nonexistent'),[],[],Mock()),{});model.assert_not_called()
 def test_child_track_replaces_parent_projection_for_the_same_pair(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);child=p/'tracks/current';child.mkdir(parents=True);a=wav(child/'take.wav');cfg=dict(ttsBackend='drama3',targetLanguage='yue',dubLanguages=['yue'],selectedEngines=['drama3']);c=cue(preserveOriginalSpeech=False,originalSpeechReason='')
   review=dict(config=cfg,cues=[c]);(p/'review.json').write_text(json.dumps(review));(child/'review.json').write_text(json.dumps(review));(p/'timing.json').write_text(json.dumps([dict(index=1,renderedAudio=str(a),renderedSeconds=1)]));(child/'timing.json').write_text(json.dumps([dict(index=1,skipped=True)]));(p/'track-progress.json').write_text(json.dumps(dict(tracks=[dict(folder=str(child),engine='drama3',language='yue')])));result=review_report.project(p,review,dict(status='complete'));self.assertEqual(len(result['deliveryCoverage']['tracks']),1);self.assertEqual(result['deliveryCoverage']['tracks'][0]['available'],0)

if __name__=='__main__':unittest.main()
