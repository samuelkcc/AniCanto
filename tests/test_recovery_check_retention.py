"""Protect unique work and pinned inputs when a completed recovery check expires."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import recovery_check_retention as retire
from generated_cache_retention import inventory


class RecoveryRetentionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.path=self.root/'.build/disaster-recovery-desktop-fixture'
        source=self.path/'materials/AniCanto/app.py';source.parent.mkdir(parents=True);source.write_text('original code')
        sha=hashlib.sha256(source.read_bytes()).hexdigest()
        (self.path/'materials/SOURCE-MATERIALS.json').write_text(json.dumps({'files':[{'path':'AniCanto/app.py','sha256':sha}]}))
        self.input=self.root/'source.tar.gz';self.input.write_bytes(b'checked source archive fixture')
        input_sha=hashlib.sha256(self.input.read_bytes()).hexdigest()
        receipt=dict(buildPassed=True,macProductVerifierPassed=True,windowsProductVerifierPassed=True,
                     ownerDataRead=False,ownerInstallationChanged=False,assetHashes={'source.tar.gz':input_sha},buildRecipeAdapters=[])
        (self.path/'receipt.json').write_text(json.dumps(receipt));self.plan=self.root/'plan.json'
        self.data=dict(path=str(self.path.relative_to(self.root)),inputs=[dict(name='source.tar.gz',path='source.tar.gz',sha256=input_sha)],
                       inventory=inventory(self.path),proofCopy='records/proof.json')
        self.plan.write_text(json.dumps(self.data))

    def tearDown(self):self.temp.cleanup()

    def test_dry_run_then_remove_keeps_source_archive_and_proof(self):
        retire.execute(self.root,self.plan);self.assertTrue(self.path.exists())
        retire.execute(self.root,self.plan,True)
        self.assertFalse(self.path.exists());self.assertTrue(self.input.exists())
        self.assertTrue(json.loads((self.root/'records/proof.json').read_text())['localPinnedInputsPreserved'])

    def test_a_unique_source_change_stops_removal(self):
        (self.path/'materials/AniCanto/app.py').write_text('unique user work')
        self.data['inventory']=inventory(self.path);self.plan.write_text(json.dumps(self.data))
        with self.assertRaises(ValueError):retire.execute(self.root,self.plan,True)
        self.assertTrue(self.path.exists())

    def test_a_missing_retained_archive_stops_removal(self):
        self.input.unlink()
        with self.assertRaises(ValueError):retire.execute(self.root,self.plan,True)
        self.assertTrue(self.path.exists())

    def test_an_owner_folder_is_not_a_generated_check_input(self):
        (self.path/'owner-videos').mkdir()
        with self.assertRaises(ValueError):retire.execute(self.root,self.plan,True)
        self.assertTrue(self.path.exists())


if __name__=='__main__':unittest.main()
