import tempfile,unittest,sys,json
from unittest.mock import Mock,patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import repair_budget as r
class BudgetTests(unittest.TestCase):
 def test_e04_short_empty_transcript_gets_one_retry_but_homophones_do_not(self):
  import delivery
  empty=dict(expected='喂，特爾緹娜！',heard='',similarity=0.0,languageUnverified=True,languageMismatch=True,requiresReview=True,cantoneseReviewPolicy=__import__('cantonese_review').REVISION,confirmedContentFailure=True,independentCheck=dict(heard='',languageUnverified=True))
  homophone=dict(expected='唔好同嗰個漁師有瓜葛。',heard='唔好同嗰個魚絲有瓜葛。',similarity=.875,languageUnverified=False,languageMismatch=False,requiresReview=True)
  good=dict(empty,heard='喂，特爾緹娜！',similarity=1.0,requiresReview=False,languageUnverified=False,languageMismatch=False)
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder);a=p/'collapsed.wav';b=p/'homophone.wav';new=p/'repaired.wav'
   for f in [a,b,new]:f.write_bytes(b'fixture')
   cues=[dict(start=0,end=1.18,cantonese=empty['expected'],reviewIndex=0),dict(start=2,end=4,cantonese=homophone['expected'],reviewIndex=1)]
   generate=Mock(return_value=[new]);run=lambda args:json.dumps(dict(format=dict(duration=.44 if Path(args[-1])==a else 1.1))).encode()
   with patch('speechcheck.inspect',side_effect=[[empty,homophone],[good]]),patch('delivery.prepare_audio',side_effect=lambda cfg,job,paths,run:paths):
    result=delivery.check_content(dict(storage=folder,ffprobe='ffprobe'),p,cues,[a,b],generate,run,lambda *args:None)
   self.assertEqual(result,[new,b]);self.assertEqual(generate.call_count,1)
   self.assertEqual([c['cantonese'] for c in generate.call_args.args[2]],[empty['expected']])
   self.assertFalse(r.claim(dict(boundedRepairs=True),p,cues[0],'content'),'Resume must not add an unlimited content retry')
   self.assertEqual(cues[0]['cantonese'],empty['expected'])
 def test_shared_across_reasons_text_edits_and_resume(self):
  with tempfile.TemporaryDirectory() as folder:
   c=dict(reviewIndex=4,speakerId='a',cantonese='你好')
   self.assertTrue(r.claim(dict(boundedRepairs=True),folder,c,'duration'))
   self.assertTrue(r.claim(dict(boundedRepairs=True),folder,dict(c,cantonese='你好呀'),'content'))
   self.assertFalse(r.claim(dict(boundedRepairs=True),folder,c,'content'))
   self.assertFalse(r.claim(dict(boundedRepairs=True),folder,c,'short-delivery'))
   self.assertTrue(r.claim(dict(boundedRepairs=True),folder,c,'voice'))
   self.assertFalse(r.claim(dict(boundedRepairs=True),folder,c,'anything-else'))
   self.assertTrue(r.claim(dict(boundedRepairs=True),folder,dict(c,reviewIndex=5),'content'))
 def test_uncertain_short_asr_does_not_trigger_retake(self):
  self.assertFalse(r.clear_content_problem(dict(cantonese='路飛！'),dict(similarity=.1)))
  self.assertTrue(r.clear_content_problem(dict(cantonese='我哋聽日一齊去嗰邊搵佢啦'),dict(similarity=.2)))
 def test_negation_loss_retries_even_when_long_line_score_is_high(self):
  self.assertTrue(r.clear_content_problem(dict(cantonese='我哋唔可以將佢留喺呢度然後全部人一齊走'),dict(similarity=.96,criticalDifferences=['negation:唔'])))
 def test_keep_accepted_take_across_rounds_and_reject_changed_file(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder);a=p/'a';b=p/'b';a.write_bytes(b'original');b.write_bytes(b'better')
   c=dict(cantonese='你好')
   r.remember_takes(p,[c],[a],[b]);self.assertEqual(r.retained_takes(p,[c],[a]),[b])
   b.write_bytes(b'changed');self.assertEqual(r.retained_takes(p,[c],[a]),[a])
