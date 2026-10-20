import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import project_edit as p

class RoleCommitRenderTests(unittest.TestCase):
 def fixture(self):
  review=dict(config=dict(duration=4),cues=[dict(start=0,end=2,text='日文',cantonese='一齊出發',speakerId='old-role',editorAudio='/old-take.wav',editorAudioBackend='gpt-sovits',editorAudioLanguage='yue')])
  row=dict(id='line',sources=[0],start=0,end=2,text='一齊出發',speakerId='new-role')
  return review,row
 def test_reassigned_voice_cannot_inherit_old_rendered_take(self):
  review,row=self.fixture();cue=p.materialize(review,dict(segments=[row]))[0]
  self.assertEqual(cue['speakerId'],'new-role');self.assertNotIn('editorAudio',cue)
  self.assertNotIn('editorAudioBackend',cue);self.assertEqual(review['cues'][0]['editorAudio'],'/old-take.wav')
 def test_explicitly_selected_recording_is_still_retained(self):
  review,row=self.fixture();row['audioTake']='/chosen-new-take.wav'
  self.assertEqual(p.materialize(review,dict(segments=[row]))[0]['editorAudio'],'/chosen-new-take.wav')
 def test_existing_failed_script_remains_visible_without_blocking_other_edits(self):
  review,row=self.fixture();review['cues'][0].update(cantonese='',missingScript=True,preserveOriginalSpeech=True)
  row['text']='';cue=p.materialize(review,dict(segments=[row]))[0]
  self.assertTrue(cue['missingScript']);self.assertFalse(cue['preserveOriginalSpeech'])
  self.assertEqual(cue['originalSpeechReason'],'missing-script')
 def test_corrected_script_clears_inherited_failure(self):
  review,row=self.fixture();review['cues'][0].update(cantonese='',missingScript=True,originalSpeechReason='missing-script',preserveOriginalSpeech=True)
  cue=p.materialize(review,dict(segments=[row]))[0]
  self.assertNotIn('missingScript',cue);self.assertNotIn('originalSpeechReason',cue);self.assertFalse(cue['preserveOriginalSpeech'])
 def test_erasing_valid_or_new_script_requires_disabling_line(self):
  review,row=self.fixture();row['text']=''
  with self.assertRaises(ValueError):p.materialize(review,dict(segments=[row]))
  row.update(manual=True,sources=[])
  with self.assertRaises(ValueError):p.materialize(review,dict(segments=[row]))
 def test_disabled_blank_line_is_valid(self):
  review,row=self.fixture();row.update(text='',enabled=False)
  valid=dict(row,id='valid',text='一齊出發',enabled=True)
  cue=p.materialize(review,dict(segments=[row,valid]))[0]
  self.assertFalse(cue['enabled'])
 def test_cache_seeding_excludes_diagnostic_and_rejected_audio(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);source=root/'source';source.mkdir();target=root/'target'
   for name in ['gpt-sovits-good.wav','gpt-sovits-good.raw.wav','gpt-sovits-bad.rejected-raw.wav','gpt-sovits-bad.rejected.wav']:(source/name).write_bytes(b'fixture')
   p.seed_cache(source,target)
   self.assertEqual([x.name for x in target.iterdir()],['gpt-sovits-good.wav'])

if __name__=='__main__':unittest.main()
