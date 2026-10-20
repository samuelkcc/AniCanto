import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import audio_fallback,multitrack
class ChannelRepairTests(unittest.TestCase):
 def test_repair_preserves_delivered_donors_and_rejects_missing_tracks(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);pairs=[('yue','cosyvoice3'),('yue','qwen-tts')];tracks=[]
   for language,engine in pairs:
    folder=root/engine;folder.mkdir();native=folder/'native.mp4';native.write_bytes(b'native');mixed=folder/'with-fallback.mp4';mixed.write_bytes(b'repaired');(folder/'cantonese.srt').write_text('captions')
    report=folder/'report.json';report.write_text(json.dumps(dict(output=str(native),audioFallbacks=[dict(index=1)])))
    tracks.append(dict(engine=engine,language=language,report=str(report)))
   parent=root/'review.json';(root/'report.json').write_text(json.dumps(dict(tracks=tracks)))
   plan=multitrack.stored_repair_tracks(parent,pairs,dict(engine='qwen-tts',language='yue'))
   self.assertEqual(plan[('yue','cosyvoice3')][2],root/'cosyvoice3/with-fallback.mp4')
   with self.assertRaises(ValueError):multitrack.stored_repair_tracks(parent,pairs,dict(engine='qwen-tts',language='en'))
   (root/'cosyvoice3/cantonese.srt').unlink()
   with self.assertRaises(ValueError):multitrack.stored_repair_tracks(parent,pairs,dict(engine='qwen-tts',language='yue'))
 def test_only_selected_channel_is_mutated_and_donors_remain_available(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);tracks=[]
   for engine in ('cosyvoice3','qwen-tts'):
    folder=root/engine;folder.mkdir();(folder/'timing.json').write_text(json.dumps([dict(index=1,start=0,end=1,renderedSeconds=0,skipped=True)]))
    tracks.append(dict(engine=engine,language='yue',folder=folder,report=dict(duration=1),output=folder/'native.mp4',id=engine))
   def run(args):raise RuntimeError('expected fake tool failure')
   audio_fallback.repair(dict(video='video',ffmpeg='ffmpeg'),root,tracks,run,lambda *a:None,target_keys={'qwen-tts:yue'})
   self.assertNotIn('channelSummary',tracks[0]['report']);self.assertEqual(tracks[1]['report']['unresolvedFallbackIndices'],[1])
   self.assertFalse((root/'cosyvoice3/fallback-error.json').exists());self.assertFalse((root/'qwen-tts/fallback-error.json').exists())
 def test_real_scoped_mux_preserves_eight_dubs_and_japanese_without_tts(self):
  self.scoped_mux(False)
 def test_explicit_missing_voice_repair_generates_only_target_and_muxes_verified_take(self):
  self.scoped_mux(True)
 def scoped_mux(self,generate):
  import shutil,subprocess,array,wave,math
  from types import SimpleNamespace
  from unittest.mock import Mock,patch
  from contextlib import nullcontext
  import ai_result_repair
  ffmpeg=shutil.which('ffmpeg');ffprobe=shutil.which('ffprobe')
  if not ffmpeg or not ffprobe:self.skipTest('FFmpeg unavailable')
  def run(args):return subprocess.run([str(x) for x in args],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);engines=['cosyvoice3','gpt-sovits-v2','gpt-sovits-v3','gpt-sovits'];pairs=[(l,e) for l in ['yue','en'] for e in engines];tracks=[];before={}
   cue=dict(start=0.,end=1.,text='Japanese',cantonese='出發啦',speakerId='actor')
   for n,(language,engine) in enumerate(pairs):
    folder=root/(language+'-'+engine);folder.mkdir();audio=folder/'take.wav'
    selected=language=='yue' and engine=='gpt-sovits'
    pcm=array.array('h',[0 if selected else int(4000*math.sin(i*2*math.pi*(300+n*100)/24000)) for i in range(48000)])
    with wave.open(str(audio),'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(pcm.tobytes())
    video=folder/'native.mp4';run([ffmpeg,'-v','error','-y','-f','lavfi','-i','color=s=64x64:r=10:d=2','-i',audio,'-map','0:v','-map','1:a','-map','1:a','-c:v','libx264','-c:a','aac','-t','2',video])
    row=dict(index=1,start=0.,end=1.,speakerId='actor',text='Go!' if language=='en' else cue['cantonese'],renderedStart=0.,renderedEnd=1.,renderedAudio=str(audio),renderedSeconds=0. if selected else 1.,skipped=selected)
    (folder/'timing.json').write_text(json.dumps([row]));(folder/'validation.json').write_text('{}');(folder/'cantonese.srt').write_text('1\n00:00:00,000 --> 00:00:01,000\nGo!\n')
    child=dict(cue,english='Go!',cantonese='Go!' if language=='en' else cue['cantonese']);(folder/'review.json').write_text(json.dumps(dict(cues=[child])))
    report=folder/'report.json';report.write_text(json.dumps(dict(output=str(video),duration=2.,qualityStatus='needs-review' if selected else 'automatic-checks-passed')))
    tracks.append(dict(engine=engine,language=language,report=str(report)))
    if not selected:before[str(report)]=report.read_bytes();before[str(video)]=video.read_bytes()
   cfg=dict(allowCrossEngineRepair=True,storage=str(root/'data'),video=str(root/'source.mkv'),duration=2.,selectedEngines=engines,dubLanguages=['yue','en'],defaultAudioEngine='cosyvoice3',includeOriginal=True,subtitleOutput='none',ffmpeg=ffmpeg,ffprobe=ffprobe)
   parent=root/'review.json';parent.write_text(json.dumps(dict(config=cfg,cues=[cue],meta=dict(streams=[dict(codec_type='video'),dict(codec_type='audio')]))));(root/'report.json').write_text(json.dumps(dict(tracks=tracks)))
   w=SimpleNamespace(emit=Mock(),atomic_json=lambda p,v:Path(p).write_text(json.dumps(v)),run=run,render_review=Mock(side_effect=AssertionError('must not synthesize')),ollama_chat=Mock(side_effect=AssertionError('must not translate')),parse_srt=lambda s:[dict(start=0.,end=1.,text='Go!')],save_srt=lambda p,c:Path(p).write_text('captions'))
   def retake(worker,settings,target,row,folder):
    self.assertEqual((target['engine'],target['language']),('gpt-sovits','yue'))
    folder.mkdir(parents=True,exist_ok=True);path=folder/'verified.wav'
    with wave.open(str(path),'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(array.array('h',(int(4000*math.sin(i*.1)) for i in range(19200))).tobytes())
    worker.atomic_json(folder/'timing.json',[dict(index=1,start=0.,end=1.,renderedStart=0.,renderedEnd=.8,renderedSeconds=.8,renderedAudio=str(path),text='出發啦',speakerId='actor')])
    worker.atomic_json(folder/'validation.json',{})
    worker.atomic_json(folder/'final-speech-check.json',dict(rows=[dict(index=1,textMatches=True,requiresReview=False,languageMismatch=False,languageUnverified=False)]))
    import hashlib
    return dict(engine=target['engine'],language=target['language'],id=target['id'],folder=folder,report=dict(duration=2.),audioSHA=hashlib.sha256(path.read_bytes()).hexdigest())
   with patch.object(ai_result_repair,'retake',side_effect=retake) as retry:
    multitrack.render(w,dict(review=str(parent),repairOnly=True,repairGenerate=generate,repairTrack=dict(engine='gpt-sovits',language='yue')))
    self.assertEqual(retry.call_count,int(generate))
   w.render_review.assert_not_called();w.ollama_chat.assert_not_called()
   self.assertTrue(all(Path(p).read_bytes()==v for p,v in before.items()),'Unselected reports and movies must remain unchanged')
   report=json.loads((root/'report.json').read_text());self.assertEqual(len(report['tracks']),8);self.assertEqual(report['audioFallbacks'][0]['sourceEngine'],'gpt-sovits' if generate else 'cosyvoice3');self.assertEqual(report['audioFallbacks'][0]['sourceLanguage'],'yue')
   streams=json.loads(run([ffprobe,'-v','error','-show_streams','-of','json',report['output']]))['streams'];self.assertEqual(sum(s['codec_type']=='audio' for s in streams),9)
   # A second repair consumes the delivered movie without using it as its own FFmpeg output.
   multitrack.render(w,dict(review=str(parent),repairOnly=True,repairTrack=dict(engine='gpt-sovits',language='yue')))
   self.assertFalse((root/'yue-gpt-sovits/fallback-error.json').exists());self.assertTrue(all(Path(p).read_bytes()==v for p,v in before.items()))
