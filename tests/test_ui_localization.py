"""Catch untranslated interface strings before an English release."""
import re
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class InterfaceLocalizationTests(unittest.TestCase):
    def setUp(self):
        self.rows=dict(re.findall(r'^"(.*?)"\s*=\s*"(.*?)";', (ROOT/'Resources/en.lproj/Localizable.strings').read_text(),re.M))

    def test_english_does_not_repeat_chinese_keys(self):
        untranslated=[key for key,value in self.rows.items() if key==value and re.search(r'[\u4e00-\u9fff]',value)]
        self.assertEqual(untranslated,[], 'Translate English resource values, not only the keys')

    def test_literal_interface_keys_have_english_resources(self):
        missing={}
        for source in (ROOT/'Sources').glob('*.swift'):
            for key in re.findall(r'L\("([^"\n]+)"\)',source.read_text()):
                if re.search(r'[\u4e00-\u9fff]',key) and key not in self.rows:
                    missing.setdefault(key,[]).append(source.name)
        self.assertEqual(missing,{})
