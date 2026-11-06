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

    def test_library_licences_build_rules_and_patches_are_rescued_with_origins(self):
        files=[self.file('old/'+name,b'source '+name.encode()) for name in ['rules.mak','Makefile.am','configure','fix.patch','COPYING.LIB','LICENSE','CMakeLists.txt']]
        self.assertTrue(retention.rescue(self.build/'old',{},[],300,[10000],[10000,0]))
        rows=[json.loads(line) for line in (self.build/'_retention-archive/source-origins.jsonl').read_text().splitlines()]
        self.assertEqual({r['source'] for r in rows},{str(p.relative_to(self.build)) for p in files})
        for row in rows:self.assertEqual(hashlib.sha256((self.build/row['archive']).read_bytes()).hexdigest(),row['sha256'])

    def test_equal_rescued_content_keeps_both_original_paths(self):
        a=self.file('old/one/module.c',b'shared source');b=self.file('old/two/module.c',b'shared source')
        self.assertTrue(retention.rescue(self.build/'old',{},[],300,[10000],[10000,0]))
        rows=[json.loads(line) for line in (self.build/'_retention-archive/source-origins.jsonl').read_text().splitlines()]
        self.assertEqual({r['source'] for r in rows},{str(a.relative_to(self.build)),str(b.relative_to(self.build))})
        self.assertEqual(len({r['archive'] for r in rows}),1)

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

    def retirement_plan(self, path, **changes):
        row = dict(path=str(path.relative_to(self.build)), bytes=path.stat().st_size,
                   mtimeNs=path.stat().st_mtime_ns, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                   url='https://huggingface.co/example/model/resolve/'+'a'*40+'/weights.bin',
                   revision='a'*40, httpStatus=200)
        row.update(changes)
        plan = self.root/'retirement.json'
        plan.write_text(json.dumps({'files':[row]}))
        return plan

    def test_retired_download_dry_then_apply_keeps_installed_hardlink(self):
        import os
        old = self.file('_retained-models/old/weights.bin',b'downloadable')
        installed = self.root/'installed.bin';os.link(old,installed)
        plan = self.retirement_plan(old)
        self.assertEqual(retention.retire_downloads(plan,[],False),12)
        self.assertTrue(old.exists())
        retention.retire_downloads(plan,[],True)
        self.assertFalse(old.exists());self.assertEqual(installed.read_bytes(),b'downloadable')

    def test_retirement_rejects_changed_unverified_and_nonarchive_paths(self):
        old = self.file('_retained-models/old/weights.bin',b'first')
        plan = self.retirement_plan(old);old.write_bytes(b'other')
        with self.assertRaises(ValueError):retention.retire_downloads(plan,[],True)
        plan = self.retirement_plan(old,httpStatus=404)
        with self.assertRaises(ValueError):retention.retire_downloads(plan,[],True)
        other = self.file('active/weights.bin',b'active')
        with self.assertRaises(ValueError):retention.retire_downloads(self.retirement_plan(other),[],True)
        self.assertTrue(old.exists());self.assertTrue(other.exists())

    def test_retirement_protects_active_dependency_symlink(self):
        old = self.file('_retained-models/old/weights.bin',b'downloadable')
        link = self.root/'mobile/Dependencies/weights.bin';link.parent.mkdir(parents=True);link.symlink_to(old)
        with self.assertRaises(ValueError):retention.retire_downloads(self.retirement_plan(old),[],True)
        self.assertEqual(link.read_bytes(),b'downloadable')

    def test_nested_product_budget_preserves_source_and_unknown_products(self):
        import plistlib
        base = self.build/'closure340'
        for build in [340,394,395,396]:
            p = base/f'qa{build}/AniCanto.app';p.mkdir(parents=True)
            (p/'Info.plist').write_bytes(plistlib.dumps({'CFBundleVersion':str(build)}))
        (base/'source').mkdir();(base/'source/live.swift').write_text('live')
        (base/'unknown.app').mkdir()
        self.assertEqual({b for _,b in retention.nested_products(base,{395,396,397,398,399})},{340,394})
        self.assertTrue((base/'source/live.swift').exists());self.assertTrue((base/'unknown.app').exists())

    def test_loose_recording_blocks_normal_retention_before_model_move(self):
        old = self.file('old/recording.wav',b'unique recording')
        model = self.file('old/weights.bin',b'weights')
        self.assertFalse(retention.rescue(old.parent,{},[],300,[100],[100,0]))
        self.assertFalse(model.is_symlink());self.assertTrue(old.exists())

    def test_nested_apply_removes_only_old_product_and_rescues_unique_source(self):
        import plistlib
        (self.root/'VERSION.json').write_text('{"build":"398"}')
        store=self.build/'testflight399/AniCanto.xcarchive';store.mkdir(parents=True)
        (store/'Info.plist').write_bytes(plistlib.dumps({'ApplicationProperties':{'CFBundleVersion':'399'}}))
        old=self.build/'closure340/release394/AniCanto.app';old.mkdir(parents=True)
        (old/'Info.plist').write_bytes(plistlib.dumps({'CFBundleVersion':'394'}))
        (old/'adapter.py').write_text('unique archived adapter')
        sdk=self.file('closure340/release394/source/library.c',b'required library source')
        result=retention.prune_nested_products([],True)
        self.assertEqual(result['retainedBuilds'],[395,396,397,398,399])
        self.assertEqual(result['products'],1);self.assertFalse(old.exists())
        self.assertEqual(sdk.read_bytes(),b'required library source')
        rescued=list((self.build/'_retention-archive').rglob('adapter.py'))
        self.assertEqual([p.read_text() for p in rescued],['unique archived adapter'])


if __name__ == '__main__':
    unittest.main()
