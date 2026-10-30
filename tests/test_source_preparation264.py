"""Cloud readiness, progress, cancellation and immutable source fixtures."""
import hashlib,json,os,sys,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'Resources')]
import source_preparation as prep
from atomic_files import write_json

class PreparationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.source=self.root/'CloudStorage/GoogleDrive/movie.mkv';self.source.parent.mkdir(parents=True);self.source.write_bytes(b'frame'*400000)
 def test_three_cloud_providers_and_local_path(self):
  for p in ['/fixture/Library/CloudStorage/GoogleDrive/film.mkv','/fixture/Library/CloudStorage/OneDrive/film.mkv','/fixture/Library/Mobile Documents/com~apple~CloudDocs/film.mkv']:
   self.assertTrue(prep.cloud(p))
  self.assertFalse(prep.cloud('/Movies/film.mkv'))
 def test_full_read_has_bytes_hash_progress_no_media_copy_and_reuses_receipt(self):
  before=prep.identity(self.source);sha=hashlib.sha256(self.source.read_bytes()).hexdigest();ctx=prep.Preparation(self.root/'app',self.source);ctx.ensure_local()
  status=json.loads((ctx.folder/'status.json').read_text());self.assertEqual(status['bytesRead'],before['bytes']);self.assertEqual(before,prep.identity(self.source));self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(),sha)
  receipt=next((self.root/'app/cache/source-readiness').glob('*.json'));self.assertEqual(json.loads(receipt.read_text())['sha256'],sha)
  self.assertFalse(list((self.root/'app').rglob('*.mkv')))
  other=prep.Preparation(self.root/'app',self.source)
  with patch.object(prep.subprocess,'Popen',side_effect=AssertionError('Completed source must not be read again')):other.ensure_local()
 def test_no_total_hydration_deadline(self):
  ctx=prep.Preparation(self.root/'app',self.source)
  def capture(args,timeout=None,reading=False):
   self.assertIsNone(timeout);self.assertTrue(reading);request=json.loads(Path(args[-1]).read_text());prep.read_source(request);return b''
  with patch.object(ctx,'capture',side_effect=capture):ctx.ensure_local()
 def test_concurrent_preparations_share_one_complete_cloud_read(self):
  from concurrent.futures import ThreadPoolExecutor
  calls=[]
  def capture(ctx,args,timeout=None,reading=False):
   calls.append(1);time.sleep(.1);prep.read_source(json.loads(Path(args[-1]).read_text()));return b''
  with patch.object(prep.Preparation,'capture',capture):
   contexts=[prep.Preparation(self.root/'app',self.source) for _ in range(2)]
   with ThreadPoolExecutor(2) as pool:list(pool.map(lambda c:c.ensure_local(),contexts))
  self.assertEqual(len(calls),1)
 def test_delayed_reader_progress_is_visible(self):
  ctx=prep.Preparation(self.root/'app',self.source);progress=ctx.folder/'read-progress.json'
  code='import time,json,pathlib; time.sleep(.2); pathlib.Path('+repr(str(progress))+').write_text(json.dumps(dict(bytesRead=100)));time.sleep(.4)'
  ctx.capture([sys.executable,'-c',code],reading=True);self.assertEqual(ctx.state['bytesRead'],100)
 def test_cancel_kills_only_owned_blocked_reader_and_keeps_source(self):
  ctx=prep.Preparation(self.root/'app',self.source);before=prep.identity(self.source);pidfile=ctx.folder/'pid'
  code='import os,time,pathlib;pathlib.Path('+repr(str(pidfile))+').write_text(str(os.getpid()));time.sleep(30)'
  timer=threading.Timer(.4,lambda:(ctx.folder/'cancel').write_text('cancel'));timer.start();self.addCleanup(timer.cancel);start=time.monotonic()
  with self.assertRaises(prep.SourcePreparationCancelled):ctx.capture([sys.executable,'-c',code],reading=True)
  self.assertLess(time.monotonic()-start,3);self.assertEqual(before,prep.identity(self.source))
  with self.assertRaises(ProcessLookupError):os.kill(int(pidfile.read_text()),0)
 def test_early_cancel_before_backend_start_is_observed(self):
  folder=self.root/'app/source-preparation/future';folder.mkdir(parents=True);(folder/'cancel').touch();ctx=prep.Preparation(self.root/'app',self.source,'future')
  with self.assertRaises(prep.SourcePreparationCancelled):ctx.ensure_local()
 def test_operation_cannot_be_reused_or_escape_directory(self):
  prep.Preparation(self.root/'app',self.source,'once')
  with self.assertRaises(ValueError):prep.Preparation(self.root/'app',self.source,'once')
  with self.assertRaises(ValueError):prep.Preparation(self.root/'app',self.source,'../escape')
 def test_incomplete_eof_has_no_completion_receipt(self):
  expected=prep.identity(self.source);expected['bytes']+=100
  request=dict(source=str(self.source),identity=expected,progress=str(self.root/'progress.json'),result=str(self.root/'result.json'))
  with patch.object(prep,'identity',return_value=expected):
   with self.assertRaisesRegex(RuntimeError,'incomplete'):prep.read_source(request)
  self.assertFalse((self.root/'result.json').exists())
 def test_cancelled_native_preparation_does_not_start_next_video(self):
  from types import SimpleNamespace
  sys.path.insert(0,str(R/'windows'));import native_queue
  root=self.root/'native';root.mkdir();calls=[]
  rows=[dict(id='a',status='waiting'),dict(id='b',status='waiting')]
  def dispatch(op,p):calls.append((op,p));raise prep.SourcePreparationCancelled(prep.CANCELLED)
  app=SimpleNamespace(root=root,store=SimpleNamespace(queue=rows,save=lambda:None),dispatch=dispatch)
  write_json(root/'studio/queue-session.json',dict(enabled=True,epoch=1,attempted=[],errors=[]))
  self.assertIsNone(native_queue.dispatch(app,'queue-next',dict(epoch=1)))
  self.assertEqual(calls,[('source-language',dict(id='a'))]);self.assertNotIn('queueNotice',rows[0]);self.assertFalse(json.loads((root/'studio/queue-session.json').read_text())['enabled'])
 def test_metadata_error_is_not_reported_as_an_incomplete_download(self):
  import source_language,subprocess
  with patch.object(prep.Preparation,'ensure_local'),patch.object(prep.Preparation,'capture',side_effect=subprocess.CalledProcessError(1,['ffprobe'])):
   with self.assertRaisesRegex(RuntimeError,'source video could not be read completely'):
    source_language.preflight(self.root/'app',self.source,dict(ffprobe='ffprobe'),dict(selectedEngines=['drama3']))
 def test_local_file_needs_no_full_hydration_read(self):
  local=self.root/'local.mkv';local.write_bytes(b'local');ctx=prep.Preparation(self.root/'app',local)
  with patch.object(ctx,'capture',side_effect=AssertionError('Local source is not a cloud download')):ctx.ensure_local()

if __name__=='__main__':unittest.main()
