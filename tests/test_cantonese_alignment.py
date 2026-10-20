import sys,unittest,tempfile,subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import cantonese_alignment as alignment

class CantoneseAlignmentTests(unittest.TestCase):
 def test_complete_homophone_sequence_retains_tone_uncertainty(self):
  result=alignment.align('呢個係羈絆能量','呢個係基本能量')
  self.assertTrue(result['accepted']);self.assertEqual(result['toneDifferences'],1)
  self.assertEqual(result['changedCharacters'],2)
 def test_missing_second_clause_cannot_pass_even_with_high_text_similarity(self):
  self.assertFalse(alignment.align('令到魔力金屬結晶化嘅神秘力量，就係羈絆能量','令到魔力金屬結晶化嘅神秘力量')['accepted'])
 def test_changed_action_number_negation_and_extra_words_refused(self):
  for expected,heard in [('我哋喺度等你','我哋喺度搵你'),('仲有四個人','仲有十個人'),('唔好走','好走'),('快啲嚟','快啲嚟快啲嚟')]:
   with self.subTest(expected=expected):self.assertFalse(alignment.align(expected,heard)['accepted'])
 def test_foreign_language_cannot_be_relabelled_cantonese_by_alignment(self):
  w=SimpleNamespace(run=Mock(),atomic_json=Mock())
  result=alignment.verify(w,dict(targetLanguage='yue'),Path('/unused'),dict(cantonese='我哋出發啦'),dict(languageMismatch=True,detectedLanguage='japanese',similarity=.9))
  self.assertFalse(result['accepted']);w.run.assert_not_called()
 def test_runtime_unavailable_never_creates_acceptance(self):
  with tempfile.TemporaryDirectory() as temp:
   w=SimpleNamespace(run=Mock(side_effect=subprocess.CalledProcessError(1,['python'])),atomic_json=Mock())
   result=alignment.verify(w,dict(storage=temp,targetLanguage='yue'),Path(temp),dict(cantonese='羈絆能量'),dict(languageMismatch=False,languageUnverified=False,detectedLanguage='cantonese',similarity=.9))
   self.assertFalse(result['accepted'])
 def test_repeated_full_homophones_are_checked_even_below_character_threshold(self):
  import worker
  from unittest.mock import patch
  expected='你哋唔好成日… 羈絆融合！羈絆融合！咁講啦！'
  heard='你哋唔好成日基本融合、基本融合咁講啦。'
  with tempfile.TemporaryDirectory() as temp:
   w=SimpleNamespace(run=Mock(return_value=__import__('json').dumps(alignment.align(expected,heard))),atomic_json=worker.atomic_json)
   with patch('runtime_paths.python_for',return_value=Path(sys.executable)):
    result=alignment.verify(w,dict(storage=temp,targetLanguage='yue'),Path(temp),dict(cantonese=expected),dict(detectedLanguage='cantonese',similarity=.7647))
   self.assertTrue(result['accepted']);self.assertEqual(result['syllables'],17)

if __name__=='__main__':unittest.main()

class RomanizedGapTests(unittest.TestCase):
 def test_only_an_isolated_romanized_gap_with_an_independent_phonetic_witness_can_pass(self):
  expected='咁即係所有魔導研究都係你話事？係。'
  heard='咁即係所有model研究都係你話事，係。'
  result=alignment.corroborate(expected,heard,'即是所有摩導研究都是你作主？是')
  self.assertTrue(result['accepted']);self.assertEqual(result['secondaryTerm'],'摩導')
 def test_another_asr_word_or_unanchored_guess_cannot_authorize_it(self):
  expected='咁即係所有魔導研究都係你話事？係。';heard='咁即係所有model研究都係你話事，係。'
  for second in ('即是所有魔法研究都是你作主','摩導研究','所有摩導過程研究','所有摩導研究，所有摩導研究'):
   self.assertFalse(alignment.corroborate(expected,heard,second)['accepted'])
 def test_missing_word_clause_negation_or_multiple_gaps_are_not_a_spelling_case(self):
  expected='咁即係所有魔導研究都唔係你話事，係。'
  for heard in ('咁即係所有model研究都係你話事係','咁即係所有model研究都唔係你話事','即係所有model研究都唔係你話事係','咁即係all嘅model研究都唔係你話事係'):
   self.assertIsNone(alignment.romanized_gap(expected,heard))
