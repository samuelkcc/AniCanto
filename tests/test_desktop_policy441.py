"""Check current producer rules, old request retention, and bounded recovery."""
import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows')]
import dialogue_policy441 as policy,target_script_guard392 as guard,normal_mode
from desktop_state import Store,read

class Desktop441(unittest.TestCase):
 def test_new_basic_and_expert_requests_keep_existing_spent_resume_bytes(self):
  for mode in ('basic','expert'):
   with self.subTest(mode=mode),tempfile.TemporaryDirectory() as d:
    r=Path(d);v=r/'fixture.mkv';v.write_bytes(b'isolated');s=Store(r);s.mode=mode;s.settings['keepOriginalNamePronunciation']=True;s.add([v]);row=s.queue[0];p=s.submit(row);cfg=read(p)
    self.assertEqual(cfg['keepOriginalNamePronunciation'],mode=='expert');self.assertEqual(cfg['draftOutputGuardRevision'],guard.REVISION)
    cfg.pop('dialoguePolicyRevision');cfg['recoverySpentSeconds']=49;p.write_text(json.dumps(cfg));before=p.read_bytes();row['status']='paused';s.submit(row);self.assertEqual(p.read_bytes(),before)
 def test_source_only_scream_keeps_short_calls_and_mixed_dialogue(self):
  cfg={};policy.configure(cfg);cues=[dict(japanese=t) for t in ['ああああ！','媽媽！','ああ','ああああ、行くぞ','[UNCONFIRMED_SOURCE]']]
  policy.prepare(cfg,cues);self.assertTrue(cues[0]['preserveOriginalSpeech']);self.assertFalse(any(c.get('preserveOriginalSpeech') for c in cues[1:]));self.assertFalse(cues[0].get('noSpeech',False))
  c=dict(japanese='ああああ',cantonese='已有錄音稿');policy.prepare(cfg,[c]);self.assertNotIn('preserveOriginalSpeech',c)
 def test_name_instruction_does_not_skip_names_or_change_reference(self):
  for value in (True,False):
   cfg={};policy.configure(cfg);cfg['keepOriginalNamePronunciation']=value;self.assertIn('dub name-only calls',policy.instruction(cfg));self.assertIn('speaker reference',policy.instruction(cfg))
  self.assertEqual(policy.instruction({}),'')
 def test_short_punctuated_target_loop_is_versioned_and_source_is_unchanged(self):
  text='你好！你好，你好。你好？你好！你好。你好！你好。你好！'
  cue=dict(japanese='あ、田中くん');self.assertTrue(guard.short_loop(text));self.assertEqual(guard.normalize({'draftOutputGuardRevision':guard.REVISION},cue,text,'yue'),'')
  self.assertEqual(guard.normalize({'draftOutputGuardRevision':guard.LEGACY_REVISION},cue,text,'yue'),text);self.assertEqual(cue['japanese'],'あ、田中くん')
 def test_unknown_does_not_spend_final_caption_rescue(self):
  c=dict(start=0,end=6,japanese='[UNCONFIRMED_SOURCE]',sourcePolicyBlocked=True,preserveOriginalSpeech=True,originalSpeechReason='source-recognition-unconfirmed')
  with tempfile.TemporaryDirectory() as d:
   cfg=dict(productionMode='normal',dubLanguages=['yue'],model='fixture',port=1)
   w=Mock();normal_mode.ensure_scripts(w,cfg,Path(d),[c]);self.assertFalse(w.ollama_chat.called);self.assertFalse((Path(d)/'normal-caption-rescue-budget.json').exists());self.assertTrue(policy.source_unconfirmed(c))
 def test_failed_target_keeps_raw_evidence_and_does_not_gain_attempts(self):
  text='你好！'*12;cfg=dict(productionMode='normal',sourceLanguage='ja',dubLanguages=['en'],_dubbingTranslationLanguages=['en'],model='fixture',port=1,targetDraftRevision='retained-target-draft-425',draftOutputGuardRevision=guard.REVISION)
  cue=dict(start=0,end=3,japanese='これは本当です。');w=Mock();w.atomic_json.side_effect=lambda p,v:Path(p).write_text(json.dumps(v,ensure_ascii=False));w.ollama_chat.return_value=json.dumps({'text':text});w.traditional_cantonese.side_effect=lambda c,t:t
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);normal_mode.ensure_scripts(w,cfg,job,[cue]);self.assertEqual(w.ollama_chat.call_count,2);self.assertFalse(cue.get('english'));self.assertIn(text,(job/'target-drafts.json').read_text())
   w.reset_mock();normal_mode.ensure_scripts(w,cfg,job,[cue]);self.assertFalse(w.ollama_chat.called)
 def test_unknown_reporting_keeps_authored_content_eligible(self):
  from primary_source import REVISION
  self.assertTrue(policy.source_unconfirmed(dict(sourcePolicyBlocked=True)))
  self.assertFalse(policy.source_unconfirmed(dict(sourcePolicyBlocked=True,primarySource=dict(revision=REVISION,kind='embedded',text='媽媽'))))

class DesktopReport441(unittest.TestCase):
 def test_unknown_source_is_not_missing_target_in_actual_report(self):
  import review_report
  cfg=dict(dubLanguages=['yue'],selectedEngines=['drama3'],ttsBackend='drama3')
  c=dict(start=0,end=3,japanese='',cantonese='',sourcePolicyBlocked=True,preserveOriginalSpeech=True,originalSpeechReason='source-recognition-unconfirmed')
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'timing.json').write_text('[]');review=dict(config=cfg,cues=[c]);(p/'review.json').write_text(json.dumps(review))
   report=review_report.project(p,review,dict(status='complete'))
   self.assertEqual(report['reportRows'][0]['reportGroup'],'reportSource')
   self.assertEqual(report['reviewState']['needsDubbing'],0)
   self.assertEqual(report['reviewState']['sourceUnconfirmed'],1)
 def test_known_dialogue_remains_missing_target_in_delivery_audit(self):
  import dialogue_delivery
  unknown=dict(start=0,end=3,japanese='',preserveOriginalSpeech=True,sourcePolicyBlocked=True,originalSpeechReason='source-recognition-unconfirmed')
  known=dict(start=3,end=5,japanese='お母さん',cantonese='媽媽！')
  with tempfile.TemporaryDirectory() as d:
   report=dialogue_delivery.audit([dict(folder=Path(d),engine='cosyvoice3',language='yue',review=dict(config={},cues=[unknown,known]))])
   self.assertEqual(report['tracks'][0]['required'],1);self.assertEqual(report['tracks'][0]['missing'],1)
   self.assertEqual(report['tracks'][0]['excluded'][0]['reason'],'source-unconfirmed')

if __name__=='__main__':unittest.main()
