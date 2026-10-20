import array,copy,json,sys,tempfile,unittest,wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
import numpy as np
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import dialogue,dialogue_units,source_evidence,hybrid_script,workflow_policy,quality,worker,visual_speakers,dubbing_runner,audio_fallback,dubbing

class AutomaticWorkflow(unittest.TestCase):
 def test_actual_reported_duplicate_prefix_and_grammatical_fragments(self):
  # The times/text are the recorded E02/E03 failure evidence; no user project is opened.
  cases=[([dict(start=706.52,end=706.84,japanese='ま',speakerId='a',asrConfidence=.1),dict(start=706.84,end=709.44,japanese='ま、イドラは可愛いってより美人系だもんな',speakerId='a',asrConfidence=.8)],dict(id='caption_1',start=706.79,end=710,text='对啊，伊德拉这种威严系的美人，跟可爱确实搭不上边。')),
   ([dict(start=1012.1,end=1012.54,japanese='でも',speakerId='a'),dict(start=1012.54,end=1014.1,japanese='でも絆はともかく',speakerId='a'),dict(start=1014.32,end=1016.56,japanese='これじゃ領主のことも聞けやしない',speakerId='a')],dict(id='caption_2',start=1012.64,end=1017.14,text='别说羁绊了，我们连问问领主的事都没机会呢。'))]
  for cues,caption in cases:
   rows,changes=dialogue_units.consolidate(cues,[caption]);self.assertEqual(len(rows),1);self.assertEqual((rows[0]['start'],rows[0]['end']),(cues[0]['start'],cues[-1]['end']));self.assertEqual(rows[0]['japanese'].count('ま、' if cues[0]['japanese']=='ま' else 'でも'),1);self.assertTrue(changes)
  self.assertEqual(rows[0]['subtitleHint'],cases[1][1]['text'])
 def test_continuations_never_join_different_or_simultaneous_roles(self):
  cues=[dict(start=0,end=.3,japanese='ま',speakerId='a'),dict(start=.3,end=2,japanese='ま、そうだ',speakerId='b')]
  self.assertEqual(len(dialogue_units.consolidate(cues,[])[0]),2)
  cues[1].update(start=.1,speakerId='a');self.assertEqual(len(dialogue_units.consolidate(cues,[])[0]),2)
 def test_caption_rescues_missing_recognition_only_with_speech(self):
  cap=dict(start=2,end=5,text='快啲走啊！');spans=[dict(start=2.7,end=3.9)]
  result=dialogue.rescue_caption_speech([], [cap],spans,10);self.assertEqual(len(result),1);self.assertGreater(result[0]['start'],cap['start']);self.assertLess(result[0]['end'],cap['end']);self.assertTrue(result[0]['captionSpeechRescue'])
  self.assertEqual(dialogue.rescue_caption_speech([], [cap],[],10),[])
  self.assertEqual(dialogue.rescue_caption_speech([], [dict(cap,text='演唱：某某')],spans,10),[])
  self.assertEqual(len(dialogue.rescue_caption_speech(result,[cap],spans,10)),1)
 def test_shared_caption_reaction_keeps_own_japanese_instead_of_repeating_full_clause(self):
  caption=dict(id='caption_1',start=0,end=4,text='佢係威嚴嘅美人。')
  source=[dict(id='1',start=0,end=3,japanese='美人だ',caption=caption['text'],caption_records=[caption]),dict(id='2',start=3,end=4,japanese='いやー',caption=caption['text'],caption_records=[caption])]
  allocation={k:dict(content=caption['text'],caption_ids=['caption_1'],uncertain=False) for k in ['1','2']}
  source_evidence.anchor_allocation(allocation,source,['1','2']);self.assertEqual(allocation['2']['content'],'いやー');self.assertFalse(source_evidence.allocation_errors(allocation,source,['1','2']))
  self.assertTrue(source_evidence.grounded_line('2',dict(evidence_id='2',quote='いやー'),source,allocation));self.assertFalse(source_evidence.grounded_line('2',dict(evidence_id='caption_1',quote=caption['text']),source,allocation))
 def test_missing_script_uses_owned_chinese_caption_after_two_model_failures(self):
  with tempfile.TemporaryDirectory() as d:
   folder=Path(d);cap=dict(id='caption_1',start=0,end=2,text='你快啲走。');context=[dict(id='1',start=0,end=2,japanese='',caption=cap['text'],caption_records=[cap])]
   w=SimpleNamespace(emit=Mock(),traditional_cantonese=worker.traditional_cantonese,atomic_json=worker.atomic_json,parse_editor_response=json.loads,ollama_chat=Mock(return_value='{}'))
   data=dict(dialogue=context,allocation={'1':dict(content=cap['text'],caption_ids=['caption_1'])});cfg=dict(model='test',port=0,continueOnError=True)
   def generate(name):return hybrid_script.complete_lines(w,cfg,folder,name,'prompt',data,{},['1'],[dict(start=0,end=2)],dict(properties={'1':{}},required=['1']))
   first=generate('script');self.assertEqual(first['1']['cantonese'],cap['text']);self.assertTrue(first['1']['captionRescue']);self.assertEqual(w.ollama_chat.call_count,2)
   second=generate('conflict');self.assertTrue(second['1']['captionRescue']);self.assertEqual(w.ollama_chat.call_count,2,'Different pass names/reopen must not reset the cue retry budget')
 def test_generation_budget_survives_resume_and_has_total_limit(self):
  with tempfile.TemporaryDirectory() as d:
   for _ in range(4):self.assertTrue(workflow_policy.reserve(d,'gpt-generation',[1,'role','approved','yue','ref'],4))
   self.assertFalse(workflow_policy.reserve(Path(d),'gpt-generation',[1,'role','approved','yue','ref'],4))
   self.assertTrue(workflow_policy.reserve(d,'gpt-generation',[1,'role','user changed text','yue','ref'],4))
 def test_gpt_retries_clean_same_role_reference_without_changing_words(self):
  model=Mock();bad=np.zeros(24000);good=.1*np.sin(np.arange(24000)*.1)
  model.run.side_effect=[iter([(24000,bad)]),iter([(24000,good)])]
  sr,audio,rows=dubbing_runner.gsv_take(model,Mock(),dict(text='出發啦！',seed=42,ref_audio_path='original.wav'),device='cpu',alternate_requests=[dict(ref_audio_path='clean-same-role.wav')])
  self.assertEqual(model.run.call_args.args[0]['ref_audio_path'],'clean-same-role.wav');self.assertEqual(model.run.call_args.args[0]['text'],'出發啦！');self.assertEqual(rows[-1]['problems'],[])
 def test_one_silent_turn_keeps_other_native_audio_and_is_marked_independently(self):
  with tempfile.TemporaryDirectory() as d:
   folder=Path(d);pcm=np.concatenate([.1*np.sin(np.arange(24000)*.1),np.zeros(24000)])
   with wave.open(str(folder/'cantonese.wav'),'wb') as wav:wav.setparams((1,2,24000,0,'NONE','not compressed'));wav.writeframes((pcm*32767).astype('<i2').tobytes())
   cues=[dict(start=i,end=i+1,cantonese='出發啦',speakerId='a') for i in range(2)];timing=[dict(index=i+1,renderedStart=i,renderedEnd=i+1) for i in range(2)]
   before=(folder/'cantonese.wav').read_bytes();rows=quality.check_voice(folder,cues,timing,True)
   self.assertFalse(rows[0].get('skipped'));self.assertTrue(rows[1]['skipped']);self.assertEqual(rows[1]['failureKind'],'no-audible-voice');self.assertEqual(before,(folder/'cantonese.wav').read_bytes())
 def test_visual_invalid_one_row_keeps_prior_identity_and_other_observations(self):
  roster=[dict(id='v1',appearance='Long red hair with a white coat and black collar')]
  valid=dict(index=1,visualId='v1',speaking=True,mouthChanged=True,continuousShot=True,multipleSpeakers=False,headVisible=True,confidence=.99)
  rows,kept,rejections=visual_speakers.validated_batch(dict(roster=[dict(id='v1',appearance='modified')],rows=[valid,dict(index=2,visualId='invented')]),[1,2],roster)
  self.assertEqual(kept,roster);self.assertEqual(rows[0],valid);self.assertTrue(rows[1]['rejected']);self.assertTrue(rejections)
  self.assertTrue(visual_speakers.valid_box([.2,.1,.5,.6]));self.assertFalse(visual_speakers.valid_box([0,0,1,1]));self.assertFalse(visual_speakers.valid_box([.6,0,.3,.4]))
 def test_mps_budget_reserves_fourth_attempt_for_cpu_with_clean_reference(self):
  with tempfile.TemporaryDirectory() as d:
   gpu=Mock();gpu.run.side_effect=lambda p:iter([(24000,np.zeros(24000))]);cpu=Mock();cpu.run.return_value=iter([(24000,.1*np.sin(np.arange(24000)*.1))])
   reserve=lambda:workflow_policy.reserve(d,'gpt-generation',['one cue'],4)
   _,audio,attempts=dubbing_runner.gsv_take(gpu,lambda:cpu,dict(text='出發…喇！',seed=42,ref_audio_path='ref.wav'),device='mps',reserve_attempt=reserve,alternate_requests=[dict(ref_audio_path='same-role.wav')])
   self.assertEqual(gpu.run.call_count,3);self.assertEqual(cpu.run.call_count,1);self.assertFalse(attempts[-1]['problems']);self.assertFalse(reserve())
 def test_automatic_overlap_flag_cannot_copy_japanese_into_dub(self):
  with tempfile.TemporaryDirectory() as d:
   cue=dict(start=0,end=1,cantonese='快啲走啊！',preserveOriginalSpeech=True,originalSpeechReason='unresolved-overlap')
   run=Mock(side_effect=AssertionError('Must not extract Japanese'))
   with patch.object(dubbing,'profile_for',side_effect=ValueError('Needs a target-language role')) as role:
    with self.assertRaisesRegex(ValueError,'target-language role'):dubbing.gsv_audio(dict(ttsBackend='gpt-sovits',continueOnError=False),Path(d),[cue],run,Mock())
   role.assert_called_once();run.assert_not_called();self.assertFalse(cue['preserveOriginalSpeech'])
 def test_corrupt_independent_take_marks_only_that_cue(self):
  with tempfile.TemporaryDirectory() as d:
   folder=Path(d);pcm=.1*np.sin(np.arange(48000)*.1)
   with wave.open(str(folder/'cantonese.wav'),'wb') as wav:wav.setparams((1,2,24000,0,'NONE','not compressed'));wav.writeframes((pcm*32767).astype('<i2').tobytes())
   bad=folder/'bad.wav';bad.write_bytes(b'corrupt')
   cues=[dict(cantonese='出發啦',speakerId='a')]*2;timing=[dict(index=1,renderedStart=0,renderedEnd=1),dict(index=2,renderedStart=1,renderedEnd=2,renderedAudio=str(bad))]
   rows=quality.check_voice(folder,cues,timing,True);self.assertFalse(rows[0].get('skipped'));self.assertEqual(rows[1]['failureKind'],'invalid-take-file');self.assertTrue(timing[1]['skipped'])
 def test_editor_export_with_missing_optional_caption_bounds_keeps_native_audio(self):
  import subprocess,math
  res=Path(__file__).parents[1]/'dist/AniCanto.app/Contents/Resources/bin'
  if not (res/'ffmpeg').exists():self.skipTest('Bundled FFmpeg required')
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);source=job/'source.mp4';audio=job/'cantonese.wav'
   def run(cmd):return subprocess.run([str(x) for x in cmd],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
   run([res/'ffmpeg','-v','error','-y','-f','lavfi','-i','color=black:s=64x64:d=1','-f','lavfi','-i','sine=frequency=440:duration=1','-shortest',source])
   with wave.open(str(audio),'wb') as wav:wav.setparams((1,2,24000,0,'NONE','not compressed'));wav.writeframes(array.array('h',[round(5000*math.sin(i*.1)) for i in range(24000)]).tobytes())
   cues=[dict(start=0,end=1,text='行くぞ',japanese='行くぞ',cantonese='出發啦！')]
   cfg=dict(storage=d,video=str(source),ffmpeg=str(res/'ffmpeg'),ffprobe=str(res/'ffprobe'),duration=1,startOffset=0,ttsBackend='cosyvoice3',_singleEngine=True,editorRender=True,scriptLocked=True,autoValidate=False,voiceProfiles=[])
   meta=json.loads(run([res/'ffprobe','-v','error','-show_streams','-show_format','-of','json',source]))
   worker.atomic_json(job/'cues.json',cues);worker.atomic_json(job/'review.json',dict(config=cfg,cues=cues,meta=meta));worker.atomic_json(job/'timing.json',[dict(index=1,start=0,end=1,renderedStart=0,renderedEnd=1,renderedSeconds=1)])
   with patch.object(worker,'synthesize',return_value=(audio,[])),patch.object(worker,'emit'):worker.render_review(dict(review=str(job/'review.json')))
   report=json.loads((job/'report.json').read_text());validation=json.loads((job/'validation.json').read_text());self.assertEqual(validation['structuralStatus'],'passed');self.assertEqual(validation['fullDecode'],'passed');self.assertFalse(report.get('generationFailed'));self.assertTrue(Path(report['output']).is_file())
 def test_verified_character_box_crops_individual_card_with_bundled_media_tool(self):
  import subprocess
  res=Path(__file__).parents[1]/'dist/AniCanto.app/Contents/Resources/bin'
  if not (res/'ffmpeg').exists():self.skipTest('Bundled FFmpeg required')
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);source=job/'source.mp4'
   subprocess.run([str(res/'ffmpeg'),'-v','error','-y','-f','lavfi','-i','testsrc2=s=576x324:d=1',str(source)],check=True)
   profiles=[dict(id='role-a')];cues=[dict(start=0,end=1,speakerId='role-a')]
   saved=dict(roster=[dict(id='v1',appearance='red jacket with black hair')],rows=[dict(index=0,visualId='v1',speaking=True,mouthChanged=True,continuousShot=True,multipleSpeakers=False,headVisible=True,confidence=.99,characterBox=[.2,.1,.5,.6])])
   visual_speakers.attach_avatars(dict(video=str(source),ffmpeg=str(res/'ffmpeg')),job,cues,profiles,saved)
   info=json.loads(subprocess.check_output([str(res/'ffprobe'),'-v','error','-show_streams','-of','json',profiles[0]['avatar']]))['streams'][0]
   self.assertEqual((info['width'],info['height']),(346,324));self.assertEqual(profiles[0]['visualId'],'v1')
 def test_no_repair_permission_never_requests_donor_or_japanese(self):
  with tempfile.TemporaryDirectory() as d:
   folder=Path(d);(folder/'timing.json').write_text(json.dumps([dict(index=1,start=0,end=1,skipped=True,speakerId='a')]))
   target=dict(engine='gpt-sovits',language='yue',id='gpt-sovits',folder=folder,output=folder/'native.mp4',report=dict(duration=1))
   with patch.object(audio_fallback,'choose',side_effect=AssertionError('unapproved donor')):
    result=audio_fallback.repair(dict(selectedEngines=['gpt-sovits'],video='source',ffmpeg='ffmpeg'),folder,[target],Mock(side_effect=AssertionError('no Japanese source extraction')),Mock())
   self.assertEqual(result,[]);self.assertEqual(target['report']['unresolvedFallbackIndices'],[1]);self.assertEqual(target['report']['channelSummary']['japaneseFallback'],0)

if __name__=='__main__':unittest.main()
