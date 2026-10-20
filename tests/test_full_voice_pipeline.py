import json,tempfile,sys,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import worker,dubbing,engine_policy

class FullVoicePipelineTests(unittest.TestCase):
 def cue(self):return dict(start=1.,end=3.,text='出発しよう',cantonese='我哋一齊出發啦。',speakerId='actor',reviewIndex=0)
 def test_every_active_default_runs_role_preparation_in_canonical_conversion(self):
  import speakers,acoustics
  class Prepared(Exception):pass
  for engine in engine_policy.ACTIVE:
   with self.subTest(engine=engine),tempfile.TemporaryDirectory() as d:
    root=Path(d);video=root/'source.mp4';video.write_bytes(b'source')
    cfg=dict(storage=str(root),video=str(video),ttsBackend=engine,autoSpeakers=True,translate=False,speechTiming=False,autoApprove=False,ffprobe='ffprobe',limit=0,dubLanguages=['yue'])
    meta=dict(format=dict(duration='10'),streams=[dict(codec_type='video'),dict(codec_type='audio')])
    with patch.object(worker,'run',return_value=json.dumps(meta).encode()),patch.object(worker,'emit'),patch.object(worker,'extract_cues',return_value=[self.cue()]),patch('model_recovery.recover'),patch.object(acoustics,'align'),patch.object(speakers,'assign',side_effect=Prepared) as assign:
     with self.assertRaises(Prepared):worker.convert(cfg)
     self.assertEqual(assign.call_count,1)
 def test_new_engine_reaches_canonical_synthesis_dispatch(self):
  for engine in ['voxcpm2','wsyue','drama3']:
   with self.subTest(engine=engine),tempfile.TemporaryDirectory() as d,patch.object(dubbing,'synthesize',return_value=('audio',[])) as synthesize:
    self.assertEqual(worker.synthesize(dict(ttsBackend=engine),Path(d),[self.cue()]),('audio',[]))
    synthesize.assert_called_once()
 def test_all_missing_profiles_stop_before_silent_takes_or_model_loading(self):
  with tempfile.TemporaryDirectory() as d,patch.object(dubbing,'gsv_audio') as generate:
   with self.assertRaisesRegex(ValueError,'全部對白未有可用角色參考'):
    dubbing.synthesize(dict(ttsBackend='voxcpm2',voiceProfiles=[],duration=10),Path(d),[self.cue()],Mock(),Mock())
   generate.assert_not_called();self.assertFalse(list(Path(d).glob('skipped*')))
 def test_profile_preflight_keeps_healthy_roles_despite_one_missing_role(self):
  with tempfile.TemporaryDirectory() as d:
   reference=Path(d)/'ref.wav';reference.write_bytes(b'fixture')
   cfg=dict(voiceProfiles=[dict(id='actor',name='Actor',reference=str(reference),promptText='出発しよう')])
   dubbing.require_profiles(cfg,[dict(self.cue(),speakerId='missing'),self.cue()])
 def test_all_skipped_timings_are_not_successful_even_with_output_file(self):
  with tempfile.TemporaryDirectory() as d,patch.object(dubbing,'synthesize',return_value=('silent.wav',[])):
   job=Path(d);(job/'timing.json').write_text(json.dumps([dict(index=1,skipped=True,renderedSeconds=0)]))
   with self.assertRaisesRegex(ValueError,'成功配音 0 段'):worker.synthesize(dict(ttsBackend='cosyvoice3'),job,[self.cue()])
 def test_restored_target_language_donor_counts_as_spoken_dialogue(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);(job/'timing.json').write_text(json.dumps([dict(index=1,skipped=True,renderedSeconds=0)]))
   self.assertEqual(dubbing.generated_dialogue({},job,[self.cue()],dict(audioFallbacks=[dict(index=1,sourceEngine='voxcpm2',sourceLanguage='yue')])),1)
   self.assertEqual(dubbing.generated_dialogue({},job,[self.cue()],dict(audioFallbacks=[dict(index=1,sourceEngine='original',sourceLanguage='ja')])),0)
 def test_original_only_vocalizations_do_not_require_role_generation(self):
  cue=dict(self.cue(),text='あああ！',japanese='あああ！',cantonese='啊！',nonverbal=True)
  self.assertEqual(dubbing.required_dialogue({},[cue]),[])
  dubbing.require_profiles({},[cue])

