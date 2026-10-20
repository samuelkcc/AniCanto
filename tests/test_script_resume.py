import copy,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import script_resume,worker,hybrid_script

class ScriptResumeTests(unittest.TestCase):
 def setup_review(self,folder):
  cfg=dict(video='ep07.mkv',model='test',duration=10,autoApprove=True)
  raw=[dict(start=1,end=2,text='以上です。',japanese='以上です。',cantonese='',hybridRevision=hybrid_script.REVISION)]
  saved=copy.deepcopy(raw);saved[0]['cantonese']='講完啦。';saved[0]['scriptGapRecovery']={'source':'own Japanese'}
  (folder/'review.json').write_text(json.dumps(dict(config=cfg,cues=saved,status='pending')))
  return cfg,raw,saved
 def test_recover_delivery_draft_before_stale_blank_cache_without_new_translation(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);cfg,cues,saved=self.setup_review(p);events=[]
   w=SimpleNamespace(validate_review=worker.validate_review,emit=lambda *a,**kw:events.append(a))
   self.assertTrue(script_resume.restore(w,cfg,p,cues));self.assertEqual(cues,saved)
   self.assertTrue(events);self.assertNotIn('scriptLocked',cfg)
 def test_source_timing_model_or_explicit_new_translation_invalidates_reuse(self):
  for change in ['clock','source','model','policy','explicit']:
   with self.subTest(change=change),tempfile.TemporaryDirectory() as d:
    p=Path(d);cfg,cues,saved=self.setup_review(p)
    if change=='clock':cues[0]['start']=1.2
    if change=='source':cues[0]['japanese']='別の言葉'
    if change=='model':cfg['model']='other'
    if change=='policy':cfg['translationSource']='audio-only'
    if change=='explicit':cfg['forceRetranslate']=True
    original=copy.deepcopy(cues)
    self.assertFalse(script_resume.restore(worker,cfg,p,cues));self.assertEqual(cues,original)
 def test_partial_or_old_automatic_draft_is_not_silently_certified(self):
  for field,value in [('cantonese',''),('hybridRevision','old')]:
   with tempfile.TemporaryDirectory() as d:
    p=Path(d);cfg,cues,saved=self.setup_review(p);saved[0][field]=value
    (p/'review.json').write_text(json.dumps(dict(config=cfg,cues=saved,status='pending')))
    self.assertFalse(script_resume.restore(worker,cfg,p,cues))
