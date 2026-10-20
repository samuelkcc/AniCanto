"""A track-workfile event cannot publish an episode or change its destination."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows'),str(ROOT/'studio')]
import output_delivery as delivery
from desktop_state import Store
from backend import Studio
import multitrack

class OutputDeliveryTests(unittest.TestCase):
 def test_child_artifacts_keep_evidence_without_overwriting_parent_output(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);store=Store(root);final=root/'exports/final.mp4';child=root/'jobs/id/tracks/yue/take.mp4'
   row=dict(output=str(final),review=str(root/'jobs/id/review.json'),job=str(root/'jobs/id'))
   event=dict(stage='完成',output=str(child),review=str(child.parent/'review.json'),job=str(child.parent),subtitles=str(child.parent/'take.srt'))
   before=copy.deepcopy(event);store.event(row,delivery.track_event(event))
   self.assertEqual(row['output'],str(final));self.assertEqual(row['review'],str(root/'jobs/id/review.json'));self.assertEqual(row['workingOutput'],str(child));self.assertNotIn('outputThisAttempt',row);self.assertEqual(event,before)
   # A worker from an older installed build has no explicit role tag.
   store.event(row,event);self.assertEqual(row['output'],str(final));self.assertNotIn('outputThisAttempt',row)
   store.event(row,dict(stage='完成',output=str(final),artifactRole='published'))
   self.assertEqual(row['outputThisAttempt'],str(final))
 def test_legacy_track_path_is_not_presented_as_a_delivered_output(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);child=root/'jobs/id/tracks/en/take.mp4';row=dict(status='attention',output=str(child),outputThisAttempt=str(child))
   before=copy.deepcopy(row);value=delivery.presentation(root,row)
   self.assertNotIn('output',value);self.assertNotIn('outputThisAttempt',value);self.assertEqual(value['workingOutput'],str(child));self.assertEqual(value['deliveryState'],'not-exported');self.assertEqual(row,before)
 def test_frozen_google_drive_style_destination_and_atomic_copy(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);folder=root/'Google Drive/My Drive/Video';folder.mkdir(parents=True)
   req=root/'requests/submitted.json';req.parent.mkdir();req.write_text(json.dumps(dict(exportFolder=str(folder))))
   source=root/'internal.mp4';source.write_bytes(b'isolated movie fixture')
   value=delivery.presentation(root,dict(request=str(req)),str(root/'different-current-setting'))
   self.assertEqual(value['requestedExportFolder'],str(folder))
   first=multitrack.export_copy(source,dict(exportFolder=value['requestedExportFolder']))
   second=multitrack.export_copy(source,dict(exportFolder=value['requestedExportFolder']))
   self.assertEqual(first.parent,folder);self.assertNotEqual(first,second);self.assertEqual(first.read_bytes(),source.read_bytes())
 def test_shared_state_hides_legacy_child_without_modifying_saved_queue(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);app=Studio(root,ROOT/'Resources',helper=root/'helper');child=root/'jobs/id/tracks/yue/take.mp4'
   app.store.queue=[dict(id='one',video=str(root/'source.mkv'),status='attention',output=str(child))];app.store.selected='one';app.store.save()
   value=app.state()['queue'][0];self.assertNotIn('output',value);self.assertEqual(value['deliveryState'],'not-exported');self.assertEqual(app.store.queue[0]['output'],str(child))

if __name__=='__main__':unittest.main()
