import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import nonverbal
class NonverbalTests(unittest.TestCase):
 def test_many_preservation_ranges_keep_stereo_mask_and_speech_gaps(self):
  import tempfile,wave,numpy as np
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'mask.wav'
   nonverbal.write_preservation_mask(path,[(i+.2,i+.7) for i in range(250)],250,rate=1000)
   with wave.open(str(path)) as f:
    self.assertEqual((f.getnchannels(),f.getnframes()),(2,250000))
    samples=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').reshape(-1,2)
   self.assertTrue(np.array_equal(samples[:,0],samples[:,1]))
   for i in (0,124,249):
    self.assertEqual(samples[i*1000+100,0],0)
    self.assertEqual(samples[i*1000+350,0],32767)
    self.assertTrue(0<samples[i*1000+220,0]<32767)
    self.assertEqual(samples[i*1000+750,0],0)
 def test_preservation_mask_rejects_invalid_ranges(self):
  import tempfile
  with tempfile.TemporaryDirectory() as directory:
   for spans in ([(-1,1)],[(1,3)],[(float('nan'),1)]):
    with self.assertRaises(ValueError):nonverbal.write_preservation_mask(Path(directory)/'mask.wav',spans,2)
 def test_word_evidence_preserves_confirmed_laugh_inside_turn_pause(self):
  cue=dict(start=0,end=5,japanese='今日は晴れ')
  words=[dict(start=0,end=1,word='今日は'),dict(start=4,end=5,word='晴れ')]
  lexical=nonverbal.lexical_ranges([cue],words)
  events=nonverbal.event_ranges([dict(start=2,duration=1,laughter=.9)],lexical,5)
  self.assertEqual([(e['start'],e['end']) for e in events],[(2,3)])
  self.assertEqual(nonverbal.lexical_ranges([cue],words[:1]),[cue])
  self.assertEqual(nonverbal.lexical_ranges([cue],[]),[cue])
 def test_requires_acoustic_evidence_not_just_absence_of_transcript(self):
  self.assertEqual(nonverbal.event_ranges([dict(start=1,duration=2,speech=.8,laughter=.9)],[],5),[])
  self.assertEqual(nonverbal.event_ranges([dict(start=1,duration=2,laughter=.3)],[],5),[])
 def test_preserve_timing_but_remove_lexical_speech(self):
  rows=[dict(start=1,duration=3,laughter=.8,speech=.05)]
  events=nonverbal.event_ranges(rows,[dict(start=2,end=3)],5)
  self.assertEqual([(e['start'],e['end']) for e in events],[(1,1.88),(3.15,4)])
 def test_scream_survives_but_never_reintroduces_lexical_japanese(self):
  rows=[dict(start=1,duration=3,screaming=.92,speech=.85)]
  scream=dict(start=1,end=2,japanese='ああああああ！')
  self.assertTrue(nonverbal.source_vocalization(scream))
  events=nonverbal.event_ranges(rows,[scream,dict(start=3,end=4,japanese='助けて')],5)
  self.assertEqual([(e['start'],e['end']) for e in events],[(1,2.88)])
  self.assertFalse(nonverbal.source_vocalization(dict(japanese='いやだ！')))
  self.assertEqual(nonverbal.event_ranges([dict(start=1,duration=2,screaming=.6,speech=.8)],[],5),[])
 def test_overlap_merges_once_and_does_not_exceed_video(self):
  events=nonverbal.event_ranges([dict(start=1,duration=2,gasp=.9),dict(start=2,duration=3,gasp=.9)],[],4)
  self.assertEqual([(e['start'],e['end']) for e in events],[(1,4)])
 def test_overlap_ducks_only_affected_sound_not_entire_event(self):
  events=nonverbal.duck_events([dict(start=1,end=4,label='laughter',confidence=.9)],[dict(start=2,end=3)])
  self.assertEqual([(e['start'],e['end'],e['gain']) for e in events],[(1,2,1.0),(2,3,.4),(3,4,1.0)])
 def test_original_audio_requires_analysis_and_excludes_uncertain_windows(self):
  rows=[dict(start=0,duration=5,speech=.01),dict(start=2,duration=1,speech=.8)]
  self.assertEqual(nonverbal.original_sound_ranges(rows,[],5),[(0,2),(3,5)])
  self.assertEqual(nonverbal.original_sound_ranges([],[],5),[])
  self.assertEqual(nonverbal.original_sound_ranges([dict(start=0,duration=5)],[],5),[])
 def test_original_audio_protects_words_and_avoids_duplicate_laughter(self):
  ranges=nonverbal.original_sound_ranges([dict(start=0,duration=5,speech=.01)],[dict(start=1,end=2)],5)
  self.assertEqual(ranges,[(0,.8),(2.2,5)])
  events=nonverbal.subtract_restored([dict(start=0,end=5,label='laughter')],ranges)
  self.assertEqual([(e['start'],e['end']) for e in events],[(.8,2.2)])

class ShortFadeTests(unittest.TestCase):
 def test_exact_25ms_remainder_is_a_valid_ffmpeg_duration(self):
  import tempfile,json,subprocess
  from unittest.mock import patch
  ffmpeg=Path(__file__).parents[1]/'dist/AniCanto.app/Contents/Resources/bin/ffmpeg'
  if not ffmpeg.exists():self.skipTest('Bundled ffmpeg unavailable')
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder);voice=p/'voice.wav'
   subprocess.run([str(ffmpeg),'-v','error','-f','lavfi','-i','sine=frequency=440:duration=1','-y',str(voice)],check=True)
   (p/'nonverbal-classification-v2.json').write_text('[]')
   # Exact source values that produced an invalid scientific-notation fade.
   event=dict(start=1024.,end=1024.025,label='gasp',confidence=.9)
   commands=[]
   def run(cmd):
    commands.append(cmd)
    return subprocess.check_output([str(x) for x in cmd],stderr=subprocess.STDOUT)
   with patch.object(nonverbal,'classification',return_value=[]),patch.object(nonverbal,'event_ranges',return_value=[event]),patch.object(nonverbal,'original_sound_ranges',return_value=[]):
    out=nonverbal.restore(dict(ffmpeg=str(ffmpeg),duration=1100,dialoguePath=str(voice),executable='unused'),p,[],voice,run,lambda *a:None)
   graph=commands[0][commands[0].index('-filter_complex')+1]
   self.assertIn('afade=t=out:st=0.000000',graph)
   self.assertTrue(out.exists())
