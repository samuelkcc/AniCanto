"""Save and reopen editing decisions through the real desktop data boundary."""
import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_shared_studio as fixture
from desktop_state import read,write
from backend import Studio
from project_edit import materialize

class ContextEditorTests(unittest.TestCase):
 setUp=fixture.SharedStudioTests.setUp
 tearDown=fixture.SharedStudioTests.tearDown
 add=fixture.SharedStudioTests.add
 project=fixture.SharedStudioTests.project
 def test_display_only_change_keeps_selected_audio_after_save_and_reopen(self):
  ident,folder=self.project();draft=self.app.dispatch('snapshot',dict(id=ident))['draft'];before=(folder/'review.json').read_bytes()
  draft['segments'][0].update(audioTake=str(folder/'accepted.wav'),captionText='只更改顯示字幕',reviewDecisions={'yue:drama3':{'action':'recording','audio':str(folder/'accepted.wav')}})
  self.app.dispatch('save-draft',dict(id=ident,draft=draft));again=Studio(self.root,fixture.ROOT/'Resources',helper=self.helper).draft(self.app.row(ident));cue=materialize(read(folder/'review.json'),again)[0]
  self.assertEqual(cue['editorAudio'],str(folder/'accepted.wav'));self.assertEqual(cue['captionText'],'只更改顯示字幕');self.assertEqual(cue['cantonese'],'你好呀。');self.assertEqual(again['segments'][0]['reviewDecisions'],draft['segments'][0]['reviewDecisions']);self.assertEqual((folder/'review.json').read_bytes(),before)
 def test_local_mix_survives_reload_without_changing_global_default(self):
  ident,folder=self.project();old=copy.deepcopy(self.app.store.settings);self.app.dispatch('configure',dict(scope='video',id=ident,useGlobalSettings=False,settings={}));self.app.dispatch('configure',dict(scope='video',id=ident,settings={'backgroundGain':.35,'backgroundDucking':False}))
  other=Studio(self.root,fixture.ROOT/'Resources',helper=self.helper);self.assertEqual(other.state()['productionSettings']['backgroundGain'],.35);self.assertFalse(other.state()['productionSettings']['backgroundDucking']);self.assertEqual(other.store.settings.get('backgroundGain'),old.get('backgroundGain'));self.assertEqual(other.store.settings.get('backgroundDucking'),old.get('backgroundDucking'))
 def test_manual_native_audio_request_does_not_start_full_movie_export(self):
  ident,folder=self.project();draft=self.app.dispatch('snapshot',dict(id=ident))['draft'];draft['settings']['previewNativeAudio']=True;before=(folder/'review.json').read_bytes();spec=self.app.dispatch('render',dict(id=ident,draft=draft,segment=draft['segments'][0]['id'],engine='drama3',language='yue'))
  cfg=read(Path(spec['args'][-1]));submitted=read(Path(cfg['submission']));self.assertTrue(cfg['previewNativeAudio']);self.assertEqual(submitted['previewSegment'],draft['segments'][0]['id']);self.assertEqual(submitted['previewEngine'],'drama3');self.assertEqual((folder/'review.json').read_bytes(),before)

if __name__=='__main__':unittest.main()
