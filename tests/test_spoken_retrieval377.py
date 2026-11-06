"""Check first-draft example boundaries and saved-policy isolation."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Resources'))
import hk_spoken_style as style


class SpokenRetrieval377(unittest.TestCase):
    def test_desktop_uses_the_complete_owned_example_set(self):
        desktop = ROOT / 'Resources/hk-spoken-retrieval-377.json'
        rows = json.loads(desktop.read_text())['entries']
        self.assertEqual(len(rows), 97)
        self.assertEqual(len({row['id'] for row in rows}), len(rows))

    def test_examples_remain_bounded_and_match_the_current_source(self):
        cfg = {'hongKongStyleRevision': style.REVISION}
        source = '難道你打算隨後確認他是否允許你無論如何都去？'
        rows = style.retrieve(cfg, source)
        self.assertEqual(len(rows), 3)
        entries = {row['id']: row for row in style.style_memory()['entries']}
        for row in rows:
            original = entries[row['id']]
            self.assertTrue(any(all(term in source for term in group)
                                for group in original['matchesAny']))
        rhetorical = style.retrieve(cfg, '難道你真的不想回家嗎？')
        self.assertIn('context377-rhetorical', [row['id'] for row in rhetorical])

    def test_saved_policies_and_other_languages_receive_no_new_examples(self):
        for revision in [None, style.LEGACY_REVISION, 'unknown']:
            self.assertEqual(style.retrieve({'hongKongStyleRevision': revision}, '難道'), [])
        for language in ['zh', 'en', 'ja']:
            self.assertEqual(style.retrieve({'hongKongStyleRevision': style.REVISION},
                                           '難道', language), [])
        self.assertNotIn('spokenStyleExamples', style.instruction(
            {'hongKongStyleRevision': style.LEGACY_REVISION}))

    def test_examples_do_not_change_or_replace_the_source(self):
        source = '沒有他的允許，我不能開門。'
        result = style.retrieve({'hongKongStyleRevision': style.REVISION}, source)
        self.assertTrue(result)
        self.assertEqual(source, '沒有他的允許，我不能開門。')
        self.assertTrue(any(row['id'] == 'context377-permission' for row in result))
        self.assertEqual(style.retrieve({'hongKongStyleRevision': style.REVISION},
                                        'ZXQ-19'), [])


if __name__ == '__main__':
    unittest.main()
