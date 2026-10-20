import sys,tempfile,unittest,zipfile,json
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows')]
from runtime_exclusions import cleanup_command,EXCLUDED
import native_setup,runtime_health

class RuntimeExclusionsTests(unittest.TestCase):
    def test_cleanup_only_applies_to_known_unused_packages_in_specific_runtime(self):
        installed={'diffq':'0.2.4','distance':'0.1.3','torch':'2.6.0'}
        self.assertIsNone(cleanup_command('/tmp/app','/tmp/app/runtime/bin/python3','worker',installed))
        self.assertEqual(cleanup_command('/tmp/app','/tmp/app/runtime/bin/python3','analysis',installed)[-1:],[ 'diffq'])
        self.assertEqual(cleanup_command('/tmp/app','/tmp/app/runtime/bin/python3','gpt',installed)[-1:],['distance'])
        self.assertIsNone(cleanup_command('/tmp/app','/tmp/app/runtime/bin/python3','analysis',{'torch':'2.6.0'}))
    def test_pinned_locks_never_reinstall_retired_packages(self):
        from mac_runtime import requirements
        for name in ('Resources/separator-requirements.lock','Resources/gsv-requirements.lock','windows/requirements-analysis.lock','windows/requirements-gpt.lock'):
            self.assertFalse({'diffq','diffq-fixed','distance'}&requirements(ROOT/name).keys(),name)
    def test_windows_subset_uses_lock_without_resolving_unused_upstream_dependency(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);python=root/'runtimes/analysis/Scripts/python.exe';python.parent.mkdir(parents=True);python.touch()
            with patch.object(native_setup,'data_root',return_value=root),patch.object(native_setup,'env_python',return_value=python),patch.object(runtime_health,'missing',side_effect=[['audio-separator'],[]]),patch.object(runtime_health,'probe'),patch.object(runtime_health,'state',return_value={'packages':{'diffq-fixed':'0.2.4'}}),patch.object(native_setup,'call') as call:
                native_setup.environment('analysis')
            commands=[args.args[0] for args in call.call_args_list]
            self.assertIn('--no-deps',commands[0]);self.assertEqual(commands[1][-1],'diffq-fixed');self.assertIn('uninstall',commands[1])
    def test_filtered_cuda_archive_keeps_legal_notices_and_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);archive=root/'tool.zip'
            with zipfile.ZipFile(archive,'w') as z:
                for name in ('bin/runtime.dll','docs/EULA.txt','docs/LICENSE','examples/unused.cpp'):z.writestr(name,'test')
            native_setup.extract_zip(archive,root/'tool','.dll')
            self.assertTrue((root/'tool/docs/EULA.txt').exists());self.assertFalse((root/'tool/examples/unused.cpp').exists())
            with zipfile.ZipFile(archive,'w') as z:z.writestr('../escape.dll','bad')
            with self.assertRaises(ValueError):native_setup.extract_zip(archive,root/'tool','.dll')

if __name__=='__main__':unittest.main()
