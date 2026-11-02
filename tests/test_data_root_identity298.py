"""Path relocation must not create fresh job identities or refund spent attempts."""
import hashlib,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'Resources'))
import job_identity,workflow_policy
class RelocationIdentity(unittest.TestCase):
 def test_relocated_saved_identity_and_spent_ledger_are_reused(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d).resolve()/'AniCanto';root.mkdir();old=root.with_name('SamCantoSync')
   original=dict(storage=str(old),video='/media/unchanged.mp4',sourceWorkflowRevision='priority-paths-2-subtitle-content-only',sourceStat=[100,123])
   body=job_identity.canonical(original);fingerprint=job_identity.digest(body);job=root/'jobs'/fingerprint[:16];job.mkdir(parents=True)
   relocated=json.loads(json.dumps(body).replace(str(old),str(root)))
   (job/'resume-identity.json').write_text(json.dumps(dict(schemaVersion=1,fingerprint=fingerprint,identity=relocated)))
   (root/'data-root-relocation.json').write_text(json.dumps(dict(schemaVersion=1,complete=True,oldRoot=str(old),newRoot=str(root))))
   self.assertEqual(job_identity.resolve(root,relocated),job)
   identity=[str(old/'jobs/reference.wav'),'fixed source'];key=hashlib.sha256(json.dumps(identity,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
   (job/'fixture-budget.json').write_text(json.dumps({key:dict(attempts=1)}))
   self.assertFalse(workflow_policy.reserve(job,'fixture',[str(root/'jobs/reference.wav'),'fixed source'],1))
   self.assertEqual(json.loads((job/'fixture-budget.json').read_text())[key]['attempts'],1)
if __name__=='__main__':unittest.main()
