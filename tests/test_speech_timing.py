import array,copy,json,math,shutil,subprocess,sys,tempfile,unittest,wave
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import speech_timing,dubbing

class SpeechTimingTests(unittest.TestCase):
 @unittest.skipUnless(shutil.which('ffmpeg'),'FFmpeg required')
 def test_explicitly_accepted_recording_renders_with_reported_small_overlap(self):
  sr=24000;ff=shutil.which('ffmpeg')
  def run(args):return subprocess.check_output([str(a) for a in args],stderr=subprocess.DEVNULL)
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);p=root/'accepted.wav'
   raw=array.array('h',(round(3000*math.sin(i*2*math.pi*300/sr)) for i in range(sr)))
   with wave.open(str(p),'wb') as f:f.setparams((1,2,sr,0,'NONE','not compressed'));f.writeframes(raw.tobytes())
   cue=dict(start=0,end=.7,cantonese='完整錄音',manualReviewChoice='accepted-defect-recording')
   following=dict(start=.7,end=1.5,cantonese='下一句')
   row=dict(index=1,seconds=1.,slot=.7)
   audio,warnings=dubbing.render_complete_preview(dict(duration=2,ffmpeg=ff,strictSpeechTiming=True,speechRatePolicy='natural'),root,[cue,following],[p],[row],run,lambda *a:None)
   self.assertTrue(audio.is_file());self.assertEqual(row['renderedSeconds'],1.)
   self.assertTrue(row['acceptedTimingOverlap']);self.assertTrue(row['requiresTimingReview'])
   self.assertIn('timing-overrun',[w['kind'] for w in warnings])
   with wave.open(str(audio)) as f:self.assertEqual(f.getnframes(),sr*2)
 def test_duration_budget_is_concise_and_short_reactions_stay_short(self):
  self.assertEqual(speech_timing.text_budget(.38),1)
  self.assertEqual(speech_timing.text_budget(2),9)
  self.assertEqual(speech_timing.text_budget(5),22)
 def test_window_uses_speech_bounds_and_keeps_source_overlap(self):
  a=dict(start=0,end=3,speechStart=.3,speechEnd=1.8,deliveryEnd=2.5)
  b=dict(start=1.5,end=4,speechStart=1.5,speechEnd=4,speakerId='another')
  self.assertEqual(speech_timing.window(a,[a,b],4),(.3,1.8))
 def test_actual_samples_are_measured_and_no_trimming_filter_is_used(self):
  calls=[];raw=b'\1\0'*48000
  def run(args):
   calls.append(args);rate=1
   for step in args[args.index('-af')+1].split(','):rate*=float(step.split('=')[1])
   return b'\1\0'*round((2/rate+.025)*24000)
  result,rate=speech_timing.fit_pcm(dict(ffmpeg='ffmpeg'),raw,.7,run)
  self.assertLessEqual(len(result)//2,16800);self.assertGreater(rate,2)
  self.assertTrue(all('atrim' not in ' '.join(map(str,c)) for c in calls))
  self.assertEqual(raw,b'\1\0'*48000)
 @unittest.skipUnless(shutil.which('ffmpeg'),'FFmpeg required')
 def test_real_overlong_takes_never_cross_next_turn_and_no_source_clock_changes(self):
  sr=24000;ff=shutil.which('ffmpeg')
  def run(args):return subprocess.check_output([str(a) for a in args],stderr=subprocess.DEVNULL)
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);paths=[]
   for n,hz in enumerate((270,410)):
    p=root/f'{n}.wav'
    raw=array.array('h',(round(4500*math.sin(i*2*math.pi*hz/sr)) for i in range(sr*2))).tobytes()
    with wave.open(str(p),'wb') as f:f.setparams((1,2,sr,0,'NONE','not compressed'));f.writeframes(raw)
    paths.append(p)
   cues=[dict(start=0,end=.7,speechStart=.1,speechEnd=.7,text='jp',cantonese='香港廣東話第一句'),dict(start=.7,end=1.5,text='jp',cantonese='第二句')]
   original=copy.deepcopy(cues)
   rows=[dict(index=i+1,seconds=2,slot=c['end']-c.get('speechStart',c['start'])) for i,c in enumerate(cues)]
   audio,warnings=dubbing.render_complete_preview(dict(duration=1.5,ffmpeg=ff,strictSpeechTiming=True),root,cues,paths,rows,run,lambda *a:None)
   for c,old,row in zip(cues,original,rows):
    self.assertEqual((c['start'],c['end']),(old['start'],old['end']))
    self.assertLessEqual(row['renderedEnd'],c.get('speechEnd',c['end']))
    self.assertEqual(row['overrun'],0);self.assertFalse(row['requiresTimingReview'])
    self.assertTrue(Path(row['renderedAudio']).is_file())
   self.assertEqual(rows[1]['overlaps'],[])
   with wave.open(str(audio)) as f:self.assertEqual(f.getnframes(),36000)
   self.assertTrue(any(w['kind']=='accelerated-delivery' for w in warnings))

if __name__=='__main__':unittest.main()
