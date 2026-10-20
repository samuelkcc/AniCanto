import sys,json,tempfile,unittest,wave,array,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import dialogue_delivery

class DeliveryAuditTests(unittest.TestCase):
 def test_caption_and_script_cannot_hide_missing_reference_or_missing_file(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   def write(name,data):(root/name).write_text(json.dumps(data))
   cues=[dict(start=i,end=i+1,text='日本語',cantonese='有廣東話稿。',subtitleHint='有中文字幕',speakerId='role') for i in range(5)]
   cues[2]['enabled']=False;cues[3]['cantonese']=''
   write('review.json',dict(config={},cues=cues));write('segment-issues.json',[dict(index=1,kind='reference')])
   write('timing.json',[dict(index=1,skipped=True,renderedSeconds=0),dict(index=2,renderedSeconds=1,renderedAudio=str(root/'missing.wav')),dict(index=5,skipped=True,renderedSeconds=0)])
   path=root/'donor.wav'
   with wave.open(str(path),'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(array.array('h',(round(3000*math.sin(i*.1)) for i in range(24000))).tobytes())
   track=dict(engine='cosyvoice3',language='yue',folder=root,report=dict(audioFallbacks=[dict(index=5,sourceLanguage='yue',audio=str(path))]))
   r=dialogue_delivery.audit([track]);self.assertEqual(r['status'],'missing-dialogue');t=r['tracks'][0]
   self.assertEqual((t['required'],t['available'],t['missing']),(4,1,3));self.assertEqual(t['causes']['reference-blocked'],1);self.assertEqual(t['causes']['missing-script'],1)
   self.assertIn('缺聲 3',dialogue_delivery.summary(r));self.assertIn('香港廣東話',dialogue_delivery.summary(r));self.assertNotIn('yue ·',dialogue_delivery.summary(r))
   missing=t['rows'][0];self.assertEqual(missing['issueKinds'],['reference']);self.assertIn('generation',missing['logs'])
 def test_wrong_language_donor_does_not_complete_missing_cantonese(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'review.json').write_text(json.dumps(dict(config={},cues=[dict(start=0,end=1,text='日本語',cantonese='出發啦。')])))
   r=dialogue_delivery.audit([dict(engine='gpt-sovits',language='yue',folder=p,report=dict(audioFallbacks=[dict(index=1,sourceLanguage='ja')]))]);self.assertEqual(r['tracks'][0]['available'],0)

 def test_preflight_failure_explains_a_missing_row_without_segment_log(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'review.json').write_text(json.dumps(dict(config={},cues=[dict(start=0,end=1,cantonese='出發啦。')])))
   result=dialogue_delivery.audit([dict(engine='voxcpm2',language='yue',folder=p,report=dict(failureReason='角色參考未通過檢查'))])
   row=result['tracks'][0]['rows'][0];self.assertEqual(row['reason'],'reference-blocked');self.assertEqual(row['messages'],['角色參考未通過檢查'])

 def test_zero_filled_recording_and_deleted_donor_are_not_delivered(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);path=p/'silent.wav'
   with wave.open(str(path),'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(bytes(48000))
   (p/'review.json').write_text(json.dumps(dict(config={},cues=[dict(start=0,end=1,text='日本語',cantonese='出發啦。')])))
   (p/'timing.json').write_text(json.dumps([dict(index=1,renderedSeconds=1,renderedAudio=str(path))]))
   result=dialogue_delivery.audit([dict(engine='gpt-sovits',language='yue',folder=p,report=dict(audioFallbacks=[dict(index=1,sourceLanguage='yue',audio=str(p/'deleted.wav'))]))])
   self.assertEqual(result['tracks'][0]['missing'],1)

class VersionRepairTests(unittest.TestCase):
 def test_failed_first_export_keeps_frozen_destination_without_previous_movie(self):
  import multitrack
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);job=root/'versions/one';job.mkdir(parents=True);submissions=root/'submissions';submissions.mkdir();exports=root/'exports';exports.mkdir()
   source=submissions/'one.json';source.write_text(json.dumps(dict(id='one',settings=dict(exportFolder=str(exports)))))
   (job/'version.json').write_text(json.dumps(dict(id='one',status='failed',submission=str(source))))
   cfg={};multitrack.repair_version_export(cfg,job,dict(repairVersion=True));self.assertEqual(cfg['exportFolder'],str(exports))

 def test_editor_wrapper_cannot_hide_missing_audio_behind_successful_ai_summary(self):
  self.assertTrue(dialogue_delivery.incomplete(dict(aiAutoFix=dict(unresolved=0),dialogueDelivery=dict(status='missing-dialogue',tracks=[dict(missing=12)]))))
  self.assertFalse(dialogue_delivery.incomplete(dict(aiAutoFix=dict(unresolved=0),dialogueDelivery=dict(status='audio-present',tracks=[dict(missing=0)]))))
 def test_repaired_output_updates_version_and_preserves_original_destination(self):
  from types import SimpleNamespace
  from unittest.mock import Mock
  import multitrack
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);job=root/'versions/one';job.mkdir(parents=True);exports=root/'exports';exports.mkdir()
   previous=exports/'movie.mp4';previous.write_bytes(b'old movie')
   state=dict(id='one',created='original timestamp',output=str(previous),status='partial');(job/'version.json').write_text(json.dumps(state))
   cfg={};saved=multitrack.repair_version_export(cfg,job,dict(repairVersion=True));self.assertEqual(cfg['exportFolder'],str(exports))
   candidate=job/'movie.mp4';candidate.write_bytes(b'repaired movie');destination=multitrack.export_copy(candidate,cfg)
   multitrack.finish_repair_version(SimpleNamespace(atomic_json=lambda p,r:p.write_text(json.dumps(r))),job,saved,destination,True)
   updated=json.loads((job/'version.json').read_text());self.assertEqual(updated['output'],str(destination));self.assertEqual(updated['created'],'original timestamp');self.assertEqual(previous.read_bytes(),b'old movie');self.assertNotEqual(destination,previous)
 def test_import_job_cannot_masquerade_as_saved_version(self):
  import multitrack
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):multitrack.repair_version_export({},Path(d),dict(repairVersion=True))

 def test_saved_edit_snapshot_is_retained_for_linked_cut_repair(self):
  import multitrack
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);job=root/'versions/one';job.mkdir(parents=True);submissions=root/'submissions';submissions.mkdir()
   draft=dict(id='one',clips=[dict(start=2,end=4,enabled=True)])
   path=submissions/'one.json';path.write_text(json.dumps(draft));(job/'version.json').write_text(json.dumps(dict(id='one',submission=str(path))))
   state=multitrack.repair_version_export({},job,dict(repairVersion=True));self.assertEqual(state['_repairDraft'],draft)


class TimingCauseTests(unittest.TestCase):
 def test_retained_overlong_take_is_explicitly_not_delivered(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);audio=root/'retained.wav';audio.write_bytes(b'retained candidate, not evidence of delivery')
   (root/'review.json').write_text(json.dumps(dict(config={},cues=[dict(start=0,end=1,text='source',cantonese='送貨呀')])) )
   (root/'timing.json').write_text(json.dumps([dict(index=1,skipped=True,renderedSeconds=0,audio=str(audio),seconds=1.67,slot=.84,failureKind='timing-overrun',error='Natural recording exceeds the available interval.')]))
   result=dialogue_delivery.audit([dict(engine='drama3',language='yue',folder=root,report={})]);track=result['tracks'][0];row=track['rows'][0]
   self.assertEqual(track['missing'],1);self.assertEqual(row['reason'],'timing-overrun');self.assertFalse(row['available']);self.assertEqual(row['retainedAudio'],str(audio));self.assertEqual(row['messages'],['Natural recording exceeds the available interval.']);self.assertIn('時長超出 1',dialogue_delivery.summary(result))
