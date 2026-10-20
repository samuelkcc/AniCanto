import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
from subtitle_render import caption_events,add_overlay
class SubtitleRenderTests(unittest.TestCase):
 def test_timing_uses_delivered_audio_and_clears_gaps_and_last_frame(self):
  events=caption_events([dict(start=1,end=2,subtitleStart=1.2,subtitleEnd=2.6,cantonese='喺度，唔該！'),dict(start=4,end=5,cantonese='你好')],6)
  self.assertEqual([x['text'] for x in events],['','喺度，唔該！','','你好','',''])
  self.assertAlmostEqual(sum(x['duration'] for x in events),6.04)
  self.assertAlmostEqual(events[1]['duration'],1.4)
 def test_overlapping_and_invalid_captions_are_not_silently_clipped(self):
  for cues in [[dict(start=2,end=1,text='錯')],[dict(start=0,end=3,text='甲'),dict(start=2,end=4,text='乙')]]:
   with self.assertRaises(ValueError):caption_events(cues,5)
 def test_overlay_input_precedes_output_options_and_preserves_audio_filter(self):
  cmd=['ffmpeg','-i','video','-i','voice','-i','subs','-i','bg','-filter_complex','[1:a][3:a]amix[dub]','-map','0:v:0','-map','[dub]','-t','180']
  result=add_overlay(cmd,'captions.ffconcat',1.5)
  self.assertLess(result.index('captions.ffconcat'),result.index('-map'))
  self.assertEqual(result.count('-filter_complex'),1)
  filters=result[result.index('-filter_complex')+1]
  self.assertIn('[1:a][3:a]amix[dub]',filters);self.assertIn('[4:v:0]overlay',filters);self.assertIn('tpad',filters)
  self.assertIn('[captioned]',result);self.assertIn('[dub]',result)
