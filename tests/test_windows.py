"""PC policy and media tests; no assertion of Windows GPU model acceptance."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'windows'))
import gpu
import downloads
import jobs
import native_tts


class WindowsPolicyTests(unittest.TestCase):
    def test_nvidia_selected_over_integrated_intel(self):
        self.assertEqual(gpu.recommended([dict(Name='Intel UHD Graphics'), dict(Name='NVIDIA GeForce RTX 4090')]), 'nvidia')

    def test_supported_amd_not_similar_unsupported_model(self):
        for name in ['AMD Radeon RX 7900 XTX', 'AMD Radeon RX 9070 XT', 'AMD Radeon RX 9060 XT Graphics']:
            self.assertTrue(gpu.amd_supported(name), name)
        for name in ['AMD Radeon RX 7900 XT', 'AMD Radeon RX 7700 XT', 'AMD Radeon RX 6600', 'AMD Radeon RX 90700']:
            self.assertFalse(gpu.amd_supported(name), name)
        self.assertEqual(gpu.recommended([dict(Name='AMD Radeon RX 6600')]), 'cpu')

    def test_intel_arc_distinct_from_uhd(self):
        self.assertEqual(gpu.recommended([dict(Name='Intel Arc A770 Graphics')]), 'intel')
        self.assertEqual(gpu.recommended([dict(Name='Intel UHD Graphics')]), 'cpu')

    def test_model_memory_uses_dedicated_vram_only_for_supported_discrete_gpu(self):
        cases=[
            (0x10DE,'NVIDIA GeForce RTX 4090',24,'cuda'),
            (0x1002,'AMD Radeon RX 9070 XT',16,'rocm'),
        ]
        for vendor,name,capacity,backend in cases:
            hardware=dict(platform='windows',memoryGB=32,suggestedSetupBackend='nvidia' if backend=='cuda' else 'amd',
                          displayAdapters=[dict(vendorId=vendor,name=name,dedicatedMemoryGB=capacity)])
            with self.subTest(name=name),patch.object(gpu,'hardware_snapshot',return_value=hardware):
                planned=gpu.planning_hardware()
            self.assertEqual(planned['backend'],backend)
            self.assertEqual(planned['acceleratorMemoryGB'],capacity)
            self.assertFalse(planned['inferenceVerified'])

    def test_integrated_gpu_uses_system_memory_budget(self):
        for vendor,name in [(0x8086,'Intel UHD Graphics'),(0x1002,'AMD Radeon 780M Graphics')]:
            hardware=dict(platform='windows',memoryGB=32,suggestedSetupBackend='cpu',
                          displayAdapters=[dict(vendorId=vendor,name=name,dedicatedMemoryGB=0.5)])
            with self.subTest(name=name),patch.object(gpu,'hardware_snapshot',return_value=hardware):
                planned=gpu.planning_hardware()
            self.assertNotIn('acceleratorMemoryGB',planned)
            self.assertNotIn(planned.get('backend'),('cuda','rocm'))

    def test_gpu_kernel_failure_is_not_reported_as_working(self):
        fake = Mock()
        fake.cuda.is_available.return_value = False
        fake.xpu.is_available.return_value = False
        with patch.dict(sys.modules, {'torch': fake}):
            with self.assertRaisesRegex(RuntimeError, 'unavailable'):
                gpu.torch_probe(requested='cuda')

    def test_encoder_fallback_after_real_hardware_error(self):
        with patch.object(jobs, 'run', side_effect=[RuntimeError('driver unavailable'), b'', b'']), patch.object(jobs, 'ffmpeg', return_value='ffmpeg'):
            name = jobs.encode_movie(['ffmpeg', '-i', 'movie', 'out.mp4'], [dict(Name='NVIDIA RTX 4090')], 'auto', lambda *a: None)
        self.assertEqual(name, 'libx264')

    def test_invalid_nonfinite_timing_rejected(self):
        for row in [dict(start=float('nan'), end=2), dict(start=2,end=1), dict(start=-1,end=1)]:
            with self.assertRaises(ValueError):
                jobs.validated_cues([row])

    def test_changed_reference_transcript_invalidates_recording(self):
        with tempfile.TemporaryDirectory() as name:
            ref = Path(name)/'reference.wav'
            ref.write_bytes(b'fixture')
            profile = dict(id='A', reference=str(ref), promptText='hello', language='en')
            cue = dict(target='approved words')
            cfg = dict(engine='gpt',language='en')
            first = jobs.take_key(cue, profile, cfg)
            second = jobs.take_key(cue, dict(profile,promptText='different words'), cfg)
            self.assertNotEqual(first, second)

    def test_download_resume_server_ignoring_range_restarts_cleanly(self):
        with tempfile.TemporaryDirectory() as name:
            target = Path(name)/'model'
            target.with_name('model.partial').write_bytes(b'prefix')
            response = Mock(status=200)
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            response.read.side_effect = [b'complete bytes', b'']
            with patch('urllib.request.urlopen', return_value=response):
                downloads.download('https://example.org/model', target, hashlib.sha256(b'complete bytes').hexdigest())
            self.assertEqual(target.read_bytes(), b'complete bytes')

    def test_bad_download_sha_never_publishes(self):
        with tempfile.TemporaryDirectory() as name:
            target = Path(name)/'model'
            response = Mock(status=200)
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            response.read.side_effect = [b'bad', b'']
            with patch('urllib.request.urlopen', return_value=response):
                with self.assertRaises(ValueError):
                    downloads.download('https://example.org/model', target, '0'*64)
            self.assertFalse(target.exists())
            self.assertEqual(len(list(Path(name).glob('*.rejected-*'))), 1)

    def test_all_pc_manifest_files_have_size_and_sha(self):
        models = json.loads((ROOT/'windows/models.json').read_text())
        for key in ('qwen-small','qwen-large','cosy','gpt'):
            for row in models[key]['files']:
                self.assertEqual(len(row['sha256']),64)
                self.assertGreater(row['size'],0)
                self.assertNotIn('..',Path(row['path']).parts)

    def test_rejected_voice_attempts_remain_bounded_across_restart(self):
        import numpy as np
        with tempfile.TemporaryDirectory() as name:
            path=Path(name)/'take.wav'
            cfg=dict(engine='qwen',storage=name,items=[dict(text='hello',output=str(path),profile=dict(reference='fixture'))])
            with patch.object(native_tts,'load_model',return_value=(object(),dict(device='cpu'))), patch.object(native_tts,'take',return_value=(np.zeros(24000,dtype=np.float32),24000)) as generate:
                for _ in range(2):
                    with self.assertRaises(RuntimeError):native_tts.synthesize(cfg)
                self.assertEqual(generate.call_count,2)
            self.assertFalse(path.exists())
            self.assertFalse(json.loads(path.with_suffix('.health.json').read_text())['passed'])

    def test_verified_take_reuse_requires_matching_file_sha(self):
        import numpy as np
        with tempfile.TemporaryDirectory() as name:
            path=Path(name)/'take.wav'
            cfg=dict(engine='qwen',storage=name,items=[dict(text='hello',output=str(path),profile=dict(reference='fixture'))])
            samples=.1*np.sin(2*np.pi*220*np.arange(24000)/24000)
            with patch.object(native_tts,'load_model',return_value=(object(),dict(device='cpu'))), patch.object(native_tts,'take',return_value=(samples,24000)) as generate:
                native_tts.synthesize(cfg);native_tts.synthesize(cfg)
                self.assertEqual(generate.call_count,1)
                path.write_bytes(b'corrupt take')
                native_tts.synthesize(cfg)
                self.assertEqual(generate.call_count,2)
                self.assertTrue(json.loads(path.with_suffix('.health.json').read_text())['passed'])
                self.assertEqual(len(list(Path(name).glob('*.invalid-*.wav'))),1)


if __name__ == '__main__':
    unittest.main()
