import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'windows'))
from memory_plan import pools,fit_model

class MemoryPlanTests(unittest.TestCase):
 def test_nvidia_cpu_drama_and_gpu_text_use_separate_pools(self):
  plan=dict(hardware=dict(memoryGB=32,acceleratorMemoryGB=16,backend='cuda'),systemReserveGB=8,
            voiceBackend='cpu',roles=dict(voice='drama3-native-q2',text='qwen3.5:9b'),
            downloads=[dict(id='drama3-native-q2',estimatedMemoryGB=22),dict(id='qwen3.5:9b',estimatedMemoryGB=9)])
  result=pools(plan)
  self.assertEqual(result['system']['peak'],22)
  self.assertEqual(result['gpu']['peak'],9)
  self.assertEqual(result['system']['budget'],24)
  self.assertEqual(result['gpu']['budget'],12.8)
 def test_igpu_uses_system_ram(self):
  hardware=dict(memoryGB=32,acceleratorMemoryGB=0,backend='cpu')
  self.assertEqual(fit_model(dict(id='drama3-native-q2',estimatedMemoryGB=22),hardware),(True,'system'))
  self.assertEqual(fit_model(dict(id='huge',estimatedMemoryGB=26),hardware),(False,'system'))
 def test_cuda_only_cosy_and_gpu_budget(self):
  cosy=dict(id='cosy-native-0.5b',engine='cosyvoice3',estimatedMemoryGB=7)
  self.assertEqual(fit_model(cosy,dict(memoryGB=32,acceleratorMemoryGB=16,backend='rocm')),(False,'requires-nvidia'))
  self.assertEqual(fit_model(cosy,dict(memoryGB=32,acceleratorMemoryGB=16,backend='cuda')),(True,'gpu'))
  self.assertEqual(fit_model(dict(id='qwen',estimatedMemoryGB=14),dict(memoryGB=32,acceleratorMemoryGB=16,backend='cuda')),(False,'gpu'))

if __name__=='__main__':unittest.main()
