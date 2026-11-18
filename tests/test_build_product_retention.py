"""Verify the one-version product rule without owner data."""
import importlib.util
import json
import plistlib
import sys
import tempfile
import unittest
import zipfile
import io
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import build_product_retention as product


class ProductTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        (self.root/'VERSION.json').write_text('{"build":"446"}')
        current=self.root/'.build/testflight465/AniCanto.xcarchive';current.mkdir(parents=True)
        (current/'Info.plist').write_bytes(plistlib.dumps({'ApplicationProperties':{'CFBundleVersion':'465','CFBundleIdentifier':'com.sckc.anicanto'}}))
        self.current=current;self.plan=self.root/'plan.json'

    def tearDown(self):self.temp.cleanup()

    def app(self, build, desktop=False):
        path=self.root/f'.build/old{build}/AniCanto.app';path.mkdir(parents=True)
        info=path/('Contents/Info.plist' if desktop else 'Info.plist');info.parent.mkdir(exist_ok=True)
        info.write_bytes(plistlib.dumps(dict(CFBundleVersion=str(build),CFBundleIdentifier='com.sckc.anicanto')))
        return path

    def test_old_products_only_and_code_is_preserved(self):
        old=self.app(464);(old/'module.py').write_text('unique old source')
        movie=self.root/'.build/old464/owner.mp4';movie.write_bytes(b'owner video')
        sdk=self.root/'.build/old464/library.c';sdk.write_text('required SDK')
        result=product.scan(self.root,self.plan)
        self.assertEqual(len(result['files']),1)
        product.execute(self.root,self.plan)
        self.assertTrue(old.exists())
        product.execute(self.root,self.plan,True)
        self.assertFalse(old.exists());self.assertTrue(self.current.exists());self.assertTrue(movie.exists());self.assertTrue(sdk.exists())
        self.assertEqual([p.read_text() for p in (self.root/'.build/_retention-archive').rglob('module.py')],['unique old source'])

    def test_platforms_have_independent_latest_versions(self):
        old=self.app(445,True);new=self.app(446,True);future=self.app(466)
        rows=product.scan(self.root,self.plan)['files']
        self.assertEqual([r['path'] for r in rows],[str(old.relative_to(self.root))])
        self.assertTrue(new.exists());self.assertTrue(future.exists())

    def test_changed_product_blocks_every_removal(self):
        old=self.app(464);product.scan(self.root,self.plan);(old/'changed.json').write_text('{}')
        with self.assertRaises(ValueError):product.execute(self.root,self.plan,True)
        self.assertTrue(old.exists())

    def test_linked_active_input_and_unknown_identity_are_kept(self):
        old=self.app(464);deps=self.root/'mobile/Dependencies';deps.mkdir(parents=True)
        (deps/'active').symlink_to(old)
        unknown=self.root/'.build/unknown.app';unknown.mkdir()
        self.assertEqual(product.scan(self.root,self.plan)['files'],[])

    def test_old_windows_payload_is_distinct_from_an_owner_zip(self):
        path=self.root/'.build/windows/release/0.25.53/payload.zip';path.parent.mkdir(parents=True)
        with zipfile.ZipFile(path,'w') as archive:
            archive.writestr('VERSION.json','{"build":"445","version":"0.25.53"}')
            archive.writestr('shared/worker.py','application worker')
        owner=path.with_name('owner.zip')
        with zipfile.ZipFile(owner,'w') as archive:archive.writestr('video.mp4','owner media')
        rows=product.scan(self.root,self.plan)['files']
        self.assertEqual([r['path'] for r in rows],[str(path.relative_to(self.root))])
        product.execute(self.root,self.plan,True)
        self.assertFalse(path.exists());self.assertTrue(owner.exists())

    def test_embedded_windows_package_identity(self):
        data=io.BytesIO()
        with zipfile.ZipFile(data,'w') as archive:
            archive.writestr('VERSION.json','{"build":"445"}')
            archive.writestr('shared/worker.py','application worker')
        exe=self.root/'.build/old.exe';exe.write_bytes(b'MZ fixture'+data.getvalue()+b'PE suffix')
        self.assertEqual(product.product(exe),dict(platform='desktop',build=445))

    def test_pending_distribution_is_separate_from_current_installation(self):
        pending=self.root/'dist/pending-445/AniCanto.app/Contents';pending.mkdir(parents=True)
        (pending/'Info.plist').write_bytes(plistlib.dumps(dict(CFBundleVersion='445',CFBundleIdentifier='com.sckc.cantosync.studio')))
        normal=self.root/'dist/AniCanto.app/Contents';normal.mkdir(parents=True)
        (normal/'Info.plist').write_bytes(plistlib.dumps(dict(CFBundleVersion='446',CFBundleIdentifier='com.sckc.cantosync.studio')))
        result=product.scan(self.root,self.plan)
        self.assertEqual([r['path'] for r in result['files']],['dist/pending-445/AniCanto.app'])
        product.execute(self.root,self.plan,True)
        self.assertTrue(normal.exists());self.assertFalse(pending.exists())


if __name__=='__main__':unittest.main()
