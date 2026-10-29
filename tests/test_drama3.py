import json,sys,tempfile,unittest,wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly  # Load native NumPy modules before patch.dict restores sys.modules.
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import drama3,local_tts,dubbing,voice_models

class Drama3Tests(unittest.TestCase):
 def test_reference_resampling_and_language_hint_preserve_approved_words(self):
  for language,cue in [('yue','用香港廣東話講'),('en','Speak natural English')]:
   with self.subTest(language=language),tempfile.TemporaryDirectory() as d:
    ref=Path(d)/'ref.wav';sf.write(ref,np.ones((24000,2),dtype=np.float32)*.1,24000)
    model=Mock();model.generate.return_value=[SimpleNamespace(audio=np.ones(10)),SimpleNamespace(audio=np.ones(20))]
    item=dict(text='Approved dialogue',profile=dict(reference=str(ref),promptText='Exact reference transcript'))
    mx=SimpleNamespace(random=Mock())
    with patch.dict(sys.modules,{'mlx.core':mx}):
     # Importing mlx.core requires the namespace too on runtimes without MLX.
     mlx=SimpleNamespace(core=mx)
     with patch.dict(sys.modules,{'mlx':mlx}):result=drama3.generate(model,item,dict(targetLanguage=language))
    args=model.generate.call_args.kwargs
    self.assertEqual({k:args[k] for k in ('temperature','top_p','top_k')},dict(temperature=1.,top_p=.9,top_k=30))
    self.assertEqual(item['text'],'Approved dialogue');self.assertIn(cue,args['text'])
    self.assertTrue(args['text'].endswith('Approved dialogue'))
    self.assertEqual(len(args['ref_audio']),44100);self.assertEqual(args['ref_audio'].ndim,1)
    self.assertEqual(args['ref_text'],'Exact reference transcript');self.assertEqual(len(result),30)
   # The strict cue must keep asking for the reference pitch movement, not a flat read.
   self.assertIn('唔好平讀',drama3.language_hint('yue','cantonese-strict'))
   self.assertIn('用香港廣東話講',drama3.language_hint('yue','cantonese-strict'))
 def test_failure_is_not_a_take_and_completed_take_survives_retry(self):
  with tempfile.TemporaryDirectory() as d:
   bad=Path(d)/'bad.wav';good=Path(d)/'good.wav'
   cfg=dict(items=[dict(text='壞錄音',output=str(bad),reviewIndex=None),dict(text='出發啦',output=str(good),reviewIndex=2)])
   raw=np.sin(np.arange(44100)*.03).astype(np.float32)*.1
   with patch.object(drama3,'load'),patch.object(drama3,'generate',side_effect=[ValueError('bad generation'),raw]),patch('tts_health.problems',return_value=[]):
    with self.assertRaisesRegex(ValueError,'第 1 段'):drama3.synthesize(cfg,Mock())
   self.assertFalse(bad.exists());self.assertTrue(good.is_file())
   self.assertEqual(json.loads(bad.with_suffix('.failure.json').read_text())['error'],'bad generation')
   self.assertFalse(good.with_suffix('.failure.json').exists())
   with wave.open(str(good)) as f:self.assertEqual(f.getframerate(),44100)
   original=good.read_bytes()
   with patch.object(drama3,'load'),patch.object(drama3,'generate') as generate:
    drama3.synthesize(dict(items=[cfg['items'][1]]),Mock());generate.assert_not_called()
   self.assertEqual(original,good.read_bytes())
 def test_cooperative_skip_is_propagated_before_loading(self):
  from track_control import UserSkipped
  with tempfile.TemporaryDirectory() as d:
   (Path(d)/'skip-generation.json').write_text(json.dumps(dict(token='current')))
   with patch.object(drama3,'load') as load:
    with self.assertRaises(UserSkipped):drama3.synthesize(dict(items=[],_trackControl=dict(folder=d,token='current')),Mock())
    load.assert_not_called()
 def test_variant_rejects_other_architecture_and_local_dispatch_is_isolated(self):
  with self.assertRaises(ValueError):drama3.validate(dict(drama3Model='voxcpm2-2b-bf16'))
  with patch.object(drama3,'synthesize') as synthesize:
   cfg=dict(items=[]);emit=Mock();local_tts.synthesize(cfg,emit,'drama3');synthesize.assert_called_once_with(cfg,emit)
 def test_child_uses_mlx_runtime_and_separate_readiness(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);python=root/'text-runtime/bin/python3';python.parent.mkdir(parents=True);python.touch()
   (root/'drama3-ready.json').write_text('{}')
   process=Mock(stdout=[]);process.wait.return_value=0
   cfg=dict(storage=d,ffmpeg='/usr/bin/ffmpeg');request=dict(job=d,items=[])
   with patch('runtime_paths.python_for',return_value=python) as runtime,patch('subprocess.Popen',return_value=process) as start:
    dubbing._model_job(cfg,'drama3',request,Mock())
   runtime.assert_called_once_with(root,'text-runtime')
   self.assertEqual(Path(start.call_args.args[0][1]).name,'drama3.py')
   self.assertEqual(start.call_args.args[0][2],'drama3')
   (root/'drama3-ready.json').unlink()
   with patch('runtime_paths.python_for',return_value=python),patch('subprocess.Popen') as start:
    with self.assertRaisesRegex(ValueError,'Drama 3'):dubbing._model_job(cfg,'drama3',request,Mock())
    start.assert_not_called()
 def test_pinned_vendor_sources_match_provenance(self):
  import hashlib
  vendor=Path(drama3.__file__).parent/'tts-vendor/drama3';source=json.loads((vendor/'SOURCE.json').read_text())
  for name,digest in source['files'].items():self.assertEqual(hashlib.sha256((vendor/name).read_bytes()).hexdigest(),digest,name)
  row=voice_models.choice('drama3');self.assertEqual(row['repo'],'mlx-community/fish-audio-drama-3-4bit')
  self.assertEqual(row['bytes'],23781117246)

