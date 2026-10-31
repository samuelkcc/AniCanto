"""A silent conversion worker must end, keep its saved work, and free the queue."""
import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'studio'),str(ROOT/'windows'),str(ROOT/'Resources')]
from backend import Studio
from desktop_state import read,write
from native_queue import dispatch as queue_dispatch

ATTEMPT='attempt-fixture'

class WorkerStallTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  self.app=Studio(self.root,ROOT/'Resources',platform='darwin')
  attempt=self.root/'attempts'/ATTEMPT;attempt.mkdir(parents=True)
  (attempt/'attempt.json').write_text(__import__('json').dumps(dict(id=ATTEMPT,action='start',status='running')),encoding='utf-8')
  self.app.store.queue=[dict(id='a',video=str(self.root/'a.mkv'),status='running',
    attempt=dict(id=ATTEMPT,action='start',path=str(attempt)),request=str(self.root/'request.json'))]
  self.app.store.selected='a';self.app.store.save()
 def row(self):return self.app.store.queue[0]
 def test_a_batch_of_worker_events_writes_the_saved_state_once(self):
  events=[dict(stage='辨識',message='line %d'%index) for index in range(1,6)]
  events.append(dict(stage='辨識',message='line 6',journey=dict(progress=.6,phase='recognition')))
  writes=[];real=self.app.store.save
  with patch.object(self.app.store,'save',side_effect=lambda *a,**k:(writes.append(1),real(*a,**k))[1]):
   self.app.dispatch('record-events',dict(id='a',events=events))
  self.assertEqual(len(writes),1,'one batch is one state write')
  self.assertEqual(self.row()['message'],'line 6')
  self.assertAlmostEqual(self.row()['progress'],.6,'a batch must merge journey progress like a single event')
  self.assertEqual(read(self.root/'studio/queue-session.json',{}),{})
  self.assertEqual(__import__('json').loads((self.root/'attempts'/ATTEMPT/'workflow.jsonl').read_text(encoding='utf-8').splitlines()[-1])['message'],'line 6')
 def test_a_single_worker_event_still_updates_the_row(self):
  self.app.dispatch('record-event',dict(id='a',event=dict(stage='辨識',message='one line')))
  self.assertEqual(self.row()['message'],'one line')
 def test_the_host_stall_is_recorded_and_the_row_stays_resumable(self):
  note='Worker produced no output for 1800 seconds. AniCanto ended this worker so the automatic queue could continue.'
  self.app.dispatch('finish',dict(id='a',code=1,paused=False,stderr=note,stalled=True))
  row=self.row()
  self.assertEqual(row['status'],'attention','a stopped worker is saved work, never a completed video')
  self.assertEqual(row['stallRecovery']['reason'],'worker-silent')
  self.assertEqual(row['lastError']['exitCode'],1)
  self.assertIn('no output for 1800 seconds',row['lastError']['message'])
  attempt=__import__('json').loads((self.root/'attempts'/ATTEMPT/'attempt.json').read_text(encoding='utf-8'))
  self.assertEqual(attempt['status'],'failed');self.assertTrue(attempt['endedAt'])
 def test_a_normal_finish_leaves_no_stall_stamp(self):
  self.app.dispatch('finish',dict(id='a',code=0,paused=False,stderr=''))
  self.assertNotIn('stallRecovery',self.row())
 def test_the_queue_takes_exactly_one_automatic_second_attempt(self):
  queue_dispatch(self.app,'queue-arm',dict(epoch=7,id='a',includeAttention=True))
  session_path=self.root/'studio/queue-session.json'
  session=read(session_path,{});session['attempted']=['a'];write(session_path,session)
  self.row().update(status='attention',stallRecovery=dict(reason='worker-silent',detectedBy='native-host'))
  self.app.store.save()
  calls=[]
  def call(op,params):
   calls.append((op,params['id']));return dict(program='adapter',args=[],action='start',rowID=params['id'])
  self.app.dispatch=call
  spec=queue_dispatch(self.app,'queue-next',dict(epoch=7))
  self.assertEqual(calls,[('start','a')]);self.assertEqual(spec['nativeQueue'],7)
  self.row().update(status='attention',stallRecovery=dict(reason='worker-silent',detectedBy='native-host'))
  self.assertIsNone(queue_dispatch(self.app,'queue-next',dict(epoch=7)),'a second stall must not loop the session')
  self.assertEqual(read(session_path,{})['stalledRetried'],['a'])
 def test_a_row_without_a_stall_stamp_is_not_restarted(self):
  queue_dispatch(self.app,'queue-arm',dict(epoch=8,id='a',includeAttention=True))
  session_path=self.root/'studio/queue-session.json'
  session=read(session_path,{});session['attempted']=['a'];write(session_path,session)
  self.row().update(status='attention')
  self.app.dispatch=lambda op,params:(_ for _ in ()).throw(AssertionError('no second start'))
  self.assertIsNone(queue_dispatch(self.app,'queue-next',dict(epoch=8)))

if __name__=='__main__':unittest.main()
