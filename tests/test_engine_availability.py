import sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).parents[1];sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows')]
from engine_availability import require
class EngineAvailabilityTests(unittest.TestCase):
 def test_cosy_is_windows_cuda_only(self):
  for platform,backend in [('darwin','metal'),('win32','rocm'),('win32','cpu'),('win32','xpu')]:
   with self.subTest(platform=platform,backend=backend),self.assertRaisesRegex(ValueError,'NVIDIA'):require('cosyvoice3',platform=platform,backend=backend)
  require('cosyvoice3',platform='win32',backend='cuda')
 def test_unprobed_windows_requires_a_physical_nvidia_adapter(self):
  with patch('gpu.adapters',return_value=[dict(Name='AMD Radeon RX 9070')]):
   with self.assertRaises(ValueError):require('cosyvoice3',platform='win32')
  with patch('gpu.adapters',return_value=[dict(Name='NVIDIA GeForce RTX 4090')]):require('cosyvoice3',platform='win32')
 def test_other_engines_keep_their_existing_platform_policy(self):
  for engine in ['drama3','gpt-sovits','gpt-sovits-v2','voxcpm2','wsyue']:require(engine,platform='win32',backend='rocm')
