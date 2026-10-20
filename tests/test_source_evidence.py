import unittest,sys,json,tempfile
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import source_evidence as s
class EvidenceTests(unittest.TestCase):
 def test_windows_merge_context_but_preserve_original_times(self):
  cues=[dict(start=5,end=5.5,asrConfidence=.01),dict(start=6,end=7,asrConfidence=.2),dict(start=30,end=31,asrConfidence=.95)]
  original=json.dumps(cues);rows=s.windows(cues,40)
  self.assertEqual(rows[0]['indices'],[0,1]);self.assertEqual((rows[0]['start'],rows[0]['end']),(3.5,8.5));self.assertEqual(json.dumps(cues),original)
 def test_shared_caption_retains_single_identity_and_full_text(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'subtitle-context.json').write_text(json.dumps([dict(start=1,end=4,text='甲 乙')]))
   cues=[dict(start=1,end=2),dict(start=2,end=3)]
   s.prepare(SimpleNamespace(),{'storage':d,'duration':4},p,cues)
   self.assertEqual(cues[0]['captionRecords'],cues[1]['captionRecords'])
   self.assertEqual(cues[0]['captionRecords'][0]['text'],'甲 乙')

 def test_shared_names_split_without_title_specific_rules(self):
  allocation={'1':{'content':'阿甲 阿乙','caption_ids':['c']},'2':{'content':'阿乙','caption_ids':['c']}}
  source=[{'id':'1','japanese':''},{'id':'2','japanese':'名前！'}]
  s.refine_allocation(allocation,source)
  self.assertEqual(allocation['1']['content'],'阿甲')
  self.assertEqual(allocation['2']['content'],'阿乙')
 def test_actual_repeated_calls_are_not_removed(self):
  allocation={'1':{'content':'阿乙','caption_ids':['c']},'2':{'content':'阿乙','caption_ids':['c']}}
  s.refine_allocation(allocation,[{'id':'1','japanese':'名前！'},{'id':'2','japanese':'名前！'}])
  self.assertEqual(allocation['1']['content'],'阿乙')
