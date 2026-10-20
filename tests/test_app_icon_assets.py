"""The desktop host embeds RGBA8 pixels; RGBA16 crashes at launch."""
import struct
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AppIconAssetsTests(unittest.TestCase):
    def test_desktop_png_icons_are_rgba8(self):
        for name in ('Resources/app-icon-art.png', 'Resources/AniCanto-icon.png',
                     'studio/src-tauri/icons/icon.png'):
            with self.subTest(name=name):
                header = (ROOT/name).read_bytes()[:26]
                self.assertEqual(header[:8], b'\x89PNG\r\n\x1a\n')
                self.assertEqual(struct.unpack('>IIBB', header[16:26]),
                                 (1024, 1024, 8, 6))


if __name__ == '__main__':
    unittest.main()
