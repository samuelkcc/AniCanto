"""Keep original desktop scenes rebuildable without publishing private mobile art."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from public_source import selected,findings,ACTIVITY_IMAGES,public_text
class PublicActivitySourcesTests(unittest.TestCase):
 def test_exact_rest_files_are_selected_and_match(self):
  for theme in ['studio','ocean','energy','ninja','retro','forest','future','mint','moonflower']:
   name='studio/web/assets/assistant-activities/corrections/'+theme+'-rest-262.png'
   self.assertIn(name,ACTIVITY_IMAGES);self.assertTrue(selected(name));self.assertEqual(findings((ROOT/name).read_bytes(),name),[])
 def test_unknown_and_mobile_assets_are_excluded(self):
  for name in ['studio/web/assets/assistant-activities/unknown.png','studio/web/assets/cache.json','mobile/StudioTheme/standby/studio.png','docs/IPAD-PRIVACY-POLICY.md']:
   self.assertFalse(selected(name),name)
 def test_corrupt_activity_bytes_fail(self):
  self.assertIn('activity-asset-hash-mismatch',findings(b'invalid','studio/web/assets/assistant-activities/corrections/studio-rest-262.png'))
 def test_shared_record_redaction_does_not_change_legal_text(self):
  raw=(str(Path.home())+'/Development/project').encode()
  cleaned=public_text(raw,'docs/RECOVERY-WORKFLOW-CONTRACT.json',ROOT)
  self.assertNotIn(str(Path.home()).encode(),cleaned)
  self.assertEqual(public_text(raw,'licenses/vendor/LICENSE',ROOT),raw)
 def test_common_guide_is_exported(self):
  self.assertTrue(selected('docs/APPLICATION-USER-GUIDE.json'));self.assertTrue(selected('docs/USER-GUIDE-MAINTENANCE.md'))
if __name__=='__main__':unittest.main()
