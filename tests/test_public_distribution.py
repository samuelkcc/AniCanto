"""Privacy and notice delivery boundaries, without downloading or inference."""
import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'Resources')]
import public_source,source_materials,model_licenses

class PublicSourceTests(unittest.TestCase):
    def test_source_assets_and_nonstandard_legal_filenames_are_retained(self):
        for path in ['Resources/tts-vendor/drama3-small/audio.cpp-LICENSE',
                     'Resources/tts-vendor/wsyue/matcha/VERSION',
                     'Resources/tts-vendor/wsyue/matcha/core.pyx',
                     'Resources/tts-vendor/wsyue/tokenizer/data.tiktoken',
                     'studio/src-tauri/Info.plist']:
            self.assertTrue(public_source.selected(path),path)
        self.assertTrue(public_source.selected('Resources/pet-studio.png'))
        self.assertFalse(public_source.selected('Resources/private-frame.png'))
        self.assertFalse(public_source.selected('docs/user-screenshot.png'))
    def fixture(self,root):
        (root/'LICENSE').write_text('Original application MIT grant')
        (root/'Resources').mkdir();(root/'Resources/worker.py').write_text('print("local worker")\n')
        (root/'licenses').mkdir();(root/'licenses/VENDOR-NOTICE.txt').write_text('Original third-party copyright')

    def test_export_is_allowlisted_and_never_relabels_vendor_notice(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.fixture(root)
            for name in ['dist/movie.mp4','.build/private.json','windows/tools/utility.exe','Resources/wheels/runtime.whl','Resources/private.wav','docs/archive/private.md']:
                file=root/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(b'private excluded material')
            out=root/'.build/public-review/candidate'
            report=public_source.export(root,out)
            self.assertTrue(report['created']);self.assertFalse(report['published'])
            self.assertEqual((out/'licenses/VENDOR-NOTICE.txt').read_text(),'Original third-party copyright')
            self.assertFalse((out/'dist').exists());self.assertFalse((out/'windows/tools').exists());self.assertFalse((out/'Resources/private.wav').exists())
            self.assertEqual(set(r['path'] for r in json.loads((out/'SOURCE-MANIFEST.json').read_text())['files']),{'LICENSE','Resources/worker.py','licenses/VENDOR-NOTICE.txt'})

    def test_bad_source_fails_before_export_creation(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.fixture(root);out=root/'.build/public-review/candidate'
            (root/'Resources/worker.py').write_bytes(b'MZ'+b'pretend executable')
            report=public_source.export(root,out)
            self.assertFalse(report['created']);self.assertFalse(out.exists())
            self.assertIn('executable-disguised-as-source',report['errors'][0]['reasons'])

    def test_symlink_and_private_path_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.fixture(root);(root/'Resources/escape.py').symlink_to(root/'LICENSE')
            report=public_source.export(root,root/'.build/public-review/candidate')
            self.assertFalse(report['created'])
        self.assertIn('private-user-path',public_source.findings(b'/'+b'Users/'+b'private-person/movie.mp4','fixture.py'))
        self.assertIn('credential-or-private-key',public_source.findings(b'ghp_'+b'x'*36,'fixture.py'))

    def test_refuses_overwriting_checkout_or_existing_export(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.fixture(root)
            with self.assertRaises(ValueError):public_source.export(root,root)
            out=root/'.build/public-review/candidate';public_source.export(root,out)
            with self.assertRaises(ValueError):public_source.export(root,out)

    def test_source_material_checksum_is_not_optional(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'source.tar.gz').write_bytes(b'exact upstream source')
            digest=hashlib.sha256(b'exact upstream source').hexdigest()
            self.assertEqual(source_materials.checked_file(root,'source.tar.gz',digest),(root/'source.tar.gz').resolve())
            with self.assertRaises(ValueError):source_materials.checked_file(root,'source.tar.gz','0'*64)
            with self.assertRaises(ValueError):source_materials.checked_file(root,'../escape.tar.gz',digest)

class AuxiliaryNoticeTests(unittest.TestCase):
    def test_model_attribution_is_separate_from_adapter_license(self):
        with tempfile.TemporaryDirectory() as temp:
            dest=model_licenses.install_auxiliary_notices('Wespeaker/wespeaker-voxceleb-resnet34-LM',temp)
            record=json.loads((dest/'provenance.json').read_text())
            self.assertEqual(record['effectiveLicense'],'CC-BY-4.0')
            self.assertIn('WeSpeaker project',(dest/'NOTICE.txt').read_text())
            self.assertIn('https://creativecommons.org/licenses/by/4.0/',(dest/'NOTICE.txt').read_text())
            self.assertEqual(hashlib.sha256((dest/'README.md').read_bytes()).hexdigest(),record['documents'][0]['sha256'])

    def test_publisher_mit_evidence_is_preserved_and_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            dest=model_licenses.install_auxiliary_notices('KimberleyJSN/melbandroformer',temp)
            self.assertIn('pinned-publisher-license-and-weight-provenance-reviewed',(dest/'NOTICE.txt').read_text())
            self.assertIn('Permission is hereby granted',(dest/'Publisher-declared-MIT-terms.txt').read_text())
            self.assertIn('Kimberley',(dest/'NOTICE.txt').read_text())
        with tempfile.TemporaryDirectory() as temp,patch.object(model_licenses.hashlib,'sha256') as fake:
            fake.return_value.hexdigest.return_value='invalid'
            with self.assertRaisesRegex(ValueError,'integrity'):model_licenses.install_auxiliary_notices('Wespeaker/wespeaker-voxceleb-resnet34-LM',temp)
            self.assertFalse((Path(temp)/'AniCanto-LICENSES').exists())

    def test_distribution_register_does_not_claim_approval(self):
        record=json.loads((ROOT/'licenses/distribution-review.json').read_text())
        self.assertFalse(record['publicReleaseApproved'])
        if record['publicationAuthorized']:
            checkpoint=record['latestStatusCheckpoint']
            self.assertIn('otherwise keep private',checkpoint['conditionalAuthorization'])
            self.assertFalse(checkpoint['published'])
            policy=json.loads((ROOT/'Resources/PUBLIC-DISTRIBUTION.json').read_text())
            self.assertTrue(policy['authorizationConditions'])
            self.assertEqual(policy['repository']['visibility'],'private')
        self.assertEqual({b['id'] for b in record['blockers']} | {b['id'] for b in record.get('resolvedIssues',[])},{'B01','B02','B03','B04','B05'})
        self.assertNotIn('B02',{b['id'] for b in record['blockers']})

if __name__=='__main__':unittest.main()
