import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import duration_fit
import worker

class FitTests(unittest.TestCase):
 def test_resume_revalidates_old_automatic_edits_but_not_human_lock(self):
  with tempfile.TemporaryDirectory() as folder:
   job=Path(folder);cues=[dict(text='動くな',cantonese='唔郁')]
   worker.atomic_json(job/'duration-edits.json',[dict(index=1,before='唔好郁',after='唔郁')])
   self.assertEqual(duration_fit.restore_unsafe_edits(dict(scriptLocked=True),job,cues),[])
   self.assertEqual(cues[0]['cantonese'],'唔郁')
   self.assertTrue(duration_fit.restore_unsafe_edits({},job,cues))
   self.assertEqual(cues[0]['cantonese'],'唔好郁')
   self.assertEqual(duration_fit.restore_unsafe_edits({},job,cues),[])
 def test_grounded_place_and_count_survive_false_positive_semantic_audit(self):
  for source,before,candidate,terms in [
   ('東京までパンを届けて','送麵包去東京','送麵包', [dict(japanese='東京',cantonese='東京')]),
   ('コーヒーを二杯','唔該畀二杯咖啡我','畀咖啡我',[]),
   ('動くな','唔好郁','唔郁',[])]:
   with self.subTest(source=source),tempfile.TemporaryDirectory() as folder:
    job=Path(folder);worker.atomic_json(job/'scene-glossary.json',terms)
    cues=[dict(text=source,cantonese=before)]
    rows=[dict(index=1,seconds=4,slot=2,needsReview=True)]
    responses=[json.dumps(dict(line_0=candidate)),json.dumps(dict(line_0=dict(faithful=True,defects=[],reason='false positive')))]
    with patch.object(worker,'ollama_chat',side_effect=responses),patch.object(duration_fit.urllib.request,'urlopen'):
     self.assertFalse(duration_fit.shorten(dict(port=1,model='local',autoApprove=True),job,cues,rows,1,lambda *a,**kw:None))
    self.assertEqual(cues[0]['cantonese'],before)
    self.assertTrue(json.loads((job/'duration-rejected-1.json').read_text()))
 def test_locked_script_never_automatically_shortens(self):
  with tempfile.TemporaryDirectory() as folder,patch.object(worker,'ollama_chat') as model:
   self.assertFalse(duration_fit.shorten(dict(scriptLocked=True),Path(folder),[],[],1,lambda *a:None));model.assert_not_called()
 def test_verified_improvement_above_character_budget_is_kept(self):
  with tempfile.TemporaryDirectory() as folder:
   cues=[dict(text='ママを怒らせりゃ実の息子でもこうなる',cantonese='不過一旦惹媽媽嬲就算係親生仔都係咁嘅下場',requiredNames=[])]
   rows=[dict(index=1,seconds=6.3,slot=2,needsReview=True)]
   shorter='激嬲媽媽，親生仔都冇情講'
   responses=[json.dumps(dict(line_0=shorter)),json.dumps(dict(line_0=dict(faithful=True,defects=[],reason='保留條件及後果')))]
   with patch.object(worker,'ollama_chat',side_effect=responses),patch.object(duration_fit.urllib.request,'urlopen'):
    self.assertTrue(duration_fit.shorten(dict(port=1,model='local',autoApprove=True),Path(folder),cues,rows,1,lambda *a,**kw:None))
   self.assertEqual(cues[0]['cantonese'],shorter)
 def test_automatic_mode_rejects_shorter_candidate_that_loses_meaning(self):
  with tempfile.TemporaryDirectory() as folder:
   cues=[dict(text='原文',cantonese='我唔會離開你',requiredNames=[])]
   rows=[dict(index=1,seconds=4,slot=2,needsReview=True)]
   responses=['{"line_0":"我會走"}','{"line_0":{"faithful":false,"defects":[],"reason":"否定意思相反"}}']
   with patch.object(worker,'ollama_chat',side_effect=responses),patch.object(duration_fit.urllib.request,'urlopen'):
    changed=duration_fit.shorten(dict(port=1,model='local',autoApprove=True),Path(folder),cues,rows,1,lambda *a,**kw:None)
   self.assertFalse(changed);self.assertEqual(cues[0]['cantonese'],'我唔會離開你')
 def test_rewrite_preserves_original_and_does_not_change_other_lines_or_timestamps(self):
  with tempfile.TemporaryDirectory() as folder:
   job=Path(folder)
   cues=[dict(start=1,end=3,text='ありがとう',cantonese='好多謝你呀',reviewIndex=0),dict(start=4,end=5,text='はい',cantonese='好',reviewIndex=1)]
   worker.atomic_json(job/'review.json',dict(config={},cues=cues,status='approved'))
   rows=[dict(index=1,seconds=4,slot=2,needsReview=True),dict(index=2,seconds=.8,slot=1,needsReview=False)]
   with patch.object(worker,'ollama_chat',return_value='{"line_0":"多謝"}'),patch.object(duration_fit.urllib.request,'urlopen'):
    self.assertTrue(duration_fit.shorten(dict(port=11439,model='local'),job,cues,rows,1,lambda *a,**kw:None))
   saved=json.loads((job/'review.json').read_text())['cues']
   self.assertEqual(saved[0]['originalCantonese'],'好多謝你呀')
   self.assertEqual(saved[0]['cantonese'],'多謝')
   self.assertEqual((saved[0]['start'],saved[0]['end']),(1,3))
   self.assertEqual(saved[1]['cantonese'],'好')
   self.assertEqual(len(json.loads((job/'duration-edits.json').read_text())),1)
 def test_invalid_rewrite_does_not_mutate_draft(self):
  with tempfile.TemporaryDirectory() as folder:
   cues=[dict(text='ありがとう',cantonese='好多謝你呀')]
   rows=[dict(index=1,seconds=4,slot=2,needsReview=True)]
   with patch.object(worker,'ollama_chat',return_value='{}'):
    self.assertFalse(duration_fit.shorten(dict(port=1,model='local'),Path(folder),cues,rows,1,lambda *a,**kw:None))
    self.assertTrue(cues[0]['translationWarnings'])
   self.assertEqual(cues[0]['cantonese'],'好多謝你呀')
