import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from public_source import selected
class PrivateIPadBoundaryTests(unittest.TestCase):
 def test_private_app_and_nested_accidental_copies_are_excluded(self):
  for name in ['docs/IPAD-PRIVACY-POLICY.md','docs/IPAD-PRIVACY-POLICY.zh-HK.md','docs/IPAD-PRIVACY-POLICY.zh-CN.md','docs/IPAD-PRIVACY-POLICY.ja.md','mobile/AniCanto/VoiceRuntime.swift','ipad/Info.plist','iOS/App.swift','Sources/mobile/App.swift','tests/ipad/Private.swift','Resources/Private.xcodeproj/project.pbxproj','Sources/Private.xcarchive/Info.plist','docs/mobile/internal.md','Resources/device.mobileprovision','windows/private.ipa','Sources/iPadPurchase.swift','Sources/StoreKitRuntime.swift']:
   with self.subTest(name=name):self.assertFalse(selected(name))
 def test_desktop_code_and_required_public_notices_are_retained(self):
  for name in ['studio/backend.py','Resources/hardware-runtimes.json','Sources/StudioSettings.swift','windows/gpu.py','docs/DESKTOP-IPAD-RECOVERY-WORKFLOW.md','licenses/library/ios/license.md']:
   with self.subTest(name=name):self.assertTrue(selected(name))

class PublicDesktopIndexTests(unittest.TestCase):
 def test_export_projects_the_public_index_and_excludes_mobile_policy(self):
  import tempfile
  from public_source import export
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'docs').mkdir();(root/'scripts').mkdir()
   (root/'docs/README.md').write_text('Internal counterpart index, not a public product page.')
   (root/'scripts/public-desktop-index.md').write_text('# Desktop documentation\nMac and Windows.\n')
   (root/'docs/IPAD-PRIVACY-POLICY.md').write_text('Separate mobile policy.')
   output=root/'.build/public-review/test';result=export(root,output)
   self.assertTrue(result['created']);self.assertEqual((output/'docs/README.md').read_text(),'# Desktop documentation\nMac and Windows.\n');self.assertFalse((output/'docs/IPAD-PRIVACY-POLICY.md').exists())

if __name__=='__main__':unittest.main()
