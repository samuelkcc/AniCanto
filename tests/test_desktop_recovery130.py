"""Reproduce actual desktop policy faults; models and iPad candidates are not used."""
import array,copy,hashlib,json,math,subprocess,sys,tempfile,unittest,wave
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows')]
from performance_fixtures import performance_row
import nonverbal,natural_schedule,speech_timing,dubbing,fast_mode,native_tools
FF=ROOT/'dist/AniCanto.app/Contents/Resources/bin/ffmpeg'

class SourceEvidenceTests(unittest.TestCase):
 def test_actual_words_and_legacy_tail_never_exempt_lexical_speech(self):
  evidence=[performance_row(start=1,duration=2,screaming=.85,speech=.6)]
  for text in ['いい','ええ','おい','ああ','こんにちは']:
   for field in ['japanese','text']:
    for tail in [False,True]:
     with self.subTest(text=text,field=field,tail=tail):
      cue=dict(start=1,end=3,nonlexicalTail=tail,cantonese='啊',**{field:text})
      self.assertFalse(nonverbal.event_ranges(evidence,[cue],6))
      self.assertFalse(dubbing.is_vocalization(cue))
      self.assertEqual(len(dubbing.required_dialogue({},[cue])),1)
  # Strong evidence still permits an isolated scream when no lexical cue occupies it.
  self.assertEqual([(e['start'],e['end']) for e in nonverbal.event_ranges(evidence,[],6)],[(1,3)])

 def test_legacy_vocalization_flag_cannot_bypass_generation_into_source_copy(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);source=root/'source.wav';source.write_bytes(b'original Japanese')
   cfg=dict(ttsBackend='drama3',productionMode='fast',dialoguePath=str(source),storage=d,continueOnError=False)
   tool=Mock(side_effect=AssertionError('No automatic source extraction'))
   for text in ['いい','ああ']:
    cue=dict(start=0,end=1,japanese=text,cantonese='啊',nonlexicalTail=True)
    with patch('natural_voices.prepare_cast'),patch('local_tts.validate'),patch('dubbing.profile_for',side_effect=ValueError('no approved reference')),self.assertRaisesRegex(ValueError,'no approved reference'):
     dubbing.gsv_audio(cfg,root,[cue],tool,Mock())
   tool.assert_not_called();self.assertEqual(source.read_bytes(),b'original Japanese')

 def test_complete_laugh_in_a_witnessed_pause_still_survives_and_ducks_locally(self):
  cue=dict(start=0,end=5,japanese='今日は晴れ')
  words=[dict(start=0,end=1,word='今日は'),dict(start=4,end=5,word='晴れ')]
  events=nonverbal.event_ranges([performance_row(start=2,duration=1,laughter=.9)],nonverbal.lexical_ranges([cue],words),5)
  self.assertEqual([(e['start'],e['end']) for e in events],[(2,3)])
  self.assertEqual([(e['start'],e['end'],e['gain']) for e in nonverbal.duck_events(events,[dict(start=2.5,end=3)])],[(2,2.5,1.),(2.5,3,.4)])
  self.assertEqual(nonverbal.subtract_restored(events,[(2,3)]),[])

 def test_all_entry_points_reject_incomplete_and_invalid_classifier_rows(self):
  full=performance_row(start=1,duration=2,laughter=.9)
  self.assertIsNone(nonverbal.validate_classification([full]))
  self.assertEqual(set(nonverbal.SCORE_LABELS),{'music','singing','choir_singing','speech','rapping','laughter','baby_laughter','belly_laugh','crying_sobbing','sigh','breathing','gasp','screaming','shout','yell'})
  bad=[]
  for key in nonverbal.SCORE_LABELS:
   row=full.copy();del row[key];bad.append(row)
  for key,value in [('speech',True),('speech',float('nan')),('singing',float('inf')),('laughter',1.1),('music',-.01),('start',True),('duration',0)]:bad.append(dict(full,**{key:value}))
  for row in bad:
   for operation in [lambda:nonverbal.validate_classification([row]),lambda:nonverbal.event_ranges([row],[],6),lambda:nonverbal.original_sound_ranges([row],[],6)]:
    with self.subTest(row=row),self.assertRaises(ValueError):operation()

 def test_partial_cache_is_rejected_once_and_not_promoted_as_success(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);source=root/'source.wav';source.write_bytes(b'isolated-fixture')
   cfg=dict(dialoguePath=str(source),executable='native',storage=d)
   complete=[performance_row(laughter=.9)];run=Mock(return_value=json.dumps(complete))
   nonverbal.classification(cfg,root,run)
   local=root/'nonverbal-classification-v3.json';saved=json.loads(local.read_text());saved['rows']=[dict(start=0,duration=1,laughter=.9)];local.write_text(json.dumps(saved))
   shared=root/'cache/nonverbal'/(saved['key']+'.json');shared.write_text(json.dumps(saved))
   run.reset_mock();self.assertEqual(nonverbal.classification(cfg,root,run),complete);run.assert_called_once()
   run.reset_mock();nonverbal.classification(cfg,root,run);run.assert_not_called()
   # An old revision, even with a full row, is never silently reused.
   for f in (local,shared):
    stale=json.loads(f.read_text());stale['key']='old-taxonomy-v4';f.write_text(json.dumps(stale))
   run.reset_mock();nonverbal.classification(cfg,root,run);run.assert_called_once()

 def test_invalid_live_data_leaves_target_untouched_and_records_failure(self):
  from track_control import UserSkipped
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);voice=root/'voice.wav';voice.write_bytes(b'keep target bytes')
   cfg=dict(duration=6,dialoguePath='source.wav',executable='native',_originalSoundRanges=[(0,6)])
   for error in [None,RuntimeError('unsupported taxonomy')]:
    options={'side_effect':error} if error else {'return_value':[dict(start=1,duration=2,laughter=.9)]}
    with patch.object(nonverbal,'classification',**options):
     tool=Mock(side_effect=AssertionError('No source rendering on missing evidence'))
     self.assertEqual(nonverbal.restore(cfg,root,[],voice,tool,Mock()),voice)
     tool.assert_not_called();self.assertEqual(voice.read_bytes(),b'keep target bytes')
     self.assertNotIn('_originalSoundRanges',cfg)
     self.assertEqual(json.loads((root/'nonverbal-report.json').read_text())['status'],'unavailable')
   with patch.object(nonverbal,'classification',side_effect=UserSkipped('skip')),self.assertRaises(UserSkipped):
    nonverbal.restore(cfg,root,[],voice,Mock(),Mock())

 def test_windows_unknown_taxonomy_is_not_zero_evidence(self):
  with self.assertRaises(ValueError):native_tools.performance_scores({0:'Laughter'},[.9],require_complete=True)
  labels={i:n for i,n in enumerate(['Music','Singing','Choir','Rapping','Speech','Laughter','Baby laughter','Belly laugh','Crying','Sigh','Breathing','Gasp','Screaming','Shout','Yell'])}
  scores=[.01]*len(labels);scores[5]=.9
  row=native_tools.performance_scores(labels,scores,require_complete=True)
  nonverbal.validate_classification([dict(start=0,duration=1,**row)])
  self.assertTrue(nonverbal.event_ranges([dict(start=0,duration=1,**row)],[],2))

