"""Use actual child output; preserve command errors and bounded termination."""
import contextlib,io,subprocess,sys,time,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'windows'))
import runtime_progress as rp
class Installer271(unittest.TestCase):
 def test_exact_transfer_and_install_phases(self):
  events=[]
  code="import time;print('Downloading torch.whl (100 bytes)',flush=True);print('Progress 0 of 100',flush=True);time.sleep(.02);print('Progress 100 of 100',flush=True);print('Installing collected packages: torch',flush=True)"
  rp.step(lambda m,**kw:events.append(dict(message=m,**kw)),'analysis','Installing missing runtime packages',rp.stream_command,[sys.executable,'-c',code],interval=.01)
  transfer=[e['download'] for e in events if e.get('download') and e['download']['receivedBytes']==100]
  self.assertTrue(transfer);self.assertEqual(transfer[0]['totalBytes'],100);self.assertEqual(transfer[0]['file'],'torch.whl')
  self.assertTrue(any(e['runtimeProgress']['phase']=='Installing downloaded runtime packages' for e in events));self.assertTrue(any(e['heartbeat'] for e in events));self.assertEqual(events[-1]['runtimeProgress']['state'],'complete')
 def test_original_error_is_retained(self):
  with contextlib.redirect_stdout(io.StringIO()):
   with self.assertRaises(subprocess.CalledProcessError) as error:rp.stream_command([sys.executable,'-c',"print('ERROR: exact failure');raise SystemExit(3)"])
  self.assertEqual(error.exception.returncode,3);self.assertIn('exact failure',error.exception.output)
 def test_timeout_stops_owned_child(self):
  start=time.monotonic()
  with self.assertRaises(subprocess.TimeoutExpired):rp.stream_command([sys.executable,'-c','import time;time.sleep(5)'],timeout=.08)
  self.assertLess(time.monotonic()-start,1)
 def test_cached_line_has_no_fabricated_download(self):
  events=[];parser=rp.InstallerOutput(lambda *args:events.append(args));parser.line('Using cached numpy.whl');self.assertIsNone(events[0][1]);self.assertEqual(events[0][2],'Reusing cached runtime packages')
if __name__=='__main__':unittest.main()
