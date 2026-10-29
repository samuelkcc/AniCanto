import copy,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows'),str(ROOT/'studio'),str(ROOT/'tests')]
import primary_source as p,source_workflow as f
from atomic_files import write_json
class WorkflowTests(unittest.TestCase):
 def cfg(self,**kw):return dict(sourcePolicyRevision=p.REVISION,sourceAllocationRevision=p.ALLOCATION_REVISION,sourceWorkflowRevision=f.LEGACY_REVISION,interfaceMode='expert',sourceWorkflow='auto',defaultSubtitleWorkflow='subtitles-speech',defaultOCRWorkflow='ocr-speech',translationSource='audio-and-subtitles',sourceLanguage='ja',model='test',port=0,**kw)
 def route(self,cfg,has_text=True):
  meta=dict(streams=[dict(index=2,codec_type='subtitle',codec_name='subrip')] if has_text else [])
  return f.configure(cfg,meta,lambda rows,*args:rows[0] if rows else None)
 def test_defaults_are_subtitles_first_or_ocr_first(self):
  a=self.route(self.cfg());b=self.route(self.cfg(),False);self.assertEqual(a['sourceWorkflowEffective'],'subtitles-speech');self.assertEqual(b['sourceWorkflowEffective'],'ocr-speech');self.assertFalse(a['ocr']);self.assertTrue(b['ocr'])
 def test_four_explicit_paths_have_correct_priority(self):
  for choice,has_text,priority in [('speech-subtitles',True,'speech'),('subtitles-speech',True,'subtitles'),('speech-ocr',False,'speech'),('ocr-speech',False,'ocr')]:
   cfg=self.cfg();cfg['sourceWorkflow']=choice;self.route(cfg,has_text);self.assertEqual(cfg['sourceWorkflowEffective'],choice);self.assertEqual(f.priority(cfg),priority)
 def test_basic_ignores_expert_override_but_uses_preferences(self):
  cfg=self.cfg();cfg.update(interfaceMode='basic',sourceWorkflow='speech-subtitles');self.route(cfg);self.assertEqual(cfg['sourceWorkflowEffective'],'subtitles-speech')
  cfg=self.cfg();cfg.update(interfaceMode='basic',defaultSubtitleWorkflow='speech-subtitles',defaultOCRWorkflow='speech-ocr');self.route(cfg);self.assertEqual(f.priority(cfg),'speech');self.route(cfg,False);self.assertEqual(cfg['sourceWorkflowEffective'],'speech-ocr')
 def test_ocr_is_not_used_when_text_track_exists(self):
  cfg=self.cfg();cfg.update(sourceWorkflow='ocr-speech',ocr=True,translationSource='audio-and-ocr',subtitleSource='burned');
  with self.assertRaisesRegex(ValueError,'does not match'):self.route(cfg)
 def test_explicit_missing_track_is_an_error_and_audio_only_stays_audio_only(self):
  cfg=self.cfg();cfg.update(batchExplicitStream=True,subtitleStream=7)
  with self.assertRaises(ValueError):self.route(cfg)
  cfg=self.cfg();cfg['translationSource']='audio-only';self.route(cfg);self.assertEqual(cfg['sourceWorkflowEffective'],'speech-only')
 def test_old_requests_are_not_migrated(self):
  cfg=self.cfg();cfg.pop('sourceWorkflowRevision');before=copy.deepcopy(cfg);self.route(cfg,False);self.assertEqual(cfg,before)
 def test_external_subtitle_has_priority_over_embedded_detection(self):
  with tempfile.TemporaryDirectory() as d:
   s=Path(d)/'a.srt';s.write_text('test');cfg=self.cfg();cfg['subtitle']=str(s);self.route(cfg,False);self.assertEqual(cfg['subtitleSource'],'external');self.assertEqual(f.priority(cfg),'subtitles')
 def test_source_conflict_resolver_and_prompts_follow_all_four_paths(self):
  for choice,has_text in [('speech-subtitles',True),('subtitles-speech',True),('speech-ocr',False),('ocr-speech',False)]:
   with self.subTest(choice=choice),tempfile.TemporaryDirectory() as d:
    job=Path(d);write_json(job/'subtitle-context.json',[dict(start=0,end=2,text='不要開窗')]);cfg=self.cfg();cfg['sourceWorkflow']=choice;self.route(cfg,has_text);cue=dict(start=0,end=2,japanese='窓を開けて',text='窓を開けて',enabled=True)
    w=SimpleNamespace(atomic_json=write_json,emit=lambda *a,**k:None,ollama_chat=lambda *a,**k:self.fail('Unshared caption must not need allocation'))
    p.prepare(w,cfg,job,[cue]);expected='窓を開けて' if choice.startswith('speech-') else '不要開窗';self.assertEqual(p.content(cue),expected);self.assertEqual(cue['japanese'],'窓を開けて');self.assertEqual((cue['start'],cue['end']),(0,2))
 def test_missing_primary_uses_auxiliary_and_records_it_but_conflicts_keep_primary(self):
  for choice,has_text in [('speech-subtitles',True),('subtitles-speech',True),('speech-ocr',False),('ocr-speech',False)]:
   with self.subTest(choice=choice),tempfile.TemporaryDirectory() as d:
    job=Path(d);cfg=self.cfg();cfg['sourceWorkflow']=choice;self.route(cfg,has_text);speech_first=choice.startswith('speech-');write_json(job/'subtitle-context.json',[dict(start=0,end=2,text='不要開窗')] if speech_first else [])
    cue=dict(start=0,end=2,japanese='' if speech_first else '窓を開けて',enabled=True)
    w=SimpleNamespace(atomic_json=write_json,emit=lambda *a,**k:None);p.prepare(w,cfg,job,[cue]);self.assertTrue(cue['sourcePrimaryFallback']);self.assertEqual(p.content(cue),'不要開窗' if speech_first else '窓を開けて');self.assertEqual(json.loads((job/'source-policy.json').read_text())['primaryFallbacks'],[1])
 def test_invalid_preferences_are_rejected(self):
  for key in ['sourceWorkflow','defaultSubtitleWorkflow','defaultOCRWorkflow']:
   cfg=self.cfg();cfg[key]='bad'
   with self.assertRaises(ValueError):f.validate(cfg)
class SubmissionWorkflowTests(unittest.TestCase):
 def setUp(self):
  import test_shared_studio as shared
  self.f=shared.SharedStudioTests('test_basic_submit_uses_automatic_captions_and_preserves_japanese_and_background');self.f.setUp();self.addCleanup(self.f.tearDown)
 def test_new_requests_freeze_preference_defaults_and_basic_is_automatic(self):
  from desktop_state import read
  ident=self.f.add();self.f.app.store.settings.update(sourceWorkflow='speech-subtitles',defaultSubtitleWorkflow='subtitles-speech');self.f.app.store.mode='basic';cfg=read(self.f.app.store.submit(self.f.app.row(ident)),{});self.assertEqual(cfg['sourceWorkflow'],'auto');self.assertEqual(cfg['sourceWorkflowRevision'],f.REVISION);self.assertEqual(cfg['sourceAllocationRevision'],p.ALLOCATION_REVISION)
if __name__=='__main__':unittest.main()
