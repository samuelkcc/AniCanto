import json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import atomic_files,project_store
real_replace=os.replace

def denied(*args,**details):
    """Windows reports a locked rename as WinError 5."""
    error=OSError(5,'Access is denied');error.winerror=5;raise error

class IssueCheckpointTests(unittest.TestCase):
 def test_denied_gap_checkpoint_keeps_the_line_running(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);job=root/'jobs/one';job.mkdir(parents=True)
   cfg=dict(storage=tmp,ttsBackend='drama3',targetLanguage='yue')
   with patch('atomic_files.write_json',side_effect=denied):
    row=project_store.record_issue(cfg,job,dict(reviewIndex=3,start=1.0,end=2.0),'tts-generation','[WinError 5] Access is denied')
    again=project_store.record_issue(cfg,job,dict(reviewIndex=7,start=4.0,end=5.0),'tts-generation','[WinError 5] Access is denied')
   self.assertEqual((row['index'],row['kind'],row['status']),(4,'tts-generation','skipped'))
   self.assertEqual(again['index'],8)
   self.assertFalse((job/'segment-issues.json').exists())
   with project_store.connect(root) as db:
    self.assertEqual([json.loads(r[0])['index'] for r in db.execute('SELECT payload FROM issues ORDER BY cue')],[4,8])
 def test_gap_checkpoint_replaces_one_row_per_index_and_kind(self):
  with tempfile.TemporaryDirectory() as tmp:
   job=Path(tmp)/'job';job.mkdir()
   cfg=dict(ttsBackend='drama3',targetLanguage='yue')
   for message in ('first','second'):
    project_store.record_issue(cfg,job,dict(reviewIndex=2,start=1.0,end=2.0),'tts-generation',message)
   project_store.record_issue(cfg,job,dict(reviewIndex=2,start=1.0,end=2.0),'reference','other kind')
   rows=json.loads((job/'segment-issues.json').read_text())
   self.assertEqual([(r['message'],r['kind']) for r in rows],[('second','tts-generation'),('other kind','reference')])
   self.assertFalse([p for p in job.iterdir() if p.suffix=='.tmp' or p.name.startswith('.segment-issues.json-')])
 def test_replace_retries_through_a_short_windows_lock(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'report.json';attempts=[]
   def flaky(source,target):
    attempts.append(1)
    if len(attempts)<3:
     error=OSError(5,'Access is denied');error.winerror=5;raise error
    real_replace(source,target)
   with patch('os.replace',side_effect=flaky):atomic_files.write_json(path,dict(ok=True))
   self.assertEqual(json.loads(path.read_text()),dict(ok=True))
   self.assertEqual(len(attempts),3)
   self.assertFalse([p for p in Path(tmp).iterdir() if p.name.startswith('.report.json-')])

if __name__=='__main__':unittest.main()
