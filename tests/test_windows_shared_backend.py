import json,sys,tempfile,unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch
R=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(R/'windows'),str(R/'Resources')]
import dubbing
import shared_backend as native

class WindowsSharedBackendTests(unittest.TestCase):
 def runtime(self,root,**changes):
  p=root/'runtimes/gpt'/('Scripts/python.exe' if sys.platform=='win32' else 'bin/python')
  p.parent.mkdir(parents=True);p.touch()
  row=dict(backend='nvidia',modelLoadPassed=True,modelVersion='v4');row.update(changes)
  (root/'gpt-windows-ready.json').write_text(json.dumps(row))
  return p
 def test_only_native_probe_markers_and_matching_gpt_version_are_accepted(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cfg=dict(storage=d)
   (root/'gsv-ready.json').write_text('{}') # An installed Mac model is not a native probe.
   with self.assertRaisesRegex(ValueError,'incomplete'):native.launch_spec(cfg,'tts',{})
   python=self.runtime(root)
   executable,req=native.launch_spec(cfg,'tts',dict(device='mps',gsvVersion='v4'))
   self.assertEqual(executable,python);self.assertEqual(req['device'],'cuda')
   self.assertEqual(req['nativeFormat'],'pytorch')
   with self.assertRaisesRegex(ValueError,'selected GPT version'):native.launch_spec(cfg,'tts',dict(gsvVersion='v2ProPlus'))
   with self.assertRaisesRegex(ValueError,'setup is incomplete'):native.launch_spec(cfg,'drama3',{})
   (root/'gpt-windows-ready.json').write_text('{"modelLoadPassed":false}')
   with self.assertRaisesRegex(ValueError,'probe'):native.launch_spec(cfg,'tts',{})
 def test_cpu_marker_cannot_claim_requested_cuda_and_explicit_cpu_is_honoured(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.runtime(root,backend='cpu')
   with self.assertRaisesRegex(ValueError,'CPU-only'):native.launch_spec(dict(storage=d),'tts',dict(device='cuda'))
   self.assertEqual(native.launch_spec(dict(storage=d),'tts',{})[1]['device'],'cpu')
 def test_explicit_gpu_index_is_not_lost_when_device_is_normalized(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.runtime(root)
   req=native.launch_spec(dict(storage=d),'tts',dict(device='cuda:1'))[1]
   self.assertEqual(req['gpuIndex'],1);self.assertEqual(req['device'],'cuda')
 def test_drama_production_uses_the_native_backend_and_variant_that_passed_setup(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);python=root/'runtimes/worker'/('Scripts/python.exe' if sys.platform=='win32' else 'bin/python');python.parent.mkdir(parents=True);python.touch()
   marker=root/'drama3-windows-ready.json';marker.write_text(json.dumps(dict(backend='cuda',variant='drama3-small-iq3',nativeFormat='gguf',modelLoadPassed=True,speechInferencePassed=True)))
   executable,req=native.launch_spec(dict(storage=d),'drama3',dict(device='auto',drama3Model='drama3-small-iq3'))
   self.assertEqual(executable,python);self.assertEqual(req['drama3Backend'],'cuda');self.assertEqual(req['drama3Model'],'drama3-small-iq3')
   with self.assertRaisesRegex(ValueError,'retired'):native.launch_spec(dict(storage=d),'drama3',dict(drama3Model='drama3-native-q2'))
   self.assertEqual(native.launch_spec(dict(storage=d),'drama3',dict(device='cpu',drama3Model='drama3-small-iq3'))[1]['drama3Backend'],'cpu')
 def test_local_voice_requires_its_own_verified_variant_and_forces_yue_cpu(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);python=root/'runtimes/local'/('Scripts/python.exe' if sys.platform=='win32' else 'bin/python');python.parent.mkdir(parents=True);python.touch()
   marker=root/'local-windows-ready.json'
   ready=dict(backend='nvidia',modelLoadPassed=True,speechInferencePassed=True,verifiedEngines=['wsyue'],variants={'wsyue':'wsyue-cosy2-zjg'})
   marker.write_text(json.dumps(ready));cfg=dict(storage=d,wsyueModel='wsyue-cosy2-zjg')
   executable,req=native.launch_spec(cfg,'wsyue',{})
   self.assertEqual(executable,python);self.assertEqual(req['device'],'cpu');self.assertEqual(req['wsyueModel'],'wsyue-cosy2-zjg')
   with self.assertRaisesRegex(ValueError,'own speech probe'):native.launch_spec(cfg,'voxcpm2',{})
   with self.assertRaisesRegex(ValueError,'not the one verified'):native.launch_spec(cfg,'wsyue',{'wsyueModel':'wsyue-cosy2-base'})
 def test_child_calls_shared_gpt_loop_and_keeps_fast_mode_and_items(self):
  import shared_inference,dubbing_runner
  calls=[]
  compatibility=SimpleNamespace(audio_compatibility=lambda:calls.append('audio'),gpt_text_compatibility=lambda:calls.append('text'))
  hardware=SimpleNamespace(torch_probe=lambda *a:dict(device='cuda:0',kernelPassed=True))
  cfg=dict(storage='native-models',device='cuda',productionMode='fast',gsvVersion='v4',items=[dict(text='講完啦。',reviewIndex=0)])
  with patch.object(shared_inference.sys,'platform','win32'),patch.dict(sys.modules,{'native_tts':compatibility,'gpu':hardware}),patch.object(dubbing_runner,'tts') as shared,patch.object(dubbing_runner,'emit'):
   shared_inference.execute('tts',cfg)
  actual=shared.call_args.args[0]
  self.assertEqual(actual['items'],cfg['items']);self.assertEqual(actual['productionMode'],'fast')
  self.assertEqual(actual['device'],'cuda:0');self.assertEqual(calls,['audio','text'])
 def fixture(self,root,body):
  (root/'shared_inference.py').write_text(body)
  cfg=dict(storage=str(root),ffmpeg='/unused/ffmpeg',ttsBackend='gpt-sovits',targetLanguage='yue')
  job=root/'job';job.mkdir();item=dict(output=str(job/'take.wav'),text='講完啦。',reviewIndex=0)
  req=dict(storage=str(root),job=str(job),items=[item])
  return cfg,req
 def test_normal_listen_uses_verified_native_asr_and_shared_single_batch(self):
  import shared_inference,normal_mode
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);python=root/'runtimes/asr'/('Scripts/python.exe' if sys.platform=='win32' else 'bin/python')
   python.parent.mkdir(parents=True);python.touch()
   (root/'asr-windows-ready.json').write_text(json.dumps(dict(backend='nvidia',modelLoadPassed=True)))
   cfg=dict(storage=d,items=[dict(audio='own-take.wav',text='等陣先。')])
   executable,request=native.launch_spec(cfg,'normal-listen',cfg)
   self.assertEqual(executable,python);self.assertEqual(request['device'],'cuda')
   with patch.object(shared_inference.sys,'platform','win32'),patch.object(normal_mode,'listen',return_value='checked') as listen:
    self.assertEqual(shared_inference.execute('normal-listen',request),'checked')
   listen.assert_called_once_with(request)
 def test_real_child_events_failure_and_rejected_history_share_the_common_policy(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cfg,req=self.fixture(root,'''import json,sys,wave
from pathlib import Path
r=json.loads(Path(sys.argv[2]).read_text());p=Path(r['items'][0]['output'])
with wave.open(str(p.with_suffix('.rejected.wav')),'wb') as w:
 w.setparams((1,2,24000,0,'NONE','not compressed'));w.writeframes(b'\\x00\\x10'*100)
p.with_suffix('.health.json').write_text(json.dumps([{'problems':['generation-limit']}]))
print(json.dumps({'stage':'配音','message':'one processed','workCompleted':1,'workTotal':1,'cueIndex':0}),flush=True)
print(json.dumps({'stage':'錯誤','message':'generation-limit'}),flush=True)
sys.exit(1)
''')
   events=[];outer=dubbing._run_model_job
   with patch.object(native,'HERE',root),patch.object(native,'launch_spec',side_effect=lambda c,a,r:(Path(sys.executable),r)),native.bind():
    with self.assertRaisesRegex(RuntimeError,'generation-limit'):
     dubbing.model_job(cfg,'tts',req,lambda *a,**kw:events.append((a,kw)))
   self.assertIs(dubbing._run_model_job,outer)
   self.assertEqual(events[0][1]['workCompleted'],1)
   records=list((root/'job/recording-history').glob('*/take.json'))
   self.assertEqual(len(records),1);record=json.loads(records[0].read_text())
   self.assertEqual(record['index'],1);self.assertFalse(record['automaticallyAccepted'])
   self.assertIn('generation-limit',record['reason'])
   self.assertTrue((root/'job/take.rejected.wav').is_file())
 def test_stalled_child_is_terminated_without_removing_a_completed_take(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cfg,req=self.fixture(root,'import time\ntime.sleep(30)\n')
   cfg['modelStallSeconds']=.01
   take=Path(req['items'][0]['output']);take.write_bytes(b'previous take')
   with patch.object(native,'HERE',root),patch.object(native,'launch_spec',side_effect=lambda c,a,r:(Path(sys.executable),r)):
    with self.assertRaisesRegex(RuntimeError,'stalled'):native.run_model_job(cfg,'tts',req,lambda *a,**kw:None)
   self.assertEqual(take.read_bytes(),b'previous take')

if __name__=='__main__':unittest.main()
