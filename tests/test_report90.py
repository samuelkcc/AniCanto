import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import review_report,review_notices,performance_review
class ReportTests(unittest.TestCase):
 def save(self,p,data):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data))
 def fixture(self,r):
  cue=dict(start=0,end=2,cantonese='完整台詞',japanese='元の言葉')
  review=dict(config=dict(ttsBackend='drama3',targetLanguage='yue'),cues=[cue]);self.save(r/'review.json',review);return review
 def test_plain_recording_checkpoint_is_not_an_issue_or_a_quality_pass(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);v=self.fixture(r);self.save(r/'normal-checks.json',dict(repairs=[dict(index=1,reason='uncertain-or-usable',check={},attempts=[],repaired=False)],unresolved=[]))
   p=review_report.project(r,v,dict(status='complete'));self.assertEqual(p['issues'],[]);self.assertFalse(p['reviewState']['qualityChecked'])
 def test_confirmed_failure_and_explicit_unresolved_still_visible(self):
  for check,unresolved in [({'contentFailure':True},[]),({},[1])]:
   with self.subTest(check=check),tempfile.TemporaryDirectory() as d:
    r=Path(d);v=self.fixture(r);self.save(r/'normal-checks.json',dict(repairs=[dict(index=1,reason='uncertain-or-usable',check=check,attempts=[])],unresolved=unresolved))
    self.assertEqual(review_report.project(r,v,dict(status='complete'))['reviewState']['pending'],1)
 def test_roundoff_is_not_an_overrun_but_real_excess_remains(self):
  for seconds,expected in [(2.7,0),(2.9,1)]:
   with self.subTest(seconds=seconds),tempfile.TemporaryDirectory() as d:
    r=Path(d);v=self.fixture(r);self.save(r/'natural-placement.json',dict(rows=[dict(index=1,start=7.3,deadline=10,seconds=seconds,fit=False)]))
    self.assertEqual(len(review_report.project(r,v,dict(status='complete'))['issues']),expected)
 def test_deliberate_subtitle_gap_is_not_missing_tts(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);v=self.fixture(r);v['cues'][0].update(cantonese='',japanese='',subtitleContentOnlyGap=True,preserveOriginalSpeech=True,sourcePolicyBlocked=True,originalSpeechReason='subtitle-content-only-gap')
   self.save(r/'segment-issues.json',[dict(index=1,kind='missing-script')]);self.save(r/'timing.json',[dict(index=1,originalFallback=True)])
   self.assertEqual(review_report.project(r,v,dict(status='complete'))['issues'],[])
 def test_continuation_clock_warning_not_mislabelled_missing_script(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);v=self.fixture(r);v['cues'][0].update(cantonese='',preserveOriginalSpeech=True,sourceClockUnconfirmed=True,originalSpeechReason='subtitle-continuation')
   self.save(r/'segment-issues.json',[dict(index=1,kind='missing-script')]);rows=review_report.project(r,v,dict(status='complete'))['issues']
   self.assertEqual(len(rows),1);self.assertEqual(rows[0]['kind'],'source-clock-unconfirmed')
 def test_notice_metrics_keep_counts_separate_from_failure_claim(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);self.save(r/'source-fragment-report.json',dict(suspectSegments=35,windows=21,recoveredSegments=1,unconfirmedSegments=34));self.save(r/'source-policy.json',dict(unresolved=[],fallbackTurns=[1,2],continuationTurns=[3],primaryFallbacks=0,subtitleClockGaps=[]))
   rows=review_notices.project(r);self.assertEqual([m['value'] for m in rows[0]['metrics']],[35,21,1,34]);self.assertIn('not missing dubbing',rows[1]['message']);self.assertEqual(rows[1]['metrics'][0]['value'],0)
 def test_parent_and_track_kept_intervals_count_once(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);child=r/'tracks/current';data=dict(events=[dict(start=1,end=2,label='laughter')],originalSoundRanges=[[3,4]],reviewEvents=[])
   self.save(r/'nonverbal-report.json',data);self.save(child/'nonverbal-report.json',data);p=performance_review.project(r,{r,child},{})
   self.assertEqual(p['keptRanges'],2);self.assertFalse(p['qualityCertified'])
class RetryEligibilityTests(unittest.TestCase):
 def test_pending_retry_ignores_advisory_but_keeps_real_delivery_target(self):
  from review_retry import submission
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);job=r/'jobs/test';track=job/'tracks/current';track.mkdir(parents=True)
   review=dict(config=dict(productionMode='normal',ttsBackend='drama3',duration=4,targetLanguage='yue'),cues=[dict(start=0,end=2,text='一',cantonese='第一句'),dict(start=2,end=4,text='二',cantonese='第二句')]);path=job/'review.json';path.write_text(json.dumps(review));(job/'report.json').write_text(json.dumps(dict(tracks=[dict(engine='drama3',language='yue',report=str(track/'report.json'))])));(track/'timing.json').write_text('[]')
   snapshot=dict(issues=[dict(index=1,engine='drama3',language='yue',repairEligible=False),dict(index=2,engine='drama3',language='yue',repairEligible=True)])
   result=submission(r,path,snapshot);self.assertEqual(result['automaticReviewRetry']['targets'],{'yue:drama3':[2]})
if __name__=='__main__':unittest.main()