class DramaCompletionTests(unittest.TestCase):
 def test_plain_whole_retry_preserves_complete_turn_without_inline_command(self):
  with tempfile.TemporaryDirectory() as temp:
   ref=Path(temp)/'ref.wav';sf.write(ref,np.ones(24000,dtype=np.float32)*.1,24000)
   text='嗯，呢位國王睇落都幾唔錯喎。';model=Mock()
   model.generate.return_value=[SimpleNamespace(audio=np.ones(1000)*.1,token_count=7)]
   mx=SimpleNamespace(random=Mock())
   with patch.dict(sys.modules,{'mlx':SimpleNamespace(core=mx),'mlx.core':mx}):
    drama3.generate(model,dict(text=text,deliveryStyle='plain-whole',profile=dict(reference=str(ref),promptText='香港聲線')),dict(targetLanguage='yue'))
   model.generate.assert_called_once();self.assertEqual(model.generate.call_args.kwargs['text'],text)
 def test_generation_budget_is_not_the_japanese_delivery_deadline(self):
  text='令到魔力金屬結晶嘅神秘力量，就係羈絆能量。'
  maximum=drama3.generation_budget(text,.5)
  self.assertGreater(maximum*2048/44100,len(text)*.5)
  self.assertLessEqual(maximum,1024)
 def test_clause_retry_generates_every_approved_clause_without_rewriting(self):
  with tempfile.TemporaryDirectory() as temp:
   ref=Path(temp)/'ref.wav';sf.write(ref,np.ones(24000,dtype=np.float32)*.1,24000)
   approved='即係，魔力金屬結晶嘅力量，就係羈絆能量？'
   pieces=drama3.complete_clauses(approved);self.assertEqual(''.join(pieces),approved)
   calls=[]
   def generate(**kwargs):
    calls.append(kwargs);return [SimpleNamespace(audio=np.ones(1000)*.1,segment_idx=0,token_count=7)]
   model=SimpleNamespace(generate=generate);mx=SimpleNamespace(random=Mock());cfg=dict(targetLanguage='yue')
   with patch.dict(sys.modules,{'mlx':SimpleNamespace(core=mx),'mlx.core':mx}):
    result=drama3.generate(model,dict(text=approved,deliveryStyle='complete-clauses',profile=dict(reference=str(ref),promptText='乾淨香港廣東話聲線')),cfg)
   self.assertEqual(len(calls),len(pieces));self.assertEqual(len(result),1000*len(pieces))
   self.assertEqual([c['text'].split('] ',1)[1] for c in calls],pieces)
   self.assertEqual(cfg['_dramaLastGeneration']['status'],'completed')
 def test_hitting_decoder_limit_never_creates_a_successful_audio_file(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);ref=root/'ref.wav';sf.write(ref,np.ones(24000,dtype=np.float32)*.1,24000);output=root/'cut.wav'
   def generate(**kwargs):return [SimpleNamespace(audio=np.ones(1000)*.1,segment_idx=0,token_count=kwargs['max_tokens'])]
   model=SimpleNamespace(generate=generate);mx=SimpleNamespace(random=Mock())
   cfg=dict(targetLanguage='yue',items=[dict(text='呢句一定要講晒',output=str(output),profile=dict(reference=str(ref),promptText='參考聲音'))])
   with patch.object(drama3,'load',return_value=model),patch.dict(sys.modules,{'mlx':SimpleNamespace(core=mx),'mlx.core':mx}):
    with self.assertRaisesRegex(ValueError,'generation-limit'):drama3.synthesize(cfg,Mock())
   self.assertFalse(output.exists())
   self.assertEqual(json.loads(output.with_suffix('.generation.json').read_text())['status'],'generation-limit')
   rejected=output.with_suffix('.rejected.raw.wav')
   self.assertTrue(rejected.is_file())
   self.assertEqual(len(sf.read(rejected)[0]),1000)
   from audio_fallback import healthy
   self.assertFalse(healthy(rejected))
   self.assertEqual(json.loads(output.with_suffix('.generation.json').read_text())['rejectedAudio'],str(rejected))

