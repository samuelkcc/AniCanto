"""Build 278 rule: a quiet provider asks the user to keep waiting instead of failing the
job, and one answer keeps the bytes already read. A read with no interface to answer still
ends on its idle limit, so a real fault stays a fault."""
import hashlib,json,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'Resources')]
import source_preparation as prep
from atomic_files import write_json

class Asked(Exception):
 """Raised by the fixture once the loading panel has been asked."""

class SourceWait278(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name)/'app'
  self.source=self.root/'Google Drive/movie.mkv';self.source.parent.mkdir(parents=True)
  self.source.write_bytes(b'frame'*4000)
  self.operation='wait-operation'
  self.folder=self.root/'source-preparation'/self.operation;self.folder.mkdir(parents=True)
 def request(self,wait=True):
  request=dict(source=str(self.source),identity=prep.identity(self.source),
   progress=str(self.folder/'read-progress.json'),result=str(self.folder/'read-result.json'))
  if wait:request['wait']=str(self.folder/prep.WAIT_FILE)
  return request
 def progress(self,request):
  try:return json.loads(Path(request['progress']).read_text())
  except (OSError,ValueError):return {}
 def clocked(self):
  """The reader measures quiet time on its own clock, so the fixture moves that clock
  forward each time it waits. Real seconds never run in these tests."""
  elapsed=[0.0]
  return (lambda seconds:elapsed.__setitem__(0,elapsed[0]+seconds)),(lambda:elapsed[0])
 def quiet_stream(self,limit,open_after=None):
  """A provider that serves `limit` bytes and then answers with nothing until the test opens
  the gate. A reopen always continues at the offset the reader asked for."""
  served=[0]
  class Quiet:
   def __init__(inner):inner.file=Path(self.source).open('rb')
   def seek(inner,position):inner.file.seek(position)
   def close(inner):inner.file.close()
   def read(inner,count):
    if open_after is not None and open_after[0]:return inner.file.read(count)
    # The served count is shared by every reopen, so a stalled provider stays stalled.
    if served[0]>=limit:return b''
    block=inner.file.read(min(count,limit-served[0]));served[0]+=len(block);return block
  return Quiet
 # One: a quiet provider asks, names the real provider, and keeps the bytes already read.
 def test_a_quiet_provider_asks_the_user_instead_of_failing(self):
  request=self.request();asked=[]
  pause,clock=self.clocked()
  def wait(seconds):
   value=self.progress(request)
   if value.get('waitingForDecision'):asked.append(value);raise Asked()
   pause(seconds)
  with patch.object(prep,'WAIT_AFTER_IDLE',2),self.assertRaises(Asked):
   prep.read_source(request,opener=self.quiet_stream(16000),pause=wait,clock=clock)
  self.assertEqual(asked[0]['provider'],'google-drive',asked[0])
  self.assertGreaterEqual(asked[0]['idleSeconds'],2,asked[0])
  self.assertGreater(asked[0]['bytesRead'],0,'the reader keeps its file offset')
  self.assertFalse(Path(request['result']).exists(),'an unfinished read has no completion receipt')
 # Two: one "keep waiting" answer resumes the same read at the same offset.
 def test_one_keep_waiting_answer_finishes_the_read(self):
  request=self.request();asked=[];resume=[False]
  pause,clock=self.clocked()
  during=[]
  def wait(seconds):
   value=self.progress(request)
   if not value.get('waitingForDecision'):
    # The reader takes the allowance on its next quiet pass and shows it in the progress
    # file. The provider only delivers the rest of the movie after that point.
    if asked and value.get('waitSeconds'):during.append(value);resume[0]=True
    return pause(seconds)
   asked.append(value);prep.grant_wait(self.root,self.operation)
  with patch.object(prep,'WAIT_AFTER_IDLE',2):
   prep.read_source(request,opener=self.quiet_stream(16000,resume),pause=wait,clock=clock)
  receipt=json.loads(Path(request['result']).read_text())
  self.assertEqual(receipt['bytesRead'],self.source.stat().st_size)
  self.assertEqual(receipt['sha256'],hashlib.sha256(self.source.read_bytes()).hexdigest())
  self.assertEqual(len(asked),1,'a live grant must not ask again inside its own window')
  self.assertEqual(asked[0]['provider'],'google-drive')
  self.assertTrue(any(value.get('waitingForDecision') is False and value.get('waitSeconds',0)>0 for value in during),
   'the open allowance is shown to the loading panel: '+json.dumps(during))
 # Three: the allowance is a wall clock, and an expired one asks the user again.
 def test_the_allowance_expires_and_asks_again(self):
  path=self.folder/prep.WAIT_FILE
  self.assertEqual(prep.wait_grant_remaining(path),0.0,'no grant file means no allowance')
  receipt=prep.grant_wait(self.root,self.operation)
  self.assertGreater(receipt['waitGrantedUntil'],time.time())
  self.assertGreater(prep.wait_grant_remaining(path),0.0)
  self.assertLessEqual(prep.wait_grant_remaining(path),float(prep.WAIT_GRACE))
  self.assertEqual(json.loads(path.read_text())['seconds'],float(prep.WAIT_GRACE))
  write_json(path,dict(until=time.time()-1,granted=time.time()-2,seconds=float(prep.WAIT_GRACE)))
  self.assertEqual(prep.wait_grant_remaining(path),0.0,'an expired grant asks again')
 # Four: with no interface to answer, the two provider faults stay distinct.
 def test_a_read_with_no_interface_still_ends_on_the_idle_limit(self):
  request=self.request(wait=False)
  class ServesNothing:
   def seek(inner,position):pass
   def close(inner):pass
   def read(inner,count):return b''
  with self.assertRaises(prep.ProviderNotReady):
   prep.read_source(request,max_idle=0,opener=ServesNothing,pause=lambda _seconds:None)
  expected=prep.identity(self.source);expected['bytes']+=100
  with patch.object(prep,'identity',return_value=expected),self.assertRaisesRegex(prep.ProviderReadInterrupted,'incomplete'):
   prep.read_source(self.request(wait=False),max_idle=0,pause=lambda _seconds:None)
  self.assertFalse(Path(self.request(wait=False)['result']).exists())
 # Five: the question travels from the reader process into the operation status.
 def test_the_question_reaches_the_operation_status(self):
  ctx=prep.Preparation(self.root/'status-app',self.source);progress=ctx.folder/'read-progress.json'
  code=('import json,pathlib,time;pathlib.Path('+repr(str(progress))+').write_text(json.dumps('
   'dict(bytesRead=100,totalBytes=4000,waitingForData=True,waitingForDecision=True,'
   'idleSeconds=90,provider="google-drive")));time.sleep(.4)')
  ctx.capture([sys.executable,'-c',code],reading=True)
  self.assertIs(ctx.state['waitingForDecision'],True,ctx.state)
  self.assertEqual(ctx.state['idleSeconds'],90)
  self.assertEqual(ctx.state['bytesRead'],100)
  ctx.finish();self.assertIs(ctx.state['waitingForDecision'],False,'a finished run clears the question')

if __name__=='__main__':unittest.main()
