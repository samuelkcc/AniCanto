"""Regression evidence for retained takes, partial checkpoints and owned timeouts."""
import array,hashlib,json,os,subprocess,sys,tempfile,unittest,wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows'),str(ROOT/'studio')]
import secondary_speech as speech,normal_mode,normal_policy
from atomic_files import write_json

def audio(p,level=4000):
 with wave.open(str(p),'wb') as f:f.setparams((1,2,16000,0,'NONE','not compressed'));f.writeframes(array.array('h',[level,-level]*800).tobytes())
 return p

class CheckpointTests(unittest.TestCase):
 def selection(self,root):return dict(backend='cpu',id='whisper-large-v3',path=str(root),revision='pinned',runtime='runtime')
 def fixture(self,root,n=3):
  items=[]
  for i in range(n):
   folder=root/str(i);folder.mkdir();items.append((folder,audio(folder/'audio.wav',4000+i)))
  return items
 def test_saved_results_survive_mid_batch_timeout_and_resume_only_missing_audio(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);items=self.fixture(root);calls=[]
   def runner(cfg,req,python,emit):
    r=json.loads(Path(req).read_text());calls.append(r)
    self.assertNotIn('expected',json.dumps(r));self.assertNotIn('prompt',json.dumps(r))
    # Simulate two completed items and a timeout during model startup. A later
    # invocation must reuse those two, rather than lose the whole batch.
    use=r['items'][:2] if len(calls)==1 else r['items']
    speech.process_request(dict(r,items=use),lambda p:dict(heard='一齊出發啦',language='zh'),emit)
    return dict(attempted={i['key'] for i in use},failure=dict(reason='timeout',key=None) if len(calls)==1 else None)
   w=SimpleNamespace(atomic_json=write_json,emit=Mock())
   with patch.object(speech,'backend',return_value=self.selection(root)),patch.object(speech,'run_batch',side_effect=runner):
    first=speech.transcribe_batch(w,dict(storage=d),items,True);self.assertEqual(sum(x is not None for x in first),2)
    second=speech.transcribe_batch(w,dict(storage=d),items,True);self.assertTrue(all(second));self.assertEqual(len(calls[1]['items']),1)
    # Identical audio in another recovery stage is reused without another model.
    stage=root/'other-stage';stage.mkdir();third=speech.transcribe_batch(w,dict(storage=d),[(stage,items[0][1])],True)
    self.assertTrue(third[0]);self.assertEqual(len(calls),2)
 def test_failed_recognizer_is_not_cached_as_missing_speech_and_later_item_finishes(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);rows=[dict(key=str(i),audio=str(i),cache=str(root/f'{i}.json')) for i in range(3)]
   def infer(p):
    if p=='1':raise RuntimeError('recognizer unavailable')
    return dict(heard='原本嘅聲音',language='zh')
   events=[];speech.process_request(dict(items=rows,backend='cpu',modelID='test',modelRevision='pin',language=None),infer,events.append)
   self.assertTrue((root/'0.json').exists());self.assertFalse((root/'1.json').exists());self.assertTrue((root/'2.json').exists())
   self.assertEqual([e['event'] for e in events].count('failed'),1)
 def test_timeout_stops_only_owned_child_and_retains_checkpoint(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);script=root/'fake-python';request=root/'request.json';request.write_text('{}')
   import shlex
   code='import json,time,sys,pathlib\np=pathlib.Path(sys.argv[-1]).parent\n(p/"saved.json").write_text("saved")\nprint(json.dumps({"event":"completed","key":"one"}),flush=True)\nprint(json.dumps({"event":"started","key":"two"}),flush=True)\ntime.sleep(20)\n'
   script.write_text('#!/bin/sh\nexec '+shlex.quote(sys.executable)+' -c '+shlex.quote(code)+' "$@"\n');script.chmod(0o755)
   other=subprocess.Popen([sys.executable,'-c','import time;time.sleep(20)'])
   try:
    outcome=speech.run_batch(dict(independentAsrItemTimeout=.4,independentAsrBatchTimeout=3),request,script,Mock())
    self.assertEqual(outcome['failure']['reason'],'timeout');self.assertEqual(outcome['failure']['key'],'two');self.assertTrue((root/'saved.json').exists());self.assertIsNone(other.poll())
   finally:other.terminate();other.wait()
 def test_backend_is_offline_and_explicit_mlx_does_not_silently_claim_cpu(self):
  with patch.object(speech.sys,'platform','darwin'),patch.object(speech.platform,'machine',return_value='arm64'),patch('model_catalog.resolve',side_effect=ValueError('not installed')):
   with self.assertRaisesRegex(ValueError,'Download'):speech.backend(dict(storage='unused',independentAsrBackend='mlx'))
 def test_resume_key_changes_when_audio_or_recognizer_changes(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);items=self.fixture(root,1);calls=[]
   def run(cfg,req,python,emit):
    r=json.loads(Path(req).read_text());calls.append(r);speech.process_request(r,lambda p:dict(heard='出發',language='zh'),emit);return dict(attempted=set(),failure=None)
   cfg=dict(storage=d);selected=self.selection(root)
   with patch.object(speech,'backend',side_effect=lambda cfg:dict(selected)),patch.object(speech,'run_batch',side_effect=run):
    w=SimpleNamespace(atomic_json=write_json)
    speech.transcribe_batch(w,cfg,items,True);speech.transcribe_batch(w,cfg,items,True);self.assertEqual(len(calls),1)
    audio(items[0][1],6000);speech.transcribe_batch(w,cfg,items,True);self.assertEqual(len(calls),2)
    selected['revision']='new-pin';speech.transcribe_batch(w,cfg,items,True);self.assertEqual(len(calls),3)

