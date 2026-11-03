"""Protect unique source and model content during build retention."""
import importlib.util
import tempfile
import unittest
import types
import contextlib
import io
import json
import hashlib
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('retention297', Path(__file__).resolve().parents[1] / 'scripts/build-retention.py')
retention = importlib.util.module_from_spec(spec)
spec.loader.exec_module(retention)


class RetentionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.build = self.root / '.build'
        self.build.mkdir()
        self.patches = [patch.object(retention, 'ROOT', self.root), patch.object(retention, 'BUILD', self.build),
                        patch.object(retention, 'SIZES_CACHE', self.build/'sizes.json')]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.temp.cleanup()

    def file(self, relative, data):
        p = self.build / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p

    def test_handover_sentence_punctuation_does_not_change_protected_names(self):
        docs=self.root/'docs';docs.mkdir()
        (docs/'CODEX-HANDOVER.md').write_text('# Record\n## Work Records\n### Current\nProtect .build/lan-diagnostics-2026-11-02.\nKeep .build/archive.app.\n')
        keep=retention.protected_names()
        self.assertIn('lan-diagnostics-2026-11-02',keep)
        self.assertIn('archive.app',keep)
        self.assertNotIn('archive.app.',keep)

    def test_equal_name_and_length_are_not_duplicate_proof(self):
        a = self.file('_retained-models/a/model.bin', b'first')
        b = self.file('_retained-models/b/model.bin', b'other')
        self.assertEqual(retention.dedupe_retained([]), 0)
        self.assertEqual(a.read_bytes(), b'first')
        self.assertEqual(b.read_bytes(), b'other')

    def test_verified_duplicate_preserves_both_paths(self):
        a = self.file('_retained-models/a/model.bin', b'equal')
        b = self.file('_retained-models/b/renamed.bin', b'equal')
        self.assertEqual(retention.dedupe_retained([]), 5)
        self.assertEqual(a.read_bytes(), b'equal')
        self.assertEqual(b.read_bytes(), b'equal')
        self.assertEqual(int(a.is_symlink()) + int(b.is_symlink()), 1)

    def test_dedupe_dry_run_has_no_file_mutation(self):
        a = self.file('_retained-models/a/model.bin', b'equal')
        b = self.file('_retained-models/b/model.bin', b'equal')
        self.assertEqual(retention.dedupe_retained([], apply=False), 5)
        self.assertFalse(a.is_symlink())
        self.assertFalse(b.is_symlink())

    def test_rescue_cap_does_not_authorize_deletion(self):
        p = self.file('old/models/weights.bin', b'unique model')
        self.assertFalse(retention.rescue(p.parent.parent, {}, [], 300, [100], [0, 0]))
        self.assertEqual(p.read_bytes(), b'unique model')

    def test_same_source_name_with_different_content_is_archived(self):
        live = self.file('live/module.py', b'current')
        old = self.file('old/module.py', b'important old source')
        self.assertTrue(retention.rescue(old.parent, {'module.py': [live]}, [], 300, [100], [100, 0]))
        copies = list((self.build / '_retention-archive').rglob('module.py'))
        self.assertEqual([p.read_bytes() for p in copies], [b'important old source'])

    def test_archive_cap_and_git_checkout_protect_original_tree(self):
        old = self.file('old/module.py', b'unique')
        self.assertFalse(retention.rescue(old.parent, {}, [], 300, [0], [100, 0]))
        self.assertTrue(old.exists())
        (old.parent / '.git').mkdir()
        self.assertFalse(retention.rescue(old.parent, {}, [], 300, [100], [100, 0]))

    def test_version_folders_retain_only_latest_five(self):
        for n in range(1, 9):
            (self.build / 'releases' / f'0.25.{n}').mkdir(parents=True)
        self.assertEqual({p.name for p in retention.prune_children(self.build / 'releases', 5)},
                         {'0.25.1', '0.25.2', '0.25.3'})

    def test_gigabyte_rescue_limit_is_not_treated_as_megabytes(self):
        model=self.file('version1/models/weight.bin',b'')
        with model.open('wb') as f:
            f.seek(65*1024*1024-1);f.write(b'x')
        for n in range(2,8):(self.build/f'version{n}').mkdir()
        args=types.SimpleNamespace(dedupe_only=False,refresh=False,apply=True,active_days=0,
            retain=5,archive_cap_mb=1,model_cap_gb=1,model_min_mb=300)
        with patch.object(retention,'du_mb',return_value={}),patch.object(retention,'protected_names',return_value={}), \
             patch.object(retention,'live_source_names',return_value={}),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(retention.run(args),0)
        self.assertFalse(model.exists())
        self.assertEqual((self.build/'_retained-models/version1/models/weight.bin').stat().st_size,65*1024*1024)

    def test_cross_root_sharing_keeps_both_models_after_either_path_is_removed(self):
        source=self.root/'installed/models/model.bin';source.parent.mkdir(parents=True);source.write_bytes(b'immutable weights')
        target=self.file('_retained-models/old/model.bin',source.read_bytes())
        plan=self.root/'plan.json';plan.write_text(json.dumps({'groups':[{'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'files':[{'group':'installed','path':str(source)},{'group':'retained','path':str(target)}]}]}))
        retention.share_live_models(plan,source.parent,[],False);self.assertFalse(source.samefile(target))
        retention.share_live_models(plan,source.parent,[],True);self.assertTrue(source.samefile(target))
        source.unlink();self.assertEqual(target.read_bytes(),b'immutable weights')

    def test_changed_live_model_rejects_plan_without_modifying_retained_copy(self):
        source=self.root/'installed/models/model.bin';source.parent.mkdir(parents=True);source.write_bytes(b'new model')
        target=self.file('_retained-models/old/model.bin',b'old model')
        plan=self.root/'plan.json';plan.write_text(json.dumps({'groups':[{'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
            'files':[{'group':'installed','path':str(source)},{'group':'retained','path':str(target)}]}]}))
        with self.assertRaises(ValueError):retention.share_live_models(plan,source.parent,[],True)
        self.assertEqual(target.read_bytes(),b'old model')

    def test_small_litert_model_is_preserved(self):
        model=self.file('old/models/gemma.litertlm',b'weights')
        self.assertTrue(retention.rescue(model.parent.parent,{},[],300,[0],[1024,0]))
        self.assertEqual((self.build/'_retained-models/old/models/gemma.litertlm').read_bytes(),b'weights')

    def test_embedded_semver_and_source_archives_obey_five_release_limit(self):
        folder=self.build/'public-review';folder.mkdir()
        for n in range(1,8):
            (folder/f'candidate-0.25.{n}').mkdir()
            (folder/f'available-source-materials-0.25.{n}.tar.gz').write_bytes(b'archive fixture')
        (folder/'candidate-0.24.99').mkdir()
        removed={p.name for p in retention.prune_children(folder,5)}
        self.assertEqual(removed,{'candidate-0.25.1','candidate-0.25.2','candidate-0.24.99',
            'available-source-materials-0.25.1.tar.gz','available-source-materials-0.25.2.tar.gz'})
        self.assertNotIn('available-source-materials-0.25.7.tar.gz',removed)

    def test_one_budget_applies_across_containers_and_keeps_published_release(self):
        (self.root/'VERSION.json').write_text('{"version":"0.25.37"}')
        (self.root/'docs').mkdir();(self.root/'docs/DESKTOP-DOWNLOADS.json').write_text('{"mac":{"version":"0.25.25"}}')
        for n in range(30,38):(self.build/'shared-release'/f'0.25.{n}').mkdir(parents=True)
        old=self.build/'previous/before-0164/old.app/Contents';old.mkdir(parents=True)
        import plistlib
        (old/'Info.plist').write_bytes(plistlib.dumps({'CFBundleShortVersionString':'0.16.3'}))
        budget=retention.desktop_release_budget(5)
        self.assertEqual(budget,{(0,25,25),(0,25,34),(0,25,35),(0,25,36),(0,25,37)})
        self.assertEqual(retention.prune_children(self.build/'previous',5,budget),[old.parents[1]])

    def test_git_worktree_pointer_also_protects_source(self):
        pointer=self.file('work/.git',b'gitdir: /some/managed/worktree')
        self.assertFalse(retention.rescue(pointer.parent,{},[],300,[100],[100,0]))
        self.assertTrue(pointer.exists())

    def test_nested_git_guard_runs_before_any_model_move(self):
        model=self.file('work/weights.bin',b'protected source model')
        self.file('work/nested/.git',b'gitdir: /managed/source')
        self.assertFalse(retention.rescue(model.parent,{},[],300,[100],[100,0]))
        self.assertFalse(model.is_symlink())
        self.assertEqual(model.read_bytes(),b'protected source model')
        self.assertFalse((self.build/'_retained-models').exists())

    def test_active_native_project_protects_external_library_inputs(self):
        project=self.root/'mobile/App.xcodeproj/project.pbxproj'
        project.parent.mkdir(parents=True)
        project.write_text('OTHER_LDFLAGS = "/work/.build/native456/inputs/library.a";')
        self.assertIn('native456',retention.protected_names())

    def test_partial_rescue_keeps_the_original_model_path_readable(self):
        model=self.file('work/weights.bin',b'preserved model')
        self.file('work/nested/module.py',b'unique source beyond the archive limit')
        self.assertFalse(retention.rescue(model.parent,{},[],300,[0],[100,0]))
        self.assertTrue(model.is_symlink())
        self.assertEqual(model.read_bytes(),b'preserved model')

    def test_dedupe_keeps_installed_hardlink_and_does_not_claim_shared_blocks(self):
        import os
        source=self.root/'installed.bin';source.write_bytes(b'shared model')
        first=self.build/'_retained-models/first/model.bin';first.parent.mkdir(parents=True);os.link(source,first)
        other=self.file('_retained-models/second/model.bin',source.read_bytes())
        retention.dedupe_retained([])
        self.assertTrue(first.samefile(source));self.assertEqual(other.read_bytes(),source.read_bytes())
        third=self.build/'_retained-models/third/model.bin';third.parent.mkdir();os.link(source,third)
        self.assertEqual(retention.dedupe_retained([]),0)


if __name__ == '__main__':
    unittest.main()
