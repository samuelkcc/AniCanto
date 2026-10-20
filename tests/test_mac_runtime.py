import base64,hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Resources'))
sys.path.insert(0,str(ROOT/'scripts'))
import mac_runtime,runtime_licenses,lightweight_mac

class MacRuntimeTests(unittest.TestCase):
 def fixture(self,root):
  python=root/'runtime/bin/python3';python.parent.mkdir(parents=True);python.touch()
  receipt=root/'runtime-receipts/runtime.json';receipt.parent.mkdir();receipt.write_text('{"importsPassed":true}')
  return receipt
 def row(self):return dict(requirements='test.lock',probe='import example',identity='lock-v1',packages={'example':'1','soundfile':'2'})
 def test_distribution_names_normalize_dots_and_underscores(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'requirements.lock';path.write_text('ruamel.yaml==1\nruamel_yaml_clib==2\n')
   self.assertEqual(mac_runtime.requirements(path),{'ruamel-yaml':'1','ruamel-yaml-clib':'2'})
 def state(self,**overrides):return dict(python=[3,11],machine='arm64',packages={'example':'1','soundfile':'2'},**overrides)
 def test_existing_valid_packages_are_not_installed_or_downloaded(self):
  with tempfile.TemporaryDirectory() as folder,patch.object(mac_runtime,'spec',return_value=self.row()):
   root=Path(folder);receipt=self.fixture(root);commands=[]
   result=mac_runtime.ensure(root,'runtime',run=lambda args,**kwargs:commands.append(args),state=lambda *args:self.state())
   self.assertEqual(len(commands),1);self.assertEqual(commands[0][-1],'import example')
   self.assertEqual(result['installedOrRepaired'],[]);self.assertTrue(json.loads(receipt.read_text())['importsPassed'])
 def test_one_missing_package_preserves_healthy_ones(self):
  with tempfile.TemporaryDirectory() as folder,patch.object(mac_runtime,'spec',return_value=self.row()):
   root=Path(folder);self.fixture(root);commands=[];states=iter([dict(python=[3,11],machine='arm64',packages={'example':'1'}),self.state()])
   result=mac_runtime.ensure(root,'runtime',run=lambda args,**kwargs:commands.append(args),state=lambda *args:next(states))
   self.assertEqual(result['installedOrRepaired'],['soundfile']);self.assertEqual(len(commands),2)
   self.assertIn('--no-deps',commands[0]);self.assertNotIn('--reinstall',commands[0])
 def test_interrupted_install_never_retains_a_success_receipt_and_keeps_cache(self):
  with tempfile.TemporaryDirectory() as folder,patch.object(mac_runtime,'spec',return_value=self.row()):
   root=Path(folder);receipt=self.fixture(root);cache=root/'cache/pip/partial';cache.parent.mkdir(parents=True);cache.write_bytes(b'partial')
   def fail(*args,**kwargs):raise subprocess.CalledProcessError(1,args[0])
   with self.assertRaises(subprocess.CalledProcessError):
    mac_runtime.ensure(root,'runtime',run=fail,state=lambda *args:dict(python=[3,11],machine='arm64',packages={}))
   self.assertFalse(receipt.exists());self.assertEqual(cache.read_bytes(),b'partial')
 def test_corruption_repairs_only_the_damaged_package_once(self):
  with tempfile.TemporaryDirectory() as folder,patch.object(mac_runtime,'spec',return_value=self.row()):
   root=Path(folder);self.fixture(root);commands=[]
   def run(args,**kwargs):
    commands.append(args)
    if len(commands)==1:raise subprocess.CalledProcessError(1,args)
   result=mac_runtime.ensure(root,'runtime',run=run,state=lambda *args:self.state(),damage=lambda *args:['example'])
   self.assertEqual(len(commands),3);self.assertEqual(commands[1][-1:],['example==1']);self.assertIn('--force-reinstall',commands[1])
   self.assertNotIn('--reinstall',commands[1]);self.assertEqual(result['installedOrRepaired'],['example'])
 def test_import_error_with_intact_files_does_not_redownload(self):
  with tempfile.TemporaryDirectory() as folder,patch.object(mac_runtime,'spec',return_value=self.row()):
   root=Path(folder);receipt=self.fixture(root);commands=[]
   def fail(args,**kwargs):commands.append(args);raise subprocess.CalledProcessError(1,args)
   with self.assertRaisesRegex(RuntimeError,'intact'):
    mac_runtime.ensure(root,'runtime',run=fail,state=lambda *args:self.state(),damage=lambda *args:[])
   self.assertEqual(len(commands),1);self.assertFalse(receipt.exists())
 def test_second_import_failure_is_bounded_and_leaves_no_ready_receipt(self):
  with tempfile.TemporaryDirectory() as folder,patch.object(mac_runtime,'spec',return_value=self.row()):
   root=Path(folder);receipt=self.fixture(root);commands=[]
   def fail(args,**kwargs):
    commands.append(args)
    if args[-1]=='import example':raise subprocess.CalledProcessError(1,args)
   with self.assertRaises(subprocess.CalledProcessError):
    mac_runtime.ensure(root,'runtime',run=fail,state=lambda *args:self.state(),damage=lambda *args:['example'])
   self.assertEqual(len(commands),3);self.assertFalse(receipt.exists())
 def test_foreign_python_is_not_marked_ready(self):
  with tempfile.TemporaryDirectory() as folder,patch.object(mac_runtime,'spec',return_value=self.row()):
   root=Path(folder);receipt=self.fixture(root)
   with self.assertRaisesRegex(ValueError,'Apple Silicon'):
    mac_runtime.ensure(root,'runtime',state=lambda *args:dict(python=[3,12],machine='x86_64',packages={}))
   self.assertFalse(receipt.exists())
 def test_record_hash_identifies_damaged_package_without_touching_healthy_files(self):
  with tempfile.TemporaryDirectory() as folder:
   site=Path(folder);good=b'healthy';(site/'good.py').write_bytes(good);(site/'bad.py').write_bytes(b'corrupt')
   for name,path in [('good','good.py'),('bad','bad.py')]:
    info=site/(name+'-1.dist-info');info.mkdir();(info/'METADATA').write_text(f'Name: {name}\nVersion: 1\n')
    digest=base64.urlsafe_b64encode(hashlib.sha256(good).digest()).rstrip(b'=').decode()
    (info/'RECORD').write_text(f'{path},sha256={digest},{len(good)}\n')
   env=dict(mac_runtime.environment(site),PYTHONPATH=str(site))
   self.assertEqual(mac_runtime.damaged_packages(sys.executable,env,{'good':'1','bad':'1'}),['bad'])
 def test_external_licenses_merge_duplicates_but_keep_notices(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder)
   for name,text in [('runtime','Copyright A'),('text-runtime','Copyright A'),('asr-runtime','Copyright B')]:
    info=root/name/'lib/python3.11/site-packages/example-1.dist-info';info.mkdir(parents=True)
    (info/'METADATA').write_text('Name: example\nVersion: 1\nLicense-Expression: MIT\n');(info/'LICENSE').write_text(text)
   rows=runtime_licenses.update(root);self.assertEqual(len(rows),1);self.assertEqual(len(rows[0]['files']),2)
   self.assertEqual(set(rows[0]['origins']),{'runtime','text-runtime','asr-runtime'})
   self.assertEqual(rows[0]['fileRoot'],'applicationSupport')
 def test_lightweight_package_excludes_heavy_payload_and_preserves_app_assets(self):
  with tempfile.TemporaryDirectory() as folder:
   target=Path(folder)
   for name in ['runtimes','gpt-sovits','ollama']:
    (target/name).mkdir();(target/name/'big-file').write_text('payload')
   (target/'welcome.png').write_text('art');(target/'worker.py').write_text('worker')
   identities=lightweight_mac.prepare(target,ROOT)
   self.assertEqual((target/'welcome.png').read_text(),'art');self.assertTrue((target/'worker.py').exists())
   self.assertEqual(list((target/'runtimes').iterdir()),[]);self.assertFalse((target/'gpt-sovits').exists());self.assertFalse((target/'ollama').exists())
   self.assertEqual(identities['runtime']['identity'],mac_runtime.spec('runtime')['identity'])
   self.assertFalse(json.loads((target/'LIGHTWEIGHT-PACKAGE.json').read_text())['bundledModelWeights'])

if __name__=='__main__':unittest.main()
