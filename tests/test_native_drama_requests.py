"""Owned native request lifecycle; CPU speed is measured on Windows separately."""
import io,json,sys,tempfile,time,unittest,urllib.error
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
import numpy as np
import soundfile as sf
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import drama_gguf,drama3

class NativeRequests(unittest.TestCase):
 def model(self,folder):
  log=Path(folder)/'native-drama-server.log';log.write_text('runtime.load.phase loaded\n')
  return SimpleNamespace(log=SimpleNamespace(name=str(log)),variant='drama3-native-q2',backend='cpu',threads=8,port=1,process=Mock(poll=Mock(return_value=None)),close=Mock())
 def test_complete_request_emits_truthful_waiting_and_durable_completion(self):
  with tempfile.TemporaryDirectory() as folder:
   model=self.model(folder);emit=Mock()
   def request(*args,**kwargs):time.sleep(.3);return b'complete wave'
   with patch.object(drama_gguf,'wav_request',side_effect=request),patch.object(drama_gguf,'HEARTBEAT_SECONDS',.01):
    self.assertEqual(drama_gguf.monitored_request(model,dict(input='你好'),emit),b'complete wave')
   row=json.loads((Path(folder)/'native-drama-request.json').read_text())
   self.assertEqual(row['state'],'completed');self.assertGreaterEqual(row['elapsedSeconds'],.3)
   self.assertEqual(row['cpuThreads'],8);self.assertFalse(row['generatedProgressAvailable'])
   waiting=[c for c in emit.call_args_list if 'nativeRequest' in c.kwargs]
   self.assertGreaterEqual(len(waiting),2)
   self.assertTrue(all(c.kwargs['nativeRequest']['state']=='waiting' for c in waiting))
   self.assertTrue(all('Drama3-small' not in c.args[1] for c in emit.call_args_list))
   model.close.assert_not_called()
 def test_timeout_stops_owned_server_and_forbids_followup_submission(self):
  for error in (TimeoutError('timed out'),urllib.error.URLError(TimeoutError('timed out'))):
   with self.subTest(error=error),tempfile.TemporaryDirectory() as folder:
    model=self.model(folder)
    with patch.object(drama_gguf,'wav_request',side_effect=error) as request:
     with self.assertRaises(drama_gguf.NativeDramaUnavailable):drama_gguf.monitored_request(model,dict(input='你好'))
     with self.assertRaises(drama_gguf.NativeDramaUnavailable):drama_gguf.generate(model,{}, {})
    request.assert_called_once();model.close.assert_called_once();self.assertTrue(model.failed)
    self.assertEqual(json.loads((Path(folder)/'native-drama-request.json').read_text())['state'],'timed-out')
 def test_dead_server_stops_track_but_ordinary_http_rejection_remains_line_failure(self):
  for dead in (False,True):
   with self.subTest(dead=dead),tempfile.TemporaryDirectory() as folder:
    model=self.model(folder);model.process.poll.return_value=1 if dead else None
    with patch.object(drama_gguf,'wav_request',side_effect=OSError('native failure')):
     with self.assertRaises(drama_gguf.NativeDramaUnavailable if dead else OSError):drama_gguf.monitored_request(model,dict(input='你好'))
    self.assertEqual(model.close.call_count,int(dead))
    self.assertEqual(json.loads((Path(folder)/'native-drama-request.json').read_text())['state'],'server-exited' if dead else 'failed')
 def test_native_fatal_failure_is_saved_and_never_queues_remaining_track(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);cfg=dict(items=[dict(text='第一句',output=str(root/'first.wav')),dict(text='第二句',output=str(root/'second.wav'))])
   def generate(*args):
    cfg['_dramaLastGeneration']=dict(status='native-request-failed')
    raise drama_gguf.NativeDramaUnavailable('native-drama-timeout')
   with patch.object(drama3,'load'),patch.object(drama3,'generate_complete',side_effect=generate) as generated:
    with self.assertRaises(drama_gguf.NativeDramaUnavailable):drama3._synthesize(cfg,Mock())
   generated.assert_called_once();self.assertFalse((root/'first.wav').exists());self.assertFalse((root/'second.failure.json').exists())
   self.assertEqual(json.loads((root/'first.generation.json').read_text())['status'],'native-request-failed')
 def test_fatal_native_failure_updates_generation_trace(self):
  with tempfile.TemporaryDirectory() as folder:
   cfg=dict(targetLanguage='yue');model=self.model(folder)
   with patch.object(drama_gguf,'monitored_request',side_effect=drama_gguf.NativeDramaUnavailable('native-drama-timeout')):
    with self.assertRaises(drama_gguf.NativeDramaUnavailable):drama_gguf.generate(model,dict(text='你好',profile=dict(reference='clean.wav')),cfg)
   self.assertEqual(cfg['_dramaLastGeneration']['status'],'native-request-failed')
   self.assertIn('native-drama-timeout',cfg['_dramaLastGeneration']['error'])
