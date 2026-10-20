import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'Resources'))
import source_access


class SourceAccessTests(unittest.TestCase):
    def test_google_drive_path_is_remote(self):
        self.assertTrue(source_access.cloud_or_remote(
            r'G:\My Drive\Video\《One Piece》-0799.mkv',
            r'C:\Users\Samuel Chen\AppData\Local\CantoSync-Windows'))

    def test_probe_exposes_ffprobe_stderr(self):
        with patch.object(source_access.subprocess, 'run', return_value=subprocess.CompletedProcess(
                [], 1, b'', b'Invalid data found when processing input')):
            with self.assertRaisesRegex(RuntimeError, 'Invalid data found'):
                source_access.probe('video.mkv', 'ffprobe')

    def test_failed_remote_probe_retries_local_copy_and_preserves_original(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root/'original.mkv'
            original.write_bytes(b'video source bytes')
            def probe(path, _tool):
                if path == original:
                    raise RuntimeError('Cloud drive read failed')
                self.assertEqual(path.read_bytes(), original.read_bytes())
                return b'{"format":{}}'
            with patch.object(source_access, 'probe', side_effect=probe), \
                 patch.object(source_access, 'cloud_or_remote', return_value=True):
                cached, metadata = source_access.accessible(original, 'ffprobe', root)
            self.assertNotEqual(cached, original)
            self.assertEqual(cached.read_bytes(), original.read_bytes())
            self.assertEqual(metadata, b'{"format":{}}')
            self.assertEqual(original.read_bytes(), b'video source bytes')

    def test_cloud_copy_recovers_from_early_eof(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root/'episode.mkv'
            original.write_bytes(b'complete video bytes')
            real_open = Path.open
            opened = 0
            class EarlyEnd:
                def __init__(self, stream):
                    self.stream = stream
                    self.calls = 0
                def read(self, size):
                    self.calls += 1
                    if self.calls == 1:
                        return self.stream.read(8)
                    return b''
                def close(self): self.stream.close()
                def seek(self, position): return self.stream.seek(position)
            def cloud_open(path, *args, **kwargs):
                nonlocal opened
                stream = real_open(path, *args, **kwargs)
                if path == original and args[0] == 'rb':
                    opened += 1
                    return EarlyEnd(stream) if opened == 1 else stream
                return stream
            def probe(path, _tool):
                if path == original: raise RuntimeError('Cloud stream ended early')
                self.assertEqual(path.read_bytes(), b'complete video bytes')
                return b'{"format":{}}'
            with patch.object(source_access, 'probe', side_effect=probe), \
                 patch.object(source_access, 'cloud_or_remote', return_value=True), \
                 patch.object(Path, 'open', cloud_open), \
                 patch.object(source_access.time, 'sleep') as pause:
                cached, _ = source_access.accessible(original, 'ffprobe', root)
            self.assertEqual(cached.read_bytes(), original.read_bytes())
            self.assertEqual(opened, 2)
            pause.assert_called_once_with(3)

    def test_local_failure_reports_actual_error_without_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'bad.mkv'
            source.write_bytes(b'bad')
            with patch.object(source_access, 'probe', side_effect=RuntimeError('Unsupported video')):
                with self.assertRaisesRegex(RuntimeError, 'Unsupported video'):
                    source_access.accessible(source, 'ffprobe', directory)
            self.assertFalse((Path(directory)/'cache'/'source-media').exists())


if __name__ == '__main__':
    unittest.main()
