"""Real Windows settings → native projection → shared worker contract coverage."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'windows'),str(ROOT/'Resources')]
from desktop_state import Store,defaults,read,write
from workflow_settings import COMBINED,AUDIO_ONLY,validated
from native_worker import configure,project_request
import translation_source

class WindowsWorkflowContractTests(unittest.TestCase):
 def fixture(self,root):
  package=root/'package';(package/'tools').mkdir(parents=True);(package/'tools/AniCanto-helper.exe').touch()
  for name in ('ffmpeg','ffprobe'):(root/(name+'.exe')).touch()
  # An old Small receipt must not change new default submissions.
  write(root/'drama3-windows-ready.json',dict(modelLoadPassed=True,speechInferencePassed=True,variant='drama3-small-iq3',backend='cuda'))
  write(root/'gpt-windows-ready.json',dict(modelLoadPassed=True,speechInferencePassed=True,speechVersions=['v2ProPlus'],modelVersions=['v2ProPlus'],backend='nvidia'))
  ready=dict(modelLoadPassed=True,speechInferencePassed=True,backend='nvidia',ffmpeg=str(root/'ffmpeg.exe'),ffprobe=str(root/'ffprobe.exe'),textModel='qwen3.5:9b-canto-pinned',roles=dict(asr='asr-native-1.7b',speech='whisper-large-v3',referenceSpeech='whisper-small',visual='qwen3.5:9b',voice='v2ProPlus'))
  return package,ready
 def test_actual_desktop_defaults_are_accepted_by_shared_source_policy(self):
  for language in ('en','zh-HK'):
   with self.subTest(language=language):
    cfg=defaults(language);self.assertEqual(cfg['translationSource'],translation_source.COMBINED);translation_source.configure(cfg)
 def test_old_state_is_migrated_without_rewriting_submitted_request(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);store=Store(root);store.add([root/'episode.mkv']);row=store.row();request=store.submit(row);old=read(request);old['translationSource']='combined';write(request,old);row['status']='paused';store.settings['translationSource']='combined';store.save();before=request.read_bytes()
   restored=Store(root);self.assertEqual(restored.settings['translationSource'],COMBINED);self.assertEqual(restored.submit(restored.row()),request);self.assertEqual(request.read_bytes(),before)
   package,ready=self.fixture(root);projection=project_request('batch',read(request),ready,root,package)
   self.assertEqual(projection['translationSource'],COMBINED);self.assertEqual(request.read_bytes(),before)
 def test_fresh_submission_is_canonical_even_if_legacy_preset_is_in_memory(self):
  with tempfile.TemporaryDirectory() as d:
   store=Store(d);store.add([Path(d)/'episode.mkv']);store.settings['translationSource']='combined';request=store.submit(store.row());self.assertEqual(read(request)['translationSource'],COMBINED)
 def test_legacy_nested_editor_and_preview_are_projected_without_source_changes(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);package,ready=self.fixture(root);review=root/'review.json';write(review,dict(config=dict(storage=str(root),translationSource='combined',ttsBackend='drama3',selectedEngines=['drama3']),cues=[]))
   submission=root/'draft.json';write(submission,dict(id='editor',review=str(review),settings=dict(translationSource='combined'),previewSegment='cue-0',previewEngine='drama3'))
   before={p:p.read_bytes() for p in (review,submission)}
   result=project_request('render-project',dict(storage=str(root),submission=str(submission),selectedEngines=['drama3'],translationSource='combined'),ready,root,package)
   self.assertEqual(result['translationSource'],COMBINED);self.assertEqual(read(result['submission'])['settings']['translationSource'],COMBINED)
   for path,data in before.items():self.assertEqual(path.read_bytes(),data)
 def test_audio_only_still_excludes_caption_evidence_and_retains_output_tracks(self):
  cfg=dict(defaults(),translationSource=AUDIO_ONLY,subtitle='source.srt',ocr=True);result=validated(cfg)
  self.assertEqual(result['subtitleSource'],'none');self.assertFalse(result['ocr']);self.assertFalse(result['batchAutoSubtitles']);self.assertEqual(result['subtitleModes'],['yue','english','dual','original']);self.assertTrue(result['includeOriginal']);self.assertEqual(cfg['subtitle'],'source.srt')
 def test_unknown_values_are_rejected_before_native_service_or_downloads(self):
  with self.assertRaisesRegex(ValueError,'Unknown translation source'):validated(dict(translationSource='typo'))
  with self.assertRaisesRegex(ValueError,'Unknown translation source'):configure(dict(translationSource='typo'),{})
 def test_native_batch_reaches_real_shared_conversion_and_core_plan(self):
  import worker,studio_core,model_recovery,native_models
  events=[];frozen=[];probes=[];freeze=studio_core.freeze
  if not studio_core.executable().is_file():self.skipTest('Shared core unavailable')
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);package,ready=self.fixture(root);video=root/'日本語 episode.mkv';video.touch()
   def run(args,*a,**kw):
    if '-show_format' in args:
     probes.append(list(args));raise RuntimeError('expected-media-probe-boundary')
    return json.dumps(dict(streams=[dict(index=2,codec_type='subtitle',codec_name='subrip',tags=dict(language='chi'))]))
   def capture_freeze(cfg):
    result=freeze(cfg);frozen.append(copy.deepcopy(cfg));return result
   for language in ('en','zh-HK'):
    for source in (COMBINED,'combined',AUDIO_ONLY):
     with self.subTest(language=language,source=source):
      events.clear();frozen.clear();probes.clear();submitted=dict(defaults(language),storage=str(root),video=str(video),videos=[dict(id='episode',video=str(video))],translationSource=source)
      projected=project_request('batch',submitted,ready,root,package)
      with patch.object(worker,'run',side_effect=run),patch.object(worker,'emit',side_effect=lambda stage,message,*a,**kw:events.append((stage,message))),patch.object(model_recovery,'recover',side_effect=native_models.recover),patch.object(studio_core,'freeze',side_effect=capture_freeze):worker.batch_convert(projected)
      self.assertEqual(len(probes),1,events);self.assertEqual(len(frozen),1,events);self.assertIn('productionPlan',frozen[0]);self.assertEqual(frozen[0]['translationSource'],AUDIO_ONLY if source==AUDIO_ONLY else COMBINED)
      self.assertIn(('批量錯誤','expected-media-probe-boundary'),events);self.assertFalse(any('Unknown translation source' in message for stage,message in events))
if __name__=='__main__':unittest.main()
