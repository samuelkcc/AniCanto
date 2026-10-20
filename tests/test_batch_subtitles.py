import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
from worker import select_batch_subtitle
class BatchSubtitles(unittest.TestCase):
 def test_missing_language_ui_label_is_not_a_filter(self):
  track=dict(index=2,codec_name='ass',tags={})
  self.assertEqual(select_batch_subtitle([track],'未標示語言'),track)
 def test_alias_and_different_indices(self):
  tracks=[dict(index=3,tags=dict(language='eng')),dict(index=5,tags=dict(language='zho'))]
  self.assertEqual(select_batch_subtitle(tracks,'chi')['index'],5)
 def test_preferred_title_and_no_track(self):
  tracks=[dict(index=2,tags=dict(language='zho',title='简体')),dict(index=3,tags=dict(language='zho',title='繁體'))]
  self.assertEqual(select_batch_subtitle(tracks,'chi','繁體')['index'],3)
  self.assertIsNone(select_batch_subtitle([],'zho'))
 def test_fallback_unknown_does_not_fail_batch(self):
  self.assertEqual(select_batch_subtitle([dict(index=7,tags={})],'zho')['index'],7)
