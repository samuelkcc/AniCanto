"""Legal resource delivery and consent boundary regressions, without inference."""
import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'scripts'),str(ROOT/'studio'),str(ROOT/'windows')]
import release_notices,use_terms

class ReleaseLicensingTests(unittest.TestCase):
    def test_clone_replaces_application_license_without_relicensing_dependencies(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'Licenses/vendor').mkdir(parents=True)
            notice=root/'Licenses/vendor/LICENSE';notice.write_bytes(b'MIT vendor grant: preserve this notice')
            (root/'Licenses/AniCanto-GPL-3.0.txt').write_text('old application license')
            release_notices.install(root)
            self.assertFalse((root/'Licenses/AniCanto-GPL-3.0.txt').exists())
            self.assertEqual((root/'Licenses/AniCanto-MIT.txt').read_bytes(),(ROOT/'LICENSE').read_bytes())
            self.assertEqual(notice.read_bytes(),b'MIT vendor grant: preserve this notice')
            self.assertEqual((root/'licenses/history/CantoSync-MIT-through-0.24.13.txt').read_bytes(),(ROOT/'licenses/history/CantoSync-MIT-through-0.24.13.txt').read_bytes())
            self.assertEqual((root/'USE-TERMS.json').read_bytes(),(ROOT/'Resources/USE-TERMS.json').read_bytes())
            rows=release_notices.records(root)
            missing=[name for row in rows for name in row['files'] if not (root/name).is_file()]
            self.assertEqual(missing,[])
    def test_acceptance_requires_explicit_current_document_and_can_be_withdrawn(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);doc=use_terms.document()
            for params in ({'accepted':True,'sha256':'old'},{'accepted':'true','sha256':doc['sha256']},{'sha256':doc['sha256']}):
                with self.assertRaises(ValueError):use_terms.accept(root,params)
                self.assertFalse(use_terms.accepted(root))
            use_terms.accept(root,dict(accepted=True,sha256=doc['sha256']))
            self.assertTrue(use_terms.accepted(root))
            changed=dict(doc,sha256='new-document-hash')
            with patch.object(use_terms,'document',return_value=changed):self.assertFalse(use_terms.accepted(root))
            use_terms.revoke(root);self.assertFalse(use_terms.accepted(root))
            with self.assertRaises(ValueError):use_terms.require(root)
    def test_unaccepted_start_cannot_create_job_or_mutate_queue(self):
        from backend import Studio
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'fixture.mp4';source.write_bytes(b'synthetic')
            app=Studio(root,ROOT/'Resources',helper=root/'helper')
            ident=app.dispatch('add',dict(paths=[str(source)]))['selected']
            before=json.loads(json.dumps(app.row(ident)))
            with self.assertRaisesRegex(ValueError,'terms'):app.dispatch('start',dict(id=ident))
            self.assertEqual(app.row(ident),before)
            self.assertFalse((root/'requests').exists())

if __name__=='__main__':unittest.main()
