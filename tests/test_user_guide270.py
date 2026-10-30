"""The complete shared manual must decode before platform filtering."""
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from validate_user_guide import validate
class SharedGuide270(unittest.TestCase):
 def setUp(self):self.doc=json.loads((ROOT/'docs/APPLICATION-USER-GUIDE.json').read_text())
 def test_complete_canonical_manual(self):self.assertGreater(validate(self.doc),100)
 def test_desktop_only_bad_shape_is_rejected_before_filter(self):
  section=next(s for c in self.doc['chapters'] for s in c['sections'] if s['id']=='desktop-runtime-maintenance-270');section['body']={'en':['invisible']}
  with self.assertRaisesRegex(ValueError,'body must'):validate(self.doc)
 def test_empty_steps_array_is_not_boolean(self):
  self.doc['chapters'][0]['sections'][0]['steps']=[]
  with self.assertRaisesRegex(ValueError,'Boolean'):validate(self.doc)
if __name__=='__main__':unittest.main()
