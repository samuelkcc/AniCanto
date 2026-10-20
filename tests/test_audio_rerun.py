import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import audio_manifest,dubbing_setup

class AudioRerunTests(unittest.TestCase):
 def test_one_line_retry_keeps_other_auditions(self):
  with tempfile.TemporaryDirectory() as name:
   cues=[dict(start=1,end=2,speakerId='a',cantonese='one'),dict(start=3,end=4,speakerId='b',cantonese='two')]
   audio_manifest.publish(name,'gpt-sovits','yue',cues,['one.wav','two.wav'])
   audio_manifest.publish(name,'gpt-sovits','yue',[dict(cues[0],_seed=73)],['new.wav'])
   saved=json.loads((Path(name)/'audio-preview.json').read_text())
   self.assertEqual(len(saved['rows']),3);self.assertIn('two.wav',[r['audio'] for r in saved['rows']])
   audio_manifest.publish(name,'gpt-sovits','yue',[dict(cues[0],_seed=73)],['leveled.wav'])
   saved=json.loads((Path(name)/'audio-preview.json').read_text());self.assertEqual(len(saved['rows']),3)
   self.assertEqual(saved['rows'][-1]['audio'],'leveled.wav');self.assertEqual(saved['rows'][-1]['modelVersion'],'v4')
 def test_engine_and_language_are_isolated(self):
  with tempfile.TemporaryDirectory() as name:
   c=dict(start=1,end=2,speakerId='a',cantonese='one')
   audio_manifest.publish(name,'gpt-sovits','yue',[c],['yue.wav'])
   audio_manifest.publish(name,'gpt-sovits','en',[c],['en.wav'])
   saved=json.loads((Path(name)/'audio-preview.json').read_text());self.assertEqual([r['audio'] for r in saved['rows']],['en.wav'])
 def test_selected_original_keeps_japanese_reference_language(self):
  import dubbing
  with tempfile.TemporaryDirectory() as name:
   path=Path(name)/'ref.wav';path.write_bytes(b'fixture')
   profile=dict(id='a',reference=str(path),promptText='old',engineReferences={'gpt-sovits:yue':dict(reference=str(path),promptText='日本語',language='ja',enabled=True)})
   selected=dubbing.profile_for(dict(speakerId='a'),dict(voiceProfiles=[profile],ttsBackend='gpt-sovits',targetLanguage='yue'))
   self.assertEqual(selected['language'],'ja');self.assertEqual(selected['promptText'],'日本語');self.assertEqual(selected['referenceCandidates'],[])
 def test_preserved_v2_recording_is_never_relabelled_v4(self):
  import multitrack
  with tempfile.TemporaryDirectory() as name:
   folder=Path(name);(folder/'review.json').write_text(json.dumps(dict(config=dict(ttsBackend='gpt-sovits'))))
   row=dict(engine='gpt-sovits',folder=folder)
   self.assertEqual(multitrack.recorded_model(row,{}),'v2')
   (folder/'review.json').write_text(json.dumps(dict(config=dict(gsvVersion='v4'))))
   self.assertEqual(multitrack.recorded_model(row,{}),'v4')
 def test_v4_manifest_never_contains_v2_weights(self):
  self.assertIn('gsv-v4-pretrained/vocoder.pth',dubbing_setup.GSV_MODELS)
  self.assertIn('gsv-v4-pretrained/s2Gv4.pth',dubbing_setup.GSV_MODELS)
  self.assertIn('s1v3.ckpt',dubbing_setup.GSV_MODELS)
  self.assertFalse(any('v2' in path for path in dubbing_setup.GSV_MODELS))
  self.assertTrue(all(len(sha)==64 for path,sha in dubbing_setup.GSV_MODELS.items() if path.endswith(('.pth','.ckpt','.bin'))))
if __name__=='__main__':unittest.main()
