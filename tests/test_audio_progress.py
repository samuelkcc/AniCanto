import array,json,sys,tempfile,time,unittest,wave,subprocess
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import track_control,processing_time,audio_fallback
class AudioProgressTests(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
 def tearDown(self):self.temp.cleanup()
 def wav(self,path,value=4000,seconds=.4):
  with wave.open(str(path),'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(array.array('h',[value,-value]*round(seconds*12000)).tobytes())
 def test_missing_model_recovers_only_explicit_ready_choice(self):
  import model_recovery,model_catalog
  (self.root/'model-selections.json').write_text(json.dumps({'qwen-tts':'qwen-0.6b-8bit'}))
  cfg=dict(storage=str(self.root),ttsBackend='qwen-tts',qwenModel='qwen-0.6b-4bit')
  def resolve(root,ident):
   if ident.endswith('4bit'):raise ValueError('missing')
   return self.root
  with patch.object(model_catalog,'resolve',side_effect=resolve):model_recovery.recover(cfg,lambda *a,**k:None)
  self.assertEqual(cfg['qwenModel'],'qwen-0.6b-8bit');self.assertEqual(len(cfg['modelRecovery']),1)
  cfg['qwenModel']='qwen-0.6b-4bit'
  with patch.object(model_catalog,'resolve',return_value=self.root):model_recovery.recover(cfg,lambda *a,**k:None)
  self.assertEqual(cfg['qwenModel'],'qwen-0.6b-4bit')
 def test_missing_selected_model_uses_other_downloaded_memory_safe_variant(self):
  import model_recovery,model_catalog
  (self.root/'model-selections.json').write_text(json.dumps({'qwen-tts':'qwen-0.6b-8bit'}))
  cfg=dict(storage=str(self.root),ttsBackend='qwen-tts',qwenModel='qwen-0.6b-4bit',modelMemoryBudgetGB=10)
  def resolve(root,ident):
   if ident!='qwen-0.6b-bf16':raise ValueError('missing')
   return self.root
  with patch.object(model_catalog,'resolve',side_effect=resolve):model_recovery.recover(cfg,lambda *a,**k:None)
  self.assertEqual(cfg['qwenModel'],'qwen-0.6b-bf16')
 def test_missing_model_never_selects_arbitrary_or_incomplete_model(self):
  import model_recovery,model_catalog
  (self.root/'model-selections.json').write_text(json.dumps({'qwen-tts':'qwen-0.6b-8bit'}))
  cfg=dict(storage=str(self.root),ttsBackend='qwen-tts',qwenModel='qwen-0.6b-4bit')
  with patch.object(model_catalog,'resolve',side_effect=ValueError('incomplete')):model_recovery.recover(cfg,lambda *a,**k:None)
  self.assertEqual(cfg['qwenModel'],'qwen-0.6b-4bit');self.assertNotIn('modelRecovery',cfg)
 def test_skip_token_cannot_skip_next_channel(self):
  c=dict(folder=str(self.root),token='old');(self.root/'skip-generation.json').write_text(json.dumps(c))
  with self.assertRaises(track_control.UserSkipped):track_control.check(dict(_trackControl=c))
  track_control.check(dict(_trackControl=dict(c,token='new')))
 def test_time_resume_accumulates_without_idle(self):
  request=dict(review=str(self.root/'review.json'));clock=[1000.]
  @processing_time.measured
  def nested(r):time.sleep(.03)
  @processing_time.measured
  def work(r):nested(r)
  # Assert accounting with a deterministic clock: filesystem/GPU contention
  # must not turn a timer invariant into a wall-time performance test.
  with patch.object(processing_time.time,'monotonic',side_effect=lambda:clock[0]),patch.object(time,'sleep',side_effect=lambda s:clock.__setitem__(0,clock[0]+s)):
   work(request);first=json.loads((self.root/'processing-time.json').read_text())
   time.sleep(.06);work(request);last=json.loads((self.root/'processing-time.json').read_text())
  self.assertEqual(len(last['runs']),2);self.assertAlmostEqual(first['seconds'],.03);self.assertAlmostEqual(last['seconds'],.06)
 def test_export_timing_stays_in_project_and_survives_reload(self):
  output=self.root/'episode-AniCanto.mp4';output.write_bytes(b'fixture')
  exported=self.root/'external-AniCanto.mp4';exported.write_bytes(b'fixture')
  @processing_time.measured
  def work(r):
   time.sleep(.01)
   (self.root/'report.json').write_text(json.dumps(dict(output=str(output),exportedOutput=str(exported))))
  work(dict(review=str(self.root/'review.json')))
  first=json.loads((self.root/'export-timing.json').read_text())
  self.assertGreater(first['seconds'],0);self.assertTrue(first['excludesPausedTime'])
  self.assertFalse(exported.with_suffix('.processing-time.json').exists());self.assertFalse(output.with_suffix('.processing-time.json').exists())
  saved=(self.root/'export-timing.json').read_bytes()
  @processing_time.measured
  def failed(r):raise RuntimeError('stopped')
  with self.assertRaises(RuntimeError):failed(dict(review=str(self.root/'review.json')))
  self.assertEqual((self.root/'export-timing.json').read_bytes(),saved)
 def test_category_timers_survive_resume_without_counting_idle_as_llm(self):
  request=dict(review=str(self.root/'review.json'));clock=[1000.]
  @processing_time.measured
  def work(r):
   processing_time.checkpoint(stage='場景改編');time.sleep(.02)
   processing_time.checkpoint(stage='配音');time.sleep(.02)
  with patch.object(processing_time.time,'monotonic',side_effect=lambda:clock[0]),patch.object(time,'sleep',side_effect=lambda s:clock.__setitem__(0,clock[0]+s)):
   work(request);first=json.loads((self.root/'processing-time.json').read_text())
   time.sleep(.06);work(request);last=json.loads((self.root/'processing-time.json').read_text())
  self.assertAlmostEqual(first['categorySeconds']['script'],.02)
  self.assertAlmostEqual(first['categorySeconds']['voice'],.02)
  self.assertAlmostEqual(last['categorySeconds']['script'],.04)
  self.assertAlmostEqual(last['categorySeconds']['voice'],.04)
  self.assertAlmostEqual(sum(last['categorySeconds'].values()),last['seconds'])
 def test_donor_only_same_language_and_not_bad_content(self):
  path=self.root/'voice.wav';self.wav(path)
  row=dict(index=1,start=0,end=1,renderedAudio=str(path))
  d=self.root/'donor';d.mkdir();(d/'timing.json').write_text(json.dumps([row]));target=dict(language='yue')
  donor=dict(language='en',folder=d,engine='gpt-sovits')
  self.assertIsNone(audio_fallback.choose(row,target,[donor]))
  donor['language']='yue';self.assertIsNotNone(audio_fallback.choose(row,target,[donor]))
  (d/'validation.json').write_text(json.dumps(dict(contentReviewIndices=[1])))
  self.assertIsNone(audio_fallback.choose(row,target,[donor]))
 def test_silent_and_partial_files_are_not_good_donors(self):
  p=self.root/'silence.wav';self.wav(p,0);self.assertFalse(audio_fallback.healthy(p))
  p.write_bytes(b'RIFF');self.assertFalse(audio_fallback.healthy(p))
 def test_manual_skip_keeps_completed_takes_even_in_strict_mode(self):
  import dubbing,engine_reference,qwen_reference
  reference=self.root/'reference.wav';self.wav(reference,seconds=4)
  cfg=dict(storage=str(self.root),ttsBackend='gpt-sovits',gsvReferenceMode='original',continueOnError=False,voiceProfiles=[])
  profile=dict(id='actor',name='Actor',reference=str(reference),language='ja',promptText='test')
  cues=[dict(start=i,end=i+.5,cantonese='Test '+str(i),speakerId='actor',reviewIndex=i) for i in range(2)]
  first=[]
  def model(c,a,req,emit):
   first.append(Path(req['items'][0]['output']));self.wav(first[0]);raise track_control.UserSkipped('requested')
  with patch.object(dubbing,'profile_for',return_value=profile),patch.object(engine_reference,'prepare',return_value=profile),patch.object(qwen_reference,'prepare',return_value=profile),patch.object(dubbing,'model_job',side_effect=model):
   result=dubbing.gsv_audio(cfg,self.root,cues,lambda *a:None,lambda *a,**k:None)
  self.assertEqual(result[0],first[0]);self.assertTrue(audio_fallback.healthy(result[0]));self.assertTrue(result[1].name.startswith('skipped-'))
  self.assertEqual(json.loads((self.root/'segment-issues.json').read_text())[0]['kind'],'user-skipped')
 def test_whole_engine_failure_keeps_channel_marked_fallback(self):
  ffmpeg=str(Path(__file__).resolve().parents[1]/'dist/AniCanto.app/Contents/Resources/bin/ffmpeg')
  def run(args):return subprocess.run([str(a) for a in args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
  movie=self.root/'source.mp4';run([ffmpeg,'-v','error','-y','-f','lavfi','-i','color=s=64x64:d=1:r=10','-f','lavfi','-i','sine=frequency=440:sample_rate=24000:duration=1','-c:v','libx264','-c:a','aac',movie])
  cfg=dict(ffmpeg=ffmpeg,video=str(movie),duration=1)
  cues=[dict(start=0,end=.5,cantonese='Test')];row=audio_fallback.original_placeholder(cfg,self.root/'failed','qwen-tts','en',cues,run)
  self.assertTrue(row['report']['generationFailed']);fallbacks=audio_fallback.repair(cfg,self.root,[row],run,lambda *a,**k:None)
  self.assertEqual(fallbacks,[]);self.assertEqual(row['report']['japaneseFallback'],0);self.assertEqual(row['report']['unresolvedFallbackIndices'],[1])
 def test_authorized_donor_repairs_missing_cue_but_never_falls_back_to_japanese(self):
  ffmpeg=str(Path(__file__).resolve().parents[1]/'dist/AniCanto.app/Contents/Resources/bin/ffmpeg')
  if not Path(ffmpeg).exists():self.skipTest('bundled ffmpeg required')
  def run(args):return subprocess.run([str(a) for a in args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
  native=self.root/'native.wav';jp=self.root/'jp.wav';self.wav(native,3000);self.wav(jp,7000,2)
  movie=self.root/'base.mp4';run([ffmpeg,'-v','error','-y','-f','lavfi','-i','color=s=64x64:d=2:r=10','-f','lavfi','-i','anullsrc=r=24000:cl=mono','-t','2','-c:v','libx264','-c:a','aac',movie])
  target_folder=self.root/'target';target_folder.mkdir();donor_folder=self.root/'donor';donor_folder.mkdir()
  missing=[dict(index=1,start=0,end=.4,skipped=True),dict(index=2,start=1,end=1.4,skipped=True)]
  (target_folder/'timing.json').write_text(json.dumps(missing));(target_folder/'report.json').write_text('{}')
  (donor_folder/'timing.json').write_text(json.dumps([dict(index=1,start=0,end=.4,renderedStart=0,renderedAudio=str(native))]))
  target=dict(id='qwen-tts',engine='qwen-tts',language='yue',folder=target_folder,output=movie,report=dict(duration=2));donor=dict(id='gpt-sovits',engine='gpt-sovits',language='yue',folder=donor_folder,output=movie,report=dict(duration=2))
  rows=audio_fallback.repair(dict(ffmpeg=ffmpeg,dialoguePath=str(jp),selectedEngines=['qwen-tts','gpt-sovits'],allowCrossEngineRepair=True),self.root,[target,donor],run,lambda *a,**k:None)
  self.assertEqual([r['sourceEngine'] for r in rows],['gpt-sovits']);self.assertTrue(target['output'].is_file())
  pcm=array.array('h',run([ffmpeg,'-v','error','-i',target['output'],'-ar','24000','-ac','1','-f','s16le','pipe:1']))
  self.assertGreater(max(abs(v) for v in pcm[:9600]),100);self.assertLess(max(abs(v) for v in pcm[25000:32600]),10);self.assertEqual(target['report']['unresolvedFallbackIndices'],[2])
  self.assertTrue(json.loads((target_folder/'timing.json').read_text())[0]['skipped'])