class RetainFirstTests(unittest.TestCase):
 def test_default_never_rejects_audible_first_take_for_language_or_omission(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);path=audio(root/'first.wav');cue=dict(start=0,end=1,cantonese='我哋一齊出發啦',speakerId='own');before=hashlib.sha256(path.read_bytes()).hexdigest()
   with patch.object(normal_mode,'inspect',side_effect=AssertionError('must not start recognition')),patch('dubbing.gsv_audio',side_effect=AssertionError('must not regenerate')):
    result=normal_mode.repair_paths(dict(productionMode='normal'),root,[cue],[path],Mock(),Mock())
   self.assertEqual(result,[path]);self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),before)
   saved=json.loads((root/'normal-checks.json').read_text());self.assertEqual(saved['languageCheckStatus'],'deferred-to-human-review');self.assertFalse(saved['qualityCertified'])
 def test_only_silent_recording_is_retried_and_success_resumes_without_regeneration(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);good=audio(root/'good.wav');silent=audio(root/'silent.wav',0);fixed=audio(root/'fixed.wav');cues=[dict(start=i,end=i+1,cantonese='出發啦',speakerId=str(i)) for i in range(2)]
   with patch('dubbing.gsv_audio',return_value=[fixed]) as generation:
    cfg=dict(productionMode='normal');one=normal_mode.repair_paths(cfg,root,cues,[good,silent],Mock(),Mock());two=normal_mode.repair_paths(cfg,root,cues,[good,silent],Mock(),Mock())
    self.assertEqual(one,[good,fixed]);self.assertEqual(two,one);generation.assert_called_once();self.assertEqual(generation.call_args.args[2][0]['reviewIndex'],1)
 def test_finish_marker_is_token_scoped(self):
  with tempfile.TemporaryDirectory() as d:
   write_json(Path(d)/'finish-with-current.json',dict(token='old'));cfg=dict(_trackControl=dict(folder=d,token='new'))
   self.assertFalse(normal_policy.finish_requested(cfg));write_json(Path(d)/'finish-with-current.json',dict(token='new'));self.assertTrue(normal_policy.finish_requested(cfg))

class FinishCurrentTests(unittest.TestCase):
 def test_backend_finish_marks_only_the_active_track_and_rejects_escape(self):
  from backend import Studio
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);job=root/'jobs/test';track=job/'tracks/voice';track.mkdir(parents=True);review=job/'review.json';write_json(review,{})
   control=dict(state='running',token='current',folder=str(track));write_json(job/'track-progress.json',dict(tracks=[control]))
   host=SimpleNamespace(row=lambda ident:dict(status='running'),review_path=lambda row:review)
   result=Studio.dispatch(host,'finish-current',dict(id='test'));self.assertEqual(result['tracks'],1)
   self.assertTrue(normal_policy.finish_requested(dict(_trackControl=control)))
   control['folder']=str(root/'outside');write_json(job/'track-progress.json',dict(tracks=[control]))
   with self.assertRaisesRegex(ValueError,'Invalid active'):Studio.dispatch(host,'finish-current',dict(id='test'))
 def test_default_retained_mix_preserves_audible_bytes_without_asr_or_retake(self):
  import shutil,math
  if not shutil.which('ffmpeg'):self.skipTest('FFmpeg required')
  import fast_mode
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);first=audio(root/'first.wav');cue=dict(start=0,end=1,speechStart=0,speechEnd=1,cantonese='出發啦',enabled=True)
   before=first.read_bytes();cfg=dict(productionMode='normal',duration=2,speechRatePolicy='natural',ttsBackend='drama3',ffmpeg=shutil.which('ffmpeg'))
   def run(args):return subprocess.check_output([str(x) for x in args],stderr=subprocess.PIPE)
   with patch('dubbing.gsv_audio',return_value=[first]) as generation,patch.object(normal_mode,'inspect',side_effect=AssertionError('No automatic ASR')),patch('normal_recovery.recover',side_effect=AssertionError('No AI director')),patch('natural_delivery.repair',side_effect=AssertionError('No rewrite')):
    output,notes=fast_mode.synthesize(cfg,root,[cue],run,Mock());self.assertTrue(output.is_file());generation.assert_called_once()
   self.assertEqual(before,first.read_bytes())
   with wave.open(str(output)) as f:self.assertGreater(f.getnframes(),0)

