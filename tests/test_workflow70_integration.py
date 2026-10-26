import copy,json,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows'),str(ROOT/'studio')]
import nonverbal,update_plan,studio_preview,worker
from performance_fixtures import performance_row
from atomic_files import write_json

class WorkflowIntegration(unittest.TestCase):
 def track(self,root,engine,language):
  folder=root/'tracks'/(language+'-'+engine);folder.mkdir(parents=True);output=folder/'voice.mp4';output.write_bytes(b'original immutable output')
  write_json(folder/'review.json',dict(config=dict(ttsBackend=engine,targetLanguage=language,duration=4),cues=[]))
  write_json(folder/'report.json',dict(output=str(output),engine=engine,language=language,duration=4))
  return dict(engine=engine,language=language,report=str(folder/'report.json'))
 def project(self,root):
  rows=[self.track(root,'drama3','yue'),self.track(root,'cosyvoice3','en')]
  write_json(root/'review.json',dict(config=dict(duration=4),cues=[]));write_json(root/'report.json',dict(tracks=rows));return root/'review.json',dict(settings={},segments=[],clips=[])
 def test_append_tracks_are_exact_pairs_and_retained_hashes_survive(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);review,draft=self.project(root);before={p:p.read_bytes() for p in (root/'tracks').rglob('*') if p.is_file()}
   plan=update_plan.build(review,draft,'append','gpt-sovits','zh')
   self.assertEqual(plan['settings']['_trackPairs'],[['yue','drama3'],['en','cosyvoice3'],['zh','gpt-sovits']])
   self.assertNotIn('_trackPairs',draft['settings']);child=root/'versions'/'new';child.mkdir(parents=True)
   donors=update_plan.retained(plan['settings'],child);self.assertEqual(set(donors),{('yue','drama3'),('en','cosyvoice3')})
   self.assertEqual({p:p.read_bytes() for p in before},before)
   donors[('yue','drama3')][2].write_bytes(b'changed')
   with self.assertRaisesRegex(ValueError,'Retained track changed'):update_plan.retained(plan['settings'],child)
 def test_replace_leaves_other_track_and_duplicate_append_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);review,draft=self.project(root)
   with self.assertRaisesRegex(ValueError,'already exists'):update_plan.build(review,draft,'append','drama3','yue')
   plan=update_plan.build(review,draft,'replace','gpt-sovits','yue',['yue','drama3'])
   self.assertEqual(plan['settings']['_trackPairs'],[['en','cosyvoice3'],['yue','gpt-sovits']])
   self.assertTrue((root/'tracks/yue-drama3/voice.mp4').is_file())
 def test_retained_external_folder_cannot_be_injected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);review,draft=self.project(root);plan=update_plan.build(review,draft,'append','gpt-sovits','yue');plan['settings']['_retainedTracks']['yue:drama3']['folder']='/tmp'
   with self.assertRaises(ValueError):update_plan.retained(plan['settings'],root)
 def test_full_regeneration_changes_explicit_token_keeps_draft(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);review,draft=self.project(root);before=copy.deepcopy(draft)
   a=update_plan.build(review,draft,'all');b=update_plan.build(review,draft,'all')
   self.assertNotEqual(a['settings']['audioRerunToken'],b['settings']['audioRerunToken']);self.assertEqual(draft,before)
 def test_source_help_is_lexical_not_restored_as_scream(self):
  for word in ('助けて！','Help!','救命！'):
   row=performance_row(start=0,duration=1,screaming=.98,speech=.8)
   self.assertEqual(nonverbal.event_ranges([row],[dict(start=0,end=1,text=word)],1),[])
 def test_generic_nonlexical_events_do_not_depend_on_title_role_or_language(self):
  for label in ('laughter','crying_sobbing','screaming','sigh'):
   row=performance_row(start=2,duration=1,**{label:.9})
   events=nonverbal.event_ranges([row],[],5);self.assertEqual(len(events),1);self.assertEqual(events[0]['label'],label)
 def test_optional_moaning_class_is_used_only_when_model_supplies_it(self):
  row=performance_row(start=0,duration=1,moaning_groaning=.9)
  self.assertEqual(nonverbal.event_ranges([row],[],2)[0]['label'],'moaning_groaning')
  del row['moaning_groaning'];self.assertEqual(nonverbal.event_ranges([row],[],2),[])
  from native_tools import performance_scores
  scores=performance_scores({0:'Groan',1:'Speech'},[.9,.01]);self.assertEqual(scores['moaning_groaning'],.9)
 def test_semantic_window_failure_is_permanent_not_random_retry(self):
  from generation_guard import permanent
  self.assertTrue(permanent('exceeded bounded ten-second semantic window'))
  self.assertFalse(permanent('GPU temporarily out of memory'))
 @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg required')
 def test_actual_multitrack_preview_selects_requested_audio_and_thumbnail(self):
  import numpy as np
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);source=root/'source.mp4';ff=shutil.which('ffmpeg');tools=dict(ffmpeg=ff,ffprobe=shutil.which('ffprobe'))
   subprocess.run([ff,'-v','error','-y','-f','lavfi','-i','testsrc2=s=320x180:r=12:d=2','-f','lavfi','-i','sine=frequency=440:duration=2','-f','lavfi','-i','sine=frequency=880:duration=2','-map','0:v','-map','1:a','-map','2:a','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',str(source)],check=True)
   a=studio_preview.prepare(root,source,tools,'darwin',audio_stream=1);b=studio_preview.prepare(root,source,tools,'darwin',audio_stream=2)
   self.assertEqual(a['mode'],'direct');self.assertEqual(b['mode'],'remux');self.assertNotEqual(a['path'],b['path'])
   raw=subprocess.check_output([ff,'-v','error','-i',b['path'],'-map','0:a:0','-ac','1','-ar','8000','-f','f32le','pipe:1']);samples=np.frombuffer(raw,dtype=np.float32)
   frequency=np.argmax(np.abs(np.fft.rfft(samples)))*8000/len(samples);self.assertLess(abs(frequency-880),3)
   thumbnail=studio_preview.thumbnail(root,source,tools,1.2);self.assertTrue(Path(thumbnail['path']).is_file());self.assertTrue(Path(thumbnail['path']).read_bytes().startswith(b'\xff\xd8'))
   with self.assertRaises(ValueError):studio_preview.prepare(root,source,tools,'darwin',audio_stream=99)
   with self.assertRaises(ValueError):studio_preview.thumbnail(root,source,tools,float('nan'))

