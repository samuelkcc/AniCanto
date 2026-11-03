"""Explicit per-line recording removal: guard rules, move, manifest and hiding."""
import json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'windows'))
from desktop_state import job_snapshot,write
from review_take_removal import remove,blocks

class ReviewTakeRemoval275(unittest.TestCase):
 def setUp(self):
  self._tmp=tempfile.TemporaryDirectory();self.root=Path(self._tmp.name)
  track=self.root/'tracks/drama';track.mkdir(parents=True)
  write(self.root/'review.json',dict(config=dict(ttsBackend='drama3',targetLanguage='yue',dubLanguages=['yue'],selectedEngines=['drama3']),cues=[dict(start=1,end=2,cantonese='你好呀')]))
  write(track/'review.json',dict(config=dict(ttsBackend='drama3',targetLanguage='yue'),cues=[]))
  self.first=track/'first.wav';self.first.write_bytes(b'first take')
  self.retry=track/'retry.wav';self.retry.write_bytes(b'retry take')
  write(track/'normal-checks.json',dict(repairs=[dict(index=1,originalAudio=str(self.first),attempts=[dict(candidateAudio=str(self.retry),repaired=False)])]))
 def tearDown(self):self._tmp.cleanup()
 def snapshot(self):return job_snapshot(dict(job=str(self.root)))
 # A report projection with one listed candidate, written by hand so each guard is tested alone.
 def listed(self,*paths):
  return dict(review=dict(config=dict(dubLanguages=['yue'],selectedEngines=['drama3'])),takes=[],history=[],issues=[],resolvedIssues=[],reportRows=[],
              recordingCandidates=[dict(path=str(self.first),index=1,engine='drama3',language='yue',kind='first',created=1)]+[dict(path=str(p),index=1,engine='drama3',language='yue',kind='generated',created=2) for p in paths if p!=self.first])

 def test_removed_recording_moves_with_manifest_and_stays_hidden(self):
  record=remove(self.root,self.snapshot(),{},0,'yue','drama3',str(self.retry),True)
  self.assertFalse(self.retry.exists())
  moved=Path(record['discarded']);self.assertTrue(moved.is_file());self.assertEqual(moved.read_bytes(),b'retry take')
  self.assertEqual((record['index'],record['language'],record['engine']),(1,'yue','drama3'))
  self.assertFalse(record['qualityCertified'])
  manifest=json.loads((moved.parent/'removal.json').read_text())
  self.assertEqual(manifest['sha256'],record['sha256']);self.assertEqual(manifest['path'],str(self.retry.resolve()))
  after=self.snapshot()
  self.assertNotIn(str(self.retry.resolve()),[x['path'] for x in after['recordingCandidates']])
  self.assertIn(str(self.first.resolve()),[x['path'] for x in after['recordingCandidates']])
  self.assertEqual([x['path'] for x in after['removedTakes']],[str(self.retry.resolve())])
  self.assertEqual(len(blocks(self.root)),1)

 def test_first_generated_recording_is_protected_without_an_export(self):
  with self.assertRaisesRegex(ValueError,'first generated recording'):
   remove(self.root,self.snapshot(),{},0,'yue','drama3',str(self.first),True)
  self.assertTrue(self.first.is_file())

 def test_line_one_uses_the_same_zero_based_position_as_the_report(self):
  self.assertEqual(remove(self.root,self.snapshot(),{},0,'yue','drama3',str(self.retry),True)['index'],1)
  with self.assertRaises(ValueError):remove(self.root,self.snapshot(),{},-1,'yue','drama3',str(self.first),True)

 def test_a_removed_recording_cannot_be_removed_twice(self):
  remove(self.root,self.snapshot(),{},0,'yue','drama3',str(self.retry),True)
  with self.assertRaisesRegex(ValueError,'already removed'):remove(self.root,self.snapshot(),{},0,'yue','drama3',str(self.retry),True)
  moved=next((self.root/'discarded-recordings').glob('*/audio.wav'))
  with self.assertRaisesRegex(ValueError,'discarded-recordings folder'):remove(self.root,self.snapshot(),{},0,'yue','drama3',str(moved),True)

 def test_audio_used_by_the_export_or_a_saved_choice_never_moves(self):
  for snapshot,draft in ((dict(self.listed(self.retry),reportRows=[dict(index=1,language='yue',engine='drama3',selectedAudio=str(self.retry))]),{}),
                         (self.listed(self.retry),dict(segments=[dict(sources=[0],audioTake=str(self.retry))])),
                         (self.listed(self.retry),dict(segments=[dict(sources=[0],reviewDecisions={'yue:drama3':dict(audio=str(self.retry))})]))):
   with self.assertRaisesRegex(ValueError,'current export or a saved choice'):remove(self.root,snapshot,draft,0,'yue','drama3',str(self.retry),True)
   self.assertTrue(self.retry.exists())
  complete=dict(self.listed(self.retry),takes=[dict(index=1,language='yue',engine='drama3',audio=str(self.retry),versionStatus='complete')])
  with self.assertRaisesRegex(ValueError,'current export or a saved choice'):remove(self.root,complete,{},0,'yue','drama3',str(self.retry),True)

 def test_only_a_listed_wav_inside_this_project_can_be_removed(self):
  outside=self.root.parent/'neighbour.wav';outside.write_bytes(b'other job')
  for snapshot,path,message in ((self.listed(),'nothing.wav','not listed'),
    (self.listed(self.retry),str(self.root/'absent.wav'),'not listed'),
    (self.listed(self.retry),str(self.root/'review.json'),'not listed'),
    (self.listed(outside),str(outside),'does not belong'),
    (self.listed(),str(self.retry),'not listed')):
   with self.assertRaisesRegex(ValueError,message):remove(self.root,snapshot,{},0,'yue','drama3',path,True)
  self.assertTrue(self.retry.exists());self.assertTrue(outside.exists())

 def test_removal_needs_confirmation_and_a_known_language(self):
  with self.assertRaisesRegex(ValueError,'Confirm'):remove(self.root,self.listed(self.retry),{},0,'yue','drama3',str(self.retry),False)
  with self.assertRaisesRegex(ValueError,'Unknown dubbing language'):remove(self.root,self.listed(self.retry),{},0,'fr','drama3',str(self.retry),True)
  self.assertTrue(self.retry.exists())

if __name__=='__main__':unittest.main()
