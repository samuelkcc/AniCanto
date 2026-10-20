import sys,unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import worker

class WorkerErrorTests(unittest.TestCase):
 def test_long_expression_keeps_readable_error_and_full_log(self):
  error="volume expression '"+'x'*15000+"'\nError initializing filters\nCannot allocate memory\n"
  with tempfile.TemporaryDirectory() as directory:
   original=tempfile.NamedTemporaryFile
   def temporary(**kwargs):return original(dir=directory,**kwargs)
   with patch('worker.subprocess.run',return_value=SimpleNamespace(returncode=244,stderr=error.encode(),stdout=b'')),patch('tempfile.NamedTemporaryFile',side_effect=temporary):
    with self.assertRaises(RuntimeError) as caught:worker.run(['ffmpeg'])
   self.assertLess(len(str(caught.exception)),1000)
   self.assertIn('Error initializing filters',str(caught.exception))
   logs=list(Path(directory).glob('AniCanto-tool-*.log'))
   self.assertEqual(len(logs),1)
   self.assertEqual(logs[0].read_text(),error)
