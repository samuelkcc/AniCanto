import json,sys,tempfile,unittest,subprocess,shutil,wave,array
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import mixed_speech_check as mix,ai_result_repair as ai

class EncodedSpeechTests(unittest.TestCase):
 def case(self,root):
  cue=dict(start=0.,end=1.,cantonese='我哋一定唔可以走',speakerId='speaker')
  (root/'review.json').write_text(json.dumps(dict(cues=[cue],config={})))
  movie=root/'movie.mp4';movie.write_bytes(b'identity')
  return cue,dict(folder=root,output=movie,language='yue',engine='drama3',id='drama3',report={})
 def save(self,p,v):p.write_text(json.dumps(v))
 def test_actual_primary_encoded_audio_is_checked_even_with_healthy_native_take(self):
  ffmpeg=shutil.which('ffmpeg')
  if not ffmpeg:self.skipTest('FFmpeg unavailable')
  def run(args):return subprocess.check_output([str(a) for a in args],stderr=subprocess.PIPE)
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);cue,track=self.case(root);healthy=root/'healthy.wav'
   with wave.open(str(healthy),'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(array.array('h',[5000,-5000]*12000).tobytes())
   run([ffmpeg,'-v','error','-y','-f','lavfi','-i','anullsrc=r=24000:cl=mono','-i',healthy,'-map','0:a','-map','1:a','-t','1','-c:a','aac',track['output']])
   self.save(root/'timing.json',[dict(index=1,start=0.,end=1.,renderedAudio=str(healthy),renderedStart=0.,renderedEnd=1.,renderedSeconds=1,text=cue['cantonese'])])
   def listen(cfg,folder,cues,paths,emit):
    with wave.open(str(paths[0])) as f:pcm=array.array('h',f.readframes(f.getnframes()))
    self.assertLess(max(map(abs,pcm)),5,'must inspect silent primary audio, not healthy second/native take')
    return [dict(heard='',similarity=0,languageUnverified=True)]
   w=SimpleNamespace(run=run,atomic_json=self.save,emit=lambda *a:None)
   with patch('speechcheck.inspect',side_effect=listen):result=mix.inspect(w,dict(ffmpeg=ffmpeg),track)
   self.assertEqual(result['strongFailures'],[1])
   self.assertTrue(ai.collect(track,[track])[0]['contentFailure'])
 def test_encoded_failures_override_verified_isolated_donors_and_cache_expires(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);cue,track=self.case(root);audio=root/'donor.wav'
   with wave.open(str(audio),'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(array.array('h',[4000,-4000]*12000).tobytes())
   track['report']['audioFallbacks']=[dict(index=1,text=cue['cantonese'],speakerId='speaker',sourceLanguage='yue',start=0.,end=1.,audio=str(audio))]
   self.save(root/'timing.json',[dict(index=1,start=0.,end=1.,renderedSeconds=1,renderedAudio=str(audio),text=cue['cantonese'])])
   self.save(root/'post-mix-speech-check.json',dict(revision=mix.REVISION,movie=mix.identity(track['output']),scripts=mix.script_identity([cue]),rows=[dict(index=1,strongContentFailure=True,criticalDifferences=['negation:唔'])]))
   self.assertTrue(ai.collect(track,[track])[0]['contentFailure'])
   track['output'].write_bytes(b'new encoded movie')
   self.assertEqual(mix.fresh(track),{})
   self.assertEqual(ai.collect(track,[track]),[])
 def test_changed_script_invalidates_encoded_verification(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);cue,track=self.case(root)
   self.save(root/'post-mix-speech-check.json',dict(revision=mix.REVISION,movie=mix.identity(track['output']),scripts=mix.script_identity([cue]),rows=[]))
   self.assertTrue(mix.fresh(track))
   cue['cantonese']='我哋而家可以走';self.save(root/'review.json',dict(cues=[cue]))
   self.assertEqual(mix.fresh(track),{})
 def test_incomplete_listener_result_cannot_be_cached_as_success(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);cue,track=self.case(root)
   w=SimpleNamespace(run=lambda args:None,atomic_json=self.save,emit=lambda *a:None)
   with patch('speechcheck.inspect',return_value=[]),self.assertRaisesRegex(ValueError,'數量不完整'):mix.inspect(w,dict(ffmpeg='ffmpeg'),track)
   self.assertFalse((root/'post-mix-speech-check.json').exists())

class AutomaticBackgroundRecoveryTests(unittest.TestCase):
 case=EncodedSpeechTests.case
 save=EncodedSpeechTests.save
 def test_verified_foreground_lost_in_encoded_mix_gets_background_trial_not_tts(self):
  ffmpeg=shutil.which('ffmpeg')
  if not ffmpeg:self.skipTest('FFmpeg unavailable')
  def run(args):return subprocess.check_output([str(a) for a in args],stderr=subprocess.PIPE)
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);cue,track=self.case(root);voice=root/'voice.wav';bg=root/'background.wav'
   for path,level in ((voice,5000),(bg,250)):
    with wave.open(str(path),'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(array.array('h',[level,-level]*12000).tobytes())
   track['report']['audioFallbacks']=[dict(index=1,text=cue['cantonese'],speakerId='speaker',sourceLanguage='yue',audio=str(voice),renderedStart=0.,renderedEnd=1.)]
   self.save(root/'post-mix-speech-check.json',dict(revision=mix.REVISION,movie=mix.identity(track['output']),scripts=mix.script_identity([cue]),rows=[],strongFailures=[1]))
   good=dict(expected=cue['cantonese'],heard=cue['cantonese'],textMatches=True,requiresReview=False,languageMismatch=False,languageUnverified=False)
   calls=[]
   def listen(cfg,folder,cues,paths,emit):
    calls.append(paths[0]);self.assertTrue(Path(paths[0]).is_file());return [good]
   w=SimpleNamespace(run=run,atomic_json=self.save,emit=lambda *a:None)
   with patch('speechcheck.inspect',side_effect=listen):self.assertTrue(mix.recover_background(w,dict(aiAutoFix=True,backgroundPath=str(bg),backgroundGain=.8,ffmpeg=ffmpeg),root,[track]))
   self.assertEqual(len(calls),2);self.assertEqual(calls[0],voice);self.assertEqual(calls[1].suffix,'.m4a')
   cap=track['report']['fallbackBackgroundCaps'][0];self.assertAlmostEqual(cap['maximumGain'],.32)
   import audio_fallback,hashlib
   pcm=array.array('h',[5000,-5000]*12000);bed=array.array('h',[250,-250]*12000)
   overlay=dict(index=1,text=cue['cantonese'],speakerId='speaker',audio=str(voice),renderedStart=0.,renderedEnd=1.)
   cfg=dict(aiAutoFix=True,backgroundGain=.8,backgroundPath=str(bg),_fallbackBackgroundCaps=[cap])
   gain,measured=audio_fallback.background_gain(cfg,bed,24000,[(0.,pcm,1.,overlay)],0.,1.)
   self.assertAlmostEqual(gain,.32);self.assertEqual(measured['evidence'],'verified-foreground-and-encoded-background-trial')
   voice.write_bytes(b'new foreground')
   gain,_=audio_fallback.background_gain(cfg,bed,24000,[(0.,pcm,1.,overlay)],0.,1.)
   self.assertEqual(gain,.8,'A changed take must invalidate a prior background cap')
 def test_unverified_foreground_is_not_accepted_by_silencing_background(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);cue,track=self.case(root);bg=root/'bed.wav';bg.write_bytes(b'bed');voice=root/'voice.wav';voice.write_bytes(b'voice')
   track['report']['audioFallbacks']=[dict(index=1,text=cue['cantonese'],speakerId='speaker',sourceLanguage='yue',audio=str(voice),renderedStart=0.)]
   self.save(root/'post-mix-speech-check.json',dict(revision=mix.REVISION,movie=mix.identity(track['output']),scripts=mix.script_identity([cue]),strongFailures=[1]))
   w=SimpleNamespace(run=lambda a:self.fail('must not mix unverified foreground'),atomic_json=self.save,emit=lambda *a:None)
   bad=dict(heard='',similarity=0,languageMismatch=True)
   with patch('speechcheck.inspect',return_value=[bad]),patch('cantonese_alignment.verify',return_value=dict(accepted=False)):
    self.assertFalse(mix.recover_background(w,dict(aiAutoFix=True,backgroundPath=str(bg)),root,[track]))
   self.assertNotIn('fallbackBackgroundCaps',track['report'])