class DurationExceptionTests(unittest.TestCase):
 def test_default_shortens_only_overlong_line_without_language_repair_and_resumes(self):
  import copy,shutil
  if not shutil.which('ffmpeg'):self.skipTest('FFmpeg required')
  from test_natural_delivery import audio as timed_audio
  import fast_mode,worker
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);long=timed_audio(job/'long.wav',1.5);short=timed_audio(job/'short.wav',.4);fitting=timed_audio(job/'fitting.wav',.4)
   original=[dict(start=0,end=.7,japanese='来て',cantonese='I would like you to come here.',speakerId='same'),dict(start=.7,end=1.5,japanese='はい',cantonese='Yes.',speakerId='other')]
   cfg=dict(duration=1.5,speechRatePolicy='natural',preferFirstAudibleTake=True,productionMode='normal',targetLanguage='en',ttsBackend='drama3',model='m',port=1,ffmpeg=shutil.which('ffmpeg'))
   def run(args):return subprocess.check_output([str(x) for x in args],stderr=subprocess.PIPE)
   def generate(c,folder,rows,*args):
    if len(rows)==2:return [long,fitting]
    self.assertEqual(rows[0]['speakerId'],'same');return [short]
   with patch('dubbing.gsv_audio',side_effect=generate) as tts,patch.object(worker,'ollama_chat',return_value='{"0":"Come here."}'),patch('semantic_review.audit',return_value={'0':dict(faithful=True)}),patch.object(normal_mode,'inspect',side_effect=AssertionError('No language reinspection')),patch('normal_recovery.recover',side_effect=AssertionError('No director')):
    for _ in range(2):
     cues=copy.deepcopy(original);output,_=fast_mode.synthesize(cfg,job,cues,run,Mock())
     self.assertTrue(output.is_file());self.assertEqual(cues[0]['cantonese'],'Come here.');self.assertEqual(cues[1],original[1])
    self.assertEqual(tts.call_count,3,'Resume must reuse the shortened recording')
   self.assertTrue(long.is_file());self.assertAlmostEqual(1.5,__import__('natural_delivery').seconds(long,cfg,run))
 def test_shorter_but_still_overlong_candidate_never_replaces_original(self):
  from test_natural_delivery import audio as timed_audio
  import natural_delivery,worker
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);old=timed_audio(job/'original.wav',2);bad=timed_audio(job/'still-long.wav',1.5)
   cue=dict(start=0,end=1,japanese='来て',cantonese='I would like you to come here.')
   cfg=dict(duration=1,automaticDurationRewrite=True,preferFirstAudibleTake=False,_durationFitRequired=True,productionMode='normal',targetLanguage='en',ttsBackend='drama3',model='m',port=1)
   with patch('dubbing.gsv_audio',return_value=[bad]) as tts,patch.object(worker,'ollama_chat',return_value='{"0":"Come here."}'),patch('semantic_review.audit',return_value={'0':dict(faithful=True)}),patch.object(normal_mode,'inspect',side_effect=AssertionError('No ASR')):
    self.assertEqual(natural_delivery.repair(cfg,job,[cue],[old],Mock(),Mock()),[old]);self.assertLessEqual(tts.call_count,2)
   self.assertEqual(cue['cantonese'],'I would like you to come here.')
   audit=json.loads((job/'natural-repair.json').read_text())['candidates'];self.assertTrue(audit);self.assertTrue(all(not r['adopted'] and r['reason']=='candidate-still-overlong' for r in audit))

if __name__=='__main__':unittest.main()
