import array,json,sys,tempfile,unittest,wave
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import overlap_policy,runtime_recovery,repair_budget,track_control,dubbing

class RecoveryTests(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
 def tearDown(self):self.temp.cleanup()
 def wav(self,path,value=3000):
  with wave.open(str(path),'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(array.array('h',[value,-value]*12000).tobytes())
 def test_simultaneous_roles_retained_and_ambiguous_source_safe(self):
  cues=[dict(start=0,end=2,speakerId='a'),dict(start=1,end=3,speakerId='b'),dict(start=4,end=6,speakerId='c',mixedVoices=True)]
  result=overlap_policy.annotate(cues,self.root)
  self.assertEqual(result['pairs'][0]['indices'],[1,2]);self.assertEqual(cues[1]['sourceOverlaps'],[1]);self.assertFalse(cues[2].get('preserveOriginalSpeech',False))
  cues[2].update(preserveOriginalSpeech=False,overlapReviewed=True);overlap_policy.annotate(cues)
  self.assertFalse(cues[2]['preserveOriginalSpeech'])
 def test_actual_overrun_is_not_intentional_overlap(self):
  a=dict(start=0,end=2,speakerId='a');b=dict(start=1,end=3,speakerId='b')
  self.assertTrue(overlap_policy.expected(a,b,1,2));self.assertFalse(overlap_policy.expected(a,b,1,2.5))
 def test_wrong_language_and_lost_negation_trigger_bounded_retake(self):
  self.assertFalse(repair_budget.clear_content_problem(dict(cantonese='等一等'),dict(similarity=.3,languageMismatch=True)))
  self.assertTrue(repair_budget.clear_content_problem(dict(cantonese='Do not go.'),dict(similarity=.8,criticalDifferences=['negation'])))
  self.assertFalse(repair_budget.clear_content_problem(dict(cantonese='路飛！'),dict(similarity=.1)))
 def test_text_memory_recovery_keeps_context_and_persists_actual_model(self):
  import mlx_text,model_catalog
  backend=mlx_text.Backend(self.root);body=dict(model='large',messages=[dict(role='user',content='full context')]);seen=[]
  def generate(request):
   seen.append(request)
   if len(seen)==1:raise RuntimeError('out of memory')
   return 'complete'
  options=[dict(id='mlx:small',category='text',estimatedMemoryGB=4)]
  with patch.object(backend,'_generate',side_effect=generate),patch.object(backend,'unload') as unload,patch.object(model_catalog,'choice',return_value=dict(estimatedMemoryGB=10)),patch.object(model_catalog,'catalog',return_value=options),patch.object(model_catalog,'resolve',return_value=self.root):
   self.assertEqual(backend.generate(body),'complete');unload.assert_called_once()
  self.assertEqual(seen[1]['messages'],body['messages']);self.assertEqual(body['model'],'large');self.assertEqual(backend.recovered_models['large'],'mlx:small')
  self.assertEqual(json.loads((self.root/'text-runtime-recovery.json').read_text())['status'],'generated-needs-review')
 def request(self,count=2):return dict(job=str(self.root),items=[dict(output=str(self.root/f'{i}.wav'),text='Test') for i in range(count)])
 def test_oom_falls_back_smaller_without_mislabelling_original_or_overwriting_completed(self):
  cfg=dict(storage=str(self.root),cosyModel='cosy-0.5b-8bit');req=self.request();self.wav(req['items'][0]['output']);original=(self.root/'0.wav').read_bytes();calls=[]
  def execute(c,a,r,e):
   calls.append(r)
   if len(calls)==1:raise RuntimeError('Metal out of memory')
   self.wav(r['items'][0]['output'])
  with patch.object(runtime_recovery,'smaller',return_value=('cosyModel','cosy-0.5b-4bit')):runtime_recovery.run(cfg,'cosy',req,lambda *a:None,execute)
  self.assertEqual(len(calls),2);self.assertEqual(cfg['cosyModel'],'cosy-0.5b-8bit');self.assertFalse((self.root/'1.wav').exists());self.assertEqual((self.root/'0.wav').read_bytes(),original)
  self.assertIn('4bit',cfg['_runtimeReplacements'][str(self.root/'1.wav')])
 def test_gpt_memory_failure_retries_cpu_one_at_time_and_bounds_failures(self):
  calls=[]
  def fail(c,a,r,e):calls.append(r);raise RuntimeError('MPS allocation failed')
  with self.assertRaises(RuntimeError):runtime_recovery.run(dict(storage=str(self.root)),'tts',self.request(8),lambda *a:None,fail)
  self.assertEqual(len(calls),3);self.assertEqual(calls[1]['device'],'cpu');self.assertEqual(len(calls[1]['items']),1)
  self.assertEqual(json.loads((self.root/'runtime-recovery.json').read_text())[0]['items'][-1]['status'],'deferred-to-fallback')
 def test_non_memory_error_or_user_skip_never_retries(self):
  for error in [ValueError('Unknown voice'),track_control.UserSkipped('out of memory')]:
   calls=[]
   def fail(*a):calls.append(a);raise error
   with self.assertRaises(type(error)):runtime_recovery.run({},'cosy',self.request(),lambda *a:None,fail)
   self.assertEqual(len(calls),1)
 def test_expected_overlap_does_not_create_timing_error(self):
  cues=[dict(start=0,end=2,speechStart=0,speechEnd=2,deliveryEnd=2,cantonese='A',speakerId='a'),dict(start=1,end=3,speechStart=1,speechEnd=3,deliveryEnd=3,cantonese='B',speakerId='b')]
  report=[dict(index=i+1,seconds=2,slot=2) for i in range(2)]
  def run(args):return array.array('h',[1000]*48000).tobytes()
  dubbing.render_complete_preview(dict(duration=3,ffmpeg='ffmpeg'),self.root,cues,[self.root/'a.wav',self.root/'b.wav'],report,run,lambda *a:None)
  self.assertEqual(report[1]['expectedOverlaps'],[1]);self.assertFalse(report[1]['requiresTimingReview'])
 def test_mixed_original_does_not_require_or_synthesize_character_reference(self):
  cues=[dict(start=0,end=1,cantonese='mixed',preserveOriginalSpeech=True)]
  source=self.root/'source.wav';self.wav(source)
  def run(args):self.wav(args[-1])
  with patch.object(dubbing,'profile_for',side_effect=AssertionError('must not clone mixed source')):
   paths=dubbing.gsv_audio(dict(dialoguePath=str(source),ttsBackend='cosyvoice3',ffmpeg='ffmpeg'),self.root,cues,run,lambda *a:None)
  self.assertTrue(paths[0].exists())
 def test_shorter_take_uses_isolated_asr_and_rejects_wrong_language(self):
  import speechcheck
  path=self.root/'take.wav';self.wav(path)
  evidence=dict(heard='Do not go.',languageMismatch=False)
  with patch.object(speechcheck,'inspect',return_value=[evidence]) as inspect:
   self.assertTrue(dubbing.candidate_content_matches(dict(targetLanguage='en',pronunciationText='alias'),path,'Do not go.')[0])
   self.assertEqual(inspect.call_args.args[0]['pronunciationText'],'')
  with patch.object(speechcheck,'inspect',return_value=[dict(heard='Do not go.',languageMismatch=True)]):
   self.assertFalse(dubbing.candidate_content_matches(dict(targetLanguage='en'),path,'Do not go.')[0])
  with patch.object(speechcheck,'inspect',return_value=[dict(heard='Do go.',languageMismatch=False)]):
   self.assertFalse(dubbing.candidate_content_matches(dict(targetLanguage='en'),path,'Do not go.')[0])
 def test_source_fallback_does_not_double_background_after_silent_stem(self):
  import audio_fallback
  folder=self.root/'track';folder.mkdir();stem=self.root/'stem.wav';self.wav(stem,0);bg=self.root/'bg.wav';self.wav(bg)
  cue=dict(index=1,start=0,end=1,renderedStart=0,renderedEnd=1,renderedSeconds=1)
  (folder/'timing.json').write_text(json.dumps([cue]))
  (folder/'final-speech-check.json').write_text(json.dumps(dict(rows=[dict(index=1,expected='This is clearly wrong.',similarity=.1,languageMismatch=True)])))
  target=dict(folder=folder,report=dict(duration=1),output=self.root/'base.mp4',id='test',engine='cosyvoice3',language='en')
  seen=[]
  def run(args):
   seen.append(args)
   self.assertNotIn(bg,args,'Full source already contains the background')
   if str(args[-1]).endswith('fallback-base-decoded.wav'):
    with wave.open(str(args[-1]),'wb') as f:f.setparams((2,2,24000,0,'NONE','not compressed'));f.writeframes(array.array('h',[1000,1000]*24000).tobytes())
   if str(args[-1]).endswith('with-fallback.partial.mp4'):Path(args[-1]).write_bytes(b'fake verified mux')
   return array.array('h',[0 if stem in args else 1000]*24000).tobytes()
  rows=audio_fallback.repair(dict(dialoguePath=str(stem),backgroundPath=str(bg),video='video',ffmpeg='ffmpeg'),self.root,[target],run,lambda *a:None)
  self.assertEqual(rows,[]);self.assertEqual(target['report']['unresolvedFallbackIndices'],[1]);self.assertFalse(seen)
 def test_fallback_tool_failure_keeps_original_tracks_and_continues(self):
  import audio_fallback
  tracks=[];messages=[]
  for name in ('a','b'):
   folder=self.root/name;folder.mkdir();(folder/'timing.json').write_text(json.dumps([dict(index=1,start=0,end=1,renderedSeconds=0,skipped=True)]))
   tracks.append(dict(folder=folder,report=dict(duration=1),output=folder/'original.mp4',id=name,engine=name,language='en'))
  before=[t['output'] for t in tracks]
  def fail(args):raise RuntimeError('tool unavailable')
  rows=audio_fallback.repair(dict(video='video',ffmpeg='ffmpeg'),self.root,tracks,fail,lambda *a:messages.append(a))
  self.assertEqual(rows,[]);self.assertEqual([t['output'] for t in tracks],before)
  self.assertEqual(len(messages),2);self.assertTrue(all(t['report']['unresolvedFallbackIndices']==[1] for t in tracks));self.assertFalse(any((t['folder']/'fallback-error.json').exists() for t in tracks))
 def test_track_wide_wrong_language_does_not_pass_similar_written_characters(self):
  from audio_fallback import track_language_failure
  wrong=dict(expected='呢度全部應該講廣東話',heard='呢度全部應該講廣東話',similarity=1,detectedLanguage='chinese',languageMismatch=True)
  good=dict(wrong,detectedLanguage='cantonese',languageMismatch=False)
  self.assertTrue(track_language_failure([wrong]*5))
  self.assertFalse(track_language_failure([wrong]*3))
  self.assertFalse(track_language_failure([wrong]*3+[good]*2))
  self.assertFalse(track_language_failure([dict(wrong,detectedLanguage='none')]*5))
