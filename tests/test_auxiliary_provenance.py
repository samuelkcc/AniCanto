"""Pinned model rights/evidence and sidecar delivery, without inference."""
import hashlib,json,sys,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'scripts')]
import model_licenses,ocr_licenses,release_notices
class AuxiliaryProvenanceTests(unittest.TestCase):
 def test_auxiliary_documents_match_and_all_gpt_tensors_have_verified_origins(self):
  rows=json.loads((ROOT/'licenses/auxiliary-models.json').read_text())['components']
  for row in rows:
   for doc in row['documents']:self.assertEqual(hashlib.sha256((ROOT/doc['path']).read_bytes()).hexdigest(),doc['sha256'])
   if row.get('conversionVerified'):
    self.assertTrue(row['weightSHA256']);self.assertTrue(row['upstreamWeightSHA256'])
    proof=next(d for d in row['documents'] if d['path'].endswith('conversion-evidence.json'))
    data=json.loads((ROOT/proof['path']).read_text());self.assertTrue(data['allConvertedTensorsAccountedFor']);self.assertEqual(data['mismatches'],[])
    self.assertFalse(data['inferenceWeightsChanged'])
 def test_declared_mit_terms_never_invent_a_holder_or_year(self):
  text=(ROOT/'licenses/common/Publisher-declared-MIT-terms.txt').read_text()
  self.assertNotIn('<year>',text);self.assertNotIn('Copyright (c) 2026',text);self.assertIn('Permission is hereby granted',text)
 def test_auxiliary_sidecars_preserve_original_data_and_separate_attribution(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);weights=root/'pytorch_model.bin';weights.write_bytes(b'original weights')
   path=model_licenses.install_auxiliary_notices('hfl/chinese-roberta-wwm-ext-large',root)
   self.assertEqual(weights.read_bytes(),b'original weights');self.assertTrue((path/'LICENSE').is_file());self.assertTrue((path/'conversion-evidence.json').is_file())
 def test_ocr_exact_wheel_models_are_linked_to_registry_and_complete_terms(self):
  row=json.loads((ROOT/'licenses/ocr-models.json').read_text());self.assertEqual(len(row['models']),3)
  for doc in row['documents']:self.assertEqual(hashlib.sha256((ROOT/doc['path']).read_bytes()).hexdigest(),doc['sha256'])
  registry=(ROOT/'licenses/ocr/RapidAI-model-registry.yaml').read_text()
  for model in row['models']:self.assertIn(model['sha256'],registry)
 def test_ocr_corruption_and_forged_evidence_fail_before_writing_notices(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);package=root/'package';package.mkdir();(package/'model.onnx').write_bytes(b'good')
   row=dict(documents=[],models=[dict(path='model.onnx',bytes=4,sha256=hashlib.sha256(b'good').hexdigest())])
   with patch.object(ocr_licenses,'evidence',return_value=(root,row)):
    result=ocr_licenses.install(root,package);self.assertTrue((result/'provenance.json').is_file())
    (package/'model.onnx').write_bytes(b'bad!')
    with self.assertRaisesRegex(ValueError,'Repair'):ocr_licenses.install(root,package)
   row['documents']=[dict(path='../escape',sha256='x')]
   with patch.object(ocr_licenses,'evidence',return_value=(root,row)):
    with self.assertRaisesRegex(ValueError,'path'):ocr_licenses.install(root,package)
 def test_release_about_includes_distinct_ocr_weight_notices(self):
  with tempfile.TemporaryDirectory() as d:
   rows=release_notices.install(Path(d));row=next(row for row in rows if row['name']=='RapidOCR model weights (Windows)')
   self.assertEqual(row['license'],'Apache-2.0');self.assertTrue(any('MODEL-LICENSES' in f for f in row['files']))
if __name__=='__main__':unittest.main()
