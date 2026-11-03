"""Manual review submissions preserve source text, settings and saved budgets."""
import json,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parent))
import test_review_line277 as fixture
from desktop_state import read,write

class ReviewCards(unittest.TestCase):
 setUp=fixture.ReviewLine277.setUp
 tearDown=fixture.ReviewLine277.tearDown
 project=fixture.ReviewLine277.project
 def test_saved_words_and_parameters_reach_only_the_manual_submission(self):
  ident,folder=self.project();source=(folder/'review.json').read_bytes()
  budget=folder/'repair-time-budget.json';write(budget,dict(spent=3));before=budget.read_bytes()
  draft=self.app.draft(self.app.row(ident));draft['segments'][0]['text']='已儲存的新翻譯。'
  self.app.dispatch('save-draft',dict(id=ident,draft=draft))
  with patch.object(self.app,'task',return_value={'id':'fixture'}) as task:
   self.app.dispatch('render',dict(id=ident,segment=draft['segments'][0]['id'],engine='drama3',language='yue',voiceParameters={'dramaTemperature':.65,'dramaTopK':25}))
  config=read(Path(task.call_args.args[1]));submitted=read(Path(config['submission']))
  self.assertEqual(submitted['segments'][0]['text'],'已儲存的新翻譯。')
  self.assertEqual(config['dramaTemperature'],.65);self.assertEqual(config['dramaTopK'],25)
  for key in ('fullAIReview','aiAutoFix','contentChecks','limitSpeechDuration','repairExcessiveAudibleOverlap'):
   self.assertEqual(config.get(key),draft['settings'].get(key),key)
  self.assertEqual(submitted['previewEngine'],'drama3')
  self.assertNotEqual(read(folder/'editor-draft-studio.json')['settings'].get('dramaTemperature'),.65)
  self.assertEqual(source,(folder/'review.json').read_bytes());self.assertEqual(before,budget.read_bytes())
 def test_invalid_manual_parameters_never_start_a_worker(self):
  ident,folder=self.project();draft=self.app.draft(self.app.row(ident))
  with patch.object(self.app,'task') as task:
   with self.assertRaises(ValueError):self.app.dispatch('render',dict(id=ident,segment=draft['segments'][0]['id'],engine='drama3',voiceParameters={'dramaTemperature':99}))
   task.assert_not_called()
 def test_saved_choice_keeps_source_identity_and_guards_both_copies(self):
  import wave
  from review_choices import select
  from review_take_removal import protection
  ident,folder=self.project();audio=folder/'new.wav'
  with wave.open(str(audio),'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(b'\0\0'*24000)
  review=read(folder/'review.json');draft=self.app.draft(self.app.row(ident))
  snapshot={'recordingCandidates':[dict(index=1,language='yue',engine='drama3',path=str(folder/'first.wav'),kind='first',created=1),dict(index=1,language='yue',engine='drama3',path=str(audio),created=2)]}
  chosen=select(folder,review,draft,snapshot,0,'drama3','yue','recording',str(audio),True)
  decision=chosen['segments'][0]['reviewDecisions']['yue:drama3'];self.assertEqual(decision['sourceAudio'],str(audio.resolve()))
  kept=protection(snapshot,chosen);self.assertIn(decision['audio'],kept);self.assertEqual(kept[str(audio.resolve())]['reason'],'saved review choice')
 def test_mandarin_selection_uses_the_saved_mandarin_words(self):
  import wave
  from review_choices import select
  ident,folder=self.project();audio=folder/'mandarin.wav'
  with wave.open(str(audio),'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(b'\0\0'*24000)
  review=read(folder/'review.json');review['config']['dubLanguages']=['zh'];draft=self.app.draft(self.app.row(ident));draft['segments'][0]['mandarin']='已保存的普通话。'
  snap={'recordingCandidates':[dict(index=1,language='zh',engine='drama3',path=str(audio),text='已保存的普通话。')]}
  chosen=select(folder,review,draft,snap,0,'drama3','zh','recording',str(audio),True)
  self.assertEqual(chosen['segments'][0]['reviewDecisions']['zh:drama3']['text'],'已保存的普通话。')
if __name__=='__main__':unittest.main()
