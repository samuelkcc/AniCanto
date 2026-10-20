import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
import numpy as np
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import dub_languages,voice_models,dialogue,dubbing_runner

class VoiceUpdates(unittest.TestCase):
 def test_gsv_retries_punctuation_without_mutating_approved_words(self):
  silent=np.zeros(24000);good=.1*np.sin(np.arange(24000)*.1)
  model=Mock();model.run.side_effect=[iter([(24000,silent)]),iter([(24000,good)])]
  request=dict(text='同埋...',seed=42,text_lang='all_yue',ref_audio_path='same.wav')
  sr,audio,attempts=dubbing_runner.gsv_take(model,Mock(),request)
  self.assertEqual(request['text'],'同埋...');self.assertEqual(attempts[-1]['text'],'同埋。');self.assertFalse(attempts[-1]['problems'])
 def test_gsv_changes_seed_before_cpu_fallback_and_never_accepts_silence(self):
  model=Mock();model.run.side_effect=lambda request:iter([(24000,np.zeros(24000))])
  fallback=Mock(return_value=model)
  _,_,attempts=dubbing_runner.gsv_take(model,fallback,dict(text='你好',seed=42),device='mps')
  self.assertEqual([a['seed'] for a in attempts],[42,73,73]);self.assertEqual(attempts[-1]['device'],'cpu');self.assertTrue(attempts[-1]['problems'])
 def test_english_track_is_independent_and_does_not_reuse_cantonese_take(self):
  cues=[dict(cantonese='你好',english='Hello.',start=0,end=1,editorAudio='yue.wav',deliveryPlan=[{}])]
  en=dub_languages.track_cues(cues,'en')
  self.assertEqual(en[0]['cantonese'],'Hello.');self.assertEqual(cues[0]['cantonese'],'你好');self.assertNotIn('editorAudio',en[0]);self.assertNotIn('deliveryPlan',en[0])
  self.assertEqual(dub_languages.selected({'dubLanguages':['yue','en','yue']}),['yue','en'])
  with self.assertRaises(ValueError):dub_languages.selected({'dubLanguages':['bad']})
 def test_english_translates_from_japanese_and_keeps_manual_english(self):
  cues=[dict(text='こんにちは',japanese='こんにちは',cantonese='唔好用呢句做翻譯',start=0,end=1),dict(text='ありがとう',cantonese='多謝',english='Thanks!',start=1,end=2)]
  with tempfile.TemporaryDirectory() as folder:
   w=Mock();w.ollama_chat.return_value='{"0":"Hey there!"}';w.atomic_json=lambda p,d:p.write_text(json.dumps(d))
   dub_languages.english_script(w,dict(model='model',port=1),Path(folder),cues)
   payload=w.ollama_chat.call_args.args[2][1]['content']
   self.assertIn('こんにちは',payload);self.assertNotIn('唔好用',payload);self.assertEqual(cues[1]['english'],'Thanks!')
 def test_coverage_reports_disabled_and_vad_gaps_but_respects_opening(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder);(p/'japanese-analysis.json').write_text(json.dumps(dict(spans=[dict(start=0,end=4)])))
   cfg=dict(duration=4,startOffset=10,opRanges=[dict(start=10,end=11)])
   report=dialogue.coverage_report(cfg,p,[dict(start=1,end=2,enabled=True),dict(start=2,end=3,enabled=False,text='聞こえる')])
   self.assertEqual(report['uncovered'],[dict(start=2,end=4)]);self.assertEqual(len(report['disabled']),1)
 def test_suspect_recognized_speech_is_flagged_not_silently_disabled(self):
  seg=[dict(words=[dict(start=0,end=5,word='こ、考えてよね',probability=.7)])]
  cues=dialogue.build_cues(seg,[dict(start=0,end=5)],[],6)
  self.assertTrue(cues[0]['enabled']);self.assertTrue(cues[0]['sourceReviewReasons'])
 def test_selected_missing_model_never_falls_back(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'models/qwen-tts';p.mkdir(parents=True);(p/'model.safetensors').touch()
   with self.assertRaisesRegex(ValueError,'未下載所選模型'):voice_models.resolve(folder,'qwen-tts')
   with self.assertRaisesRegex(ValueError,'未下載所選模型'):voice_models.resolve(folder,'qwen-tts','qwen-1.7b-bf16')
   with self.assertRaises(ValueError):voice_models.choice('cosyvoice3','qwen-1.7b-bf16')
 def test_manual_missing_dialogue_can_be_added_with_provenance(self):
  from project_edit import materialize
  source=dict(config=dict(duration=10),cues=[])
  row=dict(id='new',manual=True,sources=[],start=1,end=3,text='你好',original='こんにちは',english='Hi!')
  result=materialize(source,dict(segments=[row]))
  self.assertTrue(result[0]['manual']);self.assertEqual(result[0]['english'],'Hi!');self.assertEqual(result[0]['editorSources'],[])

class ModelOptionsTests(unittest.TestCase):
 def test_removed_model_cannot_resolve_or_download(self):
  import model_catalog
  with tempfile.TemporaryDirectory() as folder:
   for action in (model_catalog.resolve,model_catalog.install):
    with self.assertRaisesRegex(ValueError,'未知模型版本'):
     action(folder,'mlx:qwen3.5-9b:3bit')
   self.assertFalse((Path(folder)/'model-ready').exists())
 def test_catalog_is_pinned_unique_and_removed_sizes_stay_absent(self):
  import model_catalog
  rows=model_catalog.catalog()
  self.assertEqual(len(rows),len({r['id'] for r in rows}))
  self.assertTrue({.8,2,9,27,35,122,397}<={r['parameterB'] for r in rows if r['category']=='text'})
  self.assertFalse(any(r.get('licenseReviewRequired') for r in rows))
  self.assertFalse(any(r['category']=='text' and r['parameterB']==4 for r in rows))
  self.assertFalse(any(r['engine']=='cosyvoice3' for r in rows))
  for row in rows:
   self.assertEqual(len(row['revision']),40)
   self.assertEqual(row['bytes'],sum(f['size'] for f in row['files']))
   self.assertTrue(all(len(f['sha'])==64 and '..' not in Path(f['path']).parts for f in row['files']))
 def test_voice_and_general_catalog_resolve_same_folder(self):
  import model_catalog
  for row in voice_models.catalog():self.assertEqual(voice_models.folder('/tmp/test',row),model_catalog.folder('/tmp/test',model_catalog.choice(row['id'])))
 def test_model_selection_preserves_other_versions_and_no_fallback(self):
  import model_catalog
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'model-selections.json').write_text(json.dumps({'asr':'asr-0.6b-4bit'}))
   self.assertEqual(model_catalog.selected(p,'asr'),'asr-0.6b-4bit')
   self.assertEqual(model_catalog.selected(p,'speech'),'whisper-large-v3')
   with self.assertRaises(ValueError):model_catalog.resolve(p,'asr-0.6b-4bit')
 def test_nonverbal_tail_is_not_sent_as_punctuation_to_english_tts(self):
  from dubbing import is_vocalization
  cue=dict(cantonese='啊',english='—!',nonlexicalTail=True,start=0,end=.4)
  translated=dub_languages.track_cues([cue],'en')[0]
  self.assertTrue(is_vocalization(translated));self.assertTrue(cue['nonlexicalTail'])
 def test_cantonese_reference_is_not_replaced_or_bridge_silently_forced(self):
  import qwen_reference
  p=dict(language='yue',reference='user.wav')
  self.assertIs(qwen_reference.prepare({},'/tmp',p,Mock()),p)
  p=dict(language='ja',reference='original.wav')
  self.assertIs(qwen_reference.prepare({'qwenReferenceMode':'original'},'/tmp',p,Mock()),p)
 def test_english_negation_checks_are_case_and_apostrophe_aware(self):
  from speechcheck import critical_omissions
  self.assertEqual(critical_omissions("I don't know.","I don’t know."),[])
  self.assertTrue(critical_omissions('Never leave me.','Leave me.'))

