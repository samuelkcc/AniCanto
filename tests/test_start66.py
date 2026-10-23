"""Exercise the compiled Swift/Rust boundary missed by generic startup tests."""
import json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'.build/releases/0.24.66/AniCanto.app'

@unittest.skipUnless(sys.platform=='darwin' and BASE.is_dir(),'Requires the staged macOS native worker')
class NativeReadinessTests(unittest.TestCase):
 def probe(self,app,flag='--studio-validate-contract',*args):
  with tempfile.TemporaryDirectory() as d:
   return subprocess.run([str(app/'Contents/MacOS/AniCanto'),flag,*args],env=dict(os.environ,SAM_CANTO_DATA=d),capture_output=True,text=True,timeout=30)
 def test_compiled_swift_and_core_agree_on_all_three_languages(self):
  result=self.probe(BASE)
  self.assertEqual(result.returncode,0,result.stdout+result.stderr)
  self.assertEqual(json.loads(result.stdout.strip().splitlines()[-1])['languages'],['yue','zh','en'])
 def test_mismatched_catalog_is_rejected_before_any_model_work(self):
  with tempfile.TemporaryDirectory() as d:
   app=Path(d)/'AniCanto.app'
   subprocess.run(['/bin/cp','-cR',str(BASE),str(app)],check=True)
   core=app/'Contents/Resources/bin/anicanto-core';core.unlink()
   core.write_text('#!/usr/bin/python3\nimport json\nprint(json.dumps({"ok":True,"result":{"catalog":{"schemaVersion":-1}}}))\n');core.chmod(0o755)
   result=self.probe(app)
   self.assertNotEqual(result.returncode,0)
   self.assertIn('catalog version mismatch',result.stdout)
 def test_shipped_65_reproduces_the_reported_failure(self):
  old=ROOT/'.build/releases/0.24.65/AniCanto.app'
  if not old.is_dir():self.skipTest('Previous faulty native snapshot not retained')
  result=self.probe(old,'--studio-plan','drama3','{}')
  self.assertNotEqual(result.returncode,0)
  self.assertIn('catalog version mismatch',result.stdout)

class GeneratedContractTests(unittest.TestCase):
 def test_swift_source_is_generated_from_the_current_production_contract(self):
  result=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/generate_contract.py'),'--check'],capture_output=True,text=True)
  self.assertEqual(result.returncode,0,result.stderr+result.stdout)

if __name__=='__main__':unittest.main()
