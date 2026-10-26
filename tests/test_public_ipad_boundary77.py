import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from public_source import selected
class PrivateIPadBoundaryTests(unittest.TestCase):
 def test_private_app_and_nested_accidental_copies_are_excluded(self):
  for name in ['mobile/AniCanto/VoiceRuntime.swift','ipad/Info.plist','iOS/App.swift','Sources/mobile/App.swift','tests/ipad/Private.swift','Resources/Private.xcodeproj/project.pbxproj','Sources/Private.xcarchive/Info.plist','docs/mobile/internal.md','Resources/device.mobileprovision','windows/private.ipa','Sources/iPadPurchase.swift','Sources/StoreKitRuntime.swift']:
   with self.subTest(name=name):self.assertFalse(selected(name))
 def test_desktop_code_and_required_public_notices_are_retained(self):
  for name in ['studio/backend.py','Resources/hardware-runtimes.json','Sources/StudioSettings.swift','windows/gpu.py','docs/IPAD-PRIVACY-POLICY.md','docs/DESKTOP-IPAD-RECOVERY-WORKFLOW.md','licenses/library/ios/license.md']:
   with self.subTest(name=name):self.assertTrue(selected(name))
if __name__=='__main__':unittest.main()
