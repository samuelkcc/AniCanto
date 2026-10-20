import array,json,sys,tempfile,unittest,wave
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import project_store,dubbing,quality,worker,qwen_reference

class ProjectStoreTests(unittest.TestCase):
 def test_engine_language_reference_routes_independently(self):
  with tempfile.TemporaryDirectory() as tmp:
   source=Path(tmp)/'original.wav';own=Path(tmp)/'qwen-yue.wav'
   source.write_bytes(b'original');own.write_bytes(b'own')
   profile=dict(id='role',name='role',reference=str(source),promptText='日本語',language='ja',engineReferences={'qwen-tts:yue':dict(reference=str(own),promptText='你好',enabled=True)})
   cfg=dict(voiceProfiles=[profile],defaultSpeaker='role',ttsBackend='qwen-tts',targetLanguage='yue')
   chosen=dubbing.profile_for({},cfg)
   self.assertEqual((chosen['reference'],chosen['language'],chosen['promptText']),(str(own),'yue','你好'))
   for engine,language in [('gpt-sovits','yue'),('cosyvoice3','yue'),('qwen-tts','en')]:
    self.assertEqual(dubbing.profile_for({},dict(cfg,ttsBackend=engine,targetLanguage=language))['reference'],str(source))
   profile['engineReferences']['qwen-tts:yue']['enabled']=False
   self.assertEqual(dubbing.profile_for({},cfg)['reference'],str(source))
   profile['engineReferences']=None
   self.assertEqual(dubbing.profile_for({},cfg)['reference'],str(source))
 def test_migration_preserves_files_and_deleted_output_stays_deleted(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp).resolve();job=root/'jobs/one';job.mkdir(parents=True)
   review=job/'review.json';payload=dict(config=dict(video='/source.mkv'),cues=[],status='complete');review.write_text(json.dumps(payload))
   movie=job/'one-AniCanto.mp4';movie.write_bytes(b'movie');(job/'report.json').write_text(json.dumps(dict(output=str(movie))))
   project_store.migrate(root);project_store.migrate(root)
   with project_store.connect(root) as db:
    self.assertEqual(db.execute('SELECT count(*) FROM projects').fetchone()[0],1)
    db.execute('DELETE FROM outputs WHERE path=?',(str(movie),));db.execute('INSERT INTO removed_outputs VALUES(?,?)',(str(movie),1))
   project_store.sync(root,review,movie)
   with project_store.connect(root) as db:self.assertEqual(db.execute('SELECT count(*) FROM outputs').fetchone()[0],0)
   self.assertEqual(json.loads(review.read_text()),payload);self.assertTrue(movie.exists())
 def test_only_failed_take_gets_explicit_gap_not_valid_cache(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);ref=root/'ref.wav'
   with wave.open(str(ref),'wb') as f:f.setparams((1,2,24000,0,'NONE','none'));f.writeframes(array.array('h',[1000]*72000).tobytes())
   cfg=dict(storage=tmp,ttsBackend='qwen-tts',qwenReferenceMode='original',independentReferences=False,voiceProfiles=[dict(id='role',name='role',reference=str(ref),promptText='日文',language='ja')],defaultSpeaker='role')
   cues=[dict(reviewIndex=i,start=i,end=i+1,text='日文',cantonese='你好',speakerId='role',_seed=i+42) for i in range(3)]
   def fail(cfg,job,request,emit,run):
    for i,item in enumerate(request['items']):
     if i==1:continue
     with wave.open(item['output'],'wb') as f:f.setparams((1,2,24000,0,'NONE','none'));f.writeframes(array.array('h',[1000]*12000).tobytes())
    raise RuntimeError('bounded TTS health failure')
   with patch('qwen_recovery.generate',side_effect=fail):paths=dubbing.gsv_audio(cfg,root,cues,Mock(),Mock())
   self.assertFalse(paths[0].name.startswith('skipped-'));self.assertTrue(paths[1].name.startswith('skipped-'));self.assertFalse(paths[2].name.startswith('skipped-'))
   issues=json.loads((root/'segment-issues.json').read_text());self.assertEqual([r['index'] for r in issues],[2])
   report=[dict(index=i+1,seconds=.5,slot=1) for i in range(3)]
   def pcm(args):return array.array('h',[1000]*12000).tobytes()
   output,warnings=dubbing.render_complete_preview(dict(cfg,duration=3,ffmpeg='ffmpeg',autoFit=False),root,cues,paths,report,pcm,Mock())
   with wave.open(str(output)) as f:samples=array.array('h');samples.frombytes(f.readframes(f.getnframes()))
   self.assertTrue(any(samples[:24000]));self.assertFalse(any(samples[24000:48000]));self.assertTrue(any(samples[48000:]))
   self.assertTrue(report[1]['skipped']);self.assertNotIn('renderedAudio',report[1]);self.assertEqual(warnings[0]['kind'],'skipped-voice')
   checks=quality.check_voice(root,cues,report);self.assertTrue(checks[1]['skipped'])
 def test_reference_path_freeze_keeps_same_raw_take_identity(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);a=root/'original.wav';b=root/'frozen.wav';a.write_bytes(b'same PCM');b.write_bytes(a.read_bytes())
   profile=dict(id='role',name='role',reference=str(a),promptText='日文',language='ja')
   cfg=dict(storage=tmp,ttsBackend='qwen-tts',qwenReferenceMode='original',independentReferences=False,voiceProfiles=[profile],defaultSpeaker='role')
   with patch.object(dubbing,'model_job'):
    before=dubbing.gsv_audio(dict(cfg,continueOnError=False),root,[dict(cantonese='你好')],Mock(),Mock())[0]
    profile['reference']=str(b)
    after=dubbing.gsv_audio(dict(cfg,continueOnError=False),root,[dict(cantonese='你好')],Mock(),Mock())[0]
   self.assertEqual(before,after)
 def test_independent_default_needs_no_cosyvoice_reference(self):
  p=dict(reference='source.wav',language='ja',promptText='原文')
  for engine in ('qwen-tts','gpt-sovits'):
   self.assertIs(qwen_reference.prepare(dict(ttsBackend=engine,targetLanguage='yue'),'/tmp',p,Mock()),p)
 def test_failed_translation_is_saved_and_can_be_corrected(self):
  cue=dict(start=0,end=1,text='日本語',cantonese='')
  with patch.object(worker,'ollama_chat',side_effect=ValueError('bad JSON')) as generate,patch.object(worker,'emit'):
   checkpoints=[];worker.translate_batch(dict(port=1,model='test'),[cue],[],lambda:checkpoints.append(dict(cue)))
  self.assertEqual(generate.call_count,2);self.assertEqual(cue['cantonese'],'');self.assertIn('翻譯失敗',cue['reviewNote']);self.assertEqual(len(checkpoints),1)

if __name__=='__main__':unittest.main()
