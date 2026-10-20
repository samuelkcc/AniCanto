import json,os,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'windows'),str(ROOT/'Resources')]
import conversion_details as cd,diagnostics,model_maintenance
from desktop_state import write

class ConversionDetailsTests(unittest.TestCase):
 def test_frozen_configuration_actual_model_sampling_and_final_snapshot(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);request=root/'requests/one.json';write(request,dict(model='Windows-9B',drama3Model='native-model',apiKey='secret'))
   row=dict(id='one',video='E11.mp4',status='running',request=str(request));attempt=diagnostics.start(root,row,'batch',request)
   write(request,dict(model='changed after submission'))
   job=root/'jobs/one';write(job/'review.json',dict(config=dict(ttsBackend='drama3',drama3Model='native-model'),cues=[dict(start=1,end=2,cantonese='你好')]))
   write(job/'ocr-metrics.json',dict(mode='speech-guided',recognisedFrames=600,denseBaselineFrames=9000,totalSeconds=180))
   write(job/'report.json',dict(cues=1));write(job/'native-drama-server.json',dict(backend='cuda',device=0,credentials='secret'))
   write(job/'1.generation.json',dict(sampling=dict(temperature=.7,top_p=.7,top_k=30),modelVariant='native-model',backend='cuda'))
   row.update(job=str(job),status='complete',outputThisAttempt='movie.mp4');cd.finish(root,row);data=cd.build(root,row)
   self.assertEqual(data['submittedSettings']['model'],'Windows-9B');self.assertNotIn('secret',json.dumps(data));self.assertEqual(data['actualTracks'][0]['generationTraces'][0]['sampling']['top_p'],.7)
   self.assertEqual(data['ocr']['recognisedFrames'],600)
   (job/'review.json').unlink();self.assertEqual(cd.build(root,row)['sourceCues'],data['sourceCues'])
 def test_failed_new_attempt_does_not_claim_prior_success(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);job=root/'jobs/old';write(job/'report.json',dict(cues=999));os.utime(job/'report.json',(1,1))
   row=dict(id='new',video='x',job=str(job),attempt=dict(startedAt=time.time()))
   data=cd.build(root,row);self.assertIn('Earlier',data['resultsEvidence']);self.assertNotIn('result',data)
 def test_gain_evidence_is_saved_per_track_without_inventing_missing_measurements(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);job=root/'jobs/one';track=job/'yue';request=root/'requests/one.json'
   settings=dict(productionMode='normal',aiAutoFix=False,backgroundGain=.7,backgroundDucking='auto',separateBackground=True,mixOriginal=False)
   write(request,settings);row=dict(id='one',request=str(request),job=str(job),status='complete')
   write(job/'review.json',dict(config=settings,cues=[]))
   write(job/'report.json',dict(tracks=[dict(engine='gpt-sovits-v2',language='yue',report=str(track/'report.json')),dict(engine='drama3',language='en',report=str(job/'en/report.json'))]))
   write(track/'speech-levels.json',[dict(index=1,gainDB=12,outputActiveRMSDB=-19)])
   write(track/'speech-mix-level.json',dict(timelineGain=.5,boostedLines=1))
   write(track/'mix-audibility.json',dict(mode='auto',rows=[dict(index=1,voice=dict(activeRMSDB=-25))]))
   data=cd.build(root,row)
   self.assertEqual(data['submittedSettings'],settings);self.assertEqual(data['effectiveJobSettings'],settings)
   first,missing=data['actualTracks']
   self.assertEqual(first['speechLevels'][0]['gainDB'],12);self.assertEqual(first['speechMixLevel']['timelineGain'],.5)
   self.assertEqual(first['mixAudibility']['rows'][0]['voice']['activeRMSDB'],-25)
   self.assertEqual(missing['speechLevels'],[]);self.assertEqual(missing['speechMixLevel'],{});self.assertEqual(missing['mixAudibility'],{})
 def test_natural_speech_decisions_are_included_in_cross_computer_diagnostics(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);job=root/'jobs/one';track=job/'tracks/yue'
   write(job/'review.json',dict(config={},cues=[]))
   write(job/'report.json',dict(tracks=[dict(engine='drama3',language='yue',report=str(track/'report.json'))]))
   write(track/'natural-placement.json',dict(rate=1.,moved=2,maximumShiftSeconds=.5,unresolved=[3]))
   write(track/'natural-repair.json',dict(maximumRewritePasses=2,batchedEngineLoads=True))
   details=cd.build(root,dict(id='one',job=str(job),status='attention'))['actualTracks'][0]
   self.assertEqual(details['naturalPlacement']['unresolved'],[3]);self.assertEqual(details['naturalPlacement']['rate'],1.)
   self.assertTrue(details['naturalRepair']['batchedEngineLoads'])
 def test_log_capture_failure_never_prevents_conversion(self):
  with tempfile.TemporaryDirectory() as d,patch.object(cd,'start',side_effect=OSError('disk denied')):
   record=diagnostics.start(Path(d),dict(id='p',video='x'),'batch','missing.json')
   self.assertIn('conversionDetailsWarning',record)
 def test_external_request_is_not_read(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);outside=root.parent/'not-owned-secret.json'
   data=cd.build(root,dict(id='p',request=str(outside)))
   self.assertEqual(data['submittedSettings'],{})
 def test_retired_cleanup_is_owned_and_protects_paused_jobs(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);base=root/'models/retired';base.mkdir(parents=True);(base/'model').write_text('weights')
   row=dict(retired=True,files=[dict(path='model')])
   write(root/'studio/desktop-state.json',dict(queue=[dict(status='paused',drama3Model='retired')]))
   with patch.object(model_maintenance,'model',return_value=(row,base)):
    with self.assertRaisesRegex(ValueError,'paused job'):model_maintenance.remove_retired(root,'retired')
    write(root/'studio/desktop-state.json',dict(queue=[]));self.assertTrue(model_maintenance.remove_retired(root,'retired')['removed'])
   self.assertFalse((base/'model').exists())
if __name__=='__main__':unittest.main()
