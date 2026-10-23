"""Mandarin is an independent script/track; source anomalies never use OCR clocks."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows'),str(ROOT/'studio')]
import dub_languages,output_language,subtitle_policy,caption_tracks,normal_mode,source_timing_review as clock,subtitle_ocr,dialogue
from atomic_files import write_json

class MandarinTests(unittest.TestCase):
 def test_plan_has_three_languages_and_language_specific_engine_support(self):
  import studio_core
  plan=studio_core.call('plan',settings=dict(selectedEngines=['drama3','cosyvoice3'],dubLanguages=['yue','zh','en'],subtitleSelection='automatic'))
  self.assertEqual(plan['languages'],['yue','zh','en']);self.assertEqual(plan['dubbedTrackCount'],6);self.assertEqual(plan['maximumAudioTrackCount'],7);self.assertEqual(plan['subtitles'],['yue','zh','english','dual','original'])
  from engine_policy import pairs
  self.assertEqual(pairs(['drama3','wsyue'],['zh']),[('zh','drama3')])
 def test_script_projection_keeps_all_other_language_text_and_times(self):
  cues=[dict(start=2,end=4,cantonese='我哋出發啦。',mandarin='我们出发吧。',english="Let's go.",editorAudio='canto.wav',editorAudioLanguage='yue')];cues += [dict(cues[0],start=5,end=7)];before=copy.deepcopy(cues)
  new=dub_languages.track_cues(cues,'zh');self.assertEqual(new[0]['cantonese'],'我们出发吧。');self.assertEqual(new[0]['captionText'],'我们出发吧。');self.assertNotIn('editorAudio',new[0]);self.assertEqual(cues,before);self.assertEqual(new[0]['start'],2)
 def test_mandarin_translation_is_direct_cached_and_never_overwrites_cantonese(self):
  with tempfile.TemporaryDirectory() as d:
   cues=[dict(start=1,end=3,japanese='行こう',cantonese='我哋走啦。',english="Let's go.")]
   w=NS(atomic_json=write_json,emit=Mock(),ollama_chat=Mock(return_value='{"0":"我们走吧。"}'))
   for _ in range(2):dub_languages.mandarin_script(w,dict(model='local',port=1),d,cues)
   self.assertEqual(cues[0]['mandarin'],'我们走吧。');self.assertEqual(cues[0]['cantonese'],'我哋走啦。');self.assertEqual(w.ollama_chat.call_count,1)
   prompt=w.ollama_chat.call_args.args[2][0]['content'];self.assertIn('Mainland',prompt);self.assertIn('Simplified',prompt)
 def test_failed_mandarin_script_is_bounded_and_does_not_echo_japanese(self):
  with tempfile.TemporaryDirectory() as d:
   cues=[dict(start=1,end=3,japanese='行こう',cantonese='我哋走啦。')];w=NS(atomic_json=write_json,emit=Mock(),ollama_chat=Mock(return_value='{"0":"行こう"}'))
   for _ in range(3):dub_languages.mandarin_script(w,dict(model='local',port=1),d,cues)
   self.assertEqual(w.ollama_chat.call_count,2);self.assertEqual(cues[0]['mandarin'],'');self.assertTrue(cues[0]['mandarinGenerationFailed']);self.assertEqual(cues[0]['cantonese'],'我哋走啦。')
 def test_mandarin_is_accepted_as_mandarin_and_cantonese_not_certified(self):
  self.assertEqual(normal_mode.language_decision('我们走吧','我们走吧','Chinese','zh'),'mandarin')
  self.assertEqual(normal_mode.language_decision('我们走吧','我哋走啦','Cantonese','zh'),'cantonese')
  self.assertNotEqual(normal_mode.language_decision('我們出發吧','我們出發吧','Chinese','yue'),'cantonese')
  from speechcheck import evidence
  self.assertFalse(evidence('我们出发吧','我们出发吧','Chinese','zh')['languageMismatch'])
  from normal_recovery import verified_check
  self.assertTrue(verified_check(dict(decision='mandarin',heard='我们出发吧'),'我们出发吧','zh'))
 def test_subtitles_are_simplified_mandarin_and_audio_metadata_is_zho(self):
  self.assertEqual(subtitle_policy.automatic_modes(['zh']),['zh','original']);self.assertEqual(caption_tracks.labels(dict(mode='zh')),('zho','Mainland Mandarin / 普通话（简体）'));self.assertEqual(dub_languages.LANGUAGES['zh'][2],'zho')
 def test_all_adapter_instructions_target_mandarin_not_cantonese(self):
  import drama3,local_tts
  self.assertIn('普通话',drama3.language_hint('zh','normal'));self.assertIn('zh',local_tts.ENGINES['drama3']['languages'])
  from voice_expression import instruction
  self.assertIn('普通话',instruction('expressive','zh'));self.assertNotIn('粤语',instruction('expressive','zh'))
  self.assertIn("'zh':'all_zh'",(ROOT/'Resources/dubbing_runner.py').read_text())
 def test_single_mandarin_editor_draft_does_not_require_cantonese_text(self):
  from project_edit import materialize
  review=dict(config=dict(duration=3,dubLanguages=['zh']),cues=[dict(start=0,end=2,text='行こう',cantonese='',mandarin='出发吧。')]);draft=dict(settings=dict(dubLanguages=['zh']),segments=[dict(id='one',sources=[0],start=0,end=2,text='',mandarin='我们走吧。')])
  result=materialize(review,draft);self.assertEqual(result[0]['mandarin'],'我们走吧。')
 def test_english_source_keeps_explicit_mandarin_output(self):
  from source_language import apply
  cfg=dict(dubLanguages=['zh'],subtitleModes=['zh','original'],targetLanguage='zh');apply(cfg,'en');self.assertEqual(cfg['dubLanguages'],['zh']);self.assertEqual(cfg['targetLanguage'],'zh')
 def test_removed_top_export_shortcut(self):
  s=(ROOT/'studio/web/app.js').read_text();self.assertNotIn("ib('finish-current'",s);self.assertNotIn("a==='finish-current'",s)

class SourceClockTests(unittest.TestCase):
 def fixture(self):
  row=dict(start=11.6,end=26.6,text='ご視聴ありがとうございました',words=[dict(start=11.6,end=13,word='ご',probability=.01),dict(start=13,end=14.36,word='視',probability=.48),dict(start=14.36,end=26.38,word='聴',probability=1),dict(start=26.38,end=26.6,word='ありがとうございました',probability=.79)])
  spans=[dict(start=12.84,end=17.464),dict(start=19.56,end=20.216),dict(start=25.896,end=28.024)]
  return row,spans
 def test_abnormal_clock_requires_stretched_token_and_multiple_witnessed_turns(self):
  row,spans=self.fixture();self.assertTrue(clock.abnormal(row,spans));self.assertFalse(clock.abnormal(row,[dict(start=11,end=27)]))
  good=dict(start=20,end=23,text='ご視聴ありがとうございました',words=[dict(start=20,end=23,word='ご視聴ありがとうございました')]);self.assertFalse(clock.abnormal(good,spans))
 def test_local_recheck_splits_bad_source_and_persists_results(self):
  import numpy as np
  with tempfile.TemporaryDirectory() as d:
   row,spans=self.fixture();texts=['この前の豪ドル','あ','お邪魔します'];i=[0]
   def decode(audio,**kw):
    self.assertNotIn('initial_prompt',kw);text=texts[i[0]];i[0]+=1;return iter([NS(words=[NS(start=.1,end=.8,word=text,probability=.95)])]),None
   model=NS(transcribe=Mock(side_effect=decode));cfg=dict(duration=40,sourceLanguage='ja',speechModel='pinned')
   a=clock.repair(model,np.ones(16000*40),spans,[row],cfg,d,Mock());b=clock.repair(model,np.ones(16000*40),spans,[row],cfg,d,Mock())
   self.assertEqual(len(a),3);self.assertEqual(a,b);self.assertEqual(model.transcribe.call_count,3);self.assertTrue(all(x['end']-x['start']<1 for x in a))
   self.assertNotIn('ご視聴',''.join(x['text'] for x in a))
 def test_failed_source_recheck_is_flagged_for_original_speech_not_fake_translation(self):
  import numpy as np
  with tempfile.TemporaryDirectory() as d:
   row,spans=self.fixture();model=NS(transcribe=Mock(side_effect=ValueError('unavailable')))
   repaired=clock.repair(model,np.ones(16000*40),spans,[row],dict(duration=40),d,Mock());self.assertTrue(repaired[0]['sourceClockUnconfirmed'])
   cues=dialogue.build_cues(repaired,spans,[],40);self.assertTrue(cues[0]['preserveOriginalSpeech'])
 def test_partial_source_recheck_never_drops_an_unconfirmed_turn(self):
  import numpy as np
  with tempfile.TemporaryDirectory() as d:
   row,spans=self.fixture();model=NS(transcribe=Mock(side_effect=[(iter([NS(words=[NS(start=.1,end=.8,word='本当だ',probability=.95)])]),None),ValueError('failed'),(iter([]),None)]))
   result=clock.repair(model,np.ones(16000*40),spans,[row],dict(duration=40),d,Mock())
   self.assertEqual(len(result),3);self.assertEqual(sum(bool(x.get('sourceClockUnconfirmed')) for x in result),2)
   cues=dialogue.build_cues(result,spans,[],40)
   self.assertEqual(sum(bool(c.get('preserveOriginalSpeech')) for c in cues),2)
 def test_audio_only_removes_new_ocr_evidence_fields(self):
  from translation_source import remove_caption_evidence
  cues=[dict(ocrEvidence=[dict(text='caption')],subtitleConfidence=.3)]
  remove_caption_evidence(dict(translationSource='audio-only'),cues)
  self.assertNotIn('ocrEvidence',cues[0]);self.assertNotIn('subtitleConfidence',cues[0])
 def test_large_centered_japanese_caption_is_kept_when_no_chinese_exists(self):
  row=dict(index=0,boxes=[dict(text='今日はいい天気',confidence=.8,x=.25,y=.5,width=.5,height=.2)])
  self.assertEqual(subtitle_ocr.subtitle_rows([row])[0]['text'],'今日はいい天気')
 def test_unconfirmed_source_clock_is_visible_in_the_selected_language_report(self):
  import review_report
  with tempfile.TemporaryDirectory() as d:
   review=dict(config=dict(dubLanguages=['zh'],ttsBackend='drama3'),cues=[dict(start=1,end=2,sourceClockUnconfirmed=True,mandarin='原声待核对。')])
   report=review_report.project(d,review,dict(status='complete'))
   self.assertEqual(report['issues'][0]['kind'],'source-clock-unconfirmed');self.assertEqual(report['issues'][0]['language'],'zh');self.assertFalse(report['reviewState']['qualityChecked'])
 def test_source_recheck_retains_internal_zero_duration_word_tokens(self):
  import numpy as np
  with tempfile.TemporaryDirectory() as d:
   row,spans=self.fixture()
   words=[NS(start=.1,end=.4,word='お',probability=.9),NS(start=.4,end=.4,word='邪',probability=.9),NS(start=.4,end=.8,word='魔します',probability=.9)]
   model=NS(transcribe=Mock(return_value=(iter([NS(words=words)]),None)))
   # Use distinct fresh iterators for each independently witnessed turn.
   model.transcribe.side_effect=lambda *a,**k:(iter([NS(words=words)]),None)
   result=clock.repair(model,np.ones(16000*40),spans,[row],dict(duration=40),d,Mock())
   cues=dialogue.build_cues(result,spans,[],40)
   self.assertEqual(cues[0]['japanese'],'お邪魔します')
 def test_ocr_keeps_large_low_confidence_caption_and_excludes_high_confidence_page(self):
  row=dict(index=0,text='mixed',boxes=[dict(text='何この仕打ち',confidence=1,x=.05,y=.01,width=.1,height=.13),dict(text='死んだのは',confidence=.5,x=.26,y=.66,width=.08,height=.13),dict(text='（小飛的投資日記）',confidence=.3,x=.38,y=.50,width=.25,height=.34)])
  selected=subtitle_ocr.subtitle_rows([row])[0];self.assertEqual(selected['text'],'（小飛的投資日記）');self.assertEqual(selected['subtitleConfidence'],.3);self.assertEqual(selected['excludedSceneBoxes'],2)

if __name__=='__main__':unittest.main()
