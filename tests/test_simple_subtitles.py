import json,sys,tempfile,unittest,shutil,subprocess,array,math,wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import multitrack,worker,caption_tracks

class SimpleSubtitleTests(unittest.TestCase):
 def test_explicit_modes_are_exact_multiple_selection_and_never_burned(self):
  self.assertEqual(multitrack.subtitle_choices(dict(subtitleModes=['original','english','english'],burnOutputCaptions=True)),(['original','english'],None))
  self.assertEqual(multitrack.subtitle_choices(dict(subtitleModes=[])),([],None))
  for value in ('english',['invalid'],[None]):
   with self.assertRaises(ValueError):multitrack.subtitle_choices(dict(subtitleModes=value))
 def test_legacy_subtitle_presets_keep_their_existing_behavior(self):
  self.assertEqual(multitrack.subtitle_choices(dict(subtitleOutput='separate',burnOutputCaptions=True,burnSubtitleMode='dual')),(['yue','english'],'dual'))
 def test_original_subtitle_labels_preserve_language_and_title(self):
  self.assertEqual(caption_tracks.labels(dict(mode='original',sourceLanguage='jpn',sourceTitle='Japanese SDH')),('jpn','Original / 原片 · Japanese SDH'))
 def mux(self,root,modes,streams,mode="simple"):
  ffmpeg=shutil.which('ffmpeg');ffprobe=shutil.which('ffprobe')
  if not ffmpeg or not ffprobe:self.skipTest('FFmpeg unavailable')
  def run(args):return subprocess.run([str(a) for a in args],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
  def write(p,obj):Path(p).write_text(json.dumps(obj,ensure_ascii=False))
  audio=root/'voice.wav'
  with wave.open(str(audio),'wb') as f:
   f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(array.array('h',(round(3000*math.sin(i*.07)) for i in range(48000))).tobytes())
  ja=root/'ja.srt';zh=root/'zh.srt';ja.write_text('1\n00:00:00,000 --> 00:00:01,000\n行こう！\n');zh.write_text('1\n00:00:00,000 --> 00:00:01,000\n出發！\n')
  source=root/'source.mkv';run([ffmpeg,'-v','error','-y','-f','lavfi','-i','color=s=64x64:r=10:d=2','-i',audio,'-i',ja,'-i',zh,'-map','0:v','-map','1:a','-map','2:s','-map','3:s','-c:v','libx264','-c:a','aac','-c:s','srt','-metadata:s:s:0','language=jpn','-metadata:s:s:0','title=Japanese','-metadata:s:s:1','language=zho','-metadata:s:s:1','title=Chinese',source])
  cfg=dict(interfaceMode=mode,video=str(source),duration=2.,storage=str(root/'storage'),ffmpeg=ffmpeg,ffprobe=ffprobe,model='',ttsBackend='drama3',selectedEngines=['drama3'],dubLanguages=['yue','en'],includeOriginal=True,subtitleOutput='none',subtitleModes=modes,originalSubtitleStreams=streams,burnOutputCaptions=False,voiceStyleMode='clone',autoFit=False)
  cue=dict(start=0.,end=1.,text='行こう！',japanese='行こう！',cantonese='出發啦',english='Go!',speakerId='actor')
  review=root/'review.json';write(review,dict(config=cfg,cues=[cue],meta=json.loads(run([ffprobe,'-v','error','-show_streams','-of','json',source]))))
  def native(request):
   path=Path(request['review']);obj=json.loads(path.read_text());folder=path.parent;output=folder/'native.mp4'
   run([ffmpeg,'-v','error','-y','-i',source,'-map','0:v','-map','0:a','-map','0:a','-c','copy',output])
   worker.save_srt(folder/'cantonese.srt',obj['cues'])
   write(folder/'timing.json',[dict(index=1,start=0,end=1,text=obj['cues'][0]['cantonese'],speakerId='actor',renderedStart=0,renderedEnd=1,renderedSeconds=1,renderedAudio=str(audio))])
   write(folder/'validation.json',{});write(folder/'report.json',dict(output=str(output),duration=2.,qualityStatus='automatic-checks-passed'))
  w=SimpleNamespace(run=run,atomic_json=write,emit=Mock(),render_review=Mock(side_effect=native),ollama_chat=Mock(),parse_srt=worker.parse_srt,save_srt=worker.save_srt)
  multitrack.render(w,dict(review=str(review)))
  report=json.loads((root/'report.json').read_text());meta=json.loads(run([ffprobe,'-v','error','-show_streams','-of','json',report['output']]))
  return report,meta,w
 def test_bilingual_one_engine_original_audio_and_four_switchable_subtitles(self):
  with tempfile.TemporaryDirectory() as d:
   report,meta,w=self.mux(Path(d),['original','yue','english'],[2,3])
   self.assertEqual(len(report['tracks']),2);self.assertEqual({r['engine'] for r in report['tracks']},{'drama3'})
   self.assertEqual(sum(s['codec_type']=='audio' for s in meta['streams']),3)
   subs=[s for s in meta['streams'] if s['codec_type']=='subtitle'];self.assertEqual(len(subs),4)
   self.assertEqual(sorted(s.get('tags',{}).get('language') for s in subs),['eng','jpn','yue','zho'])
   self.assertFalse(report['burnOutputCaptions']);self.assertEqual({s['sourceStream'] for s in report['subtitleTracks'] if s['mode']=='original'},{2,3});w.ollama_chat.assert_not_called()
 def test_learning_track_contains_both_languages_with_cantonese_default_and_originals_last(self):
  with tempfile.TemporaryDirectory() as d:
   report,meta,w=self.mux(Path(d),['original','dual','english','yue'],[2,3])
   subs=[s for s in meta['streams'] if s['codec_type']=='subtitle']
   self.assertEqual([s['mode'] for s in report['subtitleTracks']],['yue','english','dual','original','original'])
   self.assertEqual([s['disposition']['default'] for s in subs],[1,0,0,0,0])
   self.assertEqual([s['tags']['language'] for s in subs],['yue','eng','zho','jpn','zho'])
   output=Path(report['output']);ffmpeg=shutil.which('ffmpeg')
   text=subprocess.check_output([ffmpeg,'-v','error','-i',str(output),'-map','0:s:2','-f','srt','pipe:1']).decode()
   self.assertIn('出發啦\nGo!',text);w.ollama_chat.assert_not_called()

 def test_deselected_original_and_english_subtitles_stay_absent(self):
  with tempfile.TemporaryDirectory() as d:
   report,meta,w=self.mux(Path(d),['yue'],[])
   self.assertEqual([s['mode'] for s in report['subtitleTracks']],['yue'])
   self.assertEqual(sum(s['codec_type']=='subtitle' for s in meta['streams']),1)
 def test_basic_and_expert_do_not_duplicate_captions_for_bilingual_audio(self):
  # Regression: shared desktop sends "basic", while the old dedup branch
  # recognised only "simple" and emitted one copy per dubbed language.
  for mode in ('basic','expert'):
   with self.subTest(mode=mode),tempfile.TemporaryDirectory() as d:
    report,meta,w=self.mux(Path(d),['yue','english','dual','original'],None,mode=mode)
    self.assertEqual([t['mode'] for t in report['subtitleTracks']],['yue','english','dual','original'])
    subs=[s for s in meta['streams'] if s['codec_type']=='subtitle']
    self.assertEqual([s['tags']['language'] for s in subs],['yue','eng','zho','zho'])
    self.assertEqual([s['disposition']['default'] for s in subs],[1,0,0,0])
    self.assertEqual(len({s['tags']['handler_name'] for s in subs}),4)
 def test_automatic_mode_options_match_dubbing_language(self):
  for languages,expected in [(['yue'],['yue','original']),(['en'],['english','original']),(['yue','en'],['yue','english','dual','original'])]:
   self.assertEqual(multitrack.subtitle_choices(dict(subtitleSelection='automatic',dubLanguages=languages,subtitleModes=[])),(expected,None))
 def test_ocr_without_soft_subtitles_does_not_fabricate_original_track(self):
  from soft_subtitles import original_tracks
  w=SimpleNamespace(run=Mock(return_value=b'{"streams":[]}'))
  self.assertEqual(original_tracks(w,dict(video='burnt-in.mp4',ffprobe='probe',ocr=True,duration=2),Path('.')),[])
 def test_no_selected_subtitles_stays_video_and_audio_only(self):
  with tempfile.TemporaryDirectory() as d:
   report,meta,w=self.mux(Path(d),[],[])
   self.assertEqual(report['subtitleTracks'],[]);self.assertFalse(any(s['codec_type']=='subtitle' for s in meta['streams']))
