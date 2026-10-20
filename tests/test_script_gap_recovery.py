import copy,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import script_gap_recovery as gaps
import worker

class GapRecoveryTests(unittest.TestCase):
 def cue(self,**kw):
  row=dict(start=1.,end=3.,speechStart=1.,speechEnd=3.,text='だけど',japanese='だけど',cantonese='',enabled=True,speakerId='same-role',
   captionAllocation=dict(blocked=True,content='',caption_ids=[]),captionRecords=[dict(id='caption_1',start=.9,end=3.1,text='但你不能離開。')],
   hybridEvidence=dict(skipped=True),missingScript=True,originalSpeechReason='missing-script')
  row.update(kw);return row
 def worker(self,reply):
  return SimpleNamespace(atomic_json=worker.atomic_json,traditional_cantonese=lambda c,t:worker.spoken_cantonese(t),emit=Mock(),ollama_chat=Mock(return_value=reply))
 def cfg(self,**kw):return dict(dict(port=1,model='local',dubLanguages=['yue'],scriptLocked=True),**kw)
 def test_blocked_saved_review_is_recovered_without_mutating_other_text_roles_or_clocks(self):
  with tempfile.TemporaryDirectory() as temp:
   cues=[self.cue(),self.cue(start=4,end=5,cantonese='手寫香港台詞'),self.cue(enabled=False)]
   before=copy.deepcopy(cues);w=self.worker('{"0":"但你唔可以走。"}')
   rows=gaps.recover(w,self.cfg(),Path(temp),cues)
   self.assertEqual(len(rows),1);self.assertEqual(cues[0]['cantonese'],'但你唔可以走。')
   self.assertFalse(cues[0]['hybridEvidence']['skipped']);self.assertNotIn('missingScript',cues[0])
   self.assertEqual(cues[1:],before[1:])
   self.assertEqual([cues[0][k] for k in ('start','end','speakerId')],[before[0][k] for k in ('start','end','speakerId')])
   self.assertTrue(rows[0]['previousAllocation']['blocked'])
   payload=json.loads(w.ollama_chat.call_args.args[2][1]['content']);self.assertEqual(payload['missing'][0]['target_characters'],9)
 def test_model_outage_cannot_blank_available_caption_or_poison_future_resume(self):
  with tempfile.TemporaryDirectory() as temp:
   w=self.worker('{}');cue=self.cue()
   rows=gaps.recover(w,self.cfg(),Path(temp),[cue])
   self.assertEqual(rows[0]['method'],'caption-text-fallback');self.assertTrue(cue['cantonese'])
   self.assertEqual(w.ollama_chat.call_count,2)
   resumed=self.cue();w.ollama_chat.reset_mock()
   gaps.recover(w,self.cfg(),Path(temp),[resumed]);w.ollama_chat.assert_not_called()
   self.assertEqual(resumed['cantonese'],cue['cantonese'])
 def test_short_reaction_does_not_copy_neighbouring_whole_caption(self):
  with tempfile.TemporaryDirectory() as temp:
   w=self.worker('{}');cue=self.cue(japanese='え？',end=1.4)
   rows=gaps.recover(w,self.cfg(),Path(temp),[cue])
   self.assertEqual(cue['cantonese'],'吓？');self.assertEqual(rows[0]['method'],'spoken-reaction');w.ollama_chat.assert_not_called()
 def test_no_source_and_explicit_exclusions_are_not_invented(self):
  with tempfile.TemporaryDirectory() as temp:
   cues=[self.cue(captionRecords=[],subtitleHint='鄰句不可亂搬',japanese='',text=''),self.cue(captionPolicyExcluded='outside-original-chinese')]
   w=self.worker('{}');self.assertEqual(gaps.recover(w,self.cfg(),Path(temp),cues),[])
   w.ollama_chat.assert_not_called();self.assertTrue(all(not c['cantonese'] for c in cues))
 def test_english_only_does_not_generate_cantonese_and_finished_job_never_calls_model(self):
  with tempfile.TemporaryDirectory() as temp:
   w=self.worker('{}')
   self.assertEqual(gaps.recover(w,self.cfg(dubLanguages=['en']),Path(temp),[self.cue()]),[])
   self.assertEqual(gaps.recover(w,self.cfg(),Path(temp),[self.cue(cantonese='已有配音稿')]),[])
   w.ollama_chat.assert_not_called()
 def test_saved_review_repairs_script_before_it_reaches_synthesis(self):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);cue=self.cue()
   cfg=dict(self.cfg(),storage=temp,duration=4,video=str(root/'source.mp4'),ttsBackend='drama3',_singleEngine=True)
   worker.atomic_json(root/'cues.json',[cue]);worker.atomic_json(root/'review.json',dict(config=cfg,meta={},cues=[cue]))
   def synthesize(config,folder,selected):
    self.assertEqual(len(selected),1);self.assertEqual(selected[0]['cantonese'],'但你唔可以走。')
    self.assertNotIn('missingScript',selected[0]);self.assertEqual(selected[0]['start'],1.)
    self.assertTrue(config['strictSpeechTiming']);raise RuntimeError('Reached repaired synthesis')
   with patch.object(worker,'ollama_chat',return_value='{"0":"但你唔可以走。"}'),patch.object(worker,'synthesize',side_effect=synthesize),patch('project_store.clear_issues'),patch.object(worker,'emit'):
    with self.assertRaisesRegex(RuntimeError,'Reached repaired synthesis'):worker.render_review(dict(review=str(root/'review.json')))
   saved=json.loads((root/'review.json').read_text())['cues'][0]
   self.assertEqual(saved['cantonese'],'但你唔可以走。');self.assertEqual(saved['speakerId'],'same-role')
 def test_same_named_call_uses_consistent_caption_term_instead_of_invented_japanese_translation(self):
  with tempfile.TemporaryDirectory() as temp:
   cues=[self.cue(start=i*4,end=i*4+2,speechStart=i*4,speechEnd=i*4+2,japanese='アストラ合体',captionRecords=[dict(id=f'c{i}',start=i*4,end=i*4+2,text=text)]) for i,text in enumerate(('準備星光融合！','星光融合是什麼？','又是星光融合嗎？'))]
   w=self.worker('{}');rows=gaps.recover(w,self.cfg(),Path(temp),cues)
   self.assertEqual([c['cantonese'] for c in cues],['星光融合']*3)
   self.assertTrue(all(row['method']=='repeated-caption-term' for row in rows));w.ollama_chat.assert_not_called()
 def test_legacy_missing_script_japanese_fallback_is_recovered_and_disabled(self):
  with tempfile.TemporaryDirectory() as temp:
   c=self.cue(preserveOriginalSpeech=True)
   gaps.recover(self.worker('{"0":"但你唔可以走。"}'),self.cfg(),Path(temp),[c])
   self.assertEqual(c['cantonese'],'但你唔可以走。');self.assertFalse(c['preserveOriginalSpeech'])

