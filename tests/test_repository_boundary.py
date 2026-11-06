import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from repository_boundary import remote_repository, validate_paths


class RepositoryBoundaryTests(unittest.TestCase):
    def test_remote_urls_bind_the_exact_repository(self):
        for value in ['https://github.com/samuelkcc/AniCanto-iOS.git', 'git@github.com:samuelkcc/AniCanto-iOS.git']:
            self.assertEqual(remote_repository(value), 'samuelkcc/AniCanto-iOS')
        with self.assertRaises(ValueError):
            remote_repository('https://github.com.evil.example/samuelkcc/AniCanto')

    def test_public_tree_rejects_private_code_at_multiple_depths(self):
        for value in ['mobile/App.swift', 'Sources/mobile/App.swift', 'nested/App.xcodeproj/project.pbxproj',
                      '.private-mobile-repository.json', 'Sources/StoreKitRuntime.swift', 'tests/test_mobile_fixture.py']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_paths([value], 'public-desktop')
        validate_paths(['Sources/Main.swift', 'studio/backend.py', 'windows/desktop_state.py'], 'public-desktop')

    def test_private_backup_rejects_desktop_media_weights_and_credentials(self):
        for value in ['windows/desktop.py', 'studio/backend.py', 'mobile/recording.wav', 'mobile/weights.safetensors', 'signing.p12']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_paths([value], 'private-mobile')
        validate_paths(['mobile/AniCantoApp/WelcomeView.swift', 'mobile/AniCanto-iPad.xcodeproj/project.pbxproj'], 'private-mobile')