if __name__=='__main__':unittest.main()

class RealMuxUpdateTests(unittest.TestCase):
 @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg required')
 def test_append_mux_keeps_all_donor_files_byte_identical(self):
  import multitrack,numpy as np,soundfile as sf
  from types import SimpleNamespace
  from desktop_state import defaults
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);ff=shutil.which('ffmpeg');probe=shutil.which('ffprobe');source=root/'source.mp4'
   subprocess.run([ff,'-v','error','-y','-f','lavfi','-i','testsrc2=s=320x180:r=12:d=2','-f','lavfi','-i','sine=frequency=440:duration=2','-map','0:v','-map','1:a','-map','1:a','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',str(source)],check=True)
   audio=root/'voice.wav';sf.write(audio,np.sin(np.arange(24000)*.1)*.1,24000,subtype='PCM_16')
   cues=[dict(start=0,end=1,text='こんにちは',japanese='こんにちは',cantonese='你好呀',english='Hello there',speakerId='r')]
   cfg=dict(defaults(),productionMode='fast',video=str(source),duration=2,storage=str(root),ffmpeg=ff,ffprobe=probe,sourceLanguage='ja',includeOriginal=True,subtitleModes=['yue','english'],selectedEngines=['drama3','cosyvoice3'],dubLanguages=['yue','en'],autoApprove=False)
   meta=json.loads(subprocess.check_output([probe,'-v','error','-show_streams','-show_format','-of','json',str(source)]));reports=[]
   def track(folder,engine,lang):
    folder.mkdir(parents=True,exist_ok=True);out=folder/'movie.mp4';shutil.copy2(source,out);local=copy.deepcopy(cues)
    if lang=='en':local[0]['cantonese']=local[0]['english']
    write_json(folder/'review.json',dict(config=dict(cfg,ttsBackend=engine,targetLanguage=lang),cues=local));write_json(folder/'report.json',dict(output=str(out),duration=2,channelSummary=dict(generated=1,repaired=0,unresolved=[])))
    write_json(folder/'timing.json',[dict(index=1,start=0,end=1,audio=str(audio),renderedAudio=str(audio),seconds=1,renderedSeconds=1)])
    worker.save_srt(folder/'cantonese.srt',local);return dict(engine=engine,language=lang,report=str(folder/'report.json'))
   reports=[track(root/'tracks/yue-drama3','drama3','yue'),track(root/'tracks/en-cosyvoice3','cosyvoice3','en')]
   write_json(root/'review.json',dict(config=cfg,meta=meta,cues=cues));write_json(root/'report.json',dict(tracks=reports))
   draft=update_plan.build(root/'review.json',dict(settings=cfg,segments=[],clips=[]),'append','gpt-sovits','yue');cfg=draft['settings'];cfg.update(storage=str(root),ffmpeg=ff,ffprobe=probe)
   before={p:p.read_bytes() for p in (root/'tracks').rglob('*') if p.is_file()};version=root/'versions/new';version.mkdir(parents=True);review=version/'review.json';write_json(review,dict(config=cfg,meta=meta,cues=cues))
   calls=[]
   def generate(request):
    local=Path(request['review']);body=json.loads(local.read_text());calls.append((body['config']['targetLanguage'],body['config']['ttsBackend']));track(local.parent,body['config']['ttsBackend'],body['config']['targetLanguage'])
   w=SimpleNamespace(run=worker.run,emit=Mock(),atomic_json=write_json,save_srt=worker.save_srt,parse_srt=worker.parse_srt,render_review=generate)
   with patch('dub_languages.english_script',side_effect=lambda w,c,j,rows:rows),patch('caption_tracks.source_cues',return_value=[]):multitrack.render(w,dict(review=str(review)))
   self.assertEqual(calls,[('yue','gpt-sovits')]);self.assertEqual({p:p.read_bytes() for p in before},before)
   self.assertEqual({p for p in (root/'tracks').rglob('*') if p.is_file()},set(before))
   report=json.loads((version/'report.json').read_text());output=Path(report['output']);actual=json.loads(subprocess.check_output([probe,'-v','error','-show_streams','-of','json',str(output)]))
   self.assertEqual(sum(x['codec_type']=='audio' for x in actual['streams']),4);self.assertEqual(len(report['tracks']),3)
