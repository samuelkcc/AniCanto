import sys,unittest,tempfile,json,wave,array
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
from caption_tracks import combine,source_cues
from pronunciation import spoken
from multitrack import subtitle_choices
from quality import check_voice
from acoustics import refine

class OutputAlignmentTests(unittest.TestCase):
 def test_dual_tracks_do_not_copy_text_across_time_gaps(self):
  a=[dict(start=0,end=1,text='原裝'),dict(start=2,end=3,text='下一句')]
  b=[dict(start=.5,end=2.5,cantonese='廣東話')]
  rows=combine(a,b)
  self.assertEqual([(c['start'],c['end'],c['text']) for c in rows],[(0,.5,'原裝'),(.5,1,'原裝\n廣東話'),(1,2,'廣東話'),(2,2.5,'下一句\n廣東話'),(2.5,3,'下一句')])
 def test_source_captions_are_clamped_to_processing_window(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'subtitle-context.json').write_text(json.dumps([dict(start=-1,end=1,text='原裝'),dict(start=3,end=5,text='尾句')]))
   self.assertEqual([(r['start'],r['end']) for r in source_cues(p,4)],[(0,1),(3,4)])
 def test_subtitle_combination_and_burning_are_independent(self):
  soft,burn=subtitle_choices(dict(subtitleOutput='complete',burnOutputCaptions=True,burnSubtitleMode='original-english'))
  self.assertEqual(len(soft),6);self.assertEqual(burn,'original-english')
  self.assertEqual(subtitle_choices(dict(subtitleOutput='none',burnOutputCaptions=True,burnSubtitleMode='original-yue')),([], 'original-yue'))
 def test_aliases_do_not_rewrite_substrings_or_recurse(self):
  cfg=dict(pronunciationText='ONE PIECE = 海賊王\nONE = 一\n海賊王 = 航海王')
  self.assertEqual(spoken(cfg,'one piece / someone / 海賊王'),'海賊王 / someone / 航海王')
  with self.assertRaises(ValueError):spoken(dict(pronunciationText='invalid'),'abc')
 def test_overlapping_other_voice_cannot_hide_a_silent_take(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)
   for name,value in [('cantonese.wav',5000),('silent.wav',0)]:
    with wave.open(str(p/name),'wb') as w:
     w.setparams((1,2,24000,0,'NONE','not compressed'));w.writeframes(array.array('h',[value]*24000).tobytes())
   with self.assertRaisesRegex(ValueError,'第 2 句'):
    check_voice(p,[dict(cantonese='你好')],[dict(index=2,renderedStart=0,renderedEnd=1,renderedAudio=str(p/'silent.wav'))])
 def test_original_simultaneous_speakers_not_truncated_to_next_onset(self):
  rows=[dict(start=0,end=2,speakerId='a'),dict(start=1,end=3,speakerId='b')]
  refine(rows,[(0,2),(1,3)],4)
  self.assertGreater(rows[0]['speechEnd'],1)
 def test_hybrid_scene_is_not_retranslated_by_legacy_preflight(self):
  from unittest.mock import patch
  import script_preflight
  with tempfile.TemporaryDirectory() as d:
   c=dict(start=0,end=.5,text='ラステン',japanese='ラステン',cantonese='最後個島拉夫坦',originalCantonese='目標最終嘅島嶼，拉夫德魯',hybridRevision='hybrid-scenes-3',hybridEvidence={'cantonese':'目標最終嘅島嶼，拉夫德魯'},preflightRevision='source-script-3',preflightTextHash=script_preflight.digest('最後個島拉夫坦'))
   with patch('worker.ollama_chat') as model:
    script_preflight.repair({},Path(d),[c],lambda *a:None)
   model.assert_not_called()
   self.assertEqual(c['cantonese'],'目標最終嘅島嶼，拉夫德魯')
   c['cantonese']='使用者改稿';c['preflightTextHash']='different'
   script_preflight.repair({},Path(d),[c],lambda *a:None)
   self.assertEqual(c['cantonese'],'使用者改稿')
