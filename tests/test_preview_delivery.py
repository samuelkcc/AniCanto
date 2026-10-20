import json,sys,tempfile,unittest
from pathlib import Path
sys.path[:0]=[str(Path(__file__).parents[1]/'Resources'),str(Path(__file__).parents[1]/'windows')]
import preview_delivery as preview,output_delivery
from desktop_state import Store

class PreviewDeliveryTests(unittest.TestCase):
 def test_only_automatic_normal_jobs_get_labelled_preview_policy(self):
  coverage=dict(status='missing-dialogue',tracks=[])
  self.assertTrue(preview.needed(dict(productionMode='normal'),coverage,{},[]))
  self.assertFalse(preview.needed(dict(productionMode='fast'),coverage,{},[]))
  self.assertFalse(preview.needed(dict(productionMode='normal',editorRender=True),coverage,{},[]))
  self.assertFalse(preview.needed(dict(productionMode='normal',autoPreviewIncomplete=False),coverage,{},[]))
 def test_complete_dubbing_stays_formal_despite_quality_warnings(self):
  coverage=dict(status='complete',tracks=[dict(rows=[dict(index=1,available=True)])])
  with tempfile.TemporaryDirectory() as d:
   folder=Path(d);(folder/'normal-checks.json').write_text(json.dumps(dict(unresolved=[1])))
   self.assertFalse(preview.needed(dict(productionMode='normal'),coverage,dict(qualityWarning=True),[dict(folder=folder)]))
 def test_delivery_evidence_exposes_missing_times_without_claiming_certification(self):
  result=preview.details(dict(tracks=[dict(engine='drama3',language='en',rows=[dict(index=7,start=12.,end=13.,reason='timing-overrun',available=False),dict(index=8,start=13.,end=14.,reason='audio-present',available=True)])]))
  self.assertEqual(result['missingDialogue'],1);self.assertEqual(result['missing'][0]['start'],12.);self.assertFalse(result['qualityCertified'])
 def test_preview_event_remains_distinct_from_success_and_later_success_clears_label(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);app=Store(root);movie=root/'video.mp4';movie.write_bytes(b'movie')
   row=dict(id='p',video='source.mkv',status='running',progress=0);app.queue=[row]
   app.event(row,dict(stage='完成',output=str(movie),previewOutput=str(movie),deliveryKind='preview',artifactRole='labelled-preview',missingDialogue=2,partial=True))
   app.finish(row,0)
   self.assertEqual(row['status'],'attention');self.assertEqual(row['missingDialogue'],2)
   shown=output_delivery.presentation(root,row);self.assertEqual(shown['deliveryState'],'preview-exported')
   row['partial']=False;app.event(row,dict(stage='完成',output=str(movie),deliveryKind='complete',artifactRole='published'))
   self.assertNotIn('previewOutput',row);self.assertNotIn('missingDialogue',row)

 def test_old_mac_missing_event_metadata_is_recovered_only_from_matching_report(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);job=root/'jobs'/'episode';job.mkdir(parents=True)
   movie=root/'movie.mp4';movie.write_bytes(b'movie')
   report=dict(deliveryKind='preview',exportedOutput=str(movie),previewDelivery=dict(missingDialogue=16,incompleteDialogue=20))
   (job/'report.json').write_text(json.dumps(report))
   row=dict(status='attention',review=str(job/'review.json'),output=str(movie));(job/'review.json').write_text('{}')
   shown=output_delivery.presentation(root,row)
   self.assertEqual(shown['deliveryKind'],'preview');self.assertEqual(shown['incompleteDialogue'],20)
   self.assertEqual(shown['deliveryState'],'preview-exported');self.assertNotIn('deliveryKind',row)
   other=output_delivery.presentation(root,dict(row,output=str(root/'other.mp4')))
   self.assertNotIn('deliveryKind',other)
   self.assertEqual(output_delivery.presentation(root,dict(row,deliveryKind='complete'))['deliveryKind'],'complete')

 def test_pending_language_checks_are_counted_even_when_audio_exists(self):
  with tempfile.TemporaryDirectory() as d:
   folder=Path(d);(folder/'normal-checks.json').write_text(json.dumps(dict(unresolved=[4])))
   result=preview.details(dict(tracks=[]),[dict(engine='drama3',language='yue',folder=folder)])
   self.assertEqual(result['missingDialogue'],0);self.assertEqual(result['incompleteDialogue'],1)
   self.assertEqual(result['unresolvedChecks'][0]['index'],4)
