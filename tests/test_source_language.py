import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import source_language as source

class SourceLanguageTests(unittest.TestCase):
 def test_english_subtitle_cannot_turn_japanese_audio_into_english(self):
  meta=dict(streams=[dict(index=1,codec_type='audio',tags=dict(language='jpn')),dict(index=2,codec_type='subtitle',tags=dict(language='eng'))])
  self.assertEqual(source.metadata(meta)['language'],'ja')
 def test_selected_default_audio_is_the_detection_and_processing_source(self):
  streams=[dict(index=1,codec_type='audio',tags=dict(language='jpn')),dict(index=3,codec_type='audio',tags=dict(language='eng'),disposition=dict(default=1))]
  self.assertEqual(source.metadata(dict(streams=streams)),dict(language='en',stream=3,method='audio-stream-metadata'))
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
 def test_metadata_probe_is_cached_but_confirmation_token_tracks_engine_choice(self):
  with tempfile.TemporaryDirectory() as d:
   video=Path(d)/'source.mkv';video.write_bytes(b'fixture')
   meta=dict(streams=[dict(index=1,codec_type='audio',tags=dict(language='eng'))])
   with patch.object(source.subprocess,'check_output',return_value=json.dumps(meta).encode()) as probe:
    a=source.preflight(d,str(video),dict(ffprobe='probe'),dict(selectedEngines=['drama3']))
    b=source.preflight(d,str(video),dict(ffprobe='probe'),dict(selectedEngines=['gpt-sovits-v2']))
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
