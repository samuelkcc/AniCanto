"""Regressions reconstructed from the user's recorded E03 timestamps, not a film fixture."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import source_evidence as s
import hybrid_script as h
import caption_tracks as t
import video_acceleration as v
from worker import save_srt,parse_srt

class CaptionAuthorityTests(unittest.TestCase):
 def rows(self):
  captions=[dict(id='c220',start=822.74,end=825.91,text='洛基，你的羁绊还挺不错！'),dict(id='c222',start=841.42,end=846.05,text='羁绊巨剑')]
  cues=[dict(start=822.32,end=825.34,speechStart=822.77,speechEnd=825.30,japanese='あんたもいい絆持ってるじゃねえかロジ'),dict(start=825.34,end=825.62,japanese='ー'),dict(start=831.50,end=834.16,japanese='ご聴ありがとうございました'),dict(start=840.98,end=843.50,japanese='クレートバンスゾード'),dict(start=843.54,end=845.64,japanese='レッドバンソード'),dict(start=858.58,end=863.28,japanese='無限の絆で未来を作る')]
  for c in cues:c.update(text=c['japanese'],enabled=True)
  return captions,cues
 def test_caption_policy_excludes_music_hallucination_and_tail_not_dialogue(self):
  captions,cues=self.rows();cfg=dict(duration=900)
  report=s.apply_caption_policy(cfg,captions,cues)
  self.assertEqual(report['excluded'],[2,3,6])
  self.assertEqual([c['enabled'] for c in cues],[True,False,False,True,True,False])
  self.assertTrue(any(r['start']<=858.58 and r['end']>=863.28 for r in cfg['_captionPreserveRanges']))
  self.assertEqual(cues[0]['captionRecords'][0]['id'],'c220')
 def test_short_tail_cannot_erase_healthy_caption_draft(self):
  captions,cues=self.rows();s.apply_caption_policy(dict(duration=900),captions,cues)
  source=[h.evidence(c,i) for i,c in enumerate(cues)]
  allocation={'1':dict(content=captions[0]['text'],caption_ids=['c220'],uncertain=False)}
  self.assertEqual(s.allocation_errors(allocation,source,['1']),{})
  self.assertTrue(s.grounded_line('1',dict(evidence_id='c220',quote=captions[0]['text']),source,allocation))
 def test_duplicate_rejects_weaker_only_and_attack_calls_survive(self):
  captions,cues=self.rows();s.apply_caption_policy(dict(duration=900),captions,cues)
  source=[h.evidence(c,i) for i,c in enumerate(cues)]
  allocation={k:dict(content='羁绊巨剑',caption_ids=['c222'],uncertain=False) for k in ('4','5')}
  self.assertEqual(s.allocation_errors(allocation,source,['4','5']),{})
  self.assertFalse(s.repeated_short_call(dict(start=0,end=1,japanese='エネルギー'),dict(start=1,end=2,japanese='ロボット'),'羁绊巨剑'))
  duplicate=[dict(id='a',start=1,end=3,japanese='普通の文',caption_records=[dict(id='c',start=1,end=3.4,text='一整句對白')]),dict(id='b',start=3,end=3.4,japanese='ぶん',caption_records=[dict(id='c',start=1,end=3.4,text='一整句對白')])]
  allocation={k:dict(content='一整句對白',caption_ids=['c'],uncertain=False) for k in ('a','b')}
  self.assertEqual(s.allocation_errors(allocation,duplicate,['a','b']),{'b':'duplicated-shared-caption'})
 def test_japanese_only_or_subtitle_free_film_keeps_asr_workflow(self):
  captions=[dict(start=0,end=1,text='出発'),dict(start=2,end=3,text='行くぞ！'),dict(start=4,end=5,text='どこだ？')]
  cues=[dict(start=6,end=7,japanese='待て',enabled=True)]
  self.assertEqual(s.apply_caption_policy(dict(duration=10),captions,cues)['mode'],'audio-only')
  self.assertTrue(cues[0]['enabled'])
  self.assertEqual(s.apply_caption_policy(dict(duration=10,sourceCaptionLanguage='jpn'),captions[:1],cues)['mode'],'audio-only')
 def test_chinese_subtitle_with_quoted_japanese_is_still_a_caption(self):
  cap=dict(start=0,end=2,text='他大喊「行くぞ」')
  self.assertEqual(s.chinese_captions([cap],dict(sourceCaptionLanguage='zho')),[cap])
 def test_auto_source_prefers_chinese_regional_language_tags(self):
  import worker
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);cfg=dict(ffmpeg='ffmpeg',video='movie.mkv',duration=3)
   def extract(command):
    self.assertIn('0:3',command)
    job.joinpath('source.srt').write_text('1\n00:00:00,000 --> 00:00:02,000\n原裝中文字幕\n')
   meta=dict(streams=[dict(index=2,codec_type='subtitle',codec_name='ass',tags=dict(language='jpn')),dict(index=3,codec_type='subtitle',codec_name='ass',tags=dict(language='zh-Hans'))])
   with patch.object(worker,'run',side_effect=extract):rows=worker.extract_cues(cfg,job,meta)
   self.assertEqual(rows[0]['text'],'原裝中文字幕')
   self.assertEqual(cfg['sourceCaptionLanguage'],'zh-Hans')
 def test_external_chinese_captions_do_not_inherit_old_japanese_language(self):
  import worker
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);cfg=dict(ffmpeg='ffmpeg',video='movie.mkv',subtitle='chinese.srt',duration=3,sourceCaptionLanguage='jpn')
   def extract(command):job.joinpath('source.srt').write_text('1\n00:00:00,000 --> 00:00:02,000\n原裝中文字幕\n')
   with patch.object(worker,'run',side_effect=extract):rows=worker.extract_cues(cfg,job,{})
   self.assertEqual(s.apply_caption_policy(cfg,rows,[dict(start=0,end=1,japanese='出発')])['mode'],'original-chinese')
 def test_small_boundary_crumb_cannot_duplicate_prior_clause(self):
  caps=[dict(id='prior',start=808.77,end=813.48,text='上一句'),dict(id='own',start=813.56,end=816.36,text='下一句')]
  cues=[dict(start=813.32,end=817.6,japanese='次だ')]
  s.apply_caption_policy(dict(duration=900),caps,cues)
  self.assertEqual([r['id'] for r in cues[0]['captionRecords']],['own'])
 def test_repeated_reaction_is_not_neighbours_dialogue(self):
  self.assertTrue(s.reaction_only(dict(japanese='ええええええ。')))
 def test_policy_disabled_rows_never_request_llm_and_are_saved(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);job.joinpath('subtitle-context.json').write_text(json.dumps([dict(start=1,end=2,text='真對白')]))
   cues=[dict(start=10,end=12,text='歌',japanese='無限の絆で未来を作る',cantonese='錯稿')]
   w=SimpleNamespace(emit=Mock(),atomic_json=lambda p,r:p.write_text(json.dumps(r)),ollama_chat=Mock())
   h.render(w,dict(duration=20,storage=d,model='test'),job,cues)
   w.ollama_chat.assert_not_called()
   self.assertFalse(json.loads((job/'cues.json').read_text())[0]['enabled'])
 def test_disabled_english_rows_never_request_llm(self):
  import dub_languages
  with tempfile.TemporaryDirectory() as d:
   cues=[dict(start=0,end=1,text='歌',enabled=False)]
   w=SimpleNamespace(emit=Mock(),ollama_chat=Mock(),atomic_json=lambda p,r:p.write_text(json.dumps(r)))
   dub_languages.english_script(w,dict(model='test'),Path(d),cues)
   w.ollama_chat.assert_not_called();self.assertEqual(cues[0]['english'],'')
   self.assertEqual(dub_languages.track_cues(cues,'en')[0]['cantonese'],'')
 def test_blank_draft_does_not_export_japanese_as_cantonese(self):
  with tempfile.TemporaryDirectory() as d:
   rows=[dict(start=0,end=1,text='日本語',cantonese=''),dict(start=2,end=3,text='日本語',cantonese='你好'),dict(start=4,end=5,text='歌',cantonese='不要',enabled=False)]
   path=Path(d)/'s.srt';save_srt(path,rows)
   self.assertEqual([r['text'] for r in parse_srt(path.read_text())],['你好'])
   self.assertIs(t.matching_cue(parse_srt(path.read_text())[0],rows),rows[1])
 def test_cantonese_is_first_and_original_is_last(self):
  tracks=[dict(mode='yue',language='yue'),dict(mode='original',language='yue'),dict(mode='english',language='en')]
  self.assertEqual([r['mode'] for r in t.ordered(tracks)],['yue','english','original'])
  self.assertEqual(t.labels(tracks[0]),('yue','Cantonese translation / 廣東話譯文'))
  self.assertEqual(t.labels(dict(mode='original',sourceLanguage='jpn'))[0],'jpn')

class HardwareEncodingTests(unittest.TestCase):
 def test_copy_never_encodes_and_session_failure_has_one_retry(self):
  cfg=dict(ffmpeg='ffmpeg');run=Mock(return_value=b'ok');emit=Mock()
  copycmd=['ffmpeg','-c:v','copy','out.mp4']
  v.encode(run,copycmd,cfg,emit);run.assert_called_once_with(copycmd)
  cmd=['ffmpeg','-y','-c:v','libx264','-preset','veryfast','-crf','20','-c:a','copy','out.mp4']
  run=Mock(side_effect=[RuntimeError('h264_videotoolbox: cannot create compression session'),b'ok'])
  with patch.object(v,'available',return_value=True):self.assertEqual(v.encode(run,cmd,cfg,emit),b'ok')
  self.assertEqual(run.call_count,2)
  self.assertIn('h264_videotoolbox',run.call_args_list[0].args[0]);self.assertNotIn('-crf',run.call_args_list[0].args[0])
  self.assertEqual(run.call_args_list[1].args[0],cmd)
 def test_input_failure_not_retried(self):
  run=Mock(side_effect=RuntimeError('input missing'));cmd=['ffmpeg','-c:v','libx264','out.mp4']
  with patch.object(v,'available',return_value=True):
   with self.assertRaises(RuntimeError):v.encode(run,cmd,dict(ffmpeg='ffmpeg'),Mock())
  self.assertEqual(run.call_count,1)

class PCMMixTests(unittest.TestCase):
 def test_vectorized_mixing_matches_prior_pcm_including_overlaps_and_clipping(self):
  import array
  from pcm_mix import add,finish
  actual=array.array('i',[0])*2000;expected=array.array('i',[0])*2000
  for offset,gain in ((0,1),(500,.75),(1900,.125),(2500,1)):
   samples=array.array('h',[(i*251)%64001-32000 for i in range(1500)])
   add(actual,samples,offset,gain)
   for i,sample in enumerate(samples):
    if offset+i>=len(expected):break
    expected[offset+i]+=round(sample*gain)
  self.assertEqual(actual,expected)
  pcm,gain=finish(actual)
  old_gain=min(1,32000/max(1,max(abs(v) for v in expected)))
  self.assertEqual(gain,old_gain)
  self.assertEqual(pcm,array.array('h',(round(v*old_gain) for v in expected)))

class EpisodeFiveBoundaryTests(unittest.TestCase):
 def test_short_lexical_reaction_survives_seven_hundredths_subtitle_gap(self):
  cfg=dict(duration=1400,sourceCaptionLanguage='zho')
  caps=[dict(start=729.6,end=731.36,text='-什么… -好奇怪的武器！'),dict(start=1200.16,end=1201.08,text='没事。')]
  cues=[dict(start=728.87,end=729.59,speechStart=728.83,speechEnd=729.53,japanese='なんだ',asrConfidence=.9,enabled=True),dict(start=1199.44,end=1200.18,speechStart=1199.08,speechEnd=1200.11,japanese='んいや',asrConfidence=.8,enabled=True)]
  times=[(c['start'],c['end']) for c in cues];s.apply_caption_policy(cfg,caps,cues)
  self.assertTrue(all(c['enabled'] and c.get('captionBoundaryRescue') for c in cues));self.assertEqual(times,[(c['start'],c['end']) for c in cues])
 def test_hum_far_caption_and_manual_disable_are_not_reenabled(self):
  caps=[dict(start=10,end=12,text='原裝中文字幕')]
  cues=[dict(start=9,end=9.94,japanese='ん',asrConfidence=.99,enabled=True),dict(start=7,end=8,japanese='なんだ',asrConfidence=.99,enabled=True),dict(start=9,end=9.94,japanese='なんだ',asrConfidence=.99,enabled=False)]
  s.apply_caption_policy(dict(duration=20,sourceCaptionLanguage='zho'),caps,cues)
  self.assertFalse(any(c['enabled'] for c in cues))
