import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows')]
import normal_mode
class WitnessTests(unittest.TestCase):
 def test_foreign_script_hypothesis_needs_independent_hearing_not_automatic_rejection(self):
  self.assertTrue(normal_mode.needs_dialect_witness('香吉先生你煮嘢真係好食呀',dict(decision='unconfirmed',language='Korean',heard='신기 선생 내 주에'),'yue'))
  self.assertFalse(normal_mode.needs_dialect_witness('蒙奇·D·路飛',dict(decision='unconfirmed',language='English',heard='Monkey D Luffy'),'yue'))
 def test_second_listener_can_preserve_han_evidence_after_foreign_script_first_pass(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);python=root/'python';python.touch();audio=root/'test.wav';audio.write_bytes(b'fixture');cfg=dict(storage=d,ffmpeg='ffmpeg',targetLanguage='yue',productionMode='normal',_forceIndependentListening=True);cue=dict(start=0,end=4,cantonese='香吉先生你煮嘢真係好食呀',japanese='サンジさん本当にお料理は上手ね')
   def first(cfg,kind,request,emit):
    self.assertEqual(kind,'normal-listen');Path(request['cache']).write_text(json.dumps({x['key']:dict(key=x['key'],heard='신기 선생 내 주에 잔해 보색가',language='Korean') for x in request['items']}))
   with patch('normal_mode.audio_present',return_value=True),patch('runtime_paths.python_for',return_value=python),patch('dubbing.model_job',side_effect=first),patch('secondary_speech.transcribe_batch',return_value=[dict(heard='香吉先生你煮嘢真係好食呀',language='zh')]) as second:
    result=normal_mode.inspect(cfg,root,[cue],[audio],Mock())
   self.assertEqual(second.call_count,1);self.assertEqual(result[1]['independent']['heard'],cue['cantonese']);self.assertFalse(result[1].get('languageFailure'))
if __name__=='__main__':unittest.main()
