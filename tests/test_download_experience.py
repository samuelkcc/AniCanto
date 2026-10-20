import contextlib,hashlib,io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'windows'))
import downloads
class DownloadExperienceTests(unittest.TestCase):
 def events(self,buffer):return [json.loads(s)['download'] for s in buffer.getvalue().splitlines()]
 def test_restart_reuses_verified_file_without_http_and_explains_verification(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'model.gguf';p.write_bytes(b'weight');buf=io.StringIO()
   with patch.object(downloads.urllib.request,'urlopen',side_effect=AssertionError('No download needed')),contextlib.redirect_stdout(buf):downloads.download('https://example.org/m',p,hashlib.sha256(b'weight').hexdigest(),6)
   rows=self.events(buf);self.assertEqual(rows[0]['state'],'verifying');self.assertEqual(rows[-1]['state'],'reused');self.assertEqual(rows[-1]['receivedBytes'],6)
 def test_finished_partial_is_published_on_restart_without_http(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'model.gguf';p.with_name(p.name+'.partial').write_bytes(b'weight')
   with patch.object(downloads.urllib.request,'urlopen',side_effect=AssertionError('Already downloaded')),contextlib.redirect_stdout(io.StringIO()):downloads.download('https://example.org/m',p,hashlib.sha256(b'weight').hexdigest(),6)
   self.assertEqual(p.read_bytes(),b'weight')
 def test_fast_download_always_has_a_final_ready_event(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'model.gguf';response=MagicMock();response.__enter__.return_value=response;response.status=200;response.headers={'Content-Length':'6'};response.read.side_effect=[b'weight',b''];buf=io.StringIO()
   with patch.object(downloads.urllib.request,'urlopen',return_value=response),contextlib.redirect_stdout(buf):downloads.download('https://example.org/m',p,hashlib.sha256(b'weight').hexdigest(),6)
   self.assertEqual(self.events(buf)[-1]['state'],'complete');self.assertEqual(self.events(buf)[-1]['receivedBytes'],6)
 def test_corrupt_complete_partial_is_restarted_and_not_reused(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'model.gguf';p.with_name(p.name+'.partial').write_bytes(b'broken');response=MagicMock();response.__enter__.return_value=response;response.status=200;response.headers={'Content-Length':'6'};response.read.side_effect=[b'weight',b'']
   with patch.object(downloads.urllib.request,'urlopen',return_value=response) as network,contextlib.redirect_stdout(io.StringIO()):downloads.download('https://example.org/m',p,hashlib.sha256(b'weight').hexdigest(),6)
   network.assert_called_once();self.assertEqual(p.read_bytes(),b'weight')
