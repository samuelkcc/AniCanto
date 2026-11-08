"""Check new source retrieval and preserve saved377requests."""
import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Resources'))
import hk_spoken_style as style
class SpokenRetrieval415(unittest.TestCase):
 def test_shared_first_party_data_and_foreign_source_keys(self):
  self.assertEqual((ROOT/'Resources/hk-spoken-source-415.json').read_bytes(),(ROOT/'mobile/LanguageData/hk-spoken-source-415.json').read_bytes())
  cfg={'hongKongStyleRevision':style.REVISION}
  for source,lang,term in [('まだ鍵が見つからない。','ja','鎖匙'),('Please lend me your umbrella.','en','遮')]:
   rows=style.retrieve(cfg,source,source_language=lang)
   self.assertTrue(any(term in r['spoken'] for r in rows));self.assertLessEqual(len(rows),3)
 def test_duplicate_examples_and_wrong_word_fragments(self):
  cfg={'hongKongStyleRevision':style.REVISION}
  rows=style.retrieve(cfg,'他們還沒有回來，我們先不要走。',source_language='zh')
  self.assertEqual(len({(r['written'],r['spoken'])for r in rows}),len(rows))
  self.assertEqual(style.retrieve(cfg,'keynote address',source_language='en'),[])
 def test_old_revision_reads_exact_frozen_data(self):
  self.assertEqual(style.style_memory(style.EXPANDED_REVISION),json.loads((ROOT/'Resources/hk-spoken-retrieval-377.json').read_text()))
  self.assertEqual(style.retrieve({'hongKongStyleRevision':style.EXPANDED_REVISION},'umbrella',source_language='en'),[])
  self.assertEqual(style.retrieve({'hongKongStyleRevision':style.LEGACY_REVISION},'鑰匙'),[])
