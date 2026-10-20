import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import delivery

class ContentWorkflowTests(unittest.TestCase):
 def fixture(self,root):
  (root/'asr-ready.json').write_text('{}')
  paths=[root/'skipped-gpt-sovits-0.wav',root/'before.wav',root/'after.wav']
  for p in paths:p.write_bytes(p.name.encode())
  cues=[dict(start=0,end=2,cantonese='This reference is missing.',reviewIndex=0),dict(start=2,end=5,cantonese='Do not leave me behind.',reviewIndex=1,speakerId='same-role')]
  cfg=dict(storage=str(root),targetLanguage='en',ttsBackend='gpt-sovits',autoFit=False,ffprobe='probe',voiceProfiles=[])
  bad=dict(requiresReview=True,similarity=.1,languageMismatch=True,detectedLanguage='japanese',criticalDifferences=['negation'])
  good=dict(requiresReview=False,similarity=1.,languageMismatch=False,detectedLanguage='english',criticalDifferences=[])
  return cfg,cues,paths,bad,good
 def test_failed_line_does_not_bypass_healthy_line_repair_with_autofit_off(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cfg,cues,p,bad,good=self.fixture(root)
   generate=Mock(side_effect=[[p[0],p[1]],[p[2]]]);run=lambda args:json.dumps({'format':{'duration':3}}).encode()
   with patch.object(delivery,'prepare_audio',side_effect=lambda cfg,job,paths,run:paths),patch('speechcheck.inspect',side_effect=[[bad],[good]]) as inspect:
    actual=delivery.synthesize(cfg,root,cues,generate,run,lambda *a:None)
   self.assertEqual(actual,[p[0],p[2]])
   self.assertEqual(generate.call_count,2)
   self.assertEqual(generate.call_args.args[2][0]['cantonese'],cues[1]['cantonese'])
   self.assertEqual(generate.call_args.args[2][0]['speakerId'],'same-role')
   self.assertEqual(len(inspect.call_args_list[0].args[2]),1)
   saved=json.loads((root/'speech-check.json').read_text());self.assertEqual(saved['rows'][0]['similarity'],1.)
   # Resume must retain the accepted take and never spend a second retake.
   generate=Mock(return_value=[p[0],p[1]])
   with patch.object(delivery,'prepare_audio',side_effect=lambda cfg,job,paths,run:paths),patch('speechcheck.inspect',return_value=[good]):
    self.assertEqual(delivery.synthesize(cfg,root,cues,generate,run,lambda *a:None),actual)
   self.assertEqual(generate.call_count,1)
 def test_language_failure_retries_once_across_resume_and_keeps_failed_candidate_out(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cfg,cues,p,bad,good=self.fixture(root);generate=Mock(return_value=[p[2]])
   run=lambda args:json.dumps({'format':{'duration':3}}).encode()
   with patch.object(delivery,'prepare_audio',side_effect=lambda cfg,job,paths,run:paths),patch('speechcheck.inspect',return_value=[bad]):
    for _ in range(2):self.assertEqual(delivery.check_content(cfg,root,cues[1:],[p[1]],generate,run,lambda *a:None),[p[1]])
   self.assertEqual(generate.call_count,1)
 def test_manual_original_and_missing_audio_are_not_automatically_replaced(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cfg,cues,p,bad,good=self.fixture(root);generate=Mock();run=Mock()
   protected=[dict(cues[1],editorAudio=str(p[1])),dict(cues[1],preserveOriginalSpeech=True),cues[0]]
   with patch('speechcheck.inspect') as inspect:
    self.assertEqual(delivery.check_content(cfg,root,protected,[p[1],p[1],p[0]],generate,run,lambda *a:None),[p[1],p[1],p[0]])
   generate.assert_not_called();inspect.assert_not_called()
 def test_wrong_voice_rejects_otherwise_correct_content(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cfg,cues,p,bad,good=self.fixture(root);(root/'speakers-ready.json').write_text('{}');cfg['voiceProfiles']=[dict(id='same-role',name='Test role',reference=str(p[1]),promptText='Test reference',language='en')]
   generate=Mock(return_value=[p[2]]);run=lambda args:json.dumps({'format':{'duration':3}}).encode()
   with patch.object(delivery,'prepare_audio',side_effect=lambda cfg,job,paths,run:paths),patch('speechcheck.inspect',side_effect=[[bad],[good]]),patch('voicecheck.preserves',return_value=False):
    self.assertEqual(delivery.check_content(cfg,root,cues[1:],[p[1]],generate,run,lambda *a:None),[p[1]])