if __name__=='__main__':unittest.main()

class TimedDraftTests(unittest.TestCase):
 def test_new_oversized_draft_is_shortened_but_existing_manual_text_is_untouched(self):
  helper=GapRecoveryTests()
  with tempfile.TemporaryDirectory() as temp:
   cues=[helper.cue(start=0,end=1,speechStart=0,speechEnd=1),helper.cue(start=2,end=3,cantonese='呢句手寫稿唔可以自動刪改')]
   w=helper.worker('{}');w.ollama_chat.side_effect=['{"0":"但係我絕對唔會離開你㗎"}','{"0":"我唔會走"}']
   rows=gaps.recover(w,helper.cfg(),Path(temp),cues)
   self.assertEqual(cues[0]['cantonese'],'我唔會走');self.assertEqual(rows[0]['beforeCompaction'],'但係我絕對唔會離開你㗎')
   self.assertEqual(cues[1]['cantonese'],'呢句手寫稿唔可以自動刪改')
 def test_shortening_cannot_drop_negation_or_replace_full_draft_with_blank(self):
  helper=GapRecoveryTests()
  for answer in ('{"0":"我會走"}','{"0":""}'):
   with self.subTest(answer=answer),tempfile.TemporaryDirectory() as temp:
    cue=helper.cue(start=0,end=1,speechStart=0,speechEnd=1);w=helper.worker('{}')
    w.ollama_chat.side_effect=['{"0":"但係我絕對唔會離開你㗎"}',answer]
    gaps.recover(w,helper.cfg(),Path(temp),[cue])
    self.assertEqual(cue['cantonese'],'但係我絕對唔會離開你㗎')
