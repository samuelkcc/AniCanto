"""Runtime isolation, pinned installer evidence and selective repairs."""
import hashlib,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'scripts')]
import runtime_installer as installer,release_notices

class RuntimeInstallerTests(unittest.TestCase):
 def test_pip_command_checks_wheel_and_isolates_user_configuration(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);python=root/'runtime/bin/python3'
   cmd=installer.pip_command(python,root,'install','example==1')
   self.assertIn('-I',cmd);self.assertIn('--isolated',cmd)
   self.assertEqual(cmd[cmd.index('--cache-dir')+1],str(root.resolve()/'cache/pip'))
   with patch.object(installer,'catalog',return_value={'pip':{'file':'wheels/missing.whl','sha256':'0'*64}}):
    with self.assertRaisesRegex(ValueError,'SHA-256'):installer.pip_command(python,root,'install','example')
 def test_foreign_interpreter_and_escaping_symlink_are_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   with self.assertRaises(ValueError):installer.pip_command(sys.executable,root,'install','example')
   (root/'runtime').symlink_to(Path(sys.executable).parent)
   with self.assertRaises(ValueError):installer.ensure_env(root,root/'runtime')
 def test_healthy_existing_environment_is_not_recreated(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);py=installer.python_path(root/'runtime');py.parent.mkdir(parents=True);py.touch()
   with patch.object(installer,'base_python',side_effect=AssertionError('No Python download expected')):
    self.assertEqual(installer.ensure_env(root,root/'runtime'),py)
 def test_stale_python_aliases_are_repaired_without_clearing_packages(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);folder=root/'runtime';(folder/'bin').mkdir(parents=True)
   (folder/'bin/python').symlink_to(root/'python/removed-base/bin/python3.11')
   (folder/'bin/python3').symlink_to('python')
   package=folder/'lib/kept.py';package.parent.mkdir();package.write_text('retained')
   calls=[]
   def run(command,**kwargs):
    calls.append(command);self.assertFalse((folder/'bin/python').is_symlink());self.assertFalse((folder/'bin/python3').is_symlink())
   with patch.object(installer,'base_python',return_value=root/'python/new/bin/python3'),patch.object(installer.sys,'platform','darwin'):
    installer.ensure_env(root,folder,run=run)
   self.assertEqual(len(calls),1);self.assertNotIn('--clear',calls[0]);self.assertEqual(package.read_text(),'retained')
 def test_stale_alias_to_external_python_is_not_removed(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);folder=root/'runtime';(folder/'bin').mkdir(parents=True)
   alias=folder/'bin/python';alias.symlink_to('/outside-app/nonexistent/python3')
   with patch.object(installer,'base_python',return_value=root/'python/new/bin/python3'),patch.object(installer.sys,'platform','darwin'):
    with self.assertRaisesRegex(ValueError,'inside application data'):installer.ensure_env(root,folder,run=lambda *a,**k:None)
   self.assertTrue(alias.is_symlink())
 def test_environment_removes_installer_overrides_without_exposing_user_packages(self):
  with patch.dict(os.environ,{'PIP_INDEX_URL':'https://invalid.test','UV_PYTHON':'external','PYTHONPATH':'external','PYTHONHOME':'external','VIRTUAL_ENV':'external','CANTOSYNC_UI_LANGUAGE':'en'}):
   env=installer.clean_environment('/tmp/app')
  for k in ['PIP_INDEX_URL','UV_PYTHON','PYTHONPATH','PYTHONHOME','VIRTUAL_ENV']:self.assertNotIn(k,env)
  self.assertEqual(env['PYTHONNOUSERSITE'],'1');self.assertEqual(env['CANTOSYNC_UI_LANGUAGE'],'en')
 def test_repair_only_reinstalls_named_pinned_packages(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cmd=installer.repair_command(root/'runtime/bin/python3',root,['broken'],{'broken':'1','healthy':'2'})
   self.assertEqual(cmd[-1],'broken==1');self.assertNotIn('healthy==2',cmd)
   self.assertIn('--force-reinstall',cmd);self.assertIn('--no-deps',cmd);self.assertNotIn('-r',cmd)
   with self.assertRaises(ValueError):installer.repair_command(root/'runtime/bin/python3',root,['foreign'],{'broken':'1'})
 def test_notices_match_the_exact_installer_manifest(self):
  data=installer.catalog()
  for row in [data['pip'],*data['platforms'].values()]:
   self.assertTrue(row['notices']);self.assertTrue(row['url'].startswith('https://'))
   for doc in row['notices']:
    self.assertNotIn('__pycache__',doc['path']);self.assertFalse(doc['path'].endswith(('.pyc','.pyo')))
    self.assertEqual(hashlib.sha256((ROOT/doc['path']).read_bytes()).hexdigest(),doc['sha256'])
  with tempfile.TemporaryDirectory() as d:
   target=Path(d);rows=release_notices.install(target)
   self.assertFalse(any('uv dependency' in row['name'] for row in rows))
   self.assertFalse((target/'licenses/tools/uv-dependencies').exists())
   self.assertTrue(any(row['name']=='pip and vendored dependencies' for row in rows))
 def test_windows_gpu_install_preserves_explicit_vendor_index(self):
  sys.path.insert(0,str(ROOT/'windows'))
  import install
  with tempfile.TemporaryDirectory() as d,patch.object(install,'data_root',return_value=Path(d)),patch.object(install,'call') as run:
   python=Path(d)/'runtimes/gpt/Scripts/python.exe'
   for backend,index in [('nvidia','cu128'),('intel','xpu'),('cpu','cpu')]:
    install.install_torch(python,backend)
    command=run.call_args.args[0]
    self.assertIn('https://download.pytorch.org/whl/'+index,command)
    self.assertIn('torch==2.9.1',command);self.assertIn('torchaudio==2.9.1',command)
 def test_windows_gpu_repair_does_not_reinstall_healthy_sdk_or_other_packages(self):
  sys.path.insert(0,str(ROOT/'windows'))
  import install
  with tempfile.TemporaryDirectory() as d,patch.object(install,'data_root',return_value=Path(d)),patch.object(install,'call') as run:
   python=Path(d)/'runtimes/gpt/Scripts/python.exe'
   install.install_torch(python,'amd',repair=True,packages=['torch'])
   self.assertEqual(run.call_count,1);command=run.call_args.args[0]
   urls=[x for x in command if str(x).startswith('https://repo.radeon.com/')]
   self.assertEqual(len(urls),1);self.assertIn('torch-2.9.1',urls[0])
   self.assertIn('--force-reinstall',command);self.assertIn('--no-deps',command)
 def test_python_metadata_projection_has_all_referenced_notices(self):
  data=installer.catalog()
  for platform,row in data['platforms'].items():
   evidence=row['buildEvidence'];self.assertEqual(evidence['mismatchedFiles'],[])
   self.assertGreater(evidence['installOnlyFilesCompared'],1000)
   doc=evidence['metadataProjection'];path=ROOT/doc['path']
   self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),doc['sha256'])
   metadata=json.loads(path.read_text())
   self.assertEqual(metadata['originalMetadataSHA256'],doc['originalMetadataSHA256'])
   for variants in metadata['extensions'].values():
    for variant in variants:
     for name in variant.get('license_paths',[]):self.assertTrue((path.parent/Path(name).name).is_file(),(platform,name))
 def test_windows_bootstrap_python_snippets_survive_legacy_powershell_quoting(self):
  import re
  for name in ['Resources/python-bootstrap.ps1','studio/bootstrap-windows.ps1']:
   text=(ROOT/name).read_text();snippets=re.findall(r'-c "([^"\n]*)"',text)
   self.assertTrue(snippets,name)
   for code in snippets:
    self.assertNotIn('"',code);compile(code,name,'exec')
 def test_shipping_paths_do_not_invoke_uv_and_packagers_reject_it(self):
  for name in ['Sources/Engine.swift','Sources/FirstRunDeployment.swift','Sources/MacRuntimeDeployment.swift','Resources/mac_runtime.py','Resources/dubbing_setup.py','windows/native_setup.py','windows/install.py','studio/bootstrap-windows.ps1','windows/bootstrap.ps1']:
   text=(ROOT/name).read_text()
   for pattern in ["uv_path(","run(uv,","[uv,","$Uv","uv.path","bin/uv"]:self.assertNotIn(pattern,text,name)
  self.assertIn("'uv.exe'",(ROOT/'scripts/build_portable_windows.py').read_text())
  self.assertIn("(resources/'bin/uv').unlink",(ROOT/'scripts/lightweight_mac.py').read_text())

if __name__=='__main__':unittest.main()
