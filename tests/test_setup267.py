"""Cache identity, bounded optional work and future-only production reset."""
import copy,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'studio'),str(ROOT/'windows'),str(ROOT/'Resources')]
from backend import Studio
from worker import run
import performance_audio as audio
import model_switch
import test_windows_setup_readiness266 as readiness

class AudioCacheTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.job=self.root/'tracks/one/versions/two';self.job.mkdir(parents=True)
  self.folder=self.job/'performance-tails';self.folder.mkdir()
  self.cfg=dict(video='/fixture/CloudStorage/GoogleDrive/movie.mkv',startOffset=3,duration=2,sourceAudioStream=1,ffmpeg='ffmpeg',skipNonDialogueCaptions=True)
  self.run=Mock(side_effect=AssertionError('No movie read expected'));self.emit=Mock()
 def wav(self,path,duration=2):
  import soundfile as sf,numpy as np
  sf.write(path,np.zeros(int(16000*duration)),16000)
 def cache(self,**change):
  path=self.root/'japanese-original.wav';self.wav(path)
  (self.root/'review.json').write_text(json.dumps(dict(config=dict(self.cfg,**change))))
  return path
 def test_nested_track_version_reuses_validated_pcm_with_caption_toggle_on_or_off(self):
  expected=self.cache()
  for enabled in (True,False):
   self.assertEqual(audio.original(dict(self.cfg,skipNonDialogueCaptions=enabled),self.job,self.folder,self.run,self.emit),expected.resolve())
  self.run.assert_not_called()
 def test_unrelated_root_window_stream_or_video_is_not_reused(self):
  for change in (dict(startOffset=4),dict(sourceAudioStream=2),dict(video='other')):
   self.cache(**change)
   with self.assertRaisesRegex(RuntimeError,'no complete local'):audio.original(self.cfg,self.job,self.folder,self.run,self.emit)
  self.run.assert_not_called()
 def test_incomplete_audio_is_rejected(self):
  self.cache();self.wav(self.root/'japanese-original.wav',.1)
  with self.assertRaisesRegex(RuntimeError,'no complete local'):audio.original(self.cfg,self.job,self.folder,self.run,self.emit)
 def test_local_fallback_is_atomic_and_bounded(self):
  cfg=dict(self.cfg,video=str(self.root/'local.mkv'))
  def extract(args,**kw):self.assertEqual(kw,dict(timeout=90));self.wav(Path(args[-1]))
  self.assertEqual(audio.original(cfg,self.job,self.folder,extract,self.emit),self.folder/'original-analysis.wav')
  self.assertFalse((self.folder/'original-analysis.partial.wav').exists())
 def test_failed_optional_extraction_leaves_no_valid_cache(self):
  cfg=dict(self.cfg,video=str(self.root/'local.mkv'))
  def fail(args,**kw):Path(args[-1]).write_bytes(b'partial');raise RuntimeError('timeout')
  with self.assertRaisesRegex(RuntimeError,'timeout'):audio.original(cfg,self.job,self.folder,fail,self.emit)
  self.assertFalse((self.folder/'original-analysis.partial.wav').exists());self.assertFalse((self.folder/'original-analysis.wav').exists())
 def test_worker_terminates_its_owned_timed_out_child(self):
  with self.assertRaisesRegex(RuntimeError,'completed recordings are retained'):run([sys.executable,'-c','import time;time.sleep(10)'],timeout=.05)

class ProductionResetTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.app=Studio(self.root,ROOT/'Resources',platform='darwin',helper=self.root/'helper');self.app.store.mode='expert'
  file=self.root/'source.mkv';file.write_bytes(b'fixture');self.app.store.add([str(file)]);self.row=self.app.store.queue[0]
  self.app.store.settings.update(model='keep-text',drama3Model='keep-voice',appearance='dark',includeOriginal=False,subtitleSelection='manual',dubLanguages=['en'],subtitleModes=['english'],exportFolder=str(self.root/'exports'),deploymentModels=dict(voice='keep-voice'),dramaTemperature=.5,aiAutoFix=True,contentChecks=2,backgroundGain=.2,backgroundDucking=True)
  request=self.root/'saved.json';request.write_text('{"contentChecks":2}')
  self.row.update(status='paused',request=str(request),progress=.6);self.original=request.read_bytes()
 def test_global_reset_keeps_models_languages_media_and_frozen_request(self):
  before=copy.deepcopy(self.row);settings=copy.deepcopy(self.app.store.settings)
  self.app.dispatch('reset-production-parameters',{})
  got=self.app.store.settings
  for key in ('model','drama3Model','appearance','dubLanguages','subtitleModes','exportFolder','deploymentModels'):self.assertEqual(got[key],settings[key],key)
  self.assertEqual(got['dramaTemperature'],1.);self.assertFalse(got['aiAutoFix']);self.assertEqual(got['contentChecks'],0)
  self.assertEqual((got['backgroundGain'],got['backgroundDucking']),(.8,False))
  self.assertEqual(self.row,before);self.assertEqual(Path(self.row['request']).read_bytes(),self.original)
 def test_individual_reset_does_not_modify_global_settings_or_scope(self):
  self.app.dispatch('configure',dict(scope='video',id=self.row['id'],useGlobalSettings=False,settings={}))
  before=copy.deepcopy(self.app.store.settings)
  self.app.dispatch('reset-production-parameters',dict(scope='video',id=self.row['id']))
  self.assertEqual(self.app.store.settings,before);self.assertIs(self.row['useGlobalSettings'],False)
  self.assertEqual(self.row['productionSettings']['dramaTemperature'],1.);self.assertEqual(Path(self.row['request']).read_bytes(),self.original)
 def test_running_job_blocks_reset(self):
  self.row['status']='running';before=copy.deepcopy(self.app.store.settings)
  with self.assertRaises(ValueError):self.app.dispatch('reset-production-parameters',{})
  self.assertEqual(self.app.store.settings,before)

class ExplicitBackendTests(readiness.WindowsReadinessTests):
 def test_explicit_nvidia_retry_does_not_inherit_auto_cpu_pin(self):
  original=__import__('native_setup').plan(hardware=self.hw,drama_backend='cpu');self.commit(original)
  result=__import__('native_setup').plan(hardware=self.hw,backend='nvidia',drama_backend='cuda')
  self.assertEqual(result['voiceBackend'],'cuda');self.assertFalse(result['setupReady'])
  self.assertEqual(result['verifiedVoiceBackend'],'cpu') # Truthful old verification, not new inference.

class VisualSwitchTests(unittest.TestCase):
 def test_only_verified_optional_visual_drift_can_finalize(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);models=[dict(id=x,legacy=x,files=[dict(path='w',size=4)]) for x in ('text','voice')]
   for m in models:(root/m['id']).mkdir();(root/m['id']/'w').write_bytes(b'data')
   roles=dict(text='text',voice='voice',visual='text');plan=dict(engine='drama3',roles=roles,canDeployModels=True)
   token=model_switch.begin(root,plan,dict(text='text',voice='voice'),False)
   current=dict(text='text',voice='voice',visual=None);model_switch.write(root/'model-selections.json',current)
   receipt=dict(engine='drama3',roles=current,modelLoadPassed=True,speechInferencePassed=False);model_switch.write(root/'native-ready.json',receipt)
   with self.assertRaises(ValueError):model_switch.finish(root,token,models,lambda r,m:r/m['legacy'])
   receipt['speechInferencePassed']=True;model_switch.write(root/'native-ready.json',receipt)
   result=model_switch.finish(root,token,models,lambda r,m:r/m['legacy']);self.assertEqual(result['status'],'complete')
   self.assertIsNone(result['plan']['roles']['visual']);self.assertEqual(result['proposedPlan']['roles']['visual'],'text')

class ActivationTests(unittest.TestCase):
 def test_verified_current_selection_activates_without_launching_setup(self):
  with tempfile.TemporaryDirectory() as tmp:
   app=Studio(Path(tmp),ROOT/'Resources',platform='win32',helper=Path(tmp)/'helper')
   plan=dict(setupReady=True,engine='drama3',roles=dict(text='t',voice='v'),canDeployModels=True)
   base=app.dispatch;calls=[]
   def dispatch(op,p=None):
    calls.append(op)
    if op=='plan':return plan
    if op=='finish-model-switch':return dict(status='complete')
    return base(op,p)
   with patch.object(app,'dispatch',side_effect=dispatch),patch.object(model_switch,'begin',return_value='token'):
    result=base('activate-models',dict(engine='drama3',models=dict(text='t',voice='v')))
   self.assertTrue(result['activated']);self.assertNotIn('setup',calls)
 def test_unverified_selection_never_activates(self):
  with tempfile.TemporaryDirectory() as tmp:
   app=Studio(Path(tmp),ROOT/'Resources',platform='win32',helper=Path(tmp)/'helper');base=app.dispatch
   with patch.object(app,'dispatch',return_value=dict(setupReady=False)),patch.object(model_switch,'begin') as begin:
    self.assertFalse(base('activate-models',{})['activated']);begin.assert_not_called()

if __name__=='__main__':unittest.main()
