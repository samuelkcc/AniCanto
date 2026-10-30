"""Final audio validation must work from a standard-library-only setup process."""
import json,os,subprocess,sys,tempfile,unittest,wave
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'windows'),str(ROOT/'Resources')]
import native_setup
class SetupAudio272(unittest.TestCase):
 def test_minimal_setup_python_can_validate_using_verified_worker(self):
  worker=Path.home()/'Library/Application Support/SamCantoSync/separator-runtime/bin/python3'
  if not worker.exists():self.skipTest('A soundfile-capable test worker is required.')
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'probe.wav'
   with wave.open(str(p),'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(b'\x01\x00'*4800)
   code="import sys,importlib.util,json;assert importlib.util.find_spec('soundfile') is None;sys.path[:0]=sys.argv[1:3];import native_setup;print(json.dumps(native_setup.verify_speech_probe(sys.argv[3],sys.argv[4])))"
   result=subprocess.run([sys.executable,'-I','-S','-c',code,str(ROOT/'windows'),str(ROOT/'Resources'),str(worker),str(p)],text=True,capture_output=True,timeout=30)
   self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(json.loads(result.stdout)['frames'],4800)
 def test_short_or_invalid_recording_is_not_accepted(self):
  for data in [{'frames':200,'sampleRate':24000},{'frames':4000,'sampleRate':0},[]]:
   with patch.object(native_setup.subprocess,'check_output',return_value=json.dumps(data)):
    with self.assertRaises(ValueError):native_setup.verify_speech_probe('verified-worker','probe.wav')
if __name__=='__main__':unittest.main()
