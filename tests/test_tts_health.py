import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
from tts_health import problems

class TTSHealthTests(unittest.TestCase):
 def test_nonlexical_scream_preserved_but_japanese_dialogue_not(self):
  from dubbing import is_vocalization
  self.assertTrue(is_vocalization(dict(japanese='うぃぃぃぃ!',cantonese='啊！')))
  self.assertFalse(is_vocalization(dict(japanese='やめろ!',cantonese='住手！')))
  self.assertFalse(is_vocalization(dict(japanese='いい',cantonese='好呀')))
  self.assertFalse(is_vocalization(dict(japanese='うぃぃぃ!',cantonese='住手！')))
 def test_quiet_empty_and_nonfinite_are_rejected(self):
  self.assertIn('no-audible-voice',problems(np.zeros(24000),24000,'你好'))
  self.assertIn('invalid-audio',problems(np.array([np.nan]),24000))
 def test_long_nonterminating_and_clipped_signal_is_rejected(self):
  errors=problems(np.ones(24*24000),24000,'香吉',tokens=320,budget=320)
  self.assertIn('runaway-duration',errors)
  self.assertIn('clipping',errors)
  self.assertIn('generation-limit',errors)
 def test_pcm16_and_float_speech_levels_have_same_result(self):
  audio=.1*np.sin(np.arange(24000)*.1)
  self.assertEqual(problems(audio,24000,'你好'),[])
  self.assertEqual(problems((audio*32767).astype(np.int16),24000,'你好'),[])

class QwenRetryTests(unittest.TestCase):
 def test_failed_attempt_retries_and_never_writes_bad_take(self):
  import tempfile,types
  from unittest.mock import patch,Mock
  import qwen_voice
  fake=types.ModuleType('mlx');fake.core=types.SimpleNamespace(random=types.SimpleNamespace(seed=lambda n:None))
  for recover in (False,True):
   with tempfile.TemporaryDirectory() as folder:
    out=Path(folder)/'nested/take.wav'
    silent=types.SimpleNamespace(audio=np.zeros(24000),token_count=1)
    good=types.SimpleNamespace(audio=.1*np.sin(np.arange(24000)*.1),token_count=12)
    model=Mock(sample_rate=24000);model.generate.side_effect=[[silent],[good if recover else silent],[silent]]
    sf=types.ModuleType('soundfile');sf.write=lambda path,*args,**kwargs:Path(path).write_bytes(b'audio')
    cfg=dict(storage=folder,items=[dict(text='你好',output=str(out),profile=dict(name='role',reference='reference.wav',promptText='hello'))])
    with patch.dict(sys.modules,{'mlx':fake,'mlx.core':fake.core,'soundfile':sf}),patch.object(qwen_voice,'load',return_value=model):
     if recover:qwen_voice.synthesize(cfg,lambda *a,**kw:None)
     else:
      with self.assertRaises(ValueError):qwen_voice.synthesize(cfg,lambda *a,**kw:None)
    self.assertEqual(model.generate.call_count,2 if recover else 3)
    self.assertEqual(out.exists(),recover)
    self.assertTrue(out.with_suffix('.health.json').exists())
