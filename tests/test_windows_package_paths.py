import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_portable_windows import validate_payload_paths


class WindowsPackagePathsTests(unittest.TestCase):
    def test_license_notice_paths_are_windows_safe_and_evidence_is_present(self):
        evidence = json.loads((ROOT / 'licenses/ffmpeg/notice-evidence.json').read_text())
        for source in evidence['sources']:
            for document in source['documents']:
                name = document['path']
                validate_payload_paths({name: ROOT / name})

    def test_rejects_colon_and_case_collisions_before_launcher_build(self):
        with tempfile.TemporaryDirectory() as folder:
            good = Path(folder) / 'COPYING'
            good.write_text('licence evidence')
            with self.assertRaisesRegex(ValueError, 'invalid-package-path'):
                validate_payload_paths({'shared/licenses/https:--example/COPYING': good})
            with self.assertRaisesRegex(ValueError, 'windows-package-path-collision'):
                validate_payload_paths({'shared/Licenses/COPYING': good, 'shared/licenses/COPYING': good})


if __name__ == '__main__':
    unittest.main()
