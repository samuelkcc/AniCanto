import sys,json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import voice_samples,voice_expression,project_edit,worker

class ComparisonTests(unittest.TestCase):
 def test_two_cloning_engines_keep_script_and_isolate_failures(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cue=dict(editorID='line',speakerId='R06',cantonese='唔好放棄！',start=1,end=3)
   calls=[]
   def generate(w,cfg,folder,c):
    calls.append((cfg['ttsBackend'],cfg['voiceStyleMode'],c['cantonese']))
    if len(calls)==2:raise ValueError('one failure')
    p=folder/'take.wav';p.write_bytes(b'audio');(folder/'report.json').write_text(json.dumps({'speechCheck':{'heard':c['cantonese']}}));return p,2
   w=Mock();w.atomic_json=lambda p,x:Path(p).write_text(json.dumps(x))
   with patch('natural_voices.prepare_cast'),patch('audio_audition.generate',side_effect=generate):result=voice_samples.compare(w,{'comparisonCandidates':[{'engine':'gpt-sovits-v2'},{'engine':'gpt-sovits'}]},root,[cue],'line')
   self.assertEqual(calls,[(e,s,'唔好放棄！') for e in ('gpt-sovits-v2','gpt-sovits') for s in ('clone',)]);self.assertEqual(len(result['rows']),2);self.assertEqual(len(result['errors']),1);self.assertEqual(sum(bool(x['audio']) for x in result['rows']),1);self.assertNotIn('voiceStyleMode',cue)
 def test_parameters_reject_nonfinite_out_of_bounds_and_unknown_emotions(self):
  for value in ({'gptTemperature':float('nan')},{'gptTopK':40},{'cosyExpression':'invented'},{'cosyTemperature':2}):
   with self.assertRaises(ValueError):voice_expression.settings(value)
  self.assertEqual(voice_expression.settings({})['gptRepetitionPenalty'],1.35)
  self.assertIn('香港粤语',voice_expression.instruction('expressive','yue'));self.assertIn('same voice',voice_expression.instruction('urgent','en'))
 def test_english_preview_translates_one_line_and_preserves_source(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);source=root/'movie.mkv';source.touch()
   review={'config':{'video':str(source),'duration':8,'model':'model','port':1},'meta':{'streams':[]},'cues':[{'start':1,'end':3,'text':'頑張ろう','cantonese':'一齊加油','speakerId':'R01'}]}
   (root/'review.json').write_text(json.dumps(review));before=(root/'review.json').read_bytes()
   draft={'id':'preview-english','review':str(root/'review.json'),'segments':[{'id':'a','sources':[0],'start':1,'end':3,'captionStart':1,'captionEnd':3,'text':'一齊加油','original':'頑張ろう','speakerId':'R01','enabled':True,'rate':1,'take':42,'trimStart':0,'trimEnd':0}],'clips':[{'start':0,'end':8}],'previewSegment':'a','previewLanguage':'en','previewEngine':'cosyvoice3','settings':{'previewScriptOnly':True}}
   submission=root/'submission.json';submission.write_text(json.dumps(draft))
   with patch.object(worker,'ollama_chat',return_value='{"0":"Let\'s do our best!"}'),patch.object(worker,'render_review') as movie:
    project_edit.render(worker,{'submission':str(submission)})
   version=root/'versions/preview-english';record=json.loads((version/'version.json').read_text());self.assertEqual(record['status'],'preview-script');self.assertEqual(json.loads((version/'review.json').read_text())['cues'][0]['english'],"Let's do our best!");self.assertEqual((root/'review.json').read_bytes(),before);movie.assert_not_called()
