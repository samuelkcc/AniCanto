import copy,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import source_language as source

class SourceLanguageTests(unittest.TestCase):
 def test_english_subtitle_cannot_turn_japanese_audio_into_english(self):
  meta=dict(streams=[dict(index=1,codec_type='audio',tags=dict(language='jpn')),dict(index=2,codec_type='subtitle',tags=dict(language='eng'))])
  self.assertEqual(source.metadata(meta)['language'],'ja')
 def test_first_audio_is_the_detection_and_processing_source(self):
  streams=[dict(index=1,codec_type='audio',tags=dict(language='jpn')),dict(index=3,codec_type='audio',tags=dict(language='eng'),disposition=dict(default=1))]
  self.assertEqual(source.metadata(dict(streams=streams)),dict(language='ja',stream=1,method='audio-stream-metadata'))
 def test_english_source_preserves_explicit_multilingual_output(self):
  cfg=dict(dubLanguages=['yue','en'],subtitleSelection='automatic',subtitleModes=['original','english','dual'],productionMode='standard')
  source.apply(cfg,'en')
  self.assertEqual(cfg['dubLanguages'],['yue','en']);self.assertEqual(cfg['subtitleModes'],['original','english','dual'])
  self.assertEqual(cfg['productionMode'],'normal');self.assertEqual(cfg['sourceLanguage'],'en')
 def test_nonenglish_source_keeps_selected_output_languages_and_subtitles(self):
  cfg=dict(dubLanguages=['yue','en'],subtitleModes=['yue','english','dual','original'])
  expected=copy.deepcopy(cfg);source.apply(cfg,'ko')
  self.assertEqual(cfg['dubLanguages'],expected['dubLanguages']);self.assertEqual(cfg['subtitleModes'],expected['subtitleModes'])
 def test_reference_language_support_is_engine_specific(self):
  self.assertTrue(source.supported('en',['gpt-sovits-v2']))
  self.assertTrue(source.supported('ko',['gpt-sovits-v2','drama3']))
  self.assertFalse(source.supported('fr',['gpt-sovits-v2']))
  self.assertTrue(source.supported('fr',['drama3']))
  self.assertFalse(source.supported('xx',['drama3']))
 def test_audio_probe_uses_cpu_and_multiple_confident_samples(self):
  import numpy as np
  from types import SimpleNamespace
  model=Mock();model.detect_language.side_effect=[('en',.94,[]),('ja',.91,[]),('en',.96,[])]
  constructor=Mock(return_value=model)
  samples=np.ones(32000,dtype=np.float32)*.05
  request=dict(storage='root',video='movie',duration=100,stream=3,ffmpeg='ffmpeg',speechModel='whisper')
  with patch.dict(sys.modules,{'faster_whisper':SimpleNamespace(WhisperModel=constructor)}),patch('model_catalog.resolve',return_value=Path('model')),patch.object(source.subprocess,'check_output',return_value=samples.tobytes()) as decode:
   result=source.probe(request)
   self.assertEqual(result['language'],'en');self.assertEqual(len(result['samples']),3)
   self.assertEqual(constructor.call_args.kwargs['device'],'cpu')
   self.assertTrue(all('0:3' in c.args[0] for c in decode.call_args_list))
  model.detect_language.side_effect=[('en',.4,[]),('ja',.3,[]),('en',.5,[])]
  with patch.dict(sys.modules,{'faster_whisper':SimpleNamespace(WhisperModel=constructor)}),patch('model_catalog.resolve',return_value=Path('model')),patch.object(source.subprocess,'check_output',return_value=samples.tobytes()):
   self.assertIsNone(source.probe(request)['language'])
 def test_japanese_never_requires_a_second_confirmation_on_either_desktop(self):
  for platform in ['win32','darwin']:
   with self.subTest(platform=platform),tempfile.TemporaryDirectory() as d:
    video=Path(d)/'source.mkv';video.write_bytes(b'fixture');meta=dict(streams=[dict(index=1,codec_type='audio',tags=dict(language='jpn'))])
    with patch.object(source.sys,'platform',platform),patch('source_access.accessible',return_value=(video,json.dumps(meta).encode())),patch('source_preparation.Preparation.capture',return_value=json.dumps(meta).encode()):
     result=source.preflight(d,str(video),dict(ffprobe='probe'),dict(selectedEngines=['drama3'],sourceLanguageOverride='ja'))
    self.assertEqual(result['language'],'ja');self.assertFalse(result['needsConfirmation']);self.assertTrue(result['explicitOverride'])
 def test_detected_japanese_with_conflicting_track_tag_is_automatic(self):
  for platform in ['win32','darwin']:
   with self.subTest(platform=platform),tempfile.TemporaryDirectory() as d:
    video=Path(d)/'source.mkv';video.write_bytes(b'fixture');meta=dict(streams=[dict(index=1,codec_type='audio',tags=dict(language='eng'))],format=dict(duration='100'))
    heard=dict(language='ja',method='audio-probe',probability=.95)
    samples=[json.dumps(heard).encode()] if platform=='win32' else [json.dumps(meta).encode(),json.dumps(heard).encode()]
    with patch.object(source.sys,'platform',platform),patch('source_access.accessible',return_value=(video,json.dumps(meta).encode())),patch('runtime_paths.python_for',return_value=Path(sys.executable)),patch('source_preparation.Preparation.capture',side_effect=samples):
     result=source.preflight(d,str(video),dict(ffprobe='probe',ffmpeg='ffmpeg'),dict(selectedEngines=['drama3']))
    self.assertEqual(result['language'],'ja');self.assertTrue(result['metadataConflict']);self.assertFalse(result['needsConfirmation'])
 def test_metadata_probe_is_cached_but_confirmation_token_tracks_engine_choice(self):
  with tempfile.TemporaryDirectory() as d:
   video=Path(d)/'source.mkv';video.write_bytes(b'fixture')
   meta=dict(streams=[dict(index=1,codec_type='audio',tags=dict(language='eng'))])
   with patch('source_preparation.Preparation.capture',return_value=json.dumps(meta).encode()) as probe:
    a=source.preflight(d,str(video),dict(ffprobe='probe'),dict(selectedEngines=['drama3'],autoApproveSourceLanguage=False))
    b=source.preflight(d,str(video),dict(ffprobe='probe'),dict(selectedEngines=['gpt-sovits-v2'],autoApproveSourceLanguage=False))
    self.assertEqual(probe.call_count,1);self.assertTrue(a['needsConfirmation']);self.assertTrue(a['supported'])
    self.assertNotEqual(a['token'],b['token'])
 def test_windows_preflight_uses_readable_cloud_copy(self):
  with tempfile.TemporaryDirectory() as d:
   video=Path(d)/'source.mkv';video.write_bytes(b'fixture')
   local=Path(d)/'cached.mkv'
   meta=dict(streams=[dict(index=1,codec_type='audio',tags=dict(language='jpn'))])
   with patch.object(source.sys,'platform','win32'),patch('source_access.accessible',return_value=(local,json.dumps(meta).encode())) as readable,patch.object(source.subprocess,'check_output') as direct:
    result=source.preflight(d,str(video),dict(ffprobe='probe'),dict(selectedEngines=['drama3']))
   self.assertEqual(result['language'],'ja')
   readable.assert_called_once_with(str(video),'probe',d)
   direct.assert_not_called()
 def test_the_request_records_how_the_source_language_was_detected(self):
  with tempfile.TemporaryDirectory() as d:
   video=Path(d)/'source.mkv';video.write_bytes(b'fixture')
   meta=dict(streams=[dict(index=1,codec_type='audio',tags=dict(language='jpn'))])
   with patch('source_preparation.Preparation.capture',return_value=json.dumps(meta).encode()):
    result=source.preflight(d,str(video),dict(ffprobe='probe'),dict(selectedEngines=['drama3']))
   self.assertEqual(result['detectedLanguage'],'ja');self.assertEqual(result['detectionSource'],'audio-stream-metadata')
   self.assertEqual(result['name'],'Japanese');self.assertFalse(result['needsConfirmation'])
   detection=result['detection']
   for field,value in [('language','ja'),('detectedLanguage','ja'),('method','audio-stream-metadata'),('stream',1)]:
    self.assertEqual(detection[field],value)
   self.assertFalse(detection['explicitOverride']);self.assertTrue(detection['confirmationSkipped'])
 def test_a_non_japanese_source_still_asks_and_keeps_the_detected_language(self):
  with tempfile.TemporaryDirectory() as d:
   video=Path(d)/'source.mkv';video.write_bytes(b'fixture')
   meta=dict(streams=[dict(index=2,codec_type='audio',tags=dict(language='eng'))])
   with patch('source_preparation.Preparation.capture',return_value=json.dumps(meta).encode()):
    result=source.preflight(d,str(video),dict(ffprobe='probe'),dict(selectedEngines=['drama3'],autoApproveSourceLanguage=False))
   self.assertEqual(result['language'],'en');self.assertEqual(result['detectedLanguage'],'en')
   self.assertTrue(result['needsConfirmation'])
   self.assertFalse(result['detection']['confirmationSkipped']);self.assertFalse(result['detection']['explicitOverride'])
   self.assertEqual(result['detection']['stream'],2)
 def test_an_explicit_selection_keeps_the_detected_language(self):
  with tempfile.TemporaryDirectory() as d:
   video=Path(d)/'source.mkv';video.write_bytes(b'fixture')
   meta=dict(streams=[dict(index=1,codec_type='audio',tags=dict(language='eng'))])
   with patch('source_preparation.Preparation.capture',return_value=json.dumps(meta).encode()):
    result=source.preflight(d,str(video),dict(ffprobe='probe'),dict(selectedEngines=['drama3'],sourceLanguageOverride='ko',autoApproveSourceLanguage=False))
   self.assertEqual(result['language'],'ko');self.assertEqual(result['detectedLanguage'],'en')
   self.assertTrue(result['explicitOverride']);self.assertTrue(result['needsConfirmation'])
   detection=result['detection']
   self.assertEqual(detection['method'],'user-selected-source');self.assertTrue(detection['explicitOverride'])
   self.assertEqual(detection['detectedLanguage'],'en');self.assertFalse(detection['confirmationSkipped'])
 def detected_language_preflight(self,d,language_tag,engines,listen_error=None,**settings):
  video=Path(d)/'source.mkv'
  # Write once. A rewrite would change the modification time, and the cache key
  # carries that time, so a second load in the same test would miss its own record.
  if not video.exists():video.write_bytes(b'fixture')
  meta=dict(format=dict(duration='120'),streams=[dict(index=1,codec_type='audio',tags=dict(language=language_tag))])
  params=dict(dict(selectedEngines=engines),**settings)
  # The second capture is the audio probe. An empty result means the probe
  # heard nothing. A raised fault means the probe could not run at all. Neither
  # outcome says the file label is wrong.
  listen=b'{}' if listen_error is None else listen_error
  with patch('source_preparation.Preparation.capture',side_effect=[json.dumps(meta).encode(),listen]):
   return source.preflight(d,str(video),dict(ffprobe='probe',ffmpeg='ffmpeg'),params)
 def test_auto_approval_starts_with_the_detected_language_and_never_asks(self):
  with tempfile.TemporaryDirectory() as d:
   result=self.detected_language_preflight(d,'eng',['drama3'])
   self.assertEqual(result['language'],'en');self.assertFalse(result['needsConfirmation'])
   self.assertTrue(result['supported']);self.assertTrue(result['detection']['confirmationSkipped'])
   self.assertTrue(result['detection']['autoApproveSetting'])
 def test_turning_auto_approval_off_restores_the_confirmation(self):
  with tempfile.TemporaryDirectory() as d:
   result=self.detected_language_preflight(d,'eng',['drama3'],autoApproveSourceLanguage=False)
   self.assertTrue(result['needsConfirmation'])
   self.assertFalse(result['detection']['confirmationSkipped'])
   self.assertFalse(result['detection']['autoApproveSetting'])
 def test_auto_approval_continues_in_japanese_when_no_language_was_heard(self):
  # Reported on Windows: the switch was on and the app still asked. With nothing heard and
  # no label inside the file, the run continues in the source language this product is
  # built for, and the record says the choice was an assumption rather than a detection.
  with tempfile.TemporaryDirectory() as d:
   result=self.detected_language_preflight(d,'und',['drama3'])
   self.assertEqual(result['language'],'ja');self.assertFalse(result['needsConfirmation'])
   self.assertTrue(result['supported']);self.assertEqual(result['confirmReason'],'')
   self.assertTrue(result['assumedSourceLanguage'])
   self.assertTrue(result['detection']['assumedSourceLanguage'])
   self.assertIsNone(result['detection']['detectedLanguage'])
   self.assertTrue(result['detection']['confirmationSkipped'])
 def test_turning_the_switch_off_still_asks_when_no_language_was_heard(self):
  with tempfile.TemporaryDirectory() as d:
   result=self.detected_language_preflight(d,'und',['drama3'],autoApproveSourceLanguage=False)
   self.assertIsNone(result['language']);self.assertTrue(result['needsConfirmation'])
   self.assertEqual(result['confirmReason'],'switch-off')
   self.assertFalse(result['assumedSourceLanguage'])
   self.assertFalse(result['detection']['confirmationSkipped'])
 def test_auto_approval_still_asks_when_the_voice_engine_cannot_read_the_language(self):
  with tempfile.TemporaryDirectory() as d:
   result=self.detected_language_preflight(d,'fra',['gpt-sovits-v2'])
   self.assertEqual(result['language'],'fr');self.assertFalse(result['supported'])
   self.assertTrue(result['needsConfirmation']);self.assertTrue(result['reason'])
   self.assertFalse(result['detection']['confirmationSkipped'])
 def test_japanese_never_asks_even_when_auto_approval_is_off(self):
  with tempfile.TemporaryDirectory() as d:
   result=self.detected_language_preflight(d,'jpn',['drama3'],autoApproveSourceLanguage=False)
   self.assertEqual(result['language'],'ja');self.assertFalse(result['needsConfirmation'])
   self.assertTrue(result['detection']['confirmationSkipped'])
 def test_a_metadata_conflict_autopicks_the_heard_language_when_the_switch_is_on(self):
  with tempfile.TemporaryDirectory() as d:
   video=Path(d)/'source.mkv';video.write_bytes(b'fixture')
   meta=dict(format=dict(duration='100'),streams=[dict(index=1,codec_type='audio',tags=dict(language='jpn'))])
   heard=dict(language='ko',stream=1,method='three-audio-samples',samples=[])
   with patch('source_preparation.Preparation.capture',side_effect=[json.dumps(meta).encode(),json.dumps(heard).encode()]):
    result=source.preflight(d,str(video),dict(ffprobe='probe',ffmpeg='ffmpeg'),dict(selectedEngines=['drama3']))
   self.assertTrue(result['metadataConflict']);self.assertEqual(result['language'],'ko')
   self.assertFalse(result['needsConfirmation']);self.assertTrue(result['detection']['confirmationSkipped'])
 def three_agreeing_samples_below_one_confidence_bar(self):
  from types import SimpleNamespace
  model=Mock();model.detect_language.side_effect=[('ja',.9462,[]),('ja',.7943,[]),('ja',.8468,[])]
  numpy_stub=SimpleNamespace(frombuffer=lambda raw,dtype=None:[1.0]*32000,float32=float,
    abs=lambda values:values,max=lambda values,initial=0:max(values,default=initial))
  return model,numpy_stub
 def test_agreeing_samples_and_a_matching_stream_label_form_a_consensus(self):
  model,numpy_stub=self.three_agreeing_samples_below_one_confidence_bar()
  request=dict(storage='root',video='movie',duration=120,stream=1,ffmpeg='ffmpeg',speechModel='whisper',metadataLanguage='ja')
  with patch.dict(sys.modules,{'numpy':numpy_stub}),patch('whisper_accel.load',return_value=model),patch.object(source.subprocess,'check_output',return_value=b'\0'*65536):
   result=source.probe(request)
  self.assertEqual(result['language'],'ja')
  self.assertEqual(result['method'],'three-audio-samples+stream-metadata')
  self.assertEqual(len(result['samples']),3)
 def test_the_same_samples_without_a_matching_label_stay_unconfirmed(self):
  for label in [None,'en','']:
   model,numpy_stub=self.three_agreeing_samples_below_one_confidence_bar()
   request=dict(storage='root',video='movie',duration=120,stream=1,ffmpeg='ffmpeg',speechModel='whisper')
   if label is not None:request['metadataLanguage']=label
   with self.subTest(label=label),patch.dict(sys.modules,{'numpy':numpy_stub}),patch('whisper_accel.load',return_value=model),patch.object(source.subprocess,'check_output',return_value=b'\0'*65536):
    result=source.probe(request)
   self.assertIsNone(result['language'],'audio evidence alone must not clear the gate at this confidence');self.assertEqual(result['method'],'three-audio-samples')
 def test_a_stream_label_cannot_replace_two_agreeing_audio_samples(self):
  from types import SimpleNamespace
  model=Mock();model.detect_language.side_effect=[('ja',.9462,[]),('en',.9310,[]),('ja',.4,[])]
  numpy_stub=SimpleNamespace(frombuffer=lambda raw,dtype=None:[1.0]*32000,float32=float,
    abs=lambda values:values,max=lambda values,initial=0:max(values,default=initial))
  request=dict(storage='root',video='movie',duration=120,stream=1,ffmpeg='ffmpeg',speechModel='whisper',metadataLanguage='ja')
  with patch.dict(sys.modules,{'numpy':numpy_stub}),patch('whisper_accel.load',return_value=model),patch.object(source.subprocess,'check_output',return_value=b'\0'*65536):
   result=source.probe(request)
  self.assertIsNone(result['language'],'three audio samples must agree before a label can carry the decision')
 def test_the_audio_probe_request_carries_the_stream_label(self):
  with tempfile.TemporaryDirectory() as d:
   video=Path(d)/'source.mkv';video.write_bytes(b'fixture')
   meta=dict(streams=[dict(index=1,codec_type='audio',tags=dict(language='jpn'))],format=dict(duration='120'))
   with patch('source_preparation.Preparation.capture',return_value=json.dumps(meta).encode()):
    source.preflight(d,str(video),dict(ffprobe='probe',ffmpeg='ffmpeg'),dict(selectedEngines=['drama3']))
   folder=Path(d)/'source-language';keys=list(folder.iterdir())
   self.assertTrue(keys)
   request=json.loads((keys[0]/'request.json').read_text(encoding='utf-8'))
   self.assertEqual(request['metadataLanguage'],'ja');self.assertEqual(request['stream'],1)
 def speech_fault(self):
  return subprocess.CalledProcessError(1,'speech-worker',stderr=b'Speech model folder is empty')
 def test_a_listen_that_cannot_run_keeps_the_file_label_and_never_asks(self):
  # Reported on Windows: auto-approve was on and the app still asked. A listen
  # step that could not run must not throw away the language label in the file.
  with tempfile.TemporaryDirectory() as d:
   result=self.detected_language_preflight(d,'eng',['drama3'],listen_error=self.speech_fault())
   self.assertEqual(result['language'],'en');self.assertFalse(result['needsConfirmation'])
   self.assertTrue(result['supported']);self.assertEqual(result['confirmReason'],'')
   self.assertEqual(result['detection']['confirmReason'],'')
   self.assertTrue(result['detection']['listenFailure'])
   self.assertIn('Speech model folder is empty',result['listenFailure'])
   self.assertEqual(result['detection']['method'],'audio-stream-metadata')
 def test_a_saved_listen_fault_is_reused_and_still_never_asks(self):
  with tempfile.TemporaryDirectory() as d:
   first=self.detected_language_preflight(d,'eng',['drama3'],listen_error=self.speech_fault())
   second=self.detected_language_preflight(d,'eng',['drama3'])
   self.assertEqual(first['cacheKey'],second['cacheKey'])
   self.assertEqual(second['language'],'en');self.assertFalse(second['needsConfirmation'])
   self.assertIn('Speech model folder is empty',second['listenFailure'])
 def test_a_listen_that_cannot_run_with_no_label_continues_without_asking(self):
  # A speech model that is not installed used to stop the queue here. The listen fault stays
  # in the record, and the run continues in the assumed source language instead.
  with tempfile.TemporaryDirectory() as d:
   result=self.detected_language_preflight(d,'und',['drama3'],listen_error=self.speech_fault())
   self.assertEqual(result['language'],'ja');self.assertFalse(result['needsConfirmation'])
   self.assertEqual(result['confirmReason'],'')
   self.assertEqual(result['detection']['confirmReason'],'')
   self.assertTrue(result['detection']['listenFailure'])
   self.assertTrue(result['assumedSourceLanguage'])
   self.assertIn('Speech model folder is empty',result['listenFailure'])
 def test_an_empty_listen_with_no_label_marks_the_language_as_assumed(self):
  with tempfile.TemporaryDirectory() as d:
   result=self.detected_language_preflight(d,'und',['drama3'])
   self.assertEqual(result['confirmReason'],'')
   self.assertEqual(result['language'],'ja')
   self.assertTrue(result['assumedSourceLanguage'])
   self.assertEqual(result['listenFailure'],'')
 def test_turning_the_switch_off_names_the_switch_as_the_reason(self):
  with tempfile.TemporaryDirectory() as d:
   result=self.detected_language_preflight(d,'eng',['drama3'],autoApproveSourceLanguage=False)
   self.assertTrue(result['needsConfirmation'])
   self.assertEqual(result['confirmReason'],'switch-off')
   self.assertEqual(result['detection']['confirmReason'],'switch-off')
 def test_an_engine_that_cannot_read_the_language_names_that_reason(self):
  with tempfile.TemporaryDirectory() as d:
   result=self.detected_language_preflight(d,'fra',['gpt-sovits-v2'])
   self.assertTrue(result['needsConfirmation'])
   self.assertEqual(result['confirmReason'],'engine-language-mismatch')
 def test_an_older_unconfirmed_listen_record_is_computed_again(self):
  # An older build saved a failed listen as an unconfirmed language. That record
  # must not keep asking after the rule is fixed.
  with tempfile.TemporaryDirectory() as d:
   self.detected_language_preflight(d,'eng',['drama3'])
   records=sorted((Path(d)/'source-language').glob('*/result.json'))
   self.assertTrue(records)
   for record in records:record.write_text(json.dumps(dict(method='unconfirmed-audio',language=None)),encoding='utf-8')
   result=self.detected_language_preflight(d,'eng',['drama3'])
   self.assertEqual(result['language'],'en');self.assertFalse(result['needsConfirmation'])
   saved=json.loads(records[0].read_text(encoding='utf-8'))
   self.assertEqual(saved['method'],'audio-stream-metadata');self.assertEqual(saved['language'],'en')
 def test_a_majority_of_agreeing_samples_below_the_bar_is_a_reading_not_a_guess(self):
  samples=[dict(language=language,confidence=confidence) for language,confidence in
           [('zh',.71),('zh',.66),('zh',.80)]]
  self.assertEqual(source.majority_language(samples),'zh')
  # One sample alone is not a majority, and a split vote decides nothing.
  self.assertIsNone(source.majority_language([dict(language='zh',confidence=.9)]))
  self.assertIsNone(source.majority_language([dict(language='zh',confidence=.9),dict(language='ja',confidence=.9)]))
  # Weak votes stay weak: 0.45 across three samples says nothing about the speech.
  self.assertIsNone(source.majority_language([dict(language='zh',confidence=.45)]*3))
  # A language outside the supported list can never be adopted.
  self.assertIsNone(source.majority_language([dict(language='xx',confidence=.9)]*2))
 def auto_listen_preflight(self,d,listen,**settings):
  # No audio label in the file, so only the listening samples can decide.
  video=Path(d)/'source.mkv';video.write_bytes(b'fixture')
  meta=dict(format=dict(duration='120'),streams=[dict(index=1,codec_type='audio',tags=dict(language='und'))])
  params=dict(dict(selectedEngines=['drama3']),**settings)
  with patch('source_preparation.Preparation.capture',side_effect=[json.dumps(meta).encode(),listen]):
   return source.preflight(d,str(video),dict(ffprobe='probe',ffmpeg='ffmpeg'),params)
 def test_auto_approval_adopts_the_one_language_all_the_samples_heard(self):
  # Reported on macOS: the switch was on, three samples all named Mandarin, and the
  # preview still said nothing was found. A shared reading wins over a default nobody heard.
  heard=dict(language=None,method='three-audio-samples',
             samples=[dict(language='zh',confidence=.71),dict(language='zh',confidence=.66),dict(language='zh',confidence=.8)])
  with tempfile.TemporaryDirectory() as d:
   result=self.auto_listen_preflight(d,json.dumps(heard).encode())
   self.assertEqual(result['language'],'zh');self.assertEqual(result['detectedLanguage'],'zh')
   self.assertFalse(result['assumedSourceLanguage']);self.assertFalse(result['needsConfirmation'])
   self.assertEqual(result['languageEvidence'],'audio-samples-majority')
   self.assertEqual(result['detection']['languageEvidence'],'audio-samples-majority')
   self.assertTrue(result['detection']['confirmationSkipped'])
 def test_a_split_or_weak_listen_still_falls_back_without_asking(self):
  for name,samples in [('split',[dict(language='zh',confidence=.7),dict(language='ja',confidence=.7)]),
                       ('weak',[dict(language='zh',confidence=.4)]*3)]:
   with self.subTest(listen=name),tempfile.TemporaryDirectory() as d:
    heard=dict(language=None,method='three-audio-samples',samples=samples)
    result=self.auto_listen_preflight(d,json.dumps(heard).encode())
    self.assertEqual(result['language'],'ja');self.assertTrue(result['assumedSourceLanguage'])
    self.assertEqual(result['languageEvidence'],'three-audio-samples')
    self.assertFalse(result['needsConfirmation'])
 def listen_with_no_language_at_all(self,d,extra=(),**settings):
  video=Path(d)/'source.mkv';video.write_bytes(b'fixture')
  streams=[dict(index=1,codec_type='audio',tags=dict(language='und')),*extra]
  meta=dict(format=dict(duration='120'),streams=streams)
  params=dict(dict(selectedEngines=['drama3']),**settings)
  with patch('source_preparation.Preparation.capture',side_effect=[json.dumps(meta).encode(),b'{}']):
   return source.preflight(d,str(video),dict(ffprobe='probe',ffmpeg='ffmpeg'),params)
 def test_a_tagged_subtitle_track_records_the_dialogue_language_of_the_file(self):
  # A Chinese caption track is content evidence. It is recorded and shown, and it never
  # replaces the audio language, because recognition must match what was actually recorded.
  with tempfile.TemporaryDirectory() as d:
   result=self.listen_with_no_language_at_all(d,extra=[dict(index=2,codec_type='subtitle',codec_name='subrip',tags=dict(language='chi'))])
   self.assertEqual(result['language'],'ja');self.assertTrue(result['assumedSourceLanguage'])
   self.assertEqual(result['subtitleLanguage'],'zh')
   self.assertEqual(result['subtitleMethod'],'subtitle-track-tag')
   self.assertEqual(result['detection']['subtitleLanguage'],'zh')
   self.assertEqual(result['detection']['subtitleTrack'],2)
 def test_an_untagged_subtitle_track_is_read_to_find_its_script(self):
  srt=b'1\n00:00:01,000 --> 00:00:03,000\n\xe5\xa4\xa7\xe5\xae\xb6\xe5\xa5\xbd\xe5\x97\x8e\n\n'
  with tempfile.TemporaryDirectory() as d:
   video=Path(d)/'source.mkv';video.write_bytes(b'fixture')
   meta=dict(format=dict(duration='120'),streams=[dict(index=1,codec_type='audio',tags=dict(language='und')),
          dict(index=2,codec_type='subtitle',codec_name='mov_text',tags=dict(language='und'))])
   with patch('source_preparation.Preparation.capture',side_effect=[json.dumps(meta).encode(),b'{}',srt]):
    result=source.preflight(d,str(video),dict(ffprobe='probe',ffmpeg='ffmpeg'),dict(selectedEngines=['drama3']))
   self.assertEqual(result['subtitleLanguage'],'zh')
   self.assertEqual(result['subtitleMethod'],'subtitle-script-reading')
   self.assertEqual(result['language'],'ja');self.assertTrue(result['assumedSourceLanguage'])
 def test_a_caption_that_cannot_be_read_never_stops_the_preflight(self):
  fault=subprocess.CalledProcessError(1,'ffmpeg',stderr=b'Invalid data found when processing input')
  with tempfile.TemporaryDirectory() as d:
   video=Path(d)/'source.mkv';video.write_bytes(b'fixture')
   meta=dict(format=dict(duration='120'),streams=[dict(index=1,codec_type='audio',tags=dict(language='und')),
          dict(index=2,codec_type='subtitle',codec_name='subrip',tags=dict(language='und'))])
   with patch('source_preparation.Preparation.capture',side_effect=[json.dumps(meta).encode(),b'{}',fault]):
    result=source.preflight(d,str(video),dict(ffprobe='probe',ffmpeg='ffmpeg'),dict(selectedEngines=['drama3']))
   self.assertEqual(result['subtitleLanguage'],None)
   self.assertEqual(result['subtitleMethod'],'subtitle-unreadable')
   self.assertEqual(result['language'],'ja');self.assertFalse(result['needsConfirmation'])
 def test_a_readable_subtitle_never_overrides_the_explicit_language(self):
  with tempfile.TemporaryDirectory() as d:
   result=self.listen_with_no_language_at_all(d,extra=[dict(index=2,codec_type='subtitle',codec_name='subrip',tags=dict(language='zho'))],
                                              sourceLanguageOverride='en')
   # The caption language is still recorded, but the user's choice decides the run.
   self.assertEqual(result['language'],'en');self.assertEqual(result['subtitleLanguage'],'zh')
   self.assertTrue(result['explicitOverride'])
