import copy,json,sys,tempfile,unittest,wave
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'studio'),str(ROOT/'windows'),str(ROOT/'Resources')]
import normal_mode,normal_recovery,natural_schedule,normal_reference_audit
from backend import Studio
from desktop_state import Store,write

class Release32Tests(unittest.TestCase):
 def test_generic_chinese_exact_text_is_not_a_cantonese_dialect_pass(self):
  text='我哋一齊出發啦'
  self.assertFalse(normal_recovery.verified_check(dict(heard=text,decision='unconfirmed',language='Chinese'),text,'yue'))
  self.assertTrue(normal_mode.needs_dialect_witness(text,dict(heard=text,decision='unconfirmed',language='Chinese')))
  self.assertFalse(normal_mode.needs_dialect_confirmation(text,dict(heard=text,decision='unconfirmed',language='Chinese')))
  self.assertTrue(normal_recovery.verified_check(dict(heard=text,decision='cantonese'),text,'yue'))
  self.assertEqual(normal_mode.dialect_decision('出發啦','出发啦','Mandarin'),'mandarin')
 def test_added_repetition_not_legitimate_repeat_or_short_name(self):
  self.assertTrue(normal_mode.extra_repetition('我哋一齊出發啦','我哋一齊出發啦，我哋一齊出發啦'))
  self.assertFalse(normal_mode.extra_repetition('快啲快啲嚟啦','快啲快啲嚟啦'))
  self.assertFalse(normal_mode.extra_repetition('羅拉','羅拉羅拉'))
 def test_ambiguous_chinese_does_not_force_replacing_a_healthy_actor(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);audio=root/'actor.wav'
   with wave.open(str(audio),'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(b'\0\x10'*24000)
   cue=dict(start=0,end=1,cantonese='我哋一齊出發啦',speakerId='own')
   with patch.object(normal_mode,'inspect',return_value={1:dict(decision='unconfirmed',heard=cue['cantonese'],language='Chinese')}),patch('dubbing.gsv_audio') as generate:
    self.assertEqual(normal_mode.repair_paths(dict(productionMode='normal'),root,[cue],[audio],Mock(),Mock()),[audio])
   generate.assert_not_called();report=json.loads((root/'normal-checks.json').read_text());self.assertEqual(report['dialectUnconfirmed'],[1]);self.assertFalse(report['qualityCertified'])
 def test_one_or_two_seconds_of_empty_tail_is_not_a_failure(self):
  cues=[dict(start=1,end=2,cantonese='我哋出發啦'),dict(start=5,end=6,cantonese='係呀')]
  before=copy.deepcopy(cues);rows=natural_schedule.plan(dict(duration=7),cues,[2.9,.7],cuts=[.5,6.5])
  self.assertTrue(rows[0]['fit']);self.assertEqual(rows[0]['start'],1);self.assertEqual(cues,before)
  self.assertLessEqual(rows[0]['start']+rows[0]['seconds'],rows[1]['start'])
 def test_a_shot_change_alone_does_not_reject_an_empty_tail(self):
  cues=[dict(start=1,end=2,cantonese='我哋出發啦'),dict(start=5,end=6,cantonese='係呀')]
  rows=natural_schedule.plan(dict(duration=7),cues,[2.9,.7],cuts=[2.1])
  self.assertTrue(rows[0]['fit']);self.assertEqual(rows[0]['start'],1)
 def test_preserved_opening_still_limits_an_empty_tail(self):
  cues=[dict(start=1,end=2,cantonese='我哋出發啦'),dict(start=5,end=6,cantonese='係呀')]
  rows=natural_schedule.plan(dict(duration=7,opRanges=[dict(start=2.1,end=4)]),cues,[2.9,.7],cuts=[2.1])
  self.assertFalse(rows[0]['fit'])
 def test_small_delay_uses_later_capacity_and_does_not_accumulate(self):
  cues=[dict(start=0,end=1,cantonese='出發啦'),dict(start=1,end=2,cantonese='係呀'),dict(start=3,end=4,cantonese='行啦')]
  rows=natural_schedule.plan(dict(duration=5),cues,[1.2,.7,.7])
  self.assertTrue(all(r['fit'] for r in rows));self.assertGreaterEqual(rows[1]['start'],1.2)
  self.assertTrue(all(abs(r['shift'])<=.5 for r in rows));self.assertEqual(rows[2]['start'],3)
 def test_locale_marker_only_defaults_new_install(self):
  with tempfile.TemporaryDirectory() as d:
   store=Store(d);self.assertFalse(store.ui['interfaceLanguageInitialized']);store.save()
   self.assertFalse(Store(d).ui['interfaceLanguageInitialized'])
   write(Path(d)/'desktop-state.json',dict(language='zh-HK',ui={}))
   self.assertTrue(Store(d).ui['interfaceLanguageInitialized']);self.assertEqual(Store(d).language,'zh-HK')
 def test_download_menu_limits_text_models_to_9b_and_35b_on_both_platforms(self):
  for platform in ('darwin','win32'):
   with self.subTest(platform=platform),tempfile.TemporaryDirectory() as d:
    app=Studio(d,ROOT/'Resources',platform=platform)
    rows=[r for r in app.dispatch('model-choices',{}) if r['category']=='text']
    self.assertTrue(rows)
    for row in rows:self.assertRegex(row['id'],r'(?:qwen3\.5-(?:9b|35b-a3b):|qwen3\.5:(?:9b|35b)$)')
 def test_wenet_backend_blocks_bilingual_and_keeps_settings_on_error(self):
  with tempfile.TemporaryDirectory() as d:
   app=Studio(d,ROOT/'Resources',platform='darwin');before=copy.deepcopy(app.store.settings)
   with self.assertRaisesRegex(ValueError,'Cantonese only'):app.dispatch('configure',dict(settings=dict(ttsBackend='wsyue',selectedEngines=['wsyue'],dubLanguages=['yue','en'])))
   self.assertEqual(app.store.settings,before)
 def test_explicit_per_line_strategy_is_not_overwritten_by_visual_off(self):
  with tempfile.TemporaryDirectory() as d:
   app=Studio(d,ROOT/'Resources',platform='darwin')
   state=app.dispatch('configure',dict(settings=dict(roleAnalysisMode='independent',visualRoleAnalysisEnabled=False)))
   self.assertEqual(state['settings']['roleAnalysisMode'],'independent')
 def test_same_actor_reference_audit_preserves_audio_and_does_not_accept_unrelated_words(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);source=root/'own.wav'
   with wave.open(str(source),'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(b'\0\x10'*74000)
   original=source.read_bytes();profile=dict(id='own',reference=str(source),language='ja',promptText='海賊王に俺をなる',transcriptSource='original-japanese-words');cfg=dict(voiceProfiles=[profile])
   with patch('secondary_speech.transcribe_batch',return_value=[dict(heard='海賊王に俺はなる',language='ja')]):
    result=normal_reference_audit.prepare(cfg,root,[dict(speakerId='own')],Mock(),Mock())
   self.assertEqual(result['voiceProfiles'][0]['promptText'],'海賊王に俺はなる');self.assertEqual(source.read_bytes(),original);self.assertEqual(profile['promptText'],'海賊王に俺をなる')
   with patch('secondary_speech.transcribe_batch',return_value=[dict(heard='我哋一齊出發啦',language='zh')]):
    result=normal_reference_audit.prepare(cfg,root,[dict(speakerId='own')],Mock(),Mock())
   self.assertEqual(result['voiceProfiles'][0]['promptText'],profile['promptText'])
 def test_timing_problem_alone_never_triggers_generic_voice(self):
  import normal_voice_fallback
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);source=root/'source.wav'
   with wave.open(str(source),'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(b'\0\x10'*30000)
   with patch('dubbing.gsv_audio') as generate,patch('dubbing.profile_for') as profile:
    out=normal_voice_fallback.repair(dict(productionMode='normal',targetLanguage='yue'),root,[dict(start=0,end=1,cantonese='我哋出發啦')],[source],[dict(fit=False,start=0,deadline=1)],Mock(),Mock())
   self.assertEqual(out,[source]);generate.assert_not_called();profile.assert_not_called()

if __name__=='__main__':unittest.main()
