import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows'),str(ROOT/'studio')]
import review_workbench as w,workflow_log

class WorkbenchTests(unittest.TestCase):
 def fixture(self):
  cue=dict(start=0,end=2,cantonese='你好',english='Hello',speakerId='R01')
  profile=dict(id='R01',reference='/original.wav',promptText='こんにちは',language='ja')
  segment=dict(id='cue-0',sources=[0],start=0,end=2,text='你好',english='Hello',speakerId='R01')
  issues=[dict(id=lang,index=1,language=lang,engine='drama3',kind='timing-overrun',text=cue['english' if lang=='en' else 'cantonese'],evidence=[dict(seconds=3)]) for lang in ('yue','en')]
  return dict(review=dict(config=dict(voiceProfiles=[profile]),cues=[cue]),draft=dict(settings=dict(voiceProfiles=[profile]),segments=[segment]),issues=issues,takes=[])
 def test_scoped_decisions_survive_reopen_without_claiming_quality_or_deleting_issues(self):
  with tempfile.TemporaryDirectory() as d:
   snap=w.project(d,self.fixture());fp=snap['issues'][0]['triageFingerprint'];w.mark(d,snap,'yue',fp,'checked')
   reopened=w.project(d,self.fixture());self.assertEqual(reopened['issues'][0]['triage'],'checked');self.assertEqual(reopened['issues'][1]['triage'],'pending')
   self.assertEqual(len(reopened['issues']),2);self.assertFalse(reopened['workbench']['qualityCertified']);self.assertEqual(reopened['workbench']['categories']['timing'],2)
 def test_defer_undo_and_reopen_do_not_change_evidence(self):
  with tempfile.TemporaryDirectory() as d:
   snap=w.project(d,self.fixture());evidence=copy.deepcopy(snap['issues'][0]['evidence']);fp=snap['issues'][0]['triageFingerprint']
   w.mark(d,snap,'yue',fp,'deferred');self.assertEqual(snap['workbench']['deferred'],1)
   w.mark(d,snap,None,None,'undo');self.assertEqual(snap['issues'][0]['triage'],'pending');self.assertEqual(snap['issues'][0]['evidence'],evidence)
 def test_new_words_new_reference_and_new_evidence_reopen_only_the_relevant_issue(self):
  for change in ('script','reference','evidence'):
   with self.subTest(change=change),tempfile.TemporaryDirectory() as d:
    snap=w.project(d,self.fixture());w.mark(d,snap,'yue',snap['issues'][0]['triageFingerprint'],'checked')
    new=self.fixture()
    if change=='script':new['draft']['segments'][0]['text']='你好呀'
    elif change=='reference':new['draft']['settings']['voiceProfiles'][0]['reference']='/new.wav'
    else:new['issues'][0]['evidence'].append(dict(heard='missing words'))
    self.assertEqual(w.project(d,new)['issues'][0]['triage'],'pending')
 def test_delayed_confirmation_is_rejected_and_cannot_write(self):
  with tempfile.TemporaryDirectory() as d:
   snap=w.project(d,self.fixture());fp=snap['issues'][0]['triageFingerprint'];snap['issues'][0]['text']='new words'
   with self.assertRaisesRegex(ValueError,'changed'):w.mark(d,snap,'yue',fp,'checked')
   self.assertFalse((Path(d)/'review-triage.json').exists())
 def test_latest_take_is_used_and_reference_changes_flag_only_affected_track(self):
  snap=self.fixture();profile=snap['review']['config']['voiceProfiles'][0]
  provenance=dict(speakerId='R01',reference=w.reference_signature(profile))
  snap['takes']=[dict(index=1,engine='drama3',language='yue',audio='old.wav',text='old words',recordingProvenance=provenance),dict(index=1,engine='drama3',language='yue',audio='new.wav',text='你好',recordingProvenance=provenance)]
  self.assertEqual(w.stale_recordings(snap),[])
  snap['draft']['settings']['voiceProfiles'][0]=dict(profile,reference='/replacement.wav')
  stale=w.stale_recordings(snap);self.assertEqual(len(stale),1);self.assertEqual(stale[0]['reasons'],['reference']);self.assertEqual(stale[0]['recordings'],['new.wav'])
 def test_acknowledged_take_is_protected_from_bulk_regeneration(self):
  snap=self.fixture();snap['takes']=[dict(index=1,engine='drama3',language='yue',audio='old.wav',text='old')]
  snap['draft']['segments'][0]['reviewDecisions']={'yue:drama3':dict(action='recording')}
  self.assertTrue(w.stale_recordings(snap)[0]['protected'])
 def test_unknown_historical_provenance_is_not_guessed(self):
  snap=self.fixture();snap['takes']=[dict(index=1,engine='drama3',language='yue',audio='legacy.wav')]
  self.assertEqual(w.stale_recordings(snap),[])
 def test_heartbeat_updates_last_seen_without_fake_progress_or_duplicate_log(self):
  with tempfile.TemporaryDirectory() as d:
   row=dict(attempt=dict(path=str(Path(d)/'attempts/test')));event=dict(stage='Voice',message='Loading',workID='tts',workCompleted=4,workTotal=20,progress=.5)
   with patch('workflow_log.time.time',return_value=100):workflow_log.record(d,row,event)
   with patch('workflow_log.time.time',return_value=140):workflow_log.record(d,row,event)
   self.assertEqual(row['lastEventAt'],140);self.assertEqual(row['lastProgressAt'],100)
   self.assertEqual(len((Path(d)/'attempts/test/workflow.jsonl').read_text().splitlines()),1)

class WorkbenchBoundaryTests(unittest.TestCase):
 def test_persisted_rpc_state_and_running_guard(self):
  from backend import Studio
  from desktop_state import write,defaults
  from use_terms import document
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);video=root/'source.mp4';video.write_bytes(b'fixture');app=Studio(root,ROOT/'Resources',helper=root/'helper')
   app.dispatch('accept-use-terms',dict(accepted=True,sha256=document()['sha256'],language='en'))
   ident=app.dispatch('add',dict(paths=[str(video)]))['selected'];job=root/'jobs/workbench';job.mkdir(parents=True)
   cfg=dict(defaults(),video=str(video),duration=3,voiceProfiles=[]);review=dict(config=cfg,cues=[dict(start=0,end=2,cantonese='你好',english='Hello')])
   write(job/'review.json',review);write(job/'segment-issues.json',[dict(index=1,kind='missing-audio')])
   row=app.row(ident);row.update(job=str(job),review=str(job/'review.json'),status='attention');app.store.save()
   snap=app.dispatch('snapshot',dict(id=ident));issue=snap['issues'][0]
   result=app.dispatch('review-triage',dict(id=ident,issueID=issue['id'],fingerprint=issue['triageFingerprint'],state='deferred'))
   self.assertEqual(result['workbench']['deferred'],1)
   reopened=Studio(root,ROOT/'Resources',helper=root/'helper');self.assertEqual(reopened.dispatch('snapshot',dict(id=ident))['workbench']['deferred'],1)
   reopened.row(ident)['status']='running'
   with self.assertRaisesRegex(ValueError,'Pause'):reopened.dispatch('review-triage',dict(id=ident,state='undo'))
if __name__=='__main__':unittest.main()
