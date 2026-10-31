"""Human review state on every dialogue line, desktop build 278."""
import json,sys,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Resources'));sys.path.insert(0,str(ROOT/'studio'))
import review_workbench as w

def fixture():
    return dict(review=dict(cues=[dict(start=0,end=2,speechStart=0,speechEnd=2,cantonese='你好',speakerId='R01')]),
      draft=dict(segments=[dict(id='s1',sources=[0],start=0,end=2,text='你好',speakerId='R01',take=7)]),
      reportRows=[dict(index=1,language='yue',engine='drama3',reportGroup='reportAvailable',selectedAudio='take.wav',recordingSHA256='h1')],
      issues=[],resolvedIssues=[])

class LineTriageTests(unittest.TestCase):
 def test_line_without_an_issue_carries_a_review_state(self):
  with TemporaryDirectory() as d:
   snap=w.project(d,fixture());row=snap['reportRows'][0]
   self.assertEqual(row['triage'],'pending');self.assertEqual(row['triageID'],'line-1-yue-drama3')
   self.assertTrue(row['triageFingerprint']);self.assertEqual(snap['reviewTriage'],dict(pending=1,checked=0,deferred=0,total=1))
 def test_marked_line_persists_and_counts(self):
  with TemporaryDirectory() as d:
   snap=w.project(d,fixture());row=snap['reportRows'][0]
   result=w.mark(d,snap,row['triageID'],row['triageFingerprint'],'deferred')
   self.assertEqual(result['reportRows'][0]['triage'],'deferred')
   self.assertEqual(result['reviewTriage'],dict(pending=0,checked=0,deferred=1,total=1))
   self.assertEqual(json.loads((Path(d)/'review-triage.json').read_text())['decisions']['line-1-yue-drama3']['state'],'deferred')
 def test_changed_words_or_recording_clears_the_mark(self):
  with TemporaryDirectory() as d:
   snap=w.project(d,fixture());row=snap['reportRows'][0]
   w.mark(d,snap,row['triageID'],row['triageFingerprint'],'checked')
   edited=fixture();edited['draft']['segments'][0]['text']='你好嗎';again=w.project(d,edited)
   self.assertEqual(again['reportRows'][0]['triage'],'pending')
   recorded=fixture();recorded['reportRows'][0].update(selectedAudio='take2.wav',recordingSHA256='h2')
   self.assertEqual(w.project(d,recorded)['reportRows'][0]['triage'],'pending')
 def test_stale_evidence_and_unknown_target_are_rejected(self):
  with TemporaryDirectory() as d:
   snap=w.project(d,fixture())
   with self.assertRaisesRegex(ValueError,'changed'):w.mark(d,snap,'line-1-yue-drama3','stale','checked')
   with self.assertRaisesRegex(ValueError,'Unknown review target'):w.mark(d,snap,'line-9-yue-drama3','whatever','checked')
 def test_flagged_line_keeps_the_issue_state(self):
  with TemporaryDirectory() as d:
   snap=fixture();snap['issues']=[dict(id='issue-1',index=1,language='yue',engine='drama3',kind='missing-audio',reportGroup='reportMissing',evidence=[])]
   result=w.project(d,snap);issue=result['issues'][0]
   w.mark(d,result,issue['id'],issue['triageFingerprint'],'checked')
   again=w.project(d,fixture()|dict(issues=[dict(id='issue-1',index=1,language='yue',engine='drama3',kind='missing-audio',reportGroup='reportMissing',evidence=[])]))
   self.assertEqual(again['issues'][0]['triage'],'checked')
   self.assertEqual(again['reportRows'][0]['triage'],'checked')

class ReviewRpcTests(unittest.TestCase):
 def test_report_rpc_marks_a_line_with_no_diagnostic_issue(self):
  from backend import Studio
  from desktop_state import write,defaults
  from use_terms import document
  with TemporaryDirectory() as d:
   root=Path(d);video=root/'source.mp4';video.write_bytes(b'fixture')
   app=Studio(root,ROOT/'Resources',helper=root/'helper')
   app.dispatch('accept-use-terms',dict(accepted=True,sha256=document()['sha256'],language='en'))
   ident=app.dispatch('add',dict(paths=[str(video)]))['selected'];job=root/'jobs/quiet';job.mkdir(parents=True)
   cfg=dict(defaults(),video=str(video),duration=3,voiceProfiles=[]);review=dict(config=cfg,cues=[dict(start=0,end=2,speechStart=0,speechEnd=2,cantonese='你好')])
   write(job/'review.json',review)
   row=app.row(ident);row.update(job=str(job),review=str(job/'review.json'),status='attention');app.store.save()
   snap=app.dispatch('snapshot',dict(id=ident));line=snap['reportRows'][0]
   self.assertEqual(line['triage'],'pending')
   saved=app.dispatch('review-triage',dict(id=ident,issueID=line['triageID'],fingerprint=line['triageFingerprint'],state='checked'))
   self.assertEqual(saved['reportRows'][0]['triage'],'checked')
   reopened=Studio(root,ROOT/'Resources',helper=root/'helper')
   self.assertEqual(reopened.dispatch('snapshot',dict(id=ident))['reportRows'][0]['triage'],'checked')
if __name__=='__main__':unittest.main()
