"""Verify cache cleanup boundaries with isolated files."""
import importlib.util
import json
import plistlib
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('cache_retention', Path(__file__).resolve().parents[1]/'scripts/generated_cache_retention.py')
cache = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cache)


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.product = self.root/'mobile/DerivedData/Build/object.o'
        self.product.parent.mkdir(parents=True)
        (self.product.parent.parent/'info.plist').write_text('Xcode cache')
        self.product.write_bytes(b'generated object')
        self.source = self.root/'mobile/View.swift'
        self.source.write_text('source')
        self.plan = self.root/'plan.json'

    def tearDown(self):
        self.temp.cleanup()

    def test_dry_run_then_apply_keeps_source_and_packages(self):
        package = self.root/'mobile/DerivedData/SourcePackages/checkouts/library/source.swift'
        package.parent.mkdir(parents=True)
        package.write_text('dependency source')
        cache.make_plan(self.root, self.plan)
        cache.execute(self.root, self.plan)
        self.assertTrue(self.product.exists())
        cache.execute(self.root, self.plan, True)
        self.assertFalse(self.product.exists())
        self.assertEqual(self.source.read_text(), 'source')
        self.assertEqual(package.read_text(), 'dependency source')

    def test_changed_tree_rejects_the_entire_plan(self):
        other = self.root/'studio/src-tauri/target/object.o'
        other.parent.mkdir(parents=True)
        other.write_bytes(b'other generated object')
        cache.make_plan(self.root, self.plan)
        self.product.write_bytes(b'new compilation')
        with self.assertRaises(ValueError):
            cache.execute(self.root, self.plan, True)
        self.assertTrue(other.exists())

    def test_active_dependency_link_prevents_removal(self):
        deps = self.root/'mobile/Dependencies';deps.mkdir()
        (deps/'required.a').symlink_to(self.product)
        result = cache.make_plan(self.root, self.plan)
        self.assertEqual(result['files'], [])
        self.assertEqual(len(result['skippedLiveInputs']), 1)

    def test_project_reference_prevents_removal(self):
        project = self.root/'mobile/App.xcodeproj/project.pbxproj'
        project.parent.mkdir()
        project.write_text('LIBRARY = "'+str(self.product)+'";')
        self.assertEqual(cache.make_plan(self.root, self.plan)['files'], [])

    def test_arbitrary_source_and_linked_parent_are_rejected(self):
        with self.assertRaises(ValueError):
            cache.checked(self.root, 'mobile')
        with self.assertRaises(ValueError):
            cache.checked(self.root, '../outside')
        (self.root/'linked-derived').symlink_to(self.product.parent.parent)
        with self.assertRaises(ValueError):
            cache.checked(self.root, 'linked-derived/Build')

    def test_nested_git_checkout_prevents_removal(self):
        (self.product.parent/'.git').mkdir()
        with self.assertRaises(ValueError):
            cache.make_plan(self.root, self.plan)

    def test_appledouble_requires_a_checked_header_and_bundle_path(self):
        path=self.root/'isolated/AniCanto.app/._Contents';path.parent.mkdir(parents=True)
        path.write_bytes(b'\x00\x05\x16\x07metadata')
        self.assertEqual(cache.checked(self.root,path.relative_to(self.root)),path)
        path.write_bytes(b'ordinary source')
        with self.assertRaises(ValueError):cache.checked(self.root,path.relative_to(self.root))

    def test_device_cache_uses_xcode_metadata(self):
        parent=self.root/'mobile/DerivedData/Device';(parent/'Build').mkdir(parents=True)
        (parent/'info.plist').write_bytes(plistlib.dumps({'WorkspacePath':'/isolated/App.xcodeproj'}))
        result=cache.make_plan(self.root,self.plan)
        self.assertIn('mobile/DerivedData/Device/Build',{r['path'] for r in result['files']})

    def test_a_frozen_delivered_host_is_not_a_compiler_cache(self):
        host=self.root/'studio/src-tauri/target/release/anicanto-studio';host.parent.mkdir(parents=True)
        host.write_bytes(b'verified delivered host')
        result=cache.make_plan(self.root,self.plan)
        self.assertNotIn('studio/src-tauri/target',{r['path'] for r in result['files']})


if __name__ == '__main__':
    unittest.main()