if __name__=='__main__':unittest.main()

class SilentDeliveryTests(unittest.TestCase):
 def test_all_failed_channels_never_export_eleven_silent_dubs_or_replace_old_output(self):
  import subprocess,shutil,wave
  from types import SimpleNamespace
  import multitrack
  ffmpeg=shutil.which('ffmpeg');ffprobe=shutil.which('ffprobe')
  if not ffmpeg or not ffprobe:self.skipTest('FFmpeg unavailable')
  def run(args):return subprocess.run([str(x) for x in args],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
  def write(p,x):Path(p).write_text(json.dumps(x))
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);silent=root/'silence.wav';source=root/'source.mp4'
   with wave.open(str(silent),'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(bytes(96000))
   run([ffmpeg,'-v','error','-y','-f','lavfi','-i','color=s=64x64:r=10:d=2','-i',silent,'-map','0:v','-map','1:a','-map','1:a','-c:v','libx264','-c:a','aac','-t','2',source])
   old=root/'source-AniCanto.mp4';old.write_bytes(b'previous output preserved')
   cfg=dict(storage=str(root/'data'),video=str(source),duration=2.,ffmpeg=ffmpeg,ffprobe=ffprobe,selectedEngines=list(engine_policy.ACTIVE),ttsBackend='voxcpm2',dubLanguages=['yue','en'],includeOriginal=True,subtitleOutput='none')
   cue=dict(start=0.,end=1.,text='Japanese',cantonese='出發啦',english='Go!',speakerId=None)
   review=root/'review.json';write(review,dict(config=cfg,cues=[cue],meta=dict(streams=[dict(codec_type='video'),dict(codec_type='audio')])))
   w=SimpleNamespace(run=run,atomic_json=write,emit=Mock(),render_review=Mock(side_effect=ValueError('全部對白未有可用角色參考')),ollama_chat=Mock(),parse_srt=worker.parse_srt,save_srt=worker.save_srt)
   with self.assertRaisesRegex(ValueError,'全部所選音軌成功配音 0 段'):multitrack.render(w,dict(review=str(review)))
   self.assertEqual(old.read_bytes(),b'previous output preserved');self.assertFalse((root/'report.json').exists())
   self.assertEqual(len(json.loads((root/'track-failures.json').read_text())),11)
   delivery=json.loads((root/'dialogue-delivery-audit.json').read_text())
   self.assertEqual(len(delivery['tracks']),11)
   self.assertTrue(all(t['missing']==1 and t['rows'][0]['reason']=='reference-blocked' and t['rows'][0]['messages'] for t in delivery['tracks']))
   self.assertNotIn('完成',[c.args[0] for c in w.emit.call_args_list])

class GroupedAttentionTests(unittest.TestCase):
 def test_expanded_grouped_heads_match_pytorch_prefill_and_cached_decode(self):
  import torch
  vendor=Path(__file__).parents[1]/'Resources/tts-vendor/voxcpm2';sys.path.insert(0,str(vendor))
  from voxcpm.modules.minicpm4.model import expand_grouped_kv
  torch.manual_seed(42)
  for length,causal in [(5,False),(5,True),(1,False)]:
   query=torch.randn(2,16,length,32);key=torch.randn(2,2,7,32);value=torch.randn_like(key)
   expected=torch.nn.functional.scaled_dot_product_attention(query,key,value,enable_gqa=True,is_causal=causal)
   expanded_key,expanded_value=expand_grouped_kv(query,key,value)
   actual=torch.nn.functional.scaled_dot_product_attention(query,expanded_key,expanded_value,enable_gqa=False,is_causal=causal)
   torch.testing.assert_close(actual,expected,rtol=2e-5,atol=2e-6)
 def test_invalid_grouped_head_ratio_refused(self):
  import torch
  from voxcpm.modules.minicpm4.model import expand_grouped_kv
  with self.assertRaises(ValueError):expand_grouped_kv(torch.zeros(1,3,1,4),torch.zeros(1,2,1,4),torch.zeros(1,2,1,4))
