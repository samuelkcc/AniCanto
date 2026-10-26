import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'studio'),str(ROOT/'windows'),str(ROOT/'Resources')]
import test_shared_studio as shared
import test_workflow70_integration as workflow
from desktop_state import read,write
import update_plan

class RestartTests(unittest.TestCase):
 def setUp(self):
  self.fixture=shared.SharedStudioTests('test_basic_submit_uses_automatic_captions_and_preserves_japanese_and_background');self.fixture.setUp();self.addCleanup(self.fixture.tearDown);self.app=self.fixture.app
 def test_paused_restart_creates_new_request_without_touching_frozen_job(self):
  ident=self.fixture.add();row=self.app.row(ident);old=self.fixture.root/'requests/old.json';write(old,dict(video=row['video'],model='old',frozenMarker=True));original=old.read_bytes()
  row.update(status='paused',request=str(old));self.app.store.save()
  spec=self.app.dispatch('start',dict(id=ident,freshVersion=True,reanalyze=True));cfg=read(Path(spec['args'][-1]))
  self.assertNotEqual(Path(spec['args'][-1]),old);self.assertEqual(old.read_bytes(),original)
  self.assertTrue(cfg['forceRetranslate']);self.assertTrue(cfg['rebuildDialogue']);self.assertTrue(cfg['analysisRerunToken']);self.assertEqual(row['id'],ident)
 def test_normal_paused_resume_still_uses_original_frozen_request(self):
  ident=self.fixture.add();row=self.app.row(ident);old=self.fixture.root/'requests/old.json';write(old,dict(video=row['video'],selectedEngines=['drama3'],ttsBackend='drama3',frozenMarker=True));original=old.read_bytes()
  row.update(status='paused',request=str(old));self.app.store.save()
  spec=self.app.dispatch('start',dict(id=ident));self.assertEqual(Path(spec['args'][-1]),old);self.assertEqual(old.read_bytes(),original)
 def test_completed_restart_keeps_row_id_movie_and_recordings(self):
  ident,job=self.fixture.project();row=self.app.row(ident);movie=job/'old.mp4';movie.write_bytes(b'previous movie');take=job/'old.wav';take.write_bytes(b'previous voice');row.update(status='complete',output=str(movie))
  before={p:p.read_bytes() for p in [movie,take,job/'review.json']};self.app.dispatch('start',dict(id=ident,freshVersion=True,reanalyze=True))
  self.assertEqual(len(self.app.store.queue),1);self.assertEqual(self.app.row(ident)['id'],ident)
  for p,data in before.items():self.assertEqual(p.read_bytes(),data)
 def test_running_item_cannot_restart(self):
  ident=self.fixture.add();self.app.row(ident)['status']='running'
  with self.assertRaisesRegex(ValueError,'already processing'):self.app.dispatch('start',dict(id=ident,freshVersion=True,reanalyze=True))
 def test_regenerate_all_keeps_exact_appended_pairs_and_script(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);path=root/'review.json';write(path,dict(config={},cues=[]));draft=dict(settings=dict(_trackPairs=[['yue','drama3'],['en','cosyvoice3']],selectedEngines=['drama3','cosyvoice3'],dubLanguages=['yue','en']),segments=[dict(id='a',text='保留稿件')]);before=copy.deepcopy(draft)
   plan=update_plan.build(path,draft,'all');self.assertEqual(plan['settings']['_trackPairs'],draft['settings']['_trackPairs']);self.assertEqual(plan['segments'],draft['segments']);self.assertTrue(plan['settings']['audioRerunToken']);self.assertEqual(draft,before)
if __name__=='__main__':unittest.main()
