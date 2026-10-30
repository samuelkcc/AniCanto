import copy,json,sys,tempfile,unittest,wave
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'windows'))
from desktop_state import Store,write,read,job_snapshot,editor_draft,load_draft,find_take,accept_history
from desktop_cleanup import remove
from native_worker import project_request
from native_models import missing_setup

class DesktopStateTests(unittest.TestCase):
 def test_old_editor_draft_cannot_hide_new_translation_and_timing(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);path=root/'review.json'
   old=dict(config=dict(video='same.mkv',duration=20),cues=[dict(start=1,end=2,text='日本語',cantonese='舊稿')])
   draft=editor_draft(path,old,old['config']);draft['segments'][0]['text']='用戶編輯';write(root/'editor-draft-windows.json',draft)
   self.assertEqual(load_draft(path,old,old['config'])['segments'][0]['text'],'用戶編輯')
   new=copy.deepcopy(old);new['cues'][0].update(start=4,end=5,cantonese='新翻譯')
   loaded=load_draft(path,new,new['config']);self.assertEqual(loaded['segments'][0]['text'],'新翻譯');self.assertEqual(loaded['segments'][0]['start'],4)
   backups=list(root.glob('editor-draft-superseded-*.json'));self.assertEqual(len(backups),1);self.assertEqual(read(backups[0])['segments'][0]['text'],'用戶編輯')
 def test_only_speech_probed_versions_are_deployed_and_multiversion_setup_terminates(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);marker=root/'gpt-windows-ready.json'
   write(marker,dict(modelLoadPassed=True,speechInferencePassed=True,modelVersions=['v2ProPlus','v4'],speechVersions=['v2ProPlus']))
   self.assertEqual(missing_setup(root,['gpt-sovits-v2','gpt-sovits']),['gpt-sovits'])
   write(marker,dict(modelLoadPassed=True,speechInferencePassed=True,modelVersions=['v2ProPlus','v4'],speechVersions=['v2ProPlus','v4']))
   self.assertEqual(missing_setup(root,['gpt-sovits-v2','gpt-sovits','drama3']),['drama3'])
 def test_licence_inventory_groups_same_distribution_across_runtimes(self):
  from native_licenses import inventory
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   for runtime in ('worker','gpt'):
    info=root/'runtimes'/runtime/'Lib/site-packages/example-1.dist-info';info.mkdir(parents=True)
    (info/'METADATA').write_text('Name: example\nVersion: 1\nLicense-Expression: MIT\n')
    (info/'LICENSE').write_text('The identical MIT notice')
   rows=inventory(root);self.assertEqual(len(rows),1);self.assertEqual(len(rows[0]['runtimes']),2);self.assertEqual(len(rows[0]['notices']),1)
 def test_mode_and_language_changes_do_not_rewrite_submitted_settings(self):
  with tempfile.TemporaryDirectory() as tmp:
   source=Path(tmp)/'episode.mkv';source.write_bytes(b'isolated submission fixture')
   store=Store(tmp);store.add([source]);row=store.queue[0]
   request=store.submit(row);before=request.read_bytes();row['status']='paused'
   store.mode='expert';store.settings['selectedEngines']=['cosyvoice3'];store.language_default('zh-HK')
   self.assertEqual(store.submit(row),request);self.assertEqual(request.read_bytes(),before)
   self.assertEqual(read(request)['dubLanguages'],['yue','en']);self.assertEqual(store.settings['dubLanguages'],['yue'])
   self.assertEqual(read(request)['selectedEngines'],['drama3'])
 def test_restart_changes_only_running_queue_rows_to_paused(self):
  with tempfile.TemporaryDirectory() as tmp:
   store=Store(tmp);store.add([Path(tmp)/x for x in ('one.mkv','two.mkv')]);store.queue[0]['status']='running';store.queue[1]['status']='complete';store.save()
   restored=Store(tmp);self.assertEqual([r['status'] for r in restored.queue],['paused','complete'])
 def test_child_percent_cannot_rewind_authoritative_progress(self):
  with tempfile.TemporaryDirectory() as tmp:
   store=Store(tmp);store.add([Path(tmp)/'one.mkv']);row=store.queue[0]
   store.event(row,dict(progress=.99,journey=dict(progress=.82,milestones=[])))
   store.event(row,dict(progress=.1,journey=dict(progress=.5,milestones=[])))
   self.assertEqual(row['progress'],.82);self.assertEqual(row['journey']['progress'],.82)
 def test_exit_zero_without_output_is_not_complete(self):
  with tempfile.TemporaryDirectory() as tmp:
   store=Store(tmp);store.add([Path(tmp)/'one.mkv']);row=store.queue[0];store.finish(row,0)
   self.assertEqual(row['status'],'attention')
 def test_exported_video_reaches_100_with_separate_review_status(self):
  with tempfile.TemporaryDirectory() as tmp:
   store=Store(tmp);store.add([Path(tmp)/'one.mkv']);row=store.queue[0]
   out=Path(tmp)/'output.mp4';out.write_bytes(b'fixture')
   row.update(output=str(out),partial=True,progress=.94);store.finish(row,0)
   self.assertEqual(row['status'],'attention');self.assertEqual(row['progress'],1)
 def test_old_94_percent_export_is_projected_complete_only_after_finished_run(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);output=root/'output.mp4';output.write_bytes(b'fixture')
   write(root/'production-progress.json',dict(progress=.94,complete=False,milestones=[dict(id='export',state='incomplete',seconds=65)]))
   write(root/'report.json',dict(exportedOutput=str(output),qualityStatus='needs-review'))
   write(root/'processing-time.json',dict(runs=[dict(status='finished')]))
   before=(root/'production-progress.json').read_bytes()
   restored=job_snapshot(dict(job=str(root)))['journey']
   self.assertTrue(restored['complete']);self.assertEqual(restored['progress'],1);self.assertEqual(restored['qualityStatus'],'needs-review')
   self.assertEqual((root/'production-progress.json').read_bytes(),before)
   write(root/'processing-time.json',dict(runs=[dict(status='interrupted')]))
   self.assertFalse(job_snapshot(dict(job=str(root)))['journey']['complete'])
 def test_fitted_and_versioned_takes_are_indexed_by_engine_language_and_cue(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);job=root/'jobs/a';version=job/'versions/new';version.mkdir(parents=True)
   review=dict(config=dict(voiceProfiles=[],ttsBackend='drama3'),cues=[dict(start=1,end=2,text='a'),dict(start=3,end=4,text='b')]);write(job/'review.json',review)
   wav=version/'new.wav';wav.write_bytes(b'x'*100)
   write(version/'version.json',dict(engine='gpt-sovits',language='en',segment='cue-1'))
   write(version/'timing.json',[dict(start=3,end=4,audio=str(wav))])
   data=job_snapshot(dict(review=str(job/'review.json')))
   self.assertEqual(find_take(data,1,'gpt-sovits','en')['audio'],str(wav));self.assertIsNone(find_take(data,0,'gpt-sovits','en'))
 def test_editor_projection_preserves_original_immutable_snapshot(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);package=root/'package';(package/'tools').mkdir(parents=True);(package/'tools/AniCanto-helper.exe').touch()
   for key in ('ffmpeg','ffprobe'):(root/(key+'.exe')).touch()
   write(root/'gpt-windows-ready.json',dict(modelLoadPassed=True,modelVersions=['v2ProPlus']))
   review=root/'review.json';write(review,dict(config=dict(storage=str(root),model='mlx:old',ttsBackend='drama3',selectedEngines=['drama3']),cues=[]))
   source=root/'submission.json';write(source,dict(id='abc',review=str(review),settings=dict(model='mlx:old'),previewEngine='drama3'))
   ready=dict(modelLoadPassed=True,speechInferencePassed=True,ffmpeg=str(root/'ffmpeg.exe'),ffprobe=str(root/'ffprobe.exe'),textModel='qwen3.5:9b-canto-sha',roles=dict(visual='qwen3.5:9b'),backend='nvidia')
   before=source.read_bytes();out=project_request('render-project',dict(storage=str(root),submission=str(source),selectedEngines=['drama3']),ready,root,package)
   draft=read(out['submission']);self.assertEqual(source.read_bytes(),before);self.assertNotEqual(out['submission'],str(source))
   self.assertEqual(draft['settings']['model'],ready['textModel']);self.assertEqual(draft['settings']['visualModel'],ready['textModel'])
   self.assertEqual(draft['settings']['selectedEngines'],['gpt-sovits-v2']);self.assertEqual(draft['previewEngine'],'gpt-sovits-v2')
 def test_one_pass_fitted_recording_is_playable_without_raw_audio_field(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);track=root/'tracks/drama';track.mkdir(parents=True)
   write(root/'review.json',dict(config=dict(productionMode='normal'),cues=[dict(start=1,end=2)]))
   wav=track/'fitted.wav';wav.write_bytes(b'playable fixture')
   write(track/'audio-preview.json',dict(engine='drama3',language='yue'))
   write(track/'timing.json',[dict(reviewIndex=0,start=1,end=2,renderedAudio=str(wav))])
   take=find_take(job_snapshot(dict(job=str(root))),0,'drama3','yue')
   self.assertEqual(take['audio'],str(wav));self.assertEqual(take['index'],1)
 def test_review_lists_first_and_rejected_takes_even_without_open_issue(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);track=root/'tracks/drama';track.mkdir(parents=True)
   write(root/'review.json',dict(config=dict(ttsBackend='drama3',targetLanguage='yue'),cues=[dict(start=1,end=2,cantonese='你好呀')]))
   write(track/'review.json',dict(config=dict(ttsBackend='drama3',targetLanguage='yue'),cues=[]))
   first=track/'first.wav';first.write_bytes(b'first')
   retry=track/'retry.wav';retry.write_bytes(b'retry')
   write(track/'normal-checks.json',dict(repairs=[dict(index=1,originalAudio=str(first),attempts=[dict(candidateAudio=str(retry),repaired=False)])]))
   candidates=job_snapshot(dict(job=str(root)))['recordingCandidates']
   self.assertEqual([(p['index'],p['kind'],p['path']) for p in candidates],[(1,'first',str(first.resolve())),(1,'rejected',str(retry.resolve()))])
 def test_cleanup_keeps_original_export_and_models(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);job=root/'jobs/episode';job.mkdir(parents=True);write(job/'review.json',{})
   movie=root/'original.mkv';movie.write_bytes(b'original');(root/'models').mkdir();(root/'models/weights').write_bytes(b'model')
   (job/'completed.mp4').write_bytes(b'output');(job/'completed.processing-time.json').write_text('{}');(job/'temp.wav').write_bytes(b'work')
   write(job/'report.json',dict(output=str(job/'completed.mp4')))
   paths=remove(root,dict(review=str(job/'review.json'),video=str(movie)))
   self.assertFalse(job.exists());self.assertEqual(movie.read_bytes(),b'original');self.assertTrue((root/'models/weights').exists());self.assertEqual(Path(paths[0]).read_bytes(),b'output');self.assertFalse(Path(paths[0]).with_suffix('.processing-time.json').exists())
 def test_cleanup_refuses_external_or_source_containing_job(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);external=root/'external';external.mkdir();write(external/'review.json',{})
   with self.assertRaises(ValueError):remove(root,dict(review=str(external/'review.json'),video=str(root/'original.mkv')))
   job=root/'jobs/episode';job.mkdir(parents=True);write(job/'review.json',{});(job/'source.mkv').touch()
   with self.assertRaises(ValueError):remove(root,dict(review=str(job/'review.json'),video=str(job/'source.mkv')))
 def test_decoder_fragment_cannot_be_adopted_even_with_translated_words(self):
  with tempfile.TemporaryDirectory() as tmp:
   with self.assertRaisesRegex(ValueError,'incomplete'):accept_history(tmp,dict(text='完整台詞',reason='generation-limit',generation={}), '完整台詞')

if __name__=='__main__':unittest.main()
