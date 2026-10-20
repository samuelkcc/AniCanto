import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
from speechcheck import evidence
class SpeechEvidenceTests(unittest.TestCase):
 def test_one_wrong_word_in_long_otherwise_matching_line_remains_flagged(self):
  r=evidence('呢度係想解放呢個鎮嘅反抗軍總部。','呢度系想解放呢個鎮嘅反共軍總部。','cantonese')
  self.assertGreater(r['similarity'],.9);self.assertFalse(r['textMatches']);self.assertTrue(r['requiresReview'])
 def test_copula_spelling_punctuation_and_spacing_do_not_invent_an_error(self):
  r=evidence('咁樣嘅話，我哋係同一隊！','咁樣嘅話 我哋系同一隊。','cantonese')
  self.assertTrue(r['textMatches']);self.assertFalse(r['requiresReview'])
 def test_exact_written_match_does_not_certify_cantonese_if_language_unknown(self):
  for label in ('none','chinese','japanese'):
   r=evidence('我哋一齊出發啦','我哋一齊出發啦',label);self.assertTrue(r['requiresReview'])
 def test_changed_numbers_and_negation_remain_review_items(self):
  for heard in ('There are 12 people, not 10.','There are 13 people, 10.'):
   r=evidence('There are 13 people, not 10.',heard,'english','en');self.assertTrue(r['requiresReview'])
