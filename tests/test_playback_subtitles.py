import hashlib,json,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'Resources'))
import playback_subtitles as sub,studio_preview
@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg required')
class PlaybackSubtitlesTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name);cls.tools=dict(ffmpeg=shutil.which('ffmpeg'),ffprobe=shutil.which('ffprobe'))
  cls.zh=cls.root/'中文.srt';cls.zh.write_text('1\n00:00:00,500 --> 00:00:01,750\n原裝中文字幕\n\n2\n00:00:02,000 --> 00:00:03,000\n第二句\n',encoding='utf-8')
  en=cls.root/'English.srt';en.write_text('1\n00:00:00,750 --> 00:00:02,250\nOriginal English\n',encoding='utf-8');cls.source=cls.root/'two-audio-two-subtitles.mkv'
  subprocess.run([cls.tools['ffmpeg'],'-v','error','-y','-f','lavfi','-i','testsrc2=s=320x180:r=12:d=4','-f','lavfi','-i','sine=frequency=440:duration=4','-f','lavfi','-i','sine=frequency=880:duration=4','-i',str(cls.zh),'-i',str(en),'-map','0:v','-map','1:a','-map','2:a','-map','3:s','-map','4:s','-c:v','libx264','-c:a','aac','-c:s','srt','-metadata:s:a:0','language=jpn','-metadata:s:a:1','language=eng','-metadata:s:s:0','language=chi','-metadata:s:s:1','language=eng','-disposition:s:0','default','-disposition:s:1','0',str(cls.source)],check=True)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def row(self):return dict(video=str(self.source))
 def test_lists_all_subtitles_and_audio_without_running_conversion(self):
  result=sub.read(self.root,self.row(),self.tools,'list');self.assertEqual(len(result['tracks']),2);self.assertEqual(len([x for x in result['streams'] if x['codec_type']=='audio']),2);self.assertEqual(result['cues'],[])
 def test_actual_embedded_selection_and_off_keep_source_clock(self):
  before=hashlib.sha256(self.source.read_bytes()).digest();result=sub.read(self.root,self.row(),self.tools)
  self.assertEqual(result['cues'][0]['text'],'原裝中文字幕');self.assertAlmostEqual(result['cues'][0]['start'],.5,delta=.03)
  en=sub.read(self.root,self.row(),self.tools,result['tracks'][1]['id']);self.assertEqual(en['cues'][0]['text'],'Original English')
  self.assertEqual(sub.read(self.root,self.row(),self.tools,'off')['cues'],[]);self.assertEqual(hashlib.sha256(self.source.read_bytes()).digest(),before)
 def test_external_choice_is_independent_and_invalid_choice_rejected(self):
  row=dict(self.row(),externalSubtitle=str(self.zh));before=self.zh.read_bytes();result=sub.read(self.root,row,self.tools)
  self.assertEqual(result['selected'],'external');self.assertEqual(result['cues'][1]['text'],'第二句');self.assertEqual(self.zh.read_bytes(),before)
  with self.assertRaises(ValueError):sub.read(self.root,row,self.tools,'embedded:999')
 def test_external_exported_excerpt_uses_viewer_offset_only(self):
  review=self.root/'review.json';review.write_text(json.dumps(dict(config=dict(startOffset=1.))))
  row=dict(self.row(),output=str(self.source),externalSubtitle=str(self.zh),review=str(review));result=sub.read(self.root,row,self.tools,'external',True)
  self.assertEqual(result['cues'][0]['start'],0);self.assertAlmostEqual(result['cues'][0]['end'],.75);self.assertEqual(sub.read(self.root,row,self.tools,'external',False)['cues'][0]['start'],.5)
 def test_selected_audio_remux_retains_original_subtitle_metadata(self):
  streams=sub.read(self.root,self.row(),self.tools,'list')['streams'];audio=[x for x in streams if x['codec_type']=='audio'][1]['index']
  movie=studio_preview.prepare(self.root,self.source,self.tools,'darwin',audio_stream=audio)
  self.assertEqual(movie['selectedAudioStream'],audio);self.assertEqual(len([x for x in movie['streams'] if x['codec_type']=='subtitle']),2);self.assertTrue(Path(movie['path']).is_file())
if __name__=='__main__':unittest.main()
