import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'studio'),str(ROOT/'windows'),str(ROOT/'Resources')]
import test_shared_studio as shared
from desktop_state import read,write
class ResetTests(unittest.TestCase):
 def setUp(self):
  self.fixture=shared.SharedStudioTests('test_basic_submit_uses_automatic_captions_and_preserves_japanese_and_background');self.fixture.setUp();self.addCleanup(self.fixture.tearDown);self.app=self.fixture.app
 def test_reset_keeps_media_archives_metadata_and_clears_only_selected_queue_item(self):
  ident,job=self.fixture.project();row=self.app.row(ident);movie=job/'old.mp4';movie.write_bytes(b'movie');voice=job/'old.wav';voice.write_bytes(b'voice');draft=job/'editor-draft-studio.json';write(draft,dict(marker='saved'));row.update(status='complete',output=str(movie),processingSeconds=100,termRules=[dict(source='test')],externalSubtitle='/old.srt');old=copy.deepcopy(row);settings=copy.deepcopy(self.app.store.settings);self.app.store.queue.append(dict(id='other',video='/other.mp4',status='waiting',progress=0));self.app.store.save();before={p:p.read_bytes() for p in [movie,voice,draft,job/'review.json']}
  plan=self.app.dispatch('reset-video-plan',dict(id=ident));result=self.app.dispatch('reset-video',dict(id=ident,token=plan['token']));fresh=self.app.row(ident)
  self.assertEqual(fresh['id'],ident);self.assertEqual(fresh['video'],old['video']);self.assertEqual(fresh['status'],'waiting');self.assertEqual(fresh['progress'],0);self.assertNotIn('review',fresh);self.assertNotIn('request',fresh);self.assertNotIn('externalSubtitle',fresh);self.assertNotIn('termRules',fresh);self.assertNotIn('output',fresh);self.assertEqual(self.app.store.settings,settings);self.assertEqual([r['id'] for r in self.app.store.queue],[ident,'other']);self.assertEqual(read(Path(result['archive']),{})['row'],old)
  for p,raw in before.items():self.assertEqual(p.read_bytes(),raw)
  request=read(self.app.store.submit(fresh),{});self.assertEqual(request['analysisRerunToken'],fresh['resetToken']);self.assertTrue(request['rebuildDialogue'])
 def test_reset_requires_current_confirmation_and_running_work_is_protected(self):
  ident=self.fixture.add();plan=self.app.dispatch('reset-video-plan',dict(id=ident));self.app.row(ident)['progress']=.2
  with self.assertRaisesRegex(ValueError,'changed'):self.app.dispatch('reset-video',dict(id=ident,token=plan['token']))
  self.app.row(ident)['status']='running';plan=self.app.dispatch('reset-video-plan',dict(id=ident))
  with self.assertRaisesRegex(ValueError,'Pause'):self.app.dispatch('reset-video',dict(id=ident,token=plan['token']))
 def test_reset_disarms_stale_queue_intent_without_starting_other_work(self):
  ident=self.fixture.add();self.app.store.ui.update(autoQueue=True,autoQueueAttention=True);write(self.fixture.root/'studio/queue-session.json',dict(enabled=True,epoch=4,attempted=[]));plan=self.app.dispatch('reset-video-plan',dict(id=ident));self.app.dispatch('reset-video',dict(id=ident,token=plan['token']));self.assertFalse(self.app.store.ui['autoQueue']);self.assertFalse(read(self.fixture.root/'studio/queue-session.json',{})['enabled']);self.assertIsNone(self.app.dispatch('queue-next',dict(epoch=4)))
 def test_reset_selects_confirmed_target_even_when_another_video_is_selected(self):
  ident=self.fixture.add();before=copy.deepcopy(self.app.row(ident));self.app.store.queue.append(dict(id='target',video='/target.mp4',status='complete',progress=1,output='/previous.mp4'));self.app.store.selected=ident;plan=self.app.dispatch('reset-video-plan',dict(id='target'));self.app.dispatch('reset-video',dict(id='target',token=plan['token']));self.assertEqual(self.app.store.selected,'target');self.assertEqual(self.app.row(ident),before);self.assertEqual(self.app.row('target')['status'],'waiting')
 def test_windows_uses_identical_reset_policy(self):
  self.app.platform='win32';ident=self.fixture.add();plan=self.app.dispatch('reset-video-plan',dict(id=ident));self.app.dispatch('reset-video',dict(id=ident,token=plan['token']));self.assertEqual(self.app.row(ident)['status'],'waiting')
if __name__=='__main__':unittest.main()