class PreservedTimingTests(unittest.TestCase):
 def cues(self,preserve=True):
  return [dict(start=0,end=.8,japanese='テスト',cantonese='測試'),dict(start=1,end=3,speechStart=1.3,speechEnd=2.6,enabled=False,preserveOriginalSpeech=preserve,japanese='原声',cantonese='保留')]
 def test_disabled_preserved_source_is_fixed_and_blocks_previous_take(self):
  cues=self.cues();before=copy.deepcopy(cues)
  rows=natural_schedule.plan(dict(duration=5),cues,[4,2])
  self.assertFalse(rows[0]['fit']);self.assertEqual(rows[0]['deadline'],1)
  self.assertEqual((rows[1]['start'],rows[1]['deadline'],rows[1]['shift'],rows[1]['method']),(1,3,0,'source-preserved'))
  self.assertEqual(speech_timing.natural_window(cues[0],cues,5),(0,1))
  self.assertEqual(speech_timing.natural_window(cues[1],cues,5),(1,3))
  self.assertEqual(cues,before)
  control=natural_schedule.plan(dict(duration=5),self.cues(False),[4,2]);self.assertTrue(control[0]['fit'])

 def test_source_with_narrow_asr_and_retained_take_keeps_actual_original_clock(self):
  cues=self.cues();cues[1]['_retryRetained']={'start':1.5,'end':2.5}
  self.assertEqual(speech_timing.window(cues[1],cues,5),(1,3))
  # Existing simultaneous speech stays bounded to its own witnessed turn.
  cues.append(dict(start=2,end=2.5,cantonese='同時'))
  self.assertEqual(speech_timing.natural_window(cues[-1],cues,5),(2,2.5))
  for spans in [(-1,3),(1,6),(2,2),(float('nan'),3)]:
   with self.assertRaises(ValueError):speech_timing.window(dict(start=spans[0],end=spans[1],preserveOriginalSpeech=True),[],5)

 def test_fixed_source_does_not_consume_silence_after_it_or_shift_neighbours(self):
  cues=self.cues()+[dict(start=3,end=4,cantonese='之後')]
  rows=natural_schedule.plan(dict(duration=5),cues,[.7,2,1.8])
  self.assertTrue(rows[0]['fit']);self.assertTrue(rows[2]['fit'])
  self.assertGreaterEqual(rows[2]['start'],3);self.assertEqual(rows[1]['deadline'],3)

