"""Standalone clip persistence, model boundaries and real WAV delivery checks."""
import base64,copy,json,math,shutil,subprocess,sys,tempfile,types,unittest,wave
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows'),str(ROOT/'studio')]
import speech_library as library
import speech_studio as pipeline
from desktop_state import defaults
from backend import Studio

class SpeechStudioTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.storage=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def cfg(self,**patches):
  request=library.submit(self.storage,defaults(),dict(action='generate',cantonese='你好呀，今日天氣好好。',**patches))
  return library.read(request)
 def test_language_switch_keeps_folder_identity_and_saved_audio(self):
  cfg=self.cfg();job=Path(cfg['job']);audio=job/'voice.wav'
  with wave.open(str(audio),'wb') as wav:wav.setparams((1,2,44100,0,'NONE','not compressed'));wav.writeframes(b'\x00\x10'*4410)
  row=library.read(job/'result.json');row.update(status='complete',audio=str(audio));library.write(job/'result.json',row);library.save(self.storage,row['id'])
  for language,name in library.NAMES.items():
   data=library.listing(self.storage,language);self.assertEqual(data['folder'],dict(id='speech-studio',name=name));self.assertTrue(data['clips'][0]['saved']);self.assertEqual(Path(data['clips'][0]['audio']).read_bytes(),audio.read_bytes())
 def test_recorded_input_survives_reopening(self):
  recorded=library.upload(self.storage,base64.b64encode(b'own recording').decode(),'audio/webm;codecs=opus');library.write(library.root(self.storage)/'draft.json',dict(mode='recording',inputID=recorded['id']))
  self.assertEqual(library.listing(self.storage)['draft']['inputPath'],recorded['path'])
 def test_reject_empty_invalid_or_escaping_recording(self):
  for data in ('','?notbase64'):
   with self.assertRaises(ValueError):library.upload(self.storage,data,'audio/webm')
  with self.assertRaises(ValueError):library.folder(self.storage,'../outside')
  p=library.root(self.storage)/'inputs'/('a'*32);p.mkdir(parents=True);(p/'source.wav').symlink_to(ROOT/'LICENSE')
  with self.assertRaises(ValueError):library.input_audio(self.storage,'a'*32)
 def test_unknown_or_nonfinite_controls_do_not_create_job(self):
  for controls in (dict(rate=float('nan')),dict(rate=10),dict(parameters=dict(notAParameter=4)),dict(engine='unknown')):
   with self.assertRaises(ValueError):self.cfg(**controls)
  self.assertEqual(list((library.root(self.storage)/'clips').glob('*')),[])
 def test_failed_audio_cannot_be_saved(self):
  cfg=self.cfg()
  with self.assertRaises(ValueError):library.save(self.storage,cfg['speechStudio']['id'])
  self.assertFalse(library.listing(self.storage)['clips'][0]['saved'])
 def test_complete_script_split_without_text_loss(self):
  text='香港廣東話，保持每個字。\n英文名 Alice 123！'*70
  pieces=pipeline.chunks(text);self.assertEqual(''.join(pieces),text);self.assertTrue(all(0<len(p)<=60 for p in pieces))
 def test_complete_reference_not_arbitrary_middle_cut(self):
  rows=[dict(start=1,end=2,text='one'),dict(start=2.1,end=4.5,text='two')]
  self.assertEqual(pipeline.reference_span(rows),(1.,4.5,'one two'))
  self.assertIsNone(pipeline.reference_span([dict(start=0,end=20,text='too long')]))
 def test_task_does_not_modify_video_queue_or_production_defaults(self):
  helper=self.storage/'helper';helper.write_text('test')
  app=Studio(self.storage,ROOT/'Resources',helper=helper)
  from use_terms import document
  app.dispatch('accept-use-terms',dict(accepted=True,sha256=document()['sha256'],language='en'))
  before=copy.deepcopy(app.store.settings)
  result=app.dispatch('speech-studio',dict(action='generate',cantonese='你好呀。',engine='gpt-sovits'))
  self.assertEqual(app.store.queue,[]);self.assertEqual(app.store.settings,before);self.assertNotIn('rowID',result)
  self.assertEqual(result['action'],'speech-studio');self.assertEqual(len(result['speechClipID']),32)
  final=app.dispatch('speech-finish',dict(id=result['speechClipID'],code=1,paused=True))
  self.assertEqual(final['status'],'stopped')
 def test_running_video_blocks_standalone_inference(self):
  app=Studio(self.storage,ROOT/'Resources');app.store.queue=[dict(status='running')]
  from use_terms import document
  app.dispatch('accept-use-terms',dict(accepted=True,sha256=document()['sha256'],language='en'))
  with self.assertRaisesRegex(ValueError,'Pause'):app.dispatch('speech-studio',dict(action='generate',cantonese='你好。'))
 def test_translation_failure_cannot_be_reported_complete(self):
  request=library.submit(self.storage,defaults(),dict(source='Hello',action='translate'));cfg=library.read(request)
  worker=types.SimpleNamespace(emit=lambda *a,**kw:None,ollama_chat=lambda *a,**kw:'{}')
  cfg.update(port=11447,model='test')
  with self.assertRaises(ValueError):pipeline.process(worker,cfg)
  self.assertEqual(library.read(Path(cfg['job'])/'result.json')['status'],'failed')
 def test_recording_auto_language_does_not_inherit_text_selection(self):
  # Boundary tested with a fake Whisper module: not a claim of recogniser quality.
  import array
  raw=self.storage/'pcm';raw.write_bytes(array.array('f',[.1]*1600).tobytes());out=self.storage/'transcript.json';req=self.storage/'request.json';library.write(req,dict(audio=str(raw),modelPath='installed',output=str(out)))
  seen={}
  class Whisper:
   def __init__(self,*a,**kw):pass
   def transcribe(self,audio,**kw):seen.update(kw);return iter([types.SimpleNamespace(start=0,end=4,text='bonjour')]),types.SimpleNamespace(language='fr')
  with patch.dict(sys.modules,{'faster_whisper':types.SimpleNamespace(WhisperModel=Whisper)}):pipeline.transcribe(req)
  self.assertIsNone(seen['language']);self.assertEqual(library.read(out)['language'],'fr')
 def test_final_audio_is_real_44100_wav_and_reopens(self):
  ffmpeg=shutil.which('ffmpeg');ffprobe=shutil.which('ffprobe')
  if not ffmpeg or not ffprobe:self.skipTest('FFmpeg is not available')
  cfg=self.cfg();cfg.update(ffmpeg=ffmpeg,ffprobe=ffprobe)
  job=Path(cfg['job']);tone=job/'fixture.wav'
  subprocess.run([ffmpeg,'-v','error','-f','lavfi','-i','sine=frequency=440:duration=1','-c:a','pcm_s16le',str(tone)],check=True)
  worker=types.SimpleNamespace(emit=lambda *a,**kw:None,run=lambda args:subprocess.check_output([str(a) for a in args]))
  with patch('dubbing.gsv_audio',return_value=[tone]):result=pipeline.process(worker,cfg)
  with wave.open(result['audio']) as wav:self.assertEqual(wav.getframerate(),44100);self.assertGreater(wav.getnframes(),40000)
  self.assertEqual(result['status'],'needs-review') # A synthetic tone is not speech verification.
  library.save(self.storage,result['id'],accept_review=True);self.assertTrue(library.listing(self.storage)['clips'][0]['saved'])

if __name__=='__main__':unittest.main()
