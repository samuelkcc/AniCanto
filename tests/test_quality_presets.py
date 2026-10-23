"""Real Rust planner: quality labels never bypass memory/backend limits."""
import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows')]
import studio_core,native_setup

class QualityPresetsTests(unittest.TestCase):
 def plan(self,ram=64,platform='macos',backend='metal',vram=0):
  h=dict(platform=platform,architecture='aarch64' if platform=='macos' else 'x86_64',memoryGB=ram,backend=backend,acceleratorBudgetGB=ram*.75,acceleratorMemoryGB=vram,nativeWorkflowVersion=1)
  return studio_core.call('deployment',hardware=h,models=native_setup.catalog() if platform=='windows' else json.loads((ROOT/'Resources/model-options.json').read_text()))
 def test_apple_tiers_have_honest_quality_choices(self):
  for ram,recommendation in [(8,None),(16,None),(32,'quality'),(64,'quality')]:
   with self.subTest(ram=ram):
    p=self.plan(ram);self.assertEqual(p['recommendedPreset'],recommendation)
    self.assertEqual([q['id'] for q in p['qualityPresets']],['quality','balanced'])
    high=p['qualityPresets'][0];self.assertEqual(high['available'],ram>=32)
    self.assertEqual(high['requestedModels']['text'],'mlx:qwen3.5-35b-a3b:4bit' if ram>=64 else 'mlx:qwen3.5-9b:4bit');self.assertEqual(high['requestedModels']['voice'],'drama3-35b-4bit');self.assertEqual(high['requestedModels']['asr'],'asr-1.7b-bf16')
    if ram==32:self.assertTrue(high['memoryPressure']);self.assertIn('model-memory-pressure-swap-or-load-failure-possible',high['plan']['warnings'])
    for q in p['qualityPresets']:
     if q['available']:
      self.assertEqual(q['requestedModels']['voice'],q['plan']['roles']['voice'])
      if not q['memoryPressure']:self.assertLessEqual(q['estimatedPeakModelGB'],q['availableModelBudgetGB'])
 def test_presets_pin_one_asr_independent_of_old_installed_versions(self):
  models=json.loads((ROOT/'Resources/model-options.json').read_text())
  h=dict(platform='macos',architecture='aarch64',memoryGB=64,backend='metal',acceleratorBudgetGB=48)
  result=studio_core.call('deployment',hardware=h,models=models,installedModels=['asr-1.7b-8bit','asr-1.7b-4bit','asr-1.7b-bf16'],selectedModels={'asr':'asr-1.7b-8bit'})
  self.assertEqual(result['roles']['asr'],'asr-1.7b-8bit') # Current custom choice is not silently changed.
  for preset,ident in zip(result['qualityPresets'],['asr-1.7b-bf16','asr-1.7b-8bit']):
   self.assertEqual(preset['requestedModels']['asr'],ident)
   if not preset['available']:
    self.assertIn('model-license-review-required',preset['blockers']);self.assertFalse(preset['plan']['canDeployModels']);continue
   self.assertEqual(preset['plan']['roles']['asr'],ident)
   self.assertEqual([d['id'] for d in preset['plan']['downloads'] if d['id'].startswith('asr-')],[ident])
   self.assertEqual(preset['plan']['roles']['speech'],preset['plan']['roles']['referenceSpeech'])
 def test_nvidia_all_requested_vram_tiers_are_evaluated(self):
  for vram in (8,10,12,16,24,32):
   with self.subTest(vram=vram):
    p=self.plan(32,'windows','cuda',vram);self.assertEqual(p['engine'],'drama3')
    high,balance=p['qualityPresets']
    self.assertEqual(high['available'],vram>=12)
    if high['available']:
     self.assertEqual(high['plan']['roles']['voice'],'drama3-native-q2')
     self.assertEqual(high['plan']['voiceBackend'],'cpu')
     self.assertEqual(high['plan']['systemReserveGB'],8)
    self.assertEqual(balance['available'],vram>=12)
    if vram<12:self.assertIn('insufficient-gpu-memory',balance['blockers'])
    self.assertNotIn('drama3-small-iq3',json.dumps(p))
 def test_rocm_has_memory_guard_and_intel_does_not_claim_cuda(self):
  for vram in (8,12,16,24):
   p=self.plan(32,'windows','rocm',vram)
   self.assertEqual(p['qualityPresets'][1]['available'],vram>=12)
  p=self.plan(32,'windows','cpu',16)
  self.assertEqual(p['voiceBackend'],'cpu');self.assertFalse(p['hardwarePolicy']['gpuInferenceVerified'])
 def test_intel_mac_has_no_deployable_templates(self):
  models=json.loads((ROOT/'Resources/model-options.json').read_text())
  p=studio_core.call('deployment',hardware=dict(platform='macos',architecture='x86_64',memoryGB=64,backend='cpu'),models=models)
  self.assertFalse(p['hardwarePolicy']['intelMacSupported']);self.assertTrue(all(not r['available'] for r in p['qualityPresets']))
 def test_retired_installed_model_does_not_become_fallback(self):
  h=dict(platform='windows',architecture='x86_64',memoryGB=32,backend='cuda',acceleratorMemoryGB=16,nativeWorkflowVersion=1,nativeDramaSmallCPU=True,nativeDramaSmallCUDA=True)
  p=studio_core.call('deployment',hardware=h,models=native_setup.catalog(),installedModels=['drama3-small-iq3'],selectedModels={'voice':'drama3-small-iq3'})
  self.assertEqual(p['voice']['id'],'drama3-native-q2');self.assertEqual(p['engine'],'drama3')
  with self.assertRaises(ValueError):studio_core.call('deployment',hardware=h,models=native_setup.catalog(),requestedModels={'voice':'drama3-small-iq3'})
if __name__=='__main__':unittest.main()
