import sys,json,tempfile,unittest,wave
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import prosody_experiment,reference_recovery

class ProsodyTests(unittest.TestCase):
 def test_bad_baseline_is_saved_without_processing_or_movie_adoption(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);path=root/'take.wav'
   with wave.open(str(path),'wb') as f:f.setparams((1,2,48000,0,'NONE','not compressed'));f.writeframes(bytes(48000))
   w=Mock();w.atomic_json=lambda p,o:Path(p).write_text(json.dumps(o))
   cfg=dict(dialoguePath=str(path),voiceProfiles=[dict(id='R06',reference=str(path))])
   cue=dict(editorID='a',speakerId='R06',start=1,end=3,cantonese='你好')
   with patch('dubbing.profile_for',return_value=dict(language='yue')),patch('dubbing.gsv_audio',return_value=[path]),patch('speechcheck.inspect',return_value=[dict(heard='',requiresReview=True)]):
    result=prosody_experiment.generate(w,cfg,root,cue)
   self.assertTrue(Path(result['baseline']).exists());self.assertIsNone(result['processed']);self.assertFalse(result['autoAdopt']);self.assertTrue(result['requiresReview']);self.assertIn('覆聽未通過',result['error']);w.run.assert_not_called()
 def test_processed_output_keeps_both_versions_and_independent_checks(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);path=root/'take.wav';path.write_bytes(b'audio')
   w=Mock();w.atomic_json=lambda p,o:Path(p).write_text(json.dumps(o));w.run.side_effect=[b'',b'{"maxPitchOffsetSemitones":0.7}']
   cfg=dict(storage=d,ffmpeg='ffmpeg',dialoguePath=str(path),voiceProfiles=[dict(id='R06',reference=str(path))]);cue=dict(editorID='a',speakerId='R06',start=1,end=3,cantonese='你好')
   checks=[dict(heard='你好',textMatches=True),dict(heard='你唔好',criticalDifferences=['negation:唔'])]
   with patch('dubbing.profile_for',return_value=dict(language='yue')),patch('dubbing.gsv_audio',return_value=[path]),patch('speechcheck.inspect',side_effect=[[checks[0]],[checks[1]]]):result=prosody_experiment.generate(w,cfg,root,cue)
   self.assertTrue(result['baseline']);self.assertTrue(result['processed']);self.assertEqual(result['processedCheck'],checks[1]);self.assertFalse(result['autoAdopt']);self.assertTrue(result['requiresReview'])
 def test_singing_and_repeated_vocalizations_are_not_spoken_references(self):
  self.assertFalse(reference_recovery.lexical('ろ違うああああああ'));self.assertFalse(reference_recovery.lexical('ああああああ'));self.assertTrue(reference_recovery.lexical('明日の作戦について'))
  self.assertFalse(reference_recovery.spoken_evidence([dict(singing=.8,speech=.1),dict(singing=.65,speech=.4)]));self.assertTrue(reference_recovery.spoken_evidence([dict(singing=.1,speech=.9)]))
 def test_editor_experiment_is_saved_separately_without_movie_or_track_adoption(self):
  import project_edit,worker
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);review=dict(config=dict(video=str(root/'missing.mkv'),duration=8),cues=[dict(start=1,end=3,text='こんにちは',cantonese='你好',speakerId='R06')])
   source=root/'review.json';source.write_text(json.dumps(review));before=source.read_bytes()
   draft=dict(id='experiment',review=str(source),previewSegment='a',previewLanguage='yue',previewEngine='gpt-sovits',segments=[dict(id='a',sources=[0],start=1,end=3,text='你好',original='こんにちは',speakerId='R06')],settings=dict(experimentalProsody=True,previewNativeAudio=True))
   request=root/'submission.json';request.write_text(json.dumps(draft))
   with patch('natural_voices.prepare_cast'),patch('prosody_experiment.generate',return_value=dict(baseline='baseline.wav',processed='performance.wav')) as generate,patch.object(worker,'render_review') as movie:
    project_edit.render(worker,dict(submission=str(request)))
   record=json.loads((root/'versions/experiment/version.json').read_text());self.assertEqual(record['status'],'prosody-experiment');self.assertNotIn('output',record);self.assertEqual(record['segment'],'a');movie.assert_not_called();generate.assert_called_once();self.assertEqual(source.read_bytes(),before)
 def test_manual_role_reference_is_untouched(self):
  row=dict(language='ja',reference='manual.wav',promptText='明日の作戦について',transcriptSource='user-import')
  run=Mock();self.assertIs(reference_recovery.prepare(dict(voiceStyleMode='clone'),Path('/unused'),row,run,Mock()),row);run.assert_not_called()
if __name__=='__main__':unittest.main()