class DecoderRecoveryTests(unittest.TestCase):
 def test_cap_recovery_retains_actor_words_and_immutable_failed_attempt(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);output=root/'cue.wav'
   profile=dict(reference='same-actor.wav',promptText='日本語',language='ja')
   item=dict(output=str(output),text='無論點，我都要打敗佢！',approvedText='無論點，我都要打敗佢！',reviewIndex=166,profile=profile)
   cfg=dict(job=str(root),targetLanguage='yue');calls=[]
   def generated(model,fresh,config):
    calls.append(fresh)
    config['_dramaLastGeneration']=dict(status='generation-limit' if len(calls)==1 else 'completed',seed=fresh['seed'],parts=[])
    if len(calls)==1:raise drama3.GenerationLimit(np.ones(44100,dtype=np.float32)*.1)
    return np.sin(np.arange(44100)*.03).astype(np.float32)*.1
   with patch.object(drama3,'generate',side_effect=generated):
    result=drama3.generate_complete(None,item,cfg,Mock())
   self.assertEqual(len(result),44100)
   # Recovery keeps the Hong Kong delivery cue, so a repaired take still carries the emotion instruction.
   self.assertEqual([c['deliveryStyle'] for c in calls],['normal','cantonese-strict'])
   self.assertEqual([c['text'] for c in calls],[item['text']]*2)
   self.assertTrue(all(c['profile']==profile for c in calls))
   self.assertNotEqual(calls[0]['seed'],calls[1]['seed'])
   rows=list((root/'recording-history').glob('*/take.json'));self.assertEqual(len(rows),1)
   row=json.loads(rows[0].read_text());self.assertEqual(row['index'],167)
   self.assertEqual(row['spokenText'],item['text']);self.assertFalse(row['automaticallyAccepted'])
   self.assertEqual(cfg['_dramaLastGeneration']['status'],'completed')
   self.assertEqual(len(cfg['_dramaLastGeneration']['recoveryAttempts']),1)
   self.assertFalse(output.exists(),'Only synthesize may publish a signal-checked successful file')
 def test_all_caps_are_bounded_and_remain_failures(self):
  with tempfile.TemporaryDirectory() as temp:
   cfg=dict(job=temp,targetLanguage='yue');item=dict(output=str(Path(temp)/'cut.wav'),text='唔好走！',reviewIndex=159,profile={})
   def generated(model,fresh,config):
    config['_dramaLastGeneration']=dict(status='generation-limit',seed=fresh['seed'],parts=[])
    raise drama3.GenerationLimit(np.ones(44100,dtype=np.float32)*.1)
   with patch.object(drama3,'generate',side_effect=generated) as generate:
    with self.assertRaises(drama3.GenerationLimit):drama3.generate_complete(None,item,cfg,Mock())
   self.assertEqual(generate.call_count,3)
   self.assertEqual(len(list((Path(temp)/'recording-history').glob('*/take.json'))),3)
   self.assertEqual(cfg['_dramaLastGeneration']['status'],'generation-limit')
   self.assertFalse(Path(item['output']).exists())