if __name__=='__main__':unittest.main()

class ReviewLanguageTests(unittest.TestCase):
 def test_english_nonverbal_translation_keeps_source_classification(self):
  import worker
  original=[dict(start=0,end=1,text='ー!',cantonese='啊',nonlexicalTail=True)]
  submitted=[dict(original[0],cantonese='—!')]
  cues=worker.validate_review(submitted,original,2,target_language='en')
  self.assertTrue(cues[0]['nonlexicalTail'])
  submitted[0]['cantonese']='I will leave now.'
  self.assertNotIn('nonlexicalTail',worker.validate_review(submitted,original,2,target_language='en')[0])

class GPTReferenceTests(unittest.TestCase):
 def test_matching_language_and_explicit_original_bypass_bridge(self):
  import qwen_reference
  for target in ('en','yue'):
   p=dict(language=target,reference='user.wav')
   self.assertIs(qwen_reference.prepare(dict(ttsBackend='gpt-sovits',targetLanguage=target),'/tmp',p,Mock()),p)
   p=dict(language='ja',reference='original.wav')
   self.assertIs(qwen_reference.prepare(dict(ttsBackend='gpt-sovits',targetLanguage=target,gsvReferenceMode='original'),'/tmp',p,Mock()),p)
 def test_english_gpt_requires_target_reference_dependencies(self):
  import qwen_reference
  with tempfile.TemporaryDirectory() as root:
   with self.assertRaisesRegex(ValueError,'GPT-SoVITS'):
    qwen_reference.prepare(dict(storage=root,ttsBackend='gpt-sovits',targetLanguage='en',gsvReferenceMode='target-bridge'),root,dict(language='ja'),Mock())
 def test_qwen_english_preserves_original_reference(self):
  import qwen_reference
  p=dict(language='ja',reference='original.wav')
  self.assertIs(qwen_reference.prepare(dict(ttsBackend='qwen-tts',targetLanguage='en'),'/tmp',p,Mock()),p)
