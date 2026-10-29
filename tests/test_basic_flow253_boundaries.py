"""Test real submission and translation entry points with isolated model replies."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'Resources'),str(ROOT/'windows'),str(ROOT/'studio')]
from test_basic_flow253 import cfg,cue,wav
from test_production_scope247 import ScopeTests
import normal_mode,dub_languages,worker,basic_flow,draft_length
class Submission(ScopeTests):
 def test_new_request_freezes_controls_and_resume_keeps_them(self):
  row=self.rows[0];self.app.dispatch('configure',dict(settings=dict(contentChecks=2,repairExcessiveAudibleOverlap=True)))
  path=self.app.store.submit(row);original=Path(path).read_bytes();request=json.loads(original);row.update(request=str(path),status='paused');self.app.store.save()
  self.assertEqual(request['basicFlowRevision'],basic_flow.REVISION);self.assertEqual(request['contentChecks'],2);self.assertTrue(request['repairExcessiveAudibleOverlap'])
  self.app.dispatch('configure',dict(settings=dict(contentChecks=0,repairExcessiveAudibleOverlap=False)))
  self.assertEqual(self.app.store.submit(row),path);self.assertEqual(Path(path).read_bytes(),original)
 def test_bad_count_leaves_settings_and_queue_unchanged(self):
  before=copy.deepcopy(self.app.store.settings);queue=copy.deepcopy(self.app.store.queue)
  for n in [True,-1,3,'2']:
   with self.assertRaises(ValueError):self.app.dispatch('configure',dict(settings=dict(contentChecks=n)))
   self.assertEqual(self.app.store.settings,before);self.assertEqual(self.app.store.queue,queue)
class FirstRequests(unittest.TestCase):
 def test_normal_actual_requests_all_languages_carry_original_clock_once(self):
  for language,answer in [('yue','我哋快啲走啦。'),('en',"Let's leave now."),('zh','我们快点走吧。')]:
   with self.subTest(language=language),tempfile.TemporaryDirectory() as d:
    root=Path(d);cs=[dict(cue(b=3.),text='早く行こう',japanese='早く行こう',subtitleHint='我們快走吧')];cs[0].pop('cantonese');before=copy.deepcopy(cs);w=Mock();w.atomic_json=worker.atomic_json;w.traditional_cantonese=lambda c,s:s;w.ollama_chat.return_value=json.dumps({'0':answer})
    c=cfg(port=1,model='fixture',dubLanguages=[language],subtitleModes=[])
    with patch.object(normal_mode,'glossary',return_value=[]):normal_mode.translate(w,c,root,cs)
    self.assertEqual(w.ollama_chat.call_count,1)
    args=w.ollama_chat.call_args.args;self.assertIn('FIRST-DRAFT LENGTH',args[2][0]['content']);payload=json.loads(args[2][1]['content'])
    encoded=json.dumps(payload);self.assertIn('durationGuidance',encoded);self.assertIn('source-speech',encoded)
    audit=json.loads((root/'draft-length-guidance.json').read_text());self.assertEqual(audit[language+':0']['sourceSeconds'],3.)
    self.assertEqual(cs[0]['speechStart'],before[0]['speechStart']);self.assertEqual(cs[0]['speechEnd'],before[0]['speechEnd'])
 def test_add_english_does_not_run_default_editor(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cs=[dict(cue(b=3.),text='早く行こう',japanese='早く行こう')];w=Mock();w.atomic_json=worker.atomic_json;w.ollama_chat.return_value='{"0":"Let us leave now."}'
   with patch('english_overlap.repair'):dub_languages.english_script(w,cfg(port=1,model='fixture'),root,cs)
   self.assertEqual(w.ollama_chat.call_count,1);self.assertIn('durationGuidance',w.ollama_chat.call_args.args[2][1]['content'])
 def test_legacy_direct_translation_first_request_has_guidance(self):
  with tempfile.TemporaryDirectory() as d:
   cs=[dict(cue(b=3.),text='早く行こう',japanese='早く行こう')];cs[0].pop('cantonese');response=json.dumps({'line_0':dict(meaning='leave now',speech_act='statement',names=[],cantonese='我哋快啲走啦。')})
   with patch.object(worker,'ollama_chat',return_value=response) as chat,patch.object(worker,'traditional_cantonese',side_effect=lambda c,s:s):
    worker.translate_batch(cfg(port=1,model='fixture',_translationJob=d),cs,[],Mock())
   self.assertEqual(chat.call_count,1);self.assertIn('durationGuidance',chat.call_args.args[2][1]['content'])
 def test_unconfirmed_clock_is_labeled_and_different_reference_is_not_reused(self):
  with tempfile.TemporaryDirectory() as d:
   c=cue();c.pop('speechStart');c.pop('speechEnd');rows={'0':{}}
   draft_length.apply(cfg(),d,[c],rows,'en');self.assertIn('fallback',rows['0']['durationGuidance']['clockSource']);self.assertIsNone(rows['0']['durationGuidance']['referenceIdentity'])
class ContentControl(unittest.TestCase):
 def test_repair_receives_existing_checks_without_repeating_first_inspection(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=wav(root/'voice.wav');checks={1:dict(contentFailure=True)}
   with patch.object(normal_mode,'inspect',return_value=checks) as inspect,patch.object(normal_mode,'repair_paths',return_value=[p]) as repair:
    basic_flow.finish(cfg(contentChecks=2,aiAutoFix=True),root,[cue()],[p],Mock(),Mock())
   self.assertEqual(inspect.call_count,1);self.assertIs(repair.call_args.args[0]['_initialContentChecks'],checks);self.assertEqual(repair.call_args.args[0]['_contentCheckRoot'],str(root))
