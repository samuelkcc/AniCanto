import array,json,math,shutil,subprocess,sys,tempfile,unittest,wave
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
from preview_continuity import fill
from dialogue_delivery import audit

def run(args):return subprocess.check_output([str(x) for x in args],stderr=subprocess.PIPE)

class PreviewContinuityTests(unittest.TestCase):
 @unittest.skipUnless(shutil.which('ffmpeg'),'FFmpeg required')
 def test_source_fills_preview_gap_but_never_counts_as_completed_translation(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);source=job/'source.wav';sr=24000
   with wave.open(str(source),'wb') as f:f.setparams((1,2,sr,0,'NONE','not compressed'));f.writeframes(array.array('h',(round(math.sin(i*.1)*4000) for i in range(3*sr))).tobytes())
   cfg=dict(productionMode='normal',duration=3,dialoguePath=str(source),ffmpeg=shutil.which('ffmpeg'));cue=dict(start=1,end=2,cantonese='你好呀',speakerId='r');row=dict(index=1,start=1,end=2,text='你好呀',skipped=True,renderedSeconds=0,failureKind='timing-overrun');timeline=array.array('i',[0])*(3*sr)
   self.assertTrue(fill(cfg,job,cue,row,timeline,run,sr));self.assertTrue(any(timeline[sr:2*sr]));self.assertFalse(any(timeline[:sr]));self.assertTrue(row['skipped']);self.assertTrue(row['originalFallback']);self.assertFalse(row['qualityCertified'])
   (job/'timing.json').write_text(json.dumps([row]));(job/'review.json').write_text(json.dumps(dict(config=cfg,cues=[cue])))
   coverage=audit([dict(folder=job,engine='drama3',language='yue')]);self.assertEqual(coverage['status'],'missing-dialogue');self.assertEqual(coverage['tracks'][0]['available'],0)
 def test_editor_never_gets_automatic_source_substitution(self):
  self.assertFalse(fill(dict(productionMode='normal',editorRender=True),'.',dict(start=0,end=1),{},[],None,24000))
