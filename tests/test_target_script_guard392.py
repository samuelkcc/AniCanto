"""Verify source-witnessed name cleanup at real submission and translation boundaries."""
import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows')]
import target_script_guard392 as guard,normal_mode,dialogue,independent_voices
from desktop_state import Store,read

class Guard392(unittest.TestCase):
 def test_exact_witness_only_and_language_guard_stays_strict(self):
  self.assertEqual(guard.names('啊，田中くん','あ、田中くん','ja','yue'),'啊，田中')
  self.assertEqual(guard.names('山田くん','田中くん','ja','yue'),'山田くん')
  self.assertEqual(guard.names('レイン','レイン','ja','yue'),'レイン')
  self.assertFalse(normal_mode.valid_target('レイン','yue','ja'))
  self.assertEqual(guard.names('田中くん','田中くん','ja','en'),'田中くん')
 def test_normal_translation_keeps_the_call_without_a_second_model_pass(self):
  cues=[dict(start=0,end=3,japanese='あ、田中くん',cantonese='')]
  w=Mock();w.traditional_cantonese.side_effect=lambda cfg,t:t;w.ollama_chat.return_value='{"0":"啊，田中くん"}'
  with tempfile.TemporaryDirectory() as d,patch.object(normal_mode,'glossary',return_value=[]):
   normal_mode.translate(w,dict(sourceLanguage='ja',dubLanguages=['yue'],subtitleModes=[],model='fixture',port=1,draftOutputGuardRevision=guard.REVISION),Path(d),cues)
  self.assertEqual(cues[0]['cantonese'],'啊，田中');self.assertEqual(w.ollama_chat.call_count,1)
 def test_fast_translation_uses_the_same_witnessed_cleanup_once(self):
  import fast_mode
  cues=[dict(start=0,end=3,japanese='あ、田中くん',cantonese='')]
  w=Mock();w.traditional_cantonese.side_effect=lambda cfg,t:t;w.ollama_chat.return_value='{"0":"啊，田中くん"}'
  with tempfile.TemporaryDirectory() as d:
   fast_mode.translate(w,dict(productionMode='fast',sourceLanguage='ja',dubLanguages=['yue'],subtitleModes=[],model='fixture',port=1,draftOutputGuardRevision=guard.REVISION),Path(d),cues)
  self.assertEqual(cues[0]['cantonese'],'啊，田中');self.assertEqual(w.ollama_chat.call_count,1)
 def test_authored_caption_does_not_become_an_audio_name_guess(self):
  from primary_source import REVISION
  cue=dict(japanese='山田くん',primarySource=dict(revision=REVISION,kind='embedded',text='山田くん'))
  self.assertEqual(guard.normalize(dict(draftOutputGuardRevision=guard.REVISION,sourceLanguage='ja'),cue,'山田くん','yue'),'山田くん')
 def test_absent_policy_does_not_change_saved_rules(self):
  self.assertEqual(guard.normalize({},dict(japanese='田中くん'),'田中くん','yue'),'田中くん')
 def test_new_submission_and_resume_preserve_spent_allowances(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);source=root/'fixture.mkv';source.write_bytes(b'isolated fixture');store=Store(root);store.add([source]);row=store.queue[0];p=store.submit(row);request=read(p)
   self.assertEqual(request['draftOutputGuardRevision'],guard.REVISION)
   request.pop('draftOutputGuardRevision');request['recoverySpentSeconds']=49;p.write_text(json.dumps(request));before=p.read_bytes();row['status']='paused';store.submit(row);self.assertEqual(p.read_bytes(),before)
 def test_desktop_reference_uses_word_clock_not_the_broad_segment_head(self):
  rows=[dict(start=0,end=9.76,text='明日また会いましょう',words=[dict(start=7,end=9.76,word='明日また会いましょう',probability=.95)])]
  cues=dialogue.build_cues(rows,[dict(start=7,end=9.76)],[],10)
  self.assertEqual(len(cues),1);self.assertAlmostEqual(cues[0]['speechStart'],6.94);self.assertAlmostEqual(cues[0]['speechEnd'],9.86)

if __name__=='__main__':unittest.main()
