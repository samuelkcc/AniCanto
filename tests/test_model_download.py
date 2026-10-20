import contextlib
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import socket
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import model_download as d

class DownloadTests(unittest.TestCase):
    def test_final_redirect_headers(self):
        self.assertEqual(d.header_total('HTTP/1.1 302 Found\nContent-Length: 18\n\nHTTP/1.1 206 Partial Content\nContent-Range: bytes 25-99/100\nContent-Length: 75\n',25),100)
        self.assertIsNone(d.header_total('HTTP/1.1 302 Found\nContent-Length: 18\n',0))
        self.assertEqual(d.header_total('HTTP/1.1 200 OK\nContent-Length: 100\n',0),100)

    def test_disconnect_resume_telemetry_and_sha(self):
        body=bytes(range(256))*1024
        requests=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                start=int((self.headers.get('Range') or 'bytes=0-').split('=')[1].split('-')[0])
                requests.append(start)
                self.send_response(206 if start else 200)
                self.send_header('Content-Length',str(len(body)-start))
                if start:self.send_header('Content-Range',f'bytes {start}-{len(body)-1}/{len(body)}')
                self.end_headers()
                if len(requests)==1:
                    self.wfile.write(body[:65536]);self.wfile.flush()
                    self.connection.shutdown(socket.SHUT_RDWR);self.connection.close()
                else:self.wfile.write(body[start:])
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with tempfile.TemporaryDirectory() as root,contextlib.redirect_stdout(io.StringIO()) as output:
                path=Path(root)/'model.bin'
                d.download(f'http://127.0.0.1:{server.server_port}/model',path,hashlib.sha256(body).hexdigest(),len(body))
                self.assertEqual(path.read_bytes(),body)
                self.assertFalse(path.with_name('model.bin.partial').exists())
                events=[json.loads(line)['download'] for line in output.getvalue().splitlines()]
                self.assertTrue(any(e['state']=='retrying' for e in events))
                self.assertTrue(any(e['bytesPerSecond']>0 and e['etaSeconds'] is not None for e in events))
                self.assertEqual(events[-1]['state'],'complete')
                self.assertGreater(requests[1],0)
                count=len(requests)
                d.download(f'http://127.0.0.1:{server.server_port}/model',path,hashlib.sha256(body).hexdigest(),len(body))
                self.assertEqual(len(requests),count,'Verified files must not redownload')
        finally:server.shutdown();server.server_close()

    def test_finished_partial_reuses_local_bytes_and_emits_verification(self):
        with tempfile.TemporaryDirectory() as root,patch.object(d.subprocess,'Popen',side_effect=AssertionError('No download')),contextlib.redirect_stdout(io.StringIO()) as buffer:
            path=Path(root)/'model.bin';path.with_name('model.bin.partial').write_bytes(b'weights')
            d.download('https://example.invalid/model',path,hashlib.sha256(b'weights').hexdigest(),7)
            self.assertEqual(path.read_bytes(),b'weights')
            events=[json.loads(line)['download'] for line in buffer.getvalue().splitlines()]
            self.assertEqual(events[0]['state'],'verifying');self.assertEqual(events[-1]['state'],'complete')

    def test_failure_retains_partial_and_exhausts_bounded_retries(self):
        class Process:
            returncode=56
            def poll(self):return 56
        with tempfile.TemporaryDirectory() as root,patch.object(d.subprocess,'Popen',return_value=Process()) as launch,patch.object(d.time,'sleep'),contextlib.redirect_stdout(io.StringIO()) as output:
            path=Path(root)/'model.bin';part=path.with_name('model.bin.partial');part.write_bytes(b'keep')
            with self.assertRaisesRegex(RuntimeError,'已保留下載內容'):d.download('https://example.invalid/model',path,'bad',100)
            self.assertEqual(launch.call_count,5);self.assertEqual(part.read_bytes(),b'keep');self.assertFalse(path.exists())
            self.assertEqual(json.loads(output.getvalue().splitlines()[-1])['download']['state'],'failed')

    def test_bad_checksum_never_publishes(self):
        class Process:
            returncode=0
            def poll(self):return 0
        with tempfile.TemporaryDirectory() as root,patch.object(d.subprocess,'Popen',return_value=Process()),contextlib.redirect_stdout(io.StringIO()):
            path=Path(root)/'model.bin';path.with_name('model.bin.partial').write_bytes(b'bad')
            with self.assertRaisesRegex(ValueError,'SHA-256'):d.download('https://example.invalid/model',path,'0'*64,3)
            self.assertFalse(path.exists());self.assertEqual(len(list(Path(root).glob('*.invalid-*'))),1)

if __name__=='__main__':unittest.main()
