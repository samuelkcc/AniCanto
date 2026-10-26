import sys,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows'),str(ROOT/'studio')]
from performance_fixtures import performance_row
import nonverbal,performance_refinement as tails,terminology,subtitle_snapshot,generation_guard,source_language
from desktop_state import Store

class Workflow70Tests(unittest.TestCase):
 def test_tail_windows_keep_all_words_and_only_sample_near_dialogue(self):
  rows=[performance_row(start=0,duration=5,laughter=.9,speech=.7)]
  windows=tails.gaps(rows,[dict(start=0,end=2)],5)
  self.assertEqual([(a,b) for a,b,_ in windows],[(2.2,5)])
  self.assertEqual(tails.gaps(rows,[dict(start=0,end=5,text='ハハハ')],5),[])
  self.assertEqual(tails.gaps(rows,[],5),[])
 def test_mixed_context_alone_never_restores_but_paired_isolated_tail_can(self):
  mixed=performance_row(start=0,duration=5,laughter=.85,speech=.25)
  self.assertEqual(nonverbal.event_ranges([mixed],[],5),[])
  clean=performance_row(start=0,duration=1,laughter=.8,speech=.01)
  self.assertTrue(tails.paired_ranges([clean],[clean],1))
  self.assertFalse(tails.paired_ranges([clean],[mixed],1))
 def test_padding_and_singing_do_not_authorise_source_restoration(self):
  padded=performance_row(start=2,duration=3,laughter=.9)
  self.assertEqual(tails.paired_ranges([padded],[padded],.5),[])
  singing=performance_row(start=0,duration=1,laughter=.9,choir_singing=.9)
  self.assertEqual(tails.positive([singing],1),[])
 def test_uncertain_laughter_is_reported_without_automatic_restore(self):
  row=performance_row(start=1,duration=1,laughter=.4,speech=.25)
  self.assertFalse(nonverbal.event_ranges([row],[],3));self.assertTrue(nonverbal.missing_events([row],[],3))
 def test_subtitle_snapshot_survives_original_change_and_rejects_tampering(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);original=root/'source.srt';original.write_text('1\n00:00:01,000 --> 00:00:02,000\n你好\n')
   cfg=dict(subtitle=str(original));subtitle_snapshot.freeze(cfg,root,'job');frozen=Path(cfg['subtitle'])
   before=frozen.read_bytes();original.write_text('changed');subtitle_snapshot.verify(cfg);self.assertEqual(frozen.read_bytes(),before)
   frozen.write_text('tampered')
   with self.assertRaisesRegex(ValueError,'frozen subtitle'):subtitle_snapshot.verify(cfg)
 def test_project_terms_lock_names_and_source_only_by_explicit_choice(self):
  cfg=dict(termRules=[dict(source='ルフィ',yue='路飛',kind='name'),dict(source='ゴムゴム',yue='橡膠',kind='technique',preserveOriginal=True)])
  names=terminology.merge([dict(source='ルフィ',cantonese='魯夫',english='Luffy')],cfg)
  self.assertEqual(names[0]['cantonese'],'路飛')
  cues=[dict(start=0,end=1,text='ルフィ'),dict(start=2,end=4,text='ゴムゴムの')];terminology.apply(cfg,cues)
  self.assertFalse(cues[0].get('preserveOriginalSpeech',False));self.assertTrue(cues[1]['preserveOriginalSpeech'])
  with self.assertRaises(ValueError):terminology.validate([dict(source='x',locked='false')])
 def test_exact_input_budget_persists_across_folders_and_seeds(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cfg=dict(ttsBackend='drama3',targetLanguage='yue',_generationGuardRoot=d);item=dict(text='你好',profile={},output=str(root/'take.wav'))
   request=dict(job=str(root/'child'),items=[item])
   for i in range(3):
    item['seed']=i;state=generation_guard.reserve(cfg,request);self.assertEqual(len(state[2]),1);generation_guard.finish(state,'temporary')
   state=generation_guard.reserve(cfg,request);self.assertEqual(len(state[3]),1)
   changed=dict(item,text='早晨');self.assertEqual(len(generation_guard.reserve(cfg,dict(request,items=[changed]))[2]),1)
 def test_permanent_failure_blocks_identical_input_but_new_reference_can_retry(self):
  with tempfile.TemporaryDirectory() as d:
   cfg=dict(ttsBackend='gpt-sovits',_generationGuardRoot=d);item=dict(text='名字',profile={},output=str(Path(d)/'take.wav'));request=dict(job=d,items=[item])
   state=generation_guard.reserve(cfg,request);generation_guard.finish(state,'phoneme BERT length mismatch')
   self.assertEqual(len(generation_guard.reserve(cfg,request)[3]),1)
   item['profile']['promptText']='Changed reference transcript';self.assertEqual(len(generation_guard.reserve(cfg,request)[2]),1)
 def test_explicit_manual_take_starts_new_budget_and_corrupt_ledger_cannot_reset_it(self):
  with tempfile.TemporaryDirectory() as d:
   cfg=dict(ttsBackend='drama3',_generationGuardRoot=d);item=dict(text='你好',profile={},output=str(Path(d)/'take.wav'));request=dict(job=d,items=[item])
   for n in range(3):generation_guard.finish(generation_guard.reserve(cfg,request),'temporary')
   self.assertEqual(len(generation_guard.reserve(cfg,request)[3]),1)
   manual=dict(cfg,_explicitRetakeToken='user-click-1');self.assertEqual(len(generation_guard.reserve(manual,request)[2]),1)
   (Path(d)/'generation-input-ledger.json').write_text('{invalid')
   with self.assertRaisesRegex(ValueError,'unreadable'):generation_guard.reserve(cfg,request)
 def test_extracted_subtitle_receipt_blocks_tampered_cached_source(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);srt=root/'source.srt';srt.write_text('1\n00:00:01,000 --> 00:00:02,000\n原裝字幕\n')
   subtitle_snapshot.record_extracted({},root,srt,2);subtitle_snapshot.verify_extracted(root)
   srt.write_text('altered')
   with self.assertRaisesRegex(ValueError,'Saved subtitle evidence changed'):subtitle_snapshot.verify_extracted(root)
 def test_removing_locked_original_term_stops_automatic_source_preservation(self):
  cue=dict(japanese='サンジです');cfg=dict(termRules=[dict(source='サンジ',yue='山治',preserveOriginal=True)])
  terminology.apply(cfg,[cue]);self.assertTrue(cue['preserveOriginalSpeech'])
  terminology.apply(dict(termRules=[]),[cue]);self.assertFalse(cue['preserveOriginalSpeech'])
 def test_metadata_conflict_requires_confirmation_and_override_binds_token(self):
  with tempfile.TemporaryDirectory() as d:
   video=Path(d)/'video';video.write_bytes(b'fixture');meta=dict(format=dict(duration='100'),streams=[dict(index=1,codec_type='audio',tags=dict(language='jpn'))])
   heard=dict(language='ko',stream=1,method='three-audio-samples',samples=[])
   with patch.object(source_language.subprocess,'check_output',side_effect=[json.dumps(meta).encode(),json.dumps(heard).encode()]):
    result=source_language.preflight(d,str(video),dict(ffprobe='probe',ffmpeg='ffmpeg'),dict(selectedEngines=['drama3']))
   self.assertTrue(result['metadataConflict']);self.assertTrue(result['needsConfirmation']);self.assertEqual(result['language'],'ko')
   manual=source_language.preflight(d,str(video),{},dict(selectedEngines=['drama3'],sourceLanguageOverride='ja'))
   self.assertEqual(manual['language'],'ja');self.assertNotEqual(manual['token'],result['token'])
