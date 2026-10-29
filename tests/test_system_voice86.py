import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import system_voice as native,delivery_policy,worker

class NativeVoiceTests(unittest.TestCase):
 def test_yue_never_selects_a_mandarin_voice(self):
  self.assertTrue(native.compatible('zh-HK','yue'));self.assertTrue(native.compatible('yue_HK','yue'));self.assertFalse(native.compatible('zh-CN','yue'));self.assertFalse(native.compatible('zh-TW','yue'));self.assertTrue(native.compatible('en-GB','en'))
 def test_mac_voice_enumeration_filters_by_installed_locale(self):
  with tempfile.TemporaryDirectory() as d,patch.object(native.sys,'platform','darwin'),patch.object(native,'execute',return_value=b'Sin-ji             zh_HK # demo\nTingting            zh_CN # demo\nSamantha            en_US # demo'):
   self.assertEqual(native.installed(d,'yue'),[dict(name='Sin-ji',locale='zh_HK')])
 def test_windows_uses_getinstalledvoices_and_no_user_text_in_code(self):
  with tempfile.TemporaryDirectory() as d,patch.object(native.sys,'platform','win32'),patch.object(native,'execute',return_value=b'[{"name":"HK voice","locale":"zh-HK"},{"name":"Huihui","locale":"zh-CN"}]') as run:
   self.assertEqual(native.installed(d,'yue'),[dict(name='HK voice',locale='zh-HK')]);args=run.call_args.args[0];self.assertIn('-EncodedCommand',args);self.assertIn('GetInstalledVoices()',native.PS);self.assertNotIn('Download',native.PS)
 def test_untrusted_text_and_paths_are_json_data_not_powershell_source(self):
  value='hello "; $(anything) ` / 日本語'
  with tempfile.TemporaryDirectory() as d,patch.object(native.sys,'platform','win32'),patch.object(native,'execute',return_value=b'') as run:
   native.synthesize({},d,value,dict(name='Voice;name',locale='en-US'));args=run.call_args.args[0];self.assertNotIn(value,' '.join(args));request=json.loads((Path(d)/'native-request.json').read_text());self.assertEqual(request['text'],value);self.assertEqual(request['voice'],'Voice;name')
 def test_new_policy_separates_confirmed_errors_from_asr_uncertainty(self):
  with tempfile.TemporaryDirectory() as d:
   worker.atomic_json(Path(d)/'normal-checks.json',dict(unresolved=[1,2,3],repairs=[dict(index=1,check=dict(decision='mandarin')),dict(index=2,check=dict(languageFailure='japanese')),dict(index=3,repaired=True,check=dict(contentFailure=True))]))
   self.assertEqual(delivery_policy.confirmed_indices({},d),{2})

if __name__=='__main__':unittest.main()
