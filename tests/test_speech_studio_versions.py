"""Immutable speech versions, corrected transcripts and bounded real-file review."""
import array,base64,copy,hashlib,json,math,shutil,sys,tempfile,types,unittest,wave
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows'),str(ROOT/'studio')]
import speech_library as library,speech_studio as pipeline,speech_quality as quality
from desktop_state import defaults
from backend import Studio

def wav(path,seconds=1,silent=False):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 values=array.array('h',(0 if silent else round(4000*math.sin(i*.04)) for i in range(round(44100*seconds))))
 with wave.open(str(path),'wb') as f:f.setparams((1,2,44100,0,'NONE','not compressed'));f.writeframes(values.tobytes())
 return path

class SpeechVersionTests(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.draft=library.new_document(self.root)
 def tearDown(self):self.temp.cleanup()
 def request(self,**extra):return library.read(library.submit(self.root,defaults(),dict(projectID=self.draft['projectID'],action='generate',source='Hello there.',cantonese='我哋今日一齊出發啦。',**extra)))
 def take(self,**extra):
  cfg=self.request(**extra);job=Path(cfg['job']);audio=wav(job/'voice.wav');row=library.read(job/'result.json');row.update(status='complete',audio=str(audio),audioSHA256=library.digest(audio),source=cfg['speechStudio']['source'],cantonese=cfg['speechStudio']['cantonese'],engine=cfg['ttsBackend'],quality=dict(status='passed',audioSHA256=library.digest(audio),qualityCertified=False));library.write(job/'result.json',row);return cfg,row
 def test_versions_keep_exact_scripts_hashes_and_settings_across_selection_and_rename(self):
  first,a=self.take();second,b=self.take(rate=1.1)
  self.assertEqual([a['version'],b['version']],[1,2]);self.assertNotEqual(a['id'],b['id'])
  before={p:p.read_bytes() for cfg in (first,second) for p in (Path(cfg['job'])/'request.json',Path(cfg['job'])/'voice.wav')}
  library.save(self.root,a['id']);library.save(self.root,b['id']);library.select(self.root,a['id']);library.rename(self.root,a['projectID'],'Custom title')
  data=library.listing(self.root);self.assertEqual(len(data['projects']),1);self.assertEqual(data['projects'][0]['selectedTake'],a['id'])
  self.assertEqual(data['projects'][0]['title'],'Custom title')
  for path,raw in before.items():self.assertEqual(path.read_bytes(),raw)
  loaded=library.load_take(self.root,b['id']);self.assertEqual(loaded['draft']['rate'],1.1);self.assertTrue(any(r['selected'] and r['id']==a['id'] for r in loaded['clips']))
 def test_delete_one_take_retains_other_versions_original_input_and_video_projects(self):
  original=wav(self.root/'source.wav');input_row=library.import_audio(self.root,original)
  first,a=self.take();second,b=self.take();library.save(self.root,a['id']);library.save(self.root,b['id'])
  video=self.root/'jobs/video/review.json';video.parent.mkdir(parents=True);video.write_text('original video project')
  library.delete(self.root,b['id']);self.assertTrue((library.root(self.root)/'trash'/b['id']/'voice.wav').is_file())
  self.assertTrue(Path(input_row['path']).is_file());self.assertTrue((Path(first['job'])/'voice.wav').is_file());self.assertEqual(video.read_text(),'original video project')
  data=library.listing(self.root);self.assertEqual(data['projects'][0]['selectedTake'],a['id']);self.assertEqual(len(data['clips']),1)
 def test_changed_audio_invalidates_review_and_cannot_be_exported_or_selected(self):
  cfg,row=self.take();library.save(self.root,row['id']);audio=Path(cfg['job'])/'voice.wav';audio.write_bytes(audio.read_bytes()[:-2]+b'xx')
  self.assertNotIn('audio',library.listing(self.root)['clips'][0]);self.assertEqual(library.listing(self.root)['clips'][0]['quality']['status'],'not-checked')
  with self.assertRaisesRegex(ValueError,'changed'):library.select(self.root,row['id'])
  with self.assertRaisesRegex(ValueError,'changed'):library.verified_audio(self.root,row['id'])
 def test_unconfirmed_take_needs_explicit_acceptance_and_never_becomes_certified(self):
  cfg,row=self.take();row.update(status='needs-review',quality=dict(status='needs-review',qualityCertified=False));library.write(Path(cfg['job'])/'result.json',row)
  with self.assertRaisesRegex(ValueError,'explicitly'):library.save(self.root,row['id'])
  library.save(self.root,row['id'],accept_review=True);saved=library.read(Path(cfg['job'])/'saved.json');self.assertTrue(saved['acceptedReview']);self.assertFalse(saved['qualityCertified'])
 def test_two_phase_recording_preserves_corrected_source_and_reference_identity(self):
  audio=library.import_audio(self.root,wav(self.root/'original.wav',4))
  req=library.submit(self.root,defaults(),dict(projectID=self.draft['projectID'],action='recognize',mode='recording',inputID=audio['id']));cfg=library.read(req);job=Path(cfg['job']);reference=wav(job/'reference.wav',4)
  row=library.read(job/'result.json');row.update(status='recognized',source='wrong name',detectedLanguage='en',reference=str(reference),referenceText='Hello Alice.',referenceSHA256=library.digest(reference));library.write(job/'result.json',row)
  translated=library.read(library.submit(self.root,defaults(),dict(projectID=self.draft['projectID'],action='translate',mode='recording',inputID=audio['id'],recognitionID=row['id'],source='Hello Alice, let us go.')))
  seen={}
  def chat(*a,**k):seen.update(json.loads(a[2][1]['content']));return '{"text":"Alice，我哋出發啦。"}'
  worker=types.SimpleNamespace(emit=Mock(),ollama_chat=chat,traditional_cantonese=lambda c,t:t)
  translated.update(port=1,model='test');pipeline.process(worker,translated)
  self.assertEqual(seen['source'],'Hello Alice, let us go.');self.assertEqual(seen['sourceLanguage'],'en')
  self.assertEqual(library.read(job/'result.json')['source'],'wrong name')
  other=library.import_audio(self.root,wav(self.root/'other.wav',4))
  with self.assertRaisesRegex(ValueError,'earlier input'):
   library.submit(self.root,defaults(),dict(action='generate',mode='recording',inputID=other['id'],recognitionID=row['id'],cantonese='我哋出發啦。'))
 def test_recognition_stops_before_translation_and_input_does_not_force_language(self):
  ffmpeg=shutil.which('ffmpeg')
  if not ffmpeg:self.skipTest('FFmpeg unavailable')
  audio=library.import_audio(self.root,wav(self.root/'original.wav',4));cfg=library.read(library.submit(self.root,defaults(),dict(action='recognize',mode='recording',inputID=audio['id'])))
  cfg['ffmpeg']=ffmpeg
  def run(args):
   if len(args)>2 and str(args[-2])=='transcribe':
    request=library.read(args[-1]);library.write(request['output'],dict(text='Bonjour Alice.',language='fr',segments=[dict(start=0,end=4,text='Bonjour Alice.')]))
   else:
    import subprocess
    return subprocess.check_output(list(map(str,args)))
  worker=types.SimpleNamespace(run=run,emit=Mock(),ollama_chat=Mock(side_effect=AssertionError('Recognition started translation')))
  with patch('model_catalog.resolve',return_value=self.root/'whisper'):
   result=pipeline.process(worker,cfg)
  self.assertEqual(result['status'],'recognized');self.assertEqual(result['detectedLanguage'],'fr');worker.ollama_chat.assert_not_called();self.assertTrue(Path(result['reference']).is_file())
 def test_invalid_saved_paths_and_running_take_are_not_removed(self):
  cfg,row=self.take();outside=self.root/'outside.wav';wav(outside)
  (Path(cfg['job'])/'voice.wav').unlink();(Path(cfg['job'])/'voice.wav').symlink_to(outside)
  with self.assertRaises(ValueError):library.verified_audio(self.root,row['id'])
  with self.assertRaises(ValueError):library.folder(self.root,'../video')
  row.update(status='running');library.write(Path(cfg['job'])/'result.json',row)
  with self.assertRaisesRegex(ValueError,'Stop'):library.delete(self.root,row['id'])
 def test_speech_library_rpc_offers_per_document_models_and_verified_export(self):
  helper=self.root/'helper';helper.touch();app=Studio(self.root,ROOT/'Resources',helper=helper)
  before=copy.deepcopy(app.store.settings);cfg,row=self.take()
  result=app.dispatch('speech-export-file',dict(id=row['id']));self.assertEqual(Path(result['path']).read_bytes(),(Path(cfg['job'])/'voice.wav').read_bytes())
  app.dispatch('speech-load',dict(id=row['id']));self.assertEqual(app.store.settings,before)
  with patch.object(app,'model_inventory',return_value=[dict(id='mlx:installed-qwen',title='Installed Qwen',category='text',installed=True)]):
   self.assertEqual(app.dispatch('speech-library',{})['textModels'][0]['id'],'mlx:installed-qwen')

class SpeechReviewTests(unittest.TestCase):
 def fixture(self,root):
  path=wav(root/'first.wav');cfg=dict(storage=str(root),job=str(root),ttsBackend='drama3',targetLanguage='yue',speechStudio=dict(id='a'*32,autoRepair=True))
  cue=dict(start=0,end=20,cantonese='我哋今日一齊出發啦。',text='我哋今日一齊出發啦。',reviewIndex=0)
  return cfg,cue,path
 def test_uncertain_spelling_and_unavailable_listeners_do_not_trigger_retakes(self):
  for evidence in ({},{1:dict(decision='unconfirmed',language='zh',heard='我們今日一起出發啦')}):
   with tempfile.TemporaryDirectory() as d:
    root=Path(d);cfg,cue,path=self.fixture(root)
    with patch.object(quality,'signal_problems',return_value=[]),patch('normal_mode.inspect',return_value=evidence),patch('dubbing.gsv_audio') as generate:
     selected,report=quality.review(cfg,root,[cue],[path],Mock(),Mock())
    generate.assert_not_called();self.assertEqual(selected,[path]);self.assertEqual(report['status'],'needs-review')
 def test_confirmed_defect_retries_at_most_twice_and_only_verified_candidate_replaces(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cfg,cue,path=self.fixture(root);original=path.read_bytes();bad=wav(root/'bad.wav');good=wav(root/'good.wav')
   wrong={1:dict(decision='japanese',language='ja',heard='こんにちは世界',languageFailure='japanese')};right={1:dict(decision='cantonese',language='yue',heard=cue['cantonese'])}
   with patch.object(quality,'signal_problems',return_value=[]),patch('normal_mode.inspect',side_effect=[wrong,wrong,right]),patch('dubbing.gsv_audio',side_effect=[[bad],[good]]) as generate:
    selected,report=quality.review(cfg,root,[cue],[path],Mock(),Mock())
   self.assertEqual(generate.call_count,2);self.assertEqual(selected,[good]);self.assertEqual(report['status'],'passed');self.assertEqual(path.read_bytes(),original)
   self.assertFalse(report['qualityCertified']);self.assertEqual(report['repairedParts'],[1]);self.assertEqual(len(report['parts'][0]['attempts']),2)
   # Reopening the same take cannot replenish the budget or generate again.
   with patch.object(quality,'signal_problems',return_value=[]),patch('normal_mode.inspect',side_effect=[wrong,wrong,right]),patch('dubbing.gsv_audio') as generate:
    selected,_=quality.review(cfg,root,[cue],[path],Mock(),Mock())
   generate.assert_not_called();self.assertEqual(selected,[good])
 def test_bad_candidates_keep_original_and_manual_review_note(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cfg,cue,path=self.fixture(root);candidate=wav(root/'candidate.wav');wrong={1:dict(decision='japanese',language='ja',heard='こんにちは世界',languageFailure='japanese')}
   with patch.object(quality,'signal_problems',return_value=[]),patch('normal_mode.inspect',return_value=wrong),patch('dubbing.gsv_audio',return_value=[candidate]) as generate:
    selected,report=quality.review(cfg,root,[cue],[path],Mock(),Mock())
   self.assertEqual(selected,[path]);self.assertEqual(generate.call_count,2);self.assertEqual(report['status'],'needs-review');self.assertTrue(all(not a['adopted'] for a in report['parts'][0]['attempts']))
 def test_silent_audio_is_a_physical_failure(self):
  with tempfile.TemporaryDirectory() as d:self.assertEqual(quality.signal_problems(wav(Path(d)/'silent.wav',silent=True),'你好。'),['missing-or-silent'])

if __name__=='__main__':unittest.main()
