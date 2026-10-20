"""Regressions from full-episode reruns: final status and own-turn ownership."""
import json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import normal_mode,normal_recovery,review_report
from script_preflight import neighbour_rewrite_conflicts

class TurnRecoveryBoundaries(unittest.TestCase):
 def test_latin_initial_name_is_uncertain_without_automatic_actor_replacement(self):
  text='蒙奇·D·路飛';proof=dict(decision='unconfirmed',heard='Monkey D. Luffy.',language='English')
  self.assertTrue(normal_mode.mixed_letter_name(text))
  self.assertFalse(normal_mode.needs_dialect_confirmation(text,proof))
  self.assertEqual(normal_mode.language_decision(text,proof['heard'],proof['language']),'unconfirmed')
  self.assertTrue(normal_mode.needs_dialect_confirmation(text,dict(proof,languageFailure='japanese')))
  self.assertFalse(normal_mode.mixed_letter_name('我哋·D·路飛出去'))
  self.assertEqual(normal_mode.language_decision(text,'モンキーDルフィ','Japanese'),'japanese')
 def test_mixed_name_does_not_become_a_verified_cantonese_take(self):
  from normal_recovery import verified_check
  self.assertFalse(verified_check(dict(decision='unconfirmed',heard='Monkey D. Luffy.'),'蒙奇·D·路飛','yue'))
 def test_timing_rewrite_cannot_expand_into_a_shared_subtitle_even_with_ai_approval(self):
  cues=[dict(start=0,end=2,text='いい?あんたたちはたった今から',japanese='いい?あんたたちはたった今から',cantonese='聽住，你哋而家開始',subtitleHint='听好了 你们从现在起就是我忠实的仆人了'),dict(start=2,end=5,japanese='忠実なしもべになるのよ',cantonese='就係我忠誠嘅僕人啦')]
  row=dict(key='turn',index=1,position=0,reason='timing',source=cues[0]['japanese'],caption=cues[0]['subtitleHint'],draft=cues[0]['cantonese'],availableSeconds=2)
  cfg=dict(targetLanguage='yue',model='qwen',port=1);w=SimpleNamespace(ollama_chat=Mock(return_value=json.dumps({'1':'聽好，你哋而家開始做我忠實奴隸啦！'})))
  with patch('semantic_review.audit',return_value={'1':dict(faithful=True)}) as audit:
   self.assertEqual(normal_recovery.adapt(w,cfg,cues,[row]),{})
   self.assertTrue(audit.call_args.args[0]['ocrEvidenceOnly'])
  self.assertIn('expanded',row['_adaptationRejection']);self.assertEqual(cues[0]['cantonese'],'聽住，你哋而家開始')
 def test_new_neighbour_words_are_rejected_without_rejecting_preexisting_repeated_names(self):
  cues=[dict(start=0,end=2,japanese='いい?',cantonese='聽住'),dict(start=2,end=4,japanese='忠実なしもべ',cantonese='忠誠嘅僕人')]
  self.assertTrue(neighbour_rewrite_conflicts(cues,0,'忠誠嘅僕人'))
  cues[0]['cantonese']='忠誠嘅僕人';self.assertEqual(neighbour_rewrite_conflicts(cues,0,'忠誠嘅僕人'),[])
 def test_director_cannot_report_duration_mismatch_as_missing_words_for_language_issue(self):
  w=SimpleNamespace(ollama_chat=Mock(return_value=json.dumps({'1':dict(action='retry-clauses',reason='Draft too short, match the longer reference.')})))
  row=dict(key='k',index=1,reason='language-or-content',allowedActions=['retry-clauses','retain'])
  result=normal_recovery.decisions(w,dict(port=1,model='qwen'),[row])
  self.assertIn('not evidence',result['k']['reason']);self.assertNotIn('Draft too short',result['k']['reason'])
 def final_fixture(self,root,original=False,unresolved=False):
  cue=dict(start=0,end=2,japanese='原文',cantonese='廣東話');review=dict(config=dict(ttsBackend='drama3',targetLanguage='yue'),cues=[cue])
  def save(name,d):(root/name).write_text(json.dumps(d))
  save('review.json',review);save('normal-checks.json',dict(unresolved=[1] if unresolved else []))
  save('natural-placement.json',dict(rows=[dict(index=1,start=0,deadline=2,seconds=1.,fit=True)]))
  save('automatic-recovery.json',dict(rows={'old':dict(index=1,attempts=[dict(action='retry-clauses',status='not-verified')])}))
  save('target-reference-recovery.json',{'new':dict(index=1,status='adopted',action='target-language-reference',audio=str(root/'candidate.wav'),check=dict(decision='cantonese',heard='廣東話'))})
  save('timing.json',[dict(index=1,renderedAudio=str(root/'delivered.wav'),originalFallback=original,skipped=original)])
  return review_report.project(root,review,dict(status='done'))
 def test_delivered_fallback_is_separate_from_unresolved_historical_actor_failures(self):
  with tempfile.TemporaryDirectory() as d:
   result=self.final_fixture(Path(d));self.assertEqual(result['reviewState']['pending'],0);self.assertEqual(result['reviewState']['voiceFallbacks'],1)
   self.assertEqual(result['issues'][0]['status'],'voice-fallback');self.assertFalse(result['reviewState']['qualityChecked'])
 def test_missing_delivery_or_current_failed_check_cannot_be_hidden_as_a_voice_difference(self):
  for kwargs in [dict(original=True),dict(unresolved=True)]:
   with self.subTest(kwargs=kwargs),tempfile.TemporaryDirectory() as d:
    result=self.final_fixture(Path(d),**kwargs);self.assertEqual(result['reviewState']['pending'],1);self.assertEqual(result['reviewState']['voiceFallbacks'],0)

if __name__=='__main__':unittest.main()
