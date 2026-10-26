import importlib.util
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import dubbing

class DubbingTests(unittest.TestCase):
 def test_complete_preview_keeps_source_anchors_and_mixes_overrun_without_cascade(self):
  import array,json,wave
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);cfg=dict(duration=2,ffmpeg='ffmpeg')
   cues=[dict(start=0,end=1,cantonese='第一句',text='日文'),dict(start=1,end=2,cantonese='第二句',text='日文')]
   report=[dict(index=i+1,seconds=2,slot=1) for i in range(2)]
   paths=[root/'canto-one.wav',root/'canto-two.wav'];calls=[]
   def run(args):
    calls.append(args)
    return array.array('h',[1000 if args[args.index('-i')+1]==paths[0] else 2000])*38400
   def output(args):return run(args).tobytes()
   audio,warnings=dubbing.render_complete_preview(cfg,root,cues,paths,report,output,lambda *a:None)
   with wave.open(str(audio)) as f:
    samples=array.array('h');samples.frombytes(f.readframes(f.getnframes()))
   self.assertEqual(len(samples),62400)
   self.assertEqual(samples[:24000],array.array('h',[1000])*24000)
   self.assertEqual(samples[24000:38400],array.array('h',[3000])*14400)
   self.assertEqual(samples[38400:],array.array('h',[2000])*24000)
   self.assertEqual(report[1]['renderedStart'],1)
   self.assertEqual(report[1]['overlaps'],[1])
   self.assertEqual(cfg['outputDuration'],2.6)
   self.assertEqual([w['kind'] for w in warnings],['timing-drift','timing-drift'])
   self.assertEqual(len(calls),2)
 def test_checks_rendered_atempo_duration_not_only_the_requested_ratio(self):
  import json
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);ref=root/'ref.wav';ref.write_bytes(b'audio')
   cfg=dict(duration=3,ffprobe='ffprobe',ffmpeg='ffmpeg',voiceProfiles=[dict(id='a',name='A',reference=str(ref),promptText='日文')],defaultSpeaker='a')
   audio_calls=[]
   def run(args):
    if args[0]=='ffprobe':return json.dumps({'format':{'duration':2}}).encode()
    audio_calls.append(args)
    return b'\x01\x00'*(48240 if len(audio_calls)==1 else 47760)
   with patch.object(dubbing,'gsv_audio',return_value=[root/'voice.wav']):
    dubbing.synthesize(cfg,root,[dict(start=0,end=2,cantonese='你好',text='原文')],run,lambda *a:None)
   self.assertEqual(len(audio_calls),2)
   row=json.loads((root/'timing.json').read_text())[0]
   self.assertLessEqual(row['renderedEnd'],2)
   self.assertLessEqual(row['rate'],1.25)
   self.assertFalse(row['needsReview'])
 def test_native_crash_after_completion_is_not_accepted_and_progress_is_not_error(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);python=root/'separator-runtime/bin/python3';python.parent.mkdir(parents=True);python.touch()
   (root/'separator-ready.json').write_text('{}')
   cfg=dict(storage=folder,ffmpeg='/bin/ffmpeg')
   def launch(*args,**kw):
    self.assertEqual(kw['env']['ORT_DISABLE_TELEMETRY'],'1')
    kw['stderr'].write('100%|████| 30/30 [00:09<00:00, 3.26it/s]\nlibc++abi: recursive_mutex lock failed: Invalid argument\n');kw['stderr'].flush()
    p=Mock();p.stdout=iter(['{"stage":"分離","message":"音軌已寫入"}\n']);p.wait.return_value=-6;return p
   with patch.object(dubbing.subprocess,'Popen',side_effect=launch):
    with self.assertRaisesRegex(RuntimeError,'訊號 6.*recursive_mutex') as result:
     dubbing.model_job(cfg,'separate',dict(out=folder),lambda *a:None)
   self.assertNotIn('100%',str(result.exception))
 def test_completed_work_metadata_survives_model_process_bridge(self):
  import json
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);python=root/'cosy-runtime/bin/python3';python.parent.mkdir(parents=True);python.touch()
   (root/'cosy-ready.json').write_text('{}')
   event=dict(stage='配音',message='完成',cueIndex=3,workID='tts',workCompleted=4,workTotal=20)
   process=Mock();process.stdout=iter([json.dumps(event)]);process.wait.return_value=0
   received=[]
   with patch.object(dubbing.subprocess,'Popen',return_value=process):
    dubbing._model_job(dict(storage=folder,ffmpeg='/bin/ffmpeg'),'cosy',dict(job=folder),lambda *a,**kw:received.append(kw))
   self.assertEqual(received,[dict(cueIndex=3,workID='tts',workCompleted=4,workTotal=20)])
 def test_stems_must_be_complete_stereo_before_commit(self):
  import json
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder)
   for name in ('background.wav','dialogue.wav'):(root/name).touch()
   def response(channels,duration):return json.dumps(dict(streams=[dict(codec_type='audio',channels=channels)],format=dict(duration=str(duration)))).encode()
   dubbing.validate_stems(dict(ffprobe='ffprobe',duration=60),root,lambda args:response(2,60))
   for channels,duration in [(1,60),(2,59),(2,float('nan'))]:
    with self.assertRaisesRegex(RuntimeError,'未標記為完成'):
     dubbing.validate_stems(dict(ffprobe='ffprobe',duration=60),root,lambda args:response(channels,duration))
 def test_direct_runner_disables_native_telemetry_before_model_import(self):
  import subprocess,os
  env=dict(os.environ,ORT_DISABLE_TELEMETRY='0',PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(Path(__file__).parents[1]/'Resources'))
  result=subprocess.check_output([sys.executable,'-c','import dubbing_runner,os; print(os.environ["ORT_DISABLE_TELEMETRY"])'],env=env,text=True)
  self.assertEqual(result.strip(),'1')
 def test_timing_does_not_force_fast_or_invalid_audio(self):
  self.assertEqual(dubbing.fit_rate(5,4),(1.25,True))
  self.assertFalse(dubbing.fit_rate(5.01,4)[1])
  self.assertEqual(dubbing.fit_rate(4.4,4),(1.1,True))
  self.assertEqual(dubbing.fit_rate(2,4),(1.0,True))
  for a,b in [(0,2),(2,0),(float('nan'),1),(2,float('inf'))]:
   with self.assertRaises(ValueError): dubbing.fit_rate(a,b)
 def test_vowel_text_does_not_authorize_original_audio(self):
  self.assertFalse(dubbing.is_vocalization(dict(japanese='あ…',cantonese='啊！')))
  for cue in [dict(japanese='はい',cantonese='係'),dict(japanese='あの',cantonese='嗰個'),dict(japanese='あ',cantonese='唔好'),dict(japanese='あ',cantonese='啊',sourceParts=[{},{}])]:
   self.assertFalse(dubbing.is_vocalization(cue))
 def test_short_line_compression_never_squeezes_dense_or_unknown_pronunciation(self):
  self.assertEqual(dubbing.short_line_limit('你去邊？',1),1.5)
  for text,slot in [('你究竟去咗邊度呀？',.8),('你去邊？',.2),('10分鐘',1),('Ken去邊？',1),('啊',1)]:
   self.assertEqual(dubbing.short_line_limit(text,slot),1.25)
 def test_roles_never_fall_back_to_another_voice(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'voice.wav';path.write_bytes(b'audio')
   profile=dict(id='a',name='角色A',reference=str(path),promptText='日文')
   cfg=dict(voiceProfiles=[profile],defaultSpeaker='a')
   self.assertEqual(dubbing.profile_for({},cfg),profile)
   with self.assertRaises(ValueError): dubbing.profile_for(dict(speakerId='unknown'),cfg)
   profile['promptText']=''
   with self.assertRaises(ValueError): dubbing.profile_for({},cfg)
 def test_cache_changes_with_reference_audio_and_script(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);ref=root/'ref.wav';ref.write_bytes(b'first')
   cfg=dict(independentReferences=False,storage=folder,gsvReferenceMode='original',voiceProfiles=[dict(id='a',name='A',reference=str(ref),promptText='日文')],defaultSpeaker='a')
   with patch.object(dubbing,'model_job'):
    a=dubbing.gsv_audio(cfg,root,[dict(cantonese='你好')],None,None)[0]
    b=dubbing.gsv_audio(cfg,root,[dict(cantonese='早晨')],None,None)[0]
    ref.write_bytes(b'second')
    c=dubbing.gsv_audio(cfg,root,[dict(cantonese='你好')],None,None)[0]
    d=dubbing.gsv_audio(dict(cfg,ttsBackend='cosyvoice3'),root,[dict(cantonese='你好')],None,None)[0]
   self.assertEqual(len({a,b,c,d}),4)
 def test_missing_deployment_has_actionable_error(self):
  with tempfile.TemporaryDirectory() as folder:
   with self.assertRaisesRegex(ValueError,'部署'):
    dubbing.model_job(dict(storage=folder),'tts',{},lambda *a:None)
 def test_speech_alignment_stays_in_subtitle_window(self):
  cues=[dict(start=1,end=4,text='句一'),dict(start=5,end=6,text='靜音')]
  dubbing.align_cues(cues,[dict(start=1.5,end=3.5)])
  self.assertAlmostEqual(cues[0]['speechStart'],1.44)
  self.assertAlmostEqual(cues[0]['speechEnd'],3.6)
  self.assertNotIn('speechStart',cues[1])
  self.assertIn('未偵測',cues[1]['reviewNote'])
 def test_complete_preview_never_rewrites_approved_meaning_to_meet_duration(self):
  import json,duration_fit
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);ref=root/'ref.wav';ref.write_bytes(b'audio')
   cfg=dict(duration=3,ffprobe='ffprobe',autoFit=True,speechTiming=True,translate=True,previewLooseTiming=True,ttsBackend='cosyvoice3',voiceProfiles=[dict(id='a',name='A',reference=str(ref),promptText='日文')],defaultSpeaker='a')
   cue=dict(start=0,end=2,cantonese='激嬲咗佢，親生仔都係咁嘅下場。',text='日語')
   with patch.object(dubbing,'gsv_audio',return_value=[root/'voice.wav']) as tts,patch.object(duration_fit,'shorten') as shorten,patch.object(dubbing,'render_complete_preview',return_value=(root/'done.wav',[])):
    dubbing.synthesize(cfg,root,[cue],lambda args:json.dumps({'format':{'duration':'5'}}).encode(),lambda *a:None)
    self.assertEqual(tts.call_count,2) # One bounded same-text timed take; never rewrite.
    shorten.assert_not_called()
    self.assertIn('親生仔都係咁嘅下場',cue['cantonese'])

 def test_long_line_stops_before_mixing_or_clipping(self):
  import json
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);ref=root/'reference.wav';ref.write_bytes(b'reference')
   cfg=dict(duration=3,ffprobe='ffprobe',voiceProfiles=[dict(id='a',name='A',reference=str(ref),promptText='日文')],defaultSpeaker='a')
   cues=[dict(start=0,end=2,cantonese='呢句太長',text='原文')]
   with patch.object(dubbing,'gsv_audio',return_value=[root/'cached.wav']):
    with self.assertRaisesRegex(ValueError,'超時'):
     dubbing.synthesize(cfg,root,cues,lambda args:json.dumps({'format':{'duration':'4.5'}}).encode(),lambda *a:None)
   self.assertTrue((root/'timing.json').exists())
   self.assertFalse((root/'cantonese.wav').exists())
 def test_auto_fit_is_bounded_and_uses_only_measured_overlong_lines(self):
  import json
  import duration_fit
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder); ref=root/'ref.wav';ref.write_bytes(b'audio')
   cfg=dict(storage=folder,duration=3,ffprobe='ffprobe',ffmpeg='ffmpeg',autoFit=True,speechTiming=True,translate=True,
     voiceProfiles=[dict(id='a',name='A',reference=str(ref),promptText='日文')],defaultSpeaker='a')
   cue=dict(start=0,end=2,cantonese='太長台詞',text='日語')
   def run(args):
    if args[0]=='ffprobe':return json.dumps({'format':{'duration':'4.5'}}).encode()
    raise AssertionError('must not mix an overlong line')
   with patch.object(dubbing,'gsv_audio',return_value=[root/'voice.wav']) as tts, patch.object(duration_fit,'shorten',return_value=True) as shorten:
    with self.assertRaisesRegex(ValueError,'超時'):dubbing.synthesize(cfg,root,[cue],run,lambda *a:None)
    self.assertEqual(tts.call_count,3)
    self.assertEqual(shorten.call_count,2)
    self.assertEqual(shorten.call_args.args[4],2)
 def test_brisk_retry_keeps_better_audio_across_rewrites_and_rejects_slower_retry(self):
  import json
  import duration_fit
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);ref=root/'ref.wav';ref.write_bytes(b'audio')
   cfg=dict(storage=folder,duration=5,ffprobe='ffprobe',ffmpeg='ffmpeg',ttsBackend='cosyvoice3',autoFit=True,speechTiming=True,translate=True,
     voiceProfiles=[dict(id='a',name='A',reference=str(ref),promptText='日文')],defaultSpeaker='a')
   cues=[dict(start=0,end=2,cantonese='甲',text='甲'),dict(start=3,end=5,cantonese='乙',text='乙')]
   lengths={'甲':3,'甲brisk':1.9,'乙':4,'乙brisk':5,'短':1.8}
   def audio(cfg,job,rows,*args): return [root/(c['cantonese']+c.get('_deliveryStyle','')) for c in rows]
   def run(args):
    if args[0]=='ffprobe':return json.dumps({'format':{'duration':lengths[Path(args[-1]).name]}}).encode()
    return b'\x00\x00'*100
   def shorter(cfg,job,rows,report,*args):
    self.assertFalse(report[0]['needsReview'])
    self.assertEqual(report[1]['seconds'],4)
    rows[1]['cantonese']='短';return True
   with patch.object(dubbing,'gsv_audio',side_effect=audio) as tts,patch.object(duration_fit,'shorten',side_effect=shorter) as rewrite:
    result,_=dubbing.synthesize(cfg,root,cues,run,lambda *a:None)
   self.assertTrue(result.exists())
   self.assertEqual(tts.call_count,3)
   self.assertEqual(rewrite.call_count,1)
   report=json.loads((root/'timing.json').read_text())
   self.assertEqual([r['seconds'] for r in report],[1.9,1.8])