@unittest.skipUnless(FF.is_file(),'Bundled FFmpeg required')
class ActualAudioTests(unittest.TestCase):
 def tool(self,args):return subprocess.check_output([str(a) for a in args],stderr=subprocess.STDOUT)
 def write(self,path,seconds,frequency=440,rate=44100):
  import numpy as np
  samples=(np.sin(2*np.pi*frequency*np.arange(round(seconds*rate))/rate)*1500).astype('<i2').tobytes()
  with wave.open(str(path),'wb') as f:f.setparams((1,2,rate,0,'NONE','not compressed'));f.writeframes(samples)
  return samples

 def test_restore_blocks_real_source_bytes_for_lexical_words_but_keeps_isolated_performance(self):
  import numpy as np
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);voice=root/'voice.wav';source=root/'source.wav'
   self.write(voice,4,1500);self.write(source,4,660)
   before=hashlib.sha256(voice.read_bytes()).hexdigest()
   cfg=dict(ttsBackend='drama3',ffmpeg=str(FF),duration=4,dialoguePath=str(source),executable='native')
   for text in ['いい','ええ','おい']:
    cue=dict(start=1,end=3,japanese=text,nonlexicalTail=True)
    with patch.object(nonverbal,'classification',return_value=[performance_row(start=1,duration=2,screaming=.85,speech=.6)]):
     self.assertEqual(nonverbal.restore(cfg,root,[cue],voice,self.tool,Mock()),voice)
    self.assertEqual(json.loads((root/'nonverbal-report.json').read_text())['events'],[])
   self.assertEqual(hashlib.sha256(voice.read_bytes()).hexdigest(),before)
   with patch.object(nonverbal,'classification',return_value=[performance_row(start=1,duration=1,laughter=.95,speech=.15)]):
    output=nonverbal.restore(cfg,root,[],voice,self.tool,Mock())
   with wave.open(str(output)) as f:
    self.assertEqual((f.getframerate(),f.getnframes()),(44100,4*44100));samples=np.frombuffer(f.readframes(f.getnframes()),'<i2').astype(float)
   frequencies=np.fft.rfftfreq(44100,1/44100)
   level=lambda segment:abs(np.fft.rfft(segment))[abs(frequencies-660).argmin()]
   self.assertGreater(level(samples[44100:88200]),1e6);self.assertLess(level(samples[:44100]),1000)

 def test_renderer_reserves_raw_preserved_interval_and_refuses_overlap(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);long=root/'long.wav';preserved=root/'preserved.wav'
   self.write(long,4,1500);expected=self.write(preserved,2,660);preserved_hash=hashlib.sha256(preserved.read_bytes()).hexdigest()
   cues=PreservedTimingTests().cues();cfg=dict(productionMode='normal',speechRatePolicy='natural',normalRepairPolicy='missing-only',preferFirstAudibleTake=True,duration=5,ttsBackend='drama3',ffmpeg=str(FF),targetLanguage='yue')
   # Only generation/AI boundaries are replaced; actual scheduling, decoding and mixing run.
   with patch('dubbing.gsv_audio',return_value=[long,preserved]),patch('normal_mode.repair_paths',side_effect=lambda cfg,job,cues,paths,run,emit:paths),patch('natural_delivery.repair',side_effect=lambda cfg,job,cues,paths,run,emit,**kw:paths),patch('preview_continuity.fill',return_value=False):
    output,warnings=fast_mode.synthesize(cfg,root,cues,self.tool,Mock())
   timing=json.loads((root/'timing.json').read_text())
   self.assertTrue(timing[0]['skipped']);self.assertFalse(timing[1]['skipped'])
   self.assertEqual((timing[1]['renderedStart'],timing[1]['renderedEnd'],timing[1]['rate']),(1,3,1))
   with wave.open(str(output)) as f:pcm=f.readframes(f.getnframes())
   self.assertEqual(pcm[44100*2:3*44100*2],expected)
   self.assertFalse(any(pcm[:44100*2]));self.assertTrue(any(w['kind'] in ('timing-overrun','introduced-dialogue-overlap') for w in warnings))
   self.assertEqual(hashlib.sha256(preserved.read_bytes()).hexdigest(),preserved_hash)

if __name__=='__main__':unittest.main()
