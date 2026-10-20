import json,sys,tempfile,unittest,wave,array
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import cantonese_review as policy
from speechcheck import evidence
from repair_budget import clear_content_problem
from cantonese_alignment import align
import voicecheck

class CantoneseReviewTests(unittest.TestCase):
 def check(self,expected,heard,language='cantonese',second=None,unavailable=False):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);audio=root/'take.wav'
   with wave.open(str(audio),'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(array.array('h',[1000,-1000]*12000).tobytes())
   raw=evidence(expected,heard,language)
   def phonetic(w,cfg,folder,cue,check,**kw):
    return align(cue['cantonese'],check['heard']) if check.get('detectedLanguage')=='cantonese' else dict(accepted=False)
   with patch('cantonese_alignment.verify',side_effect=phonetic),patch('secondary_speech.transcribe',side_effect=RuntimeError('unavailable') if unavailable else None,return_value=second) as witness:
    first=policy.review(dict(targetLanguage='yue',storage=tmp),root,[dict(cantonese=expected)],[audio],[raw],lambda *a:None)[0]
    cached=policy.review(dict(targetLanguage='yue',storage=tmp),root,[dict(cantonese=expected)],[audio],[raw],lambda *a:None)[0]
   self.assertEqual(first,cached);return first,witness.call_count
 def test_actual_ep06_phonetic_rejections_now_share_one_acceptance_rule(self):
  for expected,heard in [('係呀，成日管曬啲嘢，真係過火。','系啊，成日管曬啲嘢，真系過火。'),('我點樣取代得返哥哥？','我點樣取代得翻哥哥？'),('皇兄，多謝你關心。','王兄，多謝你關心。'),('羈絆融合！羈絆融合！佢哋係咪發咗神經？','基本融合，基本融合，佢哋系咪發咗神經？')]:
   with self.subTest(expected=expected):
    row,calls=self.check(expected,heard);self.assertTrue(policy.verified(row));self.assertFalse(clear_content_problem(dict(cantonese=expected),row));self.assertEqual(calls,0);self.assertTrue(row['requiresReview'],'ASR spelling evidence stays visible')
 def test_minor_unmatched_word_and_particle_remain_advisory_without_reroll(self):
  row,calls=self.check('斷網魔王，徹底斷線，連局域網都連唔到！我完全被孤立咗！','斷網魔王徹底斷線連絕域網都連唔到我完全被孤立咗')
  self.assertEqual(row['contentDecision'],'retain-with-note');self.assertTrue(policy.retain_original(row));self.assertFalse(policy.verified(row));self.assertEqual(calls,0)
 def test_single_asr_missing_negation_is_not_a_replacement_order(self):
  text='報告！我聽唔明，報告！';row,calls=self.check(text,'我聽明報告',second=dict(heard=text,language='zh'))
  self.assertEqual(calls,1);self.assertTrue(policy.verified(row));self.assertFalse(row['confirmedContentFailure'])
 def test_two_independent_negation_differences_still_require_repair(self):
  text='報告！我聽唔明，報告！';row,calls=self.check(text,'報告我聽明報告',second=dict(heard='報告我聽明報告',language='zh'))
  self.assertEqual(calls,1);self.assertTrue(row['confirmedContentFailure']);self.assertTrue(clear_content_problem(dict(cantonese=text),row));self.assertFalse(policy.retain_original(row))
 def test_second_asr_unavailable_preserves_healthy_original_without_fake_verification(self):
  row,calls=self.check('我哋唔可以將佢留喺呢度然後一齊走','我哋可以將佢留喺呢度然後一齊走',unavailable=True)
  self.assertEqual(calls,1);self.assertTrue(policy.retain_original(row));self.assertFalse(policy.verified(row));self.assertFalse(row['confirmedContentFailure'])
 def test_independent_wrong_language_is_confirmed_but_one_label_is_not(self):
  text='我哋而家一齊出發去嗰邊搵佢啦'
  row,_=self.check(text,'We should all go there now','english',second=dict(heard='We should all go over there now',language='en'))
  self.assertTrue(row['confirmedContentFailure'])
  row,_=self.check(text,'We should all go there now','english',second=dict(heard='僕たちはそこに行きましょう',language='ja'))
  self.assertFalse(row['confirmedContentFailure'],'Disagreeing foreign labels cannot establish the spoken language')
  row,_=self.check(text,'We should all go there now','english',second=dict(heard=text,language='zh'))
  self.assertFalse(policy.verified(row));self.assertTrue(policy.retain_original(row));self.assertEqual(row['detectedLanguage'],'english','Chinese text cannot certify Cantonese pronunciation')
 def test_ep07_9_matching_chinese_orthography_never_certifies_cantonese(self):
  row,calls=self.check('特爾緹娜公主，讓我為您遮蔭！','德爾提娜公主，讓我為您遮陰。','chinese')
  self.assertEqual(row['languageStatus'],'unconfirmed-cantonese');self.assertTrue(row['languageUnverified'])
  self.assertFalse(policy.verified(row));self.assertTrue(policy.retain_original(row));self.assertFalse(row['confirmedContentFailure'])
  self.assertEqual(calls,0,'A broad language label must not trigger endless re-recording')
 def test_ep07_117_stammered_courtesy_is_not_a_missing_negative(self):
  row,calls=self.check('唔……唔該。','運がいい。','japanese',second=dict(heard='うんがい',language='ja'))
  self.assertFalse(row['confirmedContentFailure']);self.assertTrue(policy.retain_original(row))
  self.assertEqual(calls,0)
 def test_major_omissions_need_both_transcripts_not_a_name_disagreement(self):
  expected='今日朝早我哋一齊出發去嗰邊搵佢，之後再返嚟食飯'
  first=evidence(expected,'出發啦','cantonese');second=evidence(expected,'出發','zh')
  self.assertEqual(policy.corroborated(expected,first,second),'independently-confirmed-major-omission')
  second=evidence(expected,expected,'zh');self.assertIsNone(policy.corroborated(expected,first,second))
 def test_english_policy_unchanged(self):
  raw=evidence('Go there','Wait here','english','en');raws=[raw]
  with patch('secondary_speech.transcribe') as witness:
   self.assertIs(policy.review(dict(targetLanguage='en'),None,[],[],raws,None),raws)
  witness.assert_not_called()
 def test_changed_audio_invalidates_review_proof(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);audio=root/'take.wav';audio.write_bytes(b'first audio');cue=dict(cantonese='我哋唔可以走呀');raw=evidence(cue['cantonese'],'我哋可以走呀','cantonese')
   with patch('cantonese_alignment.verify',return_value=dict(accepted=False)),patch('secondary_speech.transcribe',return_value=None) as witness:
    for content in (b'first audio',b'new audio'):
     audio.write_bytes(content);policy.review(dict(targetLanguage='yue'),root,[cue],[audio],[raw],lambda *a:None)
   self.assertEqual(witness.call_count,2)
 def test_ep06_75_candidate_closer_to_actual_reference_is_not_blocked_by_bad_old_take(self):
  row=voicecheck.compare_scores(.6004967,.4958307,.5590670);self.assertTrue(row['accepted']);self.assertTrue(row['referenceImproved'])
 def test_wrong_or_weak_voice_not_approved_by_small_relative_improvement(self):
  for values in ((-.04,.107,.349),(.55,.588,.299),(.35,.343,.184),(.2,.01,.1)):
   self.assertFalse(voicecheck.compare_scores(*values)['accepted'])
