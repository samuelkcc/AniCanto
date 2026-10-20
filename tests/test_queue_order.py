"""Queue moves are metadata only: preserve source, work, selection and progress."""
import copy,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'studio'),str(ROOT/'windows'),str(ROOT/'Resources')]
from backend import Studio

class QueueOrderTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.app=Studio(self.root,ROOT/'Resources',platform='darwin')
        self.rows=[dict(id=k,video=str(self.root/(k+'.mkv')),status=status,progress=.42,request='immutable-'+k,job='retained-'+k,processingSeconds=81) for k,status in [('a','running'),('b','waiting'),('c','paused')]]
        self.app.store.queue=copy.deepcopy(self.rows);self.app.store.selected='a';self.app.store.save()
    def tearDown(self):self.temp.cleanup()
    def move(self,id,before=None):return self.app.dispatch('move-video',dict(id=id,beforeID=before))
    def test_move_above_running_keeps_worker_and_selection(self):
        state=self.move('c','a')
        self.assertEqual([r['id'] for r in state['queue']],['c','a','b'])
        self.assertEqual(state['selected'],'a')
        self.assertEqual(self.app.store.queue,[self.rows[2],self.rows[0],self.rows[1]])
        restored=Studio(self.root,ROOT/'Resources',platform='darwin')
        self.assertEqual(restored.store.queue,self.app.store.queue)
        self.assertEqual(restored.store.row('a')['status'],'running')
    def test_move_to_bottom_does_not_modify_submitted_requests(self):
        self.move('a');self.assertEqual(self.app.store.queue,[self.rows[1],self.rows[2],self.rows[0]])
    def test_no_op_and_self_move(self):
        before=self.app.store.path.read_bytes()
        self.move('a','a');self.move('c')
        self.assertEqual(self.app.store.path.read_bytes(),before)
    def test_invalid_and_stale_targets_are_atomic(self):
        before=self.app.store.path.read_bytes()
        for id,target in [('unknown','a'),('a','deleted'),(None,'a'),('a',[]),([],None)]:
            with self.assertRaisesRegex(ValueError,'list changed'):self.move(id,target)
            self.assertEqual(self.app.store.path.read_bytes(),before)
    def test_newly_added_item_is_retained(self):
        self.app.store.queue.append(dict(id='d',video='new.mkv',status='waiting'));self.app.store.save()
        self.move('c','b');self.assertEqual([r['id'] for r in self.app.store.queue],['a','c','b','d'])
    def test_single_item(self):
        self.app.store.queue=self.app.store.queue[:1];self.app.store.save();self.move('a')
        self.assertEqual(self.app.store.queue,self.rows[:1])

if __name__=='__main__':unittest.main()
