import json,math,subprocess,sys,tempfile,unittest,wave
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import mix_balance

class AudibilityTests(unittest.TestCase):
 def test_float_separator_stem_is_decoded_for_analysis_without_changing_the_mix_source(self):
  ffmpeg=Path(__file__).resolve().parents[1]/'dist/AniCanto.app/Contents/Resources/bin/ffmpeg'
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);sr=24000;t=np.arange(sr)/sr
   with wave.open(str(p/'voice.wav'),'wb') as f:f.setparams((1,2,sr,0,'NONE','not compressed'));f.writeframes((.05*np.sin(2*np.pi*200*t)*32767).astype('<i2').tobytes())
   subprocess.run([str(ffmpeg),'-v','error','-i',str(p/'voice.wav'),'-c:a','pcm_f32le',str(p/'float.wav')],check=True)
   before=(p/'float.wav').read_bytes()
   (p/'timing.json').write_text(json.dumps([dict(index=1,start=0.,end=1.,renderedAudio=str(p/'voice.wav'),renderedSeconds=1.)]))
   self.assertEqual(mix_balance.resolve(dict(aiAutoFix=True,ffmpeg=str(ffmpeg)),p,p/'float.wav'),'auto')
   report=json.loads((p/'mix-audibility.json').read_text());self.assertEqual(report['status'],'checked');self.assertEqual(len(report['rows']),1)
   self.assertEqual(before,(p/'float.wav').read_bytes())
   self.assertEqual(len(list((p/'mix-balance').glob('*.wav'))),1)

 def test_auto_fix_measures_foreground_instead_of_loud_movie_peaks(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);sr=24000;t=np.arange(3*sr)/sr
   for name,x in [('voice',.06*np.sin(2*np.pi*200*t)*((t>1)&(t<2))),('bed',.1*np.sin(2*np.pi*700*t)),('silence',np.zeros(len(t)))]:
    with wave.open(str(p/(name+'.wav')),'wb') as f:f.setparams((1,2,sr,0,'NONE','not compressed'));f.writeframes((x*32767).astype('<i2').tobytes())
   row=dict(index=1,start=0.,end=3.,renderedStart=0.,renderedEnd=3.,renderedAudio=str(p/'voice.wav'),renderedSeconds=3.)
   (p/'timing.json').write_text(json.dumps([row]))
   cfg=dict(aiAutoFix=True,backgroundDucking=False,backgroundGain=.8)
   before=(p/'voice.wav').read_bytes(),(p/'bed.wav').read_bytes()
   self.assertEqual(mix_balance.resolve(cfg,p,p/'bed.wav'),'auto')
   report=json.loads((p/'mix-audibility.json').read_text());self.assertTrue(report['rows'][0]['masked'])
   self.assertEqual(before,((p/'voice.wav').read_bytes(),(p/'bed.wav').read_bytes()))
   self.assertFalse(mix_balance.resolve(dict(cfg,aiAutoFix=False),p,p/'bed.wav'));self.assertFalse((p/'mix-audibility.json').exists())
   row['renderedAudio']=str(p/'silence.wav');(p/'timing.json').write_text(json.dumps([row]))
   self.assertFalse(mix_balance.resolve(cfg,p,p/'bed.wav'),'Silence is missing speech, not a mixing problem')

 def test_automatic_ducking_is_bounded_and_does_not_attenuate_voice_or_non_speech_music(self):
  ffmpeg=Path(__file__).resolve().parents[1]/'dist/AniCanto.app/Contents/Resources/bin/ffmpeg'
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);sr=24000;t=np.arange(3*sr)/sr
   for name,x in [('voice',.06*np.sin(2*np.pi*200*t)*((t>1)&(t<2))),('bg',.1*np.sin(2*np.pi*700*t))]:
    with wave.open(str(p/(name+'.wav')),'wb') as f:f.setparams((1,2,sr,0,'NONE','not compressed'));f.writeframes((x*32767).astype('<i2').tobytes())
   rendered=[]
   for mode in (False,'auto'):
    raw=subprocess.check_output([str(ffmpeg),'-v','error','-i',str(p/'bg.wav'),'-i',str(p/'voice.wav'),'-i',str(p/'bg.wav'),'-i',str(p/'bg.wav'),'-filter_complex',mix_balance.separated_filter(.8,duck=mode),'-map','[dub]','-ar',str(sr),'-ac','1','-f','f32le','pipe:1'])
    x=np.frombuffer(raw,dtype='<f4')
    def amplitude(a,b,hz):
     clip=x[round(a*sr):round(b*sr)];return float(abs(np.mean(clip*np.exp(-2j*np.pi*hz*t[:len(clip)])))*2)
    rendered.append((amplitude(.3,.7,700),amplitude(1.3,1.7,700),amplitude(1.3,1.7,200)))
   before,after=rendered
   self.assertAlmostEqual(before[0],after[0],delta=.001)
   self.assertLess(after[1],before[1]*.9);self.assertGreaterEqual(after[1],before[1]*.395)
   self.assertAlmostEqual(before[2],after[2],delta=.001)

class FallbackAudibilityTests(unittest.TestCase):
 def test_repaired_overlay_measures_its_own_voice_and_cannot_restore_a_masking_bed(self):
  from audio_fallback import background_gain
  from array import array
  sr=24000;t=np.arange(sr)/sr
  voice=array('h',(.04*np.sin(2*np.pi*200*t)*32767).astype('<i2').tobytes())
  bed=array('h',(.3*np.sin(2*np.pi*700*t)*32767).astype('<i2').tobytes())
  overlays=[(0.,voice,1.,dict(index=1))]
  gain,report=background_gain(dict(aiAutoFix=True,backgroundGain=.8),bed,sr,overlays,0.,1.)
  self.assertTrue(report['automatic']);self.assertLessEqual(gain,.17);self.assertGreaterEqual(gain,.16)
  unchanged,_=background_gain(dict(aiAutoFix=False,backgroundGain=.8),bed,sr,overlays,0.,1.)
  self.assertEqual(unchanged,.8)
  muted,_=background_gain(dict(aiAutoFix=True,backgroundGain=0),bed,sr,overlays,0.,1.)
  self.assertEqual(muted,0)
