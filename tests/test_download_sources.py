import importlib.util,json,re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('download_sources',ROOT/'scripts/download_sources.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class DownloadSourceTests(unittest.TestCase):
 def test_catalogue_files_preserve_exact_download_urls_and_expected_hashes(self):
  data=module.inventory();self.assertEqual(data['verification'],'expected-only');rows=data['models']
  for filename in ('Resources/model-options.json','windows/native-models.json'):
   for source in json.loads((ROOT/filename).read_text()):
    if not source.get('files') or source.get('retired') or source.get('licenseReviewRequired') or source.get('engine')=='qwen-tts':continue
    if (source.get('category')=='text' or source.get('engine') in ('mlx-text','ollama')) and not re.search(r'qwen3[.]5[-:](?:9b|35b)(?:-|:|$)',source['id'],re.I):continue
    row=next(r for r in rows if source['id'] in r['ids'])
    self.assertEqual(len(row['files']),len(source['files']))
    for f,expected in zip(row['files'],source['files']):
     self.assertEqual(f['sha256'],expected['sha']);self.assertRegex(f['sha256'],r'^[0-9a-f]{64}$')
     if expected.get('url'):self.assertEqual(f['url'],expected['url'])
     if 'content' in expected:self.assertEqual(f['kind'],'generated');self.assertIsNone(f['url'])
  self.assertFalse(any(r['availability']!='catalogue' for r in rows))
  self.assertFalse(any('cosy-0.5b-8bit' in row['ids'] for row in rows))
  cosy=next(r for r in rows if 'cosy-native-0.5b' in r['ids']);self.assertEqual(cosy['platform'],'Mac · CPU / Windows · NVIDIA')
  self.assertTrue(any('registry.ollama.ai' in (f['url'] or '') for r in rows for f in r['files']))
 def test_retired_voice_engine_is_hidden_but_selectable_voices_remain(self):
  rows=module.inventory()['models']
  self.assertFalse(any(r['engine']=='qwen-tts' or 'Qwen3-TTS' in r['repo'] for r in rows))
  for engine in ('drama3','gpt-sovits','gpt-sovits-v2','cosyvoice3','voxcpm2','wsyue'):
   self.assertTrue(any(r['engine']==engine for r in rows),engine)
 def test_generated_browser_inventory_matches_catalogue_and_contains_no_user_paths(self):
  text=(ROOT/'studio/web/assets/download-sources.js').read_text();data=json.loads(text.split('=',1)[1].strip().removesuffix(';'))
  self.assertEqual(data,module.inventory());self.assertNotIn('/Users/',text);self.assertNotIn('verifiedAt',text)
if __name__=='__main__':unittest.main()
