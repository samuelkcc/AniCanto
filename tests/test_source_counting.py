import copy,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
from source_counting import repair
class CountingTests(unittest.TestCase):
 def cues(self):return [dict(start=i,end=i+.5,japanese=str(i+1),japaneseAlt=str(i+1),asrConfidence=.95,cantonese='錯誤重複稿') for i in range(4)]
 def test_repeated_caption_over_consecutive_counts_uses_each_source_number(self):
  with tempfile.TemporaryDirectory() as d:
   cues=self.cues();self.assertEqual(repair(dict(productionMode='normal'),d,cues),[0,1,2,3]);self.assertEqual([x['cantonese'] for x in cues],list('一二三四'));self.assertEqual(repair(dict(productionMode='normal'),d,cues),[])
 def test_ambiguous_isolated_numbers_or_manual_script_are_not_changed(self):
  for cfg,cues in [(dict(productionMode='normal'),self.cues()[:2]),(dict(productionMode='normal',editorRender=True),self.cues()),(dict(productionMode='normal'),[dict(x,japanese='2025') for x in self.cues()])]:
   before=copy.deepcopy(cues)
   with tempfile.TemporaryDirectory() as d:self.assertEqual(repair(cfg,d,cues),[]);self.assertEqual(cues,before)

 def test_low_confidence_digits_with_conflicting_caption_never_become_counting(self):
  cues=[dict(start=579.16+i*.58,end=579.74+i*.58,japanese=str(i+2),cantonese='快啲堵上',subtitleHint='快堵上',asrConfidence=score,sourceReviewReasons=['uncertain original speech']) for i,score in enumerate((.146,.498,.635))]
  before=copy.deepcopy(cues)
  with tempfile.TemporaryDirectory() as d:self.assertEqual(repair(dict(productionMode='normal'),d,cues),[])
  self.assertEqual(cues,before)
 def test_conflicting_caption_or_absent_independent_witness_veto_counting(self):
  for key,value in [('subtitleHint','快堵上'),('japaneseAlt',''),('asrConfidence',.4)]:
   cues=[dict(c,**{key:value}) for c in self.cues()];before=copy.deepcopy(cues)
   with tempfile.TemporaryDirectory() as d:self.assertEqual(repair(dict(productionMode='normal'),d,cues),[])
   self.assertEqual(cues,before)

 def test_resume_undoes_only_unchanged_unsafe_automatic_counting(self):
  with tempfile.TemporaryDirectory() as d:
   cues=[dict(start=0,end=.58,japanese='3',asrConfidence=.498,cantonese='三',captionText='三',preCountingRepair='快啲堵上',subtitleHint='快堵上'),dict(start=1,end=1.5,japanese='4',cantonese='人手改稿',preCountingRepair='快啲堵上')]
   self.assertEqual(repair(dict(productionMode='normal'),d,cues),[0]);self.assertEqual(cues[0]['cantonese'],'快啲堵上');self.assertEqual(cues[0]['captionText'],'快啲堵上');self.assertEqual(cues[1]['cantonese'],'人手改稿')
   self.assertEqual(repair(dict(productionMode='normal'),d,cues),[])
