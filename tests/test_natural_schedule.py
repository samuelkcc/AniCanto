import copy,json,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import natural_schedule as schedule

class NaturalScheduleTests(unittest.TestCase):
 def test_overlong_line_uses_preceding_gap_and_does_not_accelerate_or_change_source(self):
  cues=[dict(start=1,end=2,cantonese='Hello.'),dict(start=2,end=3,cantonese='Yes.',editorAudio='fixed.wav')];before=copy.deepcopy(cues)
  rows=schedule.plan(dict(naturalTimingPolicy='micro-shift',duration=4),cues,[1.35,.5])
  self.assertTrue(all(r['fit'] for r in rows));self.assertLess(rows[0]['shift'],0)
  self.assertLessEqual(rows[0]['deadline'],rows[1]['start']);self.assertEqual(cues,before)
  self.assertTrue(all(abs(r['shift'])<=.5 for r in rows))
 def test_next_turn_can_move_within_limit_but_shift_never_accumulates(self):
  cues=[dict(start=i,end=i+1,cantonese='Hello.') for i in range(3)]
  rows=schedule.plan(dict(naturalTimingPolicy='micro-shift',duration=4),cues,[1.3,.6,.6])
  self.assertTrue(all(r['fit'] for r in rows));self.assertGreater(rows[1]['shift'],0)
  self.assertEqual(rows[0]['shift'],0);self.assertLessEqual(rows[0]['deadline'],rows[1]['start'])
  self.assertTrue(all(abs(r['shift'])<=.5 for r in rows))
 def test_shot_changes_do_not_block_bounded_dialogue_placement(self):
  cues=[dict(start=1,end=1.5,cantonese='Hello.'),dict(start=2,end=3,cantonese='Yes.')]
  rows=schedule.plan(dict(naturalTimingPolicy='micro-shift',duration=4),cues,[1.2,.5],cuts=[1.1,1.2,1.6])
  self.assertTrue(all(r['fit'] for r in rows))
  self.assertLessEqual(rows[0]['start']+rows[0]['seconds'],rows[1]['start'])
  self.assertTrue(all(abs(r['shift'])<=.5 for r in rows))
 def test_artificial_twelve_second_chunk_does_not_remove_shared_capacity(self):
  cues=[dict(start=0,end=2.24,cantonese='A'),dict(start=2.24,end=3.06,cantonese='B'),dict(start=3.7,end=5.66,cantonese='C'),dict(start=5.66,end=6.44,cantonese='D'),dict(start=6.44,end=7.5,cantonese='E'),dict(start=8.62,end=12.46,cantonese='F')]
  for cue in cues:cue['start']+=1;cue['end']+=1
  rows=schedule.plan(dict(naturalTimingPolicy='micro-shift',duration=16),cues,[2.3219954648526078,1.6718367346938776,2.2755555555555556/1.04,1.253877551020408,1.3003174603174603,3.7616326530612243],cuts=[2,4,6])
  self.assertTrue(all(r['fit'] for r in rows))
  self.assertTrue(all(abs(r['shift'])<=.5 for r in rows))
  for a,b in zip(rows,rows[1:]):self.assertLessEqual(a['start']+a['seconds'],b['start'])
 def test_opening_and_fixed_editor_take_are_protected(self):
  cues=[dict(start=1,end=2,cantonese='Hello.'),dict(start=2,end=3,cantonese='Yes.',editorAudio='fixed.wav')]
  rows=schedule.plan(dict(naturalTimingPolicy='micro-shift',duration=4,opRanges=[dict(start=0,end=1)],startOffset=0),cues,[1.3,.7])
  self.assertFalse(rows[0]['fit']);self.assertEqual(rows[1]['shift'],0)
 def test_source_overlap_is_kept_and_new_overlap_is_not_introduced(self):
  cues=[dict(start=1,end=2.5,cantonese='A'),dict(start=2,end=3,cantonese='B'),dict(start=3,end=4,cantonese='C')]
  rows=schedule.plan(dict(naturalTimingPolicy='micro-shift',duration=5),cues,[2.,.5,1.3])
  self.assertFalse(rows[0]['fit']);self.assertEqual(rows[0]['shift'],0)
  self.assertEqual(rows[1]['shift'],0);self.assertGreaterEqual(rows[2]['start'],3)
 def test_insufficient_capacity_is_explicit_not_faked_complete_and_neighbours_survive(self):
  cues=[dict(start=i,end=i+1,cantonese='Hello.') for i in range(4)]
  rows=schedule.plan(dict(naturalTimingPolicy='micro-shift',duration=4),cues,[.5,4.,.5,.5])
  self.assertFalse(rows[1]['fit']);self.assertEqual(rows[1]['method'],'timing-capacity-exhausted')
  self.assertTrue(all(rows[i]['fit'] for i in (0,2,3)));self.assertEqual(rows[1]['shift'],0)
 def test_impossible_shift_keeps_source_clock_without_waiting_for_visual_cut_scan(self):
  import wave,array
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);p=job/'take.wav'
   with wave.open(str(p),'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(array.array('h',[1000,-1000]*16800).tobytes())
   cues=[dict(start=1,end=2,cantonese='Hello.'),dict(start=2,end=3,cantonese='Yes.')]
   with patch.object(schedule,'scene_boundaries',side_effect=AssertionError('visual scan must not run')):
    rows=schedule.prepare(dict(duration=3),job,cues,[p,p],Mock(),Mock())
   self.assertEqual([r['shift'] for r in rows],[0,0]);self.assertFalse(rows[0]['fit'])
   self.assertEqual(json.loads((job/'natural-placement.json').read_text())['sceneBoundaryStatus'],'not-required')
 def test_safe_shift_works_when_visual_cut_scan_is_unavailable(self):
  import wave,array
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);long=job/'long.wav';short=job/'short.wav'
   for path,seconds in ((long,1.3),(short,.6)):
    with wave.open(str(path),'wb') as f:
     f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(array.array('h',[1000,-1000]*round(seconds*12000)).tobytes())
   cues=[dict(start=1,end=2,cantonese='第一句'),dict(start=2,end=3,cantonese='第二句')]
   with patch.object(schedule,'scene_boundaries',side_effect=AssertionError('visual scan must not run')):
    rows=schedule.prepare(dict(duration=4,naturalTimingPolicy='micro-shift'),job,cues,[long,short],Mock(),Mock())
   self.assertTrue(all(row['fit'] for row in rows))
   self.assertGreater(rows[1]['shift'],0)
   self.assertLessEqual(rows[0]['start']+rows[0]['seconds'],rows[1]['start']+.001)
 @unittest.skipUnless(shutil.which('ffmpeg'),'FFmpeg required')
 def test_real_cut_scan_is_local_cached_and_shared_between_languages(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);video=job/'source.mp4';ff=shutil.which('ffmpeg')
   subprocess.run([ff,'-v','error','-f','lavfi','-i','color=c=red:s=160x90:r=12:d=1','-f','lavfi','-i','color=c=blue:s=160x90:r=12:d=1','-filter_complex','[0:v][1:v]concat=n=2:v=1:a=0[v]','-map','[v]','-c:v','libx264',str(video)],check=True)
   cfg=dict(video=str(video),duration=2,ffmpeg=ff)
   with patch.object(schedule,'cut_scan',wraps=schedule.cut_scan) as scan:
    a=schedule.scene_boundaries(cfg,job,Mock(),Mock());b=schedule.scene_boundaries(dict(cfg,targetLanguage='en'),job,Mock(),Mock())
    self.assertEqual(scan.call_count,1)
   self.assertEqual(a,b)
   self.assertEqual(a['status'],'detected');self.assertTrue(any(abs(t-1)<.1 for t in a['cuts']))

 def test_random_nonoverlapping_turns_never_acquire_new_overlap_or_unbounded_drift(self):
  import random
  rng=random.Random(4128)
  for _ in range(400):
   cues=[];lengths=[];clock=0
   for i in range(rng.randint(2,25)):
    clock+=rng.uniform(0,.8);end=clock+rng.uniform(.2,2.)
    cues.append(dict(start=clock,end=end,cantonese='Hello.',editorAudio='fixed.wav' if rng.random()<.1 else None));lengths.append(rng.uniform(.1,2.8));clock=end
   rows=schedule.plan(dict(naturalTimingPolicy='micro-shift',duration=clock+.5),cues,lengths,cuts=[cues[len(cues)//2]['start']])
   delivered=[r for r in rows if r['fit']]
   for row in delivered:
    self.assertLessEqual(abs(row['shift']),.500001)
    self.assertGreaterEqual(row['start'],0)
    self.assertLessEqual(row['start']+row['seconds'],clock+.500001)
   for a,b in zip(delivered,delivered[1:]):self.assertLessEqual(a['start']+a['seconds'],b['start']+1e-7)

 def test_scan_timeout_kills_child_and_reports_unavailable_instead_of_hanging(self):
  process=Mock();process.poll.return_value=None
  process.communicate.side_effect=[subprocess.TimeoutExpired('ffmpeg',.5),(b'',b'')]
  context=Mock();context.__enter__=Mock(return_value=process);context.__exit__=Mock(return_value=False)
  with patch('natural_schedule.subprocess.Popen',return_value=context),patch('natural_schedule.time.monotonic',side_effect=[0,121]):
   with self.assertRaisesRegex(RuntimeError,'兩分鐘上限'):schedule.cut_scan({},['ffmpeg'])
  process.kill.assert_called_once()
 def test_cooperative_skip_kills_scene_scan_without_being_swallowed(self):
  from track_control import UserSkipped
  process=Mock();process.poll.return_value=None
  context=Mock();context.__enter__=Mock(return_value=process);context.__exit__=Mock(return_value=False)
  with patch('natural_schedule.subprocess.Popen',return_value=context),patch('track_control.check',side_effect=UserSkipped('Stop')):
   with self.assertRaises(UserSkipped):schedule.cut_scan({},['ffmpeg'])
  process.kill.assert_called_once()
