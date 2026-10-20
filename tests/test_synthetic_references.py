"""Distributable fallback references must be synthetic, attributable and intact."""
import hashlib,json,sys,unittest,wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import release_notices
class SyntheticReferenceTests(unittest.TestCase):
 def test_entire_bank_is_synthetic_with_exact_recording_hashes(self):
  bank=ROOT/'Resources/natural-voices';data=json.loads((bank/'catalog.json').read_text());self.assertEqual(data['revision'],3);self.assertEqual(len(data['voices']),7)
  for row in data['voices']:
   self.assertTrue(row['synthetic']);self.assertEqual(row['license'],'CC0-1.0');self.assertNotIn('speaker',row);self.assertGreater(row['pitchHz'],70)
   p=bank/row['file'];self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),row['sha256'])
   with wave.open(str(p)) as f:self.assertAlmostEqual(f.getnframes()/f.getframerate(),row['seconds'],places=3)
  self.assertEqual({p.name for p in bank.glob('*.wav')},{v['file'] for v in data['voices']})
  self.assertFalse(list(bank.glob('CommonVoice*')))
 def test_cantonese_references_derive_only_from_own_synthetic_mixtures(self):
  bank=ROOT/'Resources/natural-voices';voices={v['id']:v for v in json.loads((bank/'catalog.json').read_text())['voices']};proof=json.loads((bank/'cantonese-generation.json').read_text())
  self.assertFalse(proof['humanReferenceInputs']);self.assertEqual(len(proof['rows']),4)
  for row in proof['rows']:
   self.assertEqual(row['sha256'],voices[row['id']]['sha256']);self.assertEqual(row['referenceSHA256'],voices[row['referenceId']]['sha256']);self.assertTrue(voices[row['referenceId']]['synthetic'])
   self.assertEqual(row['modelRevision'],'48b1a0169a28582a8984402f82cf438d3bfa6aca');self.assertEqual(row['gsvVersion'],'v2ProPlus')
   for token in ['唔錯','我哋','慢慢傾','一齊出發']:self.assertIn(token,row['qualityCheck']['transcript'])
   self.assertTrue(row['qualityCheck']['finite']);self.assertLess(row['qualityCheck']['peak'],.98)
 def test_notice_distinguishes_recording_rights_from_generator_licences(self):
  text=(ROOT/'Resources/natural-voices/NOTICE.txt').read_text();self.assertIn('rights it holds',text);self.assertIn('does not relicense upstream models',text)
if __name__=='__main__':unittest.main()
