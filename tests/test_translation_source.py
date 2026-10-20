import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import translation_source as t

class TranslationSourceTests(unittest.TestCase):
 def test_audio_only_overrides_all_input_subtitle_routes_but_not_output(self):
  cfg=dict(translationSource='audio-only',subtitleSource='external',subtitle='chinese.srt',subtitleStream=3,ocr=True,batchAutoSubtitles=True,captionSourceReview='old.json',captionPolicy={'mode':'original-chinese'},subtitleModes=['yue','english','original'],autoValidate=True,productionMode='standard')
  t.configure(cfg)
  self.assertEqual(cfg['subtitleSource'],'none');self.assertFalse(cfg['ocr']);self.assertFalse(cfg['batchAutoSubtitles']);self.assertIsNone(cfg['subtitle']);self.assertNotIn('captionSourceReview',cfg)
  self.assertEqual(cfg['subtitleModes'],['yue','english','original']);self.assertTrue(cfg['autoValidate'])
 def test_no_caption_or_scene_evidence_but_explicit_output_text_preserved(self):
  cues=[dict(start=1,end=2,japanese='ありがとう',text='ありがとう',subtitleHint='污染',captionRecords=[{'text':'污染'}],captionAllocation={'content':'污染'},scenePlan={'meaning':'污染'},captionText='manual Cantonese subtitle',englishCaptionText='manual English',nonlexicalTail=True)]
  old=copy.deepcopy(cues);out=t.translation_cues({'translationSource':'audio-only'},cues)
  self.assertEqual(cues,old);self.assertNotIn('subtitleHint',out[0]);self.assertNotIn('scenePlan',out[0]);self.assertTrue(out[0]['nonlexicalTail']);self.assertEqual(out[0]['captionPolicyExcluded'],'nonlexical-asr-tail');self.assertEqual(out[0]['captionText'],'manual Cantonese subtitle')
 def test_cached_caption_file_is_never_opened_for_translation(self):
  import source_evidence,caption_span_recovery,caption_timing_alignment,worker
  cfg={'translationSource':'audio-only'};cues=[dict(start=1,end=2,text='ありがとう',subtitleHint='污染')]
  with patch.object(source_evidence,'caption_records',side_effect=AssertionError('caption input')):
   source_evidence.prepare(SimpleNamespace(),cfg,Path('/unused'),cues)
  self.assertEqual(worker.extract_cues(cfg,Path('/unused'),{}),[])
  self.assertEqual(caption_span_recovery.recover(None,cfg,None,cues),[])
  self.assertEqual(caption_timing_alignment.audit(None,cfg,None,cues),[])
 def test_fast_translator_payload_contains_only_japanese(self):
  import fast_mode
  requests=[]
  def chat(*a,**kw):requests.append(a[2][-1]['content']);return '{"0":"多謝。"}'
  w=SimpleNamespace(emit=lambda *a,**kw:None,ollama_chat=chat,traditional_cantonese=lambda cfg,s:s,atomic_json=lambda *a:None)
  cues=[dict(start=0,end=1,text='ありがとう',subtitleHint='污染')]
  fast_mode.translate(w,dict(translationSource='audio-only',dubLanguages=['yue'],subtitleModes=['yue'],model='test',port=1),Path('/unused'),cues)
  self.assertNotIn('污染',''.join(requests));self.assertEqual(cues[0]['cantonese'],'多謝。')
 def test_default_source_keeps_legacy_job_and_track_cache_identity(self):
  import ast
  root=Path(__file__).resolve().parents[1]/'Resources'
  # Execute the real cache-identity statements, rather than copying their rule.
  worker=ast.parse((root/'worker.py').read_text());convert=next(n for n in worker.body if isinstance(n,ast.FunctionDef) and n.name=='convert')
  statements=[n for n in convert.body if isinstance(n,ast.If) and 'translationSource' in ast.unparse(n.test) and any(isinstance(x,ast.Assign) and 'identity' in ast.unparse(x.targets) for x in n.body)]
  self.assertEqual(len(statements),1)
  def identity(cfg):
   namespace={'cfg':cfg,'identity':{'video':'ep07'}};exec(compile(ast.Module(body=statements,type_ignores=[]),'<real-cache-rule>','exec'),namespace);return namespace['identity']
  self.assertEqual(identity({}),identity({'translationSource':'audio-and-subtitles'}))
  self.assertNotEqual(identity({}),identity({'translationSource':'audio-only'}))
  for name,var in [('fast_mode.py','identity'),('multitrack.py','render_cfg')]:
   tree=ast.parse((root/name).read_text())
   nodes=[n for n in ast.walk(tree) if isinstance(n,ast.If) and 'translationSource' in ast.unparse(n.test) and any(isinstance(x,ast.Expr) and var+'.pop' in ast.unparse(x) for x in n.body)]
   self.assertEqual(len(nodes),1)
   namespace={var:{'translationSource':'audio-and-subtitles','model':'same'}};exec(compile(ast.Module(body=nodes,type_ignores=[]),'<real-cache-rule>','exec'),namespace)
   self.assertEqual(namespace[var],{'model':'same'})
