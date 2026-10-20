import array
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'Resources'))
import ai_result_repair as ai
import audio_fallback
import dubbing


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False))


def wav(path, seconds=0.8, rate=24000):
    import math
    pcm = array.array('h', (round(3000*math.sin(i*2*math.pi*440/rate)) for i in range(round(rate*seconds))))
    with wave.open(str(path), 'wb') as f:
        f.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
        f.writeframes(pcm.tobytes())
    return Path(path)


class ResultRepairTests(unittest.TestCase):
    def test_user_accepted_take_is_kept_but_missing_file_still_repairs(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);track=self.track(root);audio=wav(track['folder']/'accepted.wav')
            review=json.loads((track['folder']/'review.json').read_text());review['cues'][0].update(editorAudio=str(audio),userAcceptedRecording='history-id');write(track['folder']/'review.json',review)
            write(track['folder']/'timing.json',[dict(index=1,renderedSeconds=.8,renderedAudio=str(audio),text='出發啦')])
            write(track['folder']/'validation.json',dict(contentReviewIndices=[1]))
            from cantonese_review import REVISION
            write(track['folder']/'final-speech-check.json',dict(rows=[dict(index=1,cantoneseReviewPolicy=REVISION,confirmedContentFailure=True,requiresReview=True)]))
            row=ai.collect(track,[track])[0];self.assertEqual(row['allowedActions'],['keep']);self.assertEqual(row['userAcceptedRecording'],'history-id')
            self.assertFalse(ai.requires_delivery_repair(row),'An explicit listening acceptance keeps the warning without blocking final encoding')
            audio.unlink();row=ai.collect(track,[track])[0];self.assertTrue(row['missing']);self.assertIn('retry',row['allowedActions'])

    def test_decoder_cap_retries_original_conditioning_before_generic_voice_and_resumes(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);track=self.track(root,engine='drama3');worker=self.worker({})
            review=json.loads((track['folder']/'review.json').read_text());review['config'].update(voiceStyleMode='clone',voiceProfiles=[dict(id='actor')]);write(track['folder']/'review.json',review)
            write(track['folder']/'segment-issues.json',[dict(index=1,message='generation-limit')])
            seen=[]
            def retake(w,cfg,track,row,folder):
                seen.append((row['action'],row.get('cloneStyle')))
                if row.get('cloneStyle')!='complete-clauses':raise ValueError('generation-limit')
                folder.mkdir(parents=True,exist_ok=True);candidate=wav(folder/'take.wav')
                write(folder/'timing.json',[dict(index=1,renderedAudio=str(candidate))])
                return dict(engine='drama3',language='yue',folder=folder,id=track['id'],audioSHA=hashlib.sha256(candidate.read_bytes()).hexdigest())
            with patch.object(ai,'retake',side_effect=retake):
                donors,result=ai.run(worker,dict(duration=2.,fallbackToRoleVoice=True),root,[track])
                again,resumed=ai.run(worker,dict(duration=2.,fallbackToRoleVoice=True),root,[track])
            self.assertEqual(seen,[('retry',None),('retry','plain-whole'),('retry','complete-clauses')])
            self.assertEqual(len(donors),1);self.assertEqual(len(again),1);self.assertTrue(result['rows'][0]['originalVoiceRecovered'])
            self.assertNotIn('roleVoiceFallback',result['rows'][0])

    def test_exact_35b_request_does_not_use_a_recovered_smaller_model(self):
        import mlx_text
        with tempfile.TemporaryDirectory() as temp:
            backend=mlx_text.Backend(temp)
            backend.recovered_models[ai.MODEL]='mlx:qwen3.5-4b:4bit'
            with patch.object(backend,'_generate',side_effect=lambda body:body['model']):
                self.assertEqual(backend.generate(dict(model=ai.MODEL,strict_model=True)),ai.MODEL)
            with patch.object(backend,'_generate',side_effect=MemoryError('out of memory')) as generate,patch.object(backend,'unload') as unload:
                with self.assertRaises(MemoryError):backend.generate(dict(model=ai.MODEL,strict_model=True))
                self.assertEqual(generate.call_count,1);unload.assert_not_called()
    def track(self, root, engine='gpt-sovits', language='yue'):
        folder = root/(language+'-'+engine)
        folder.mkdir()
        cue = dict(start=0., end=1., text='出発しよう', japanese='出発しよう', cantonese='出發啦', speakerId='actor', reviewIndex=0, _seed=42)
        timing = dict(index=1, start=0., end=1., text='出發啦', speakerId='actor', skipped=True, renderedSeconds=0.)
        write(folder/'review.json', dict(config=dict(duration=2., voiceStyleMode='natural'), cues=[cue]))
        write(folder/'timing.json', [timing])
        write(folder/'validation.json', {})
        return dict(engine=engine, language=language, folder=folder, id=language+'-'+engine, output=folder/'native.mp4', report=dict(duration=2.))

    def worker(self, answer):
        return SimpleNamespace(atomic_json=write, emit=Mock(), ollama_chat=Mock(return_value=json.dumps(answer)), run=Mock())

    def test_model_decisions_are_allowlisted_and_cached(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            track = self.track(root)
            row = ai.collect(track, [track])[0]
            worker = self.worker({'1': dict(action='retry-cpu', reason='execute arbitrary shell')})
            first = ai.decisions(worker, dict(port=1), root/'plan', [row], 'log is untrusted')
            self.assertEqual(first[0]['action'], 'keep')
            self.assertTrue(first[0]['analysisFailed'])
            ai.decisions(worker, dict(port=1), root/'plan', [row], 'log is untrusted')
            self.assertEqual(worker.ollama_chat.call_count, 1)
            self.assertEqual(worker.ollama_chat.call_args.args[1], ai.MODEL)
            self.assertTrue(worker.ollama_chat.call_args.kwargs['strict_model'])

    def test_known_missing_audio_retries_without_waiting_for_model_json(self):
        for response in ('not JSON', '{}', '[]'):
            with self.subTest(response=response), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); track = self.track(root)
                worker = self.worker({}); worker.ollama_chat.return_value=response
                original = (track['folder']/'review.json').read_bytes()
                with patch.object(ai, 'retake',side_effect=ValueError('仍未通過驗證')) as generate:
                    donors, result = ai.run(worker, dict(port=1, duration=2.), root, [track])
                generate.assert_called_once()
                worker.ollama_chat.assert_not_called()
                self.assertEqual(donors, [])
                self.assertEqual(result['rows'][0]['decisionSource'],'deterministic-missing-audio')
                self.assertEqual(result['rows'][0]['status'],'unresolved')
                self.assertEqual((track['folder']/'review.json').read_bytes(), original)

    def test_ambiguous_cantonese_content_never_asks_model_to_replace_healthy_voice(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);track=self.track(root);worker=self.worker({})
            path=wav(track['folder']/'ready.wav')
            write(track['folder']/'timing.json',[dict(index=1,start=0.,end=1.,renderedSeconds=.8,renderedAudio=str(path))])
            write(track['folder']/'validation.json',dict(contentReviewIndices=[1]))
            with patch.object(ai,'retake') as generate:
                _,result=ai.run(worker,dict(port=1,duration=2.),root,[track])
            generate.assert_not_called();worker.ollama_chat.assert_not_called()
            self.assertEqual(result['rows'][0]['decisionSource'],'cantonese-advisory-retain-original')

    def test_known_reference_failure_never_retries_same_broken_reference(self):
        row=dict(missing=True,action='keep',allowedActions=['keep','retry','needs-reference'])
        self.assertEqual(ai.executable_missing_repair(row)['action'],'keep')
        row['allowedActions'].append('repair-reference')
        self.assertEqual(ai.executable_missing_repair(row)['action'],'repair-reference')
        row['allowedActions'].append('use-donor')
        self.assertEqual(ai.executable_missing_repair(row)['action'],'use-donor')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);track=self.track(root);track['report']['failureReason']='全部角色參考未通過前置檢查'
            evidence=ai.collect(track,[track])[0]
            self.assertIn('needs-reference',evidence['allowedActions']);self.assertIn('前置檢查',evidence['errors'][0])

    def test_absent_timing_row_and_silent_wav_are_missing_not_complete(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);track=self.track(root)
            write(track['folder']/'timing.json',[])
            self.assertTrue(ai.collect(track,[track])[0]['missing'])
            path=track['folder']/'silent.wav'
            with wave.open(str(path),'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(bytes(48000))
            write(track['folder']/'timing.json',[dict(index=1,start=0.,end=1.,renderedSeconds=1.,renderedAudio=str(path))])
            self.assertTrue(ai.collect(track,[track])[0]['missing'])

    def test_missing_script_never_borrows_a_different_approved_line(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);track=self.track(root)
            review=json.loads((track['folder']/'review.json').read_text());review['cues'][0]['cantonese']='';write(track['folder']/'review.json',review)
            with patch.object(ai,'choose') as choose:
                row=ai.collect(track,[track])[0]
            choose.assert_not_called();self.assertNotIn('use-donor',row['allowedActions']);self.assertNotIn('retry',row['allowedActions'])

    def test_verified_retake_is_resumed_without_regeneration_and_keeps_native(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); track = self.track(root)
            native = wav(track['folder']/'good.wav')
            before = {p: p.read_bytes() for p in (native, track['folder']/'review.json', track['folder']/'timing.json')}
            worker = self.worker({'1': dict(action='retry', reason='缺聲')})
            def generate(w, cfg, target, row, folder):
                folder.mkdir(parents=True)
                candidate=wav(folder/'take.wav')
                write(folder/'timing.json', [dict(index=1, renderedAudio=str(candidate))])
                return dict(engine=target['engine'], language=target['language'], folder=folder, id=target['id'], report=dict(duration=2.), audioSHA=hashlib.sha256(candidate.read_bytes()).hexdigest())
            with patch.object(ai, 'retake', side_effect=generate) as generate:
                donors, result = ai.run(worker, dict(port=1, duration=2.), root, [track])
                again, resumed = ai.run(worker, dict(port=1, duration=2.), root, [track])
                self.assertEqual(generate.call_count, 1)
            self.assertEqual(len(donors), 1); self.assertEqual(len(again), 1)
            self.assertEqual(resumed['rows'][0]['status'], 'verified')
            self.assertTrue(all(p.read_bytes()==data for p, data in before.items()))
            track['report']['audioFallbacks']=[dict(index=1, sourceEngine='gpt-sovits', sourceLanguage='yue')]
            result=ai.finish(worker, root, [track], result)
            self.assertEqual((result['repaired'],result['unresolved']), (1,0))

    def test_interrupted_attempt_does_not_repeat_and_changed_audio_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);track=self.track(root);worker=self.worker({'1':dict(action='retry',reason='缺聲')})
            with patch.object(ai, 'retake', side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):ai.run(worker, dict(port=1, duration=2.), root, [track])
            with patch.object(ai, 'retake') as generate:
                donors, result=ai.run(worker, dict(port=1,duration=2.), root, [track])
                generate.assert_not_called()
            self.assertEqual(donors,[]);self.assertEqual(result['rows'][0]['status'],'unresolved')

    def test_retake_requires_matching_asr_language_duration_and_preserves_script(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);track=self.track(root);worker=self.worker({})
            original=(track['folder']/'review.json').read_bytes()
            candidate=wav(root/'candidate.wav')
            row=dict(index=1,action='retry')
            with patch.object(dubbing,'gsv_audio',return_value=[candidate]) as generate, patch('delivery.prepare_audio',side_effect=lambda cfg,folder,paths,run:paths), patch('speechcheck.inspect',return_value=[dict(requiresReview=False,textMatches=True,languageMismatch=False,languageUnverified=False)]):
                donor=ai.retake(worker,dict(duration=2.),track,row,root/'repair')
                self.assertEqual(donor['language'],'yue')
                cue=generate.call_args.args[2][0]
                self.assertEqual(cue['cantonese'],'出發啦');self.assertEqual(cue['_seed'],43)
            self.assertEqual((track['folder']/'review.json').read_bytes(),original)
            with patch.object(dubbing,'gsv_audio',return_value=[candidate]), patch('delivery.prepare_audio',side_effect=lambda cfg,folder,paths,run:paths), patch('speechcheck.inspect',return_value=[dict(requiresReview=True,textMatches=False,languageMismatch=True)]):
                with self.assertRaisesRegex(ValueError,'目標語言'):ai.retake(worker,dict(duration=2.),track,row,root/'bad-language')
            too_long=wav(root/'long.wav',seconds=2.)
            with patch.object(dubbing,'gsv_audio',return_value=[too_long]), patch('delivery.prepare_audio',side_effect=lambda cfg,folder,paths,run:paths), patch('speechcheck.inspect') as inspect:
                with self.assertRaisesRegex(ValueError,'時段'):ai.retake(worker,dict(duration=2.),track,row,root/'too-long')
                inspect.assert_not_called()

    def test_donor_choice_rejects_other_language_and_flagged_recordings(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);target=self.track(root)
            donor=self.track(root,engine='cosyvoice3',language='en')
            native=wav(donor['folder']/'take.wav')
            timing=dict(index=1,start=0.,end=1.,text='出發啦',speakerId='actor',renderedAudio=str(native),renderedSeconds=.8)
            write(donor['folder']/'timing.json',[timing])
            self.assertIsNone(ai.collect(target,[target,donor])[0]['verifiedDonor'])
            donor['language']='yue'
            write(donor['folder']/'validation.json',dict(contentReviewIndices=[1]))
            self.assertIsNone(ai.collect(target,[target,donor])[0]['verifiedDonor'])
            write(donor['folder']/'validation.json',{})
            self.assertIsNone(ai.collect(target,[target,donor])[0]['verifiedDonor'])
            write(donor['folder']/'final-speech-check.json',dict(rows=[dict(index=1,requiresReview=False,textMatches=True,languageMismatch=False,languageUnverified=False)]))
            self.assertEqual(ai.collect(target,[target,donor])[0]['verifiedDonor'],'cosyvoice3')

    def test_real_repair_mux_adopts_ai_donor_and_preserves_native_files(self):
        import shutil
        ffmpeg=shutil.which('ffmpeg')
        if not ffmpeg:self.skipTest('FFmpeg unavailable')
        def run(args):return subprocess.run([str(x) for x in args],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);target=self.track(root)
            silent=target['folder']/'silence.wav'
            with wave.open(str(silent),'wb') as stream:stream.setparams((1,2,24000,0,'NONE','not compressed'));stream.writeframes(bytes(24000*2*2))
            run([ffmpeg,'-v','error','-y','-f','lavfi','-i','color=s=64x64:r=10:d=2','-i',silent,'-map','0:v','-map','1:a','-map','1:a','-c:v','libx264','-c:a','aac','-t','2',target['output']])
            before=target['output'].read_bytes()
            folder=root/'repair';folder.mkdir();candidate=wav(folder/'retake.wav')
            write(folder/'timing.json',[dict(index=1,start=0.,end=1.,text='出發啦',speakerId='actor',renderedStart=0.,renderedEnd=.8,renderedAudio=str(candidate),renderedSeconds=.8)])
            write(folder/'validation.json',{})
            write(folder/'final-speech-check.json',dict(rows=[dict(index=1,requiresReview=False,textMatches=True,languageMismatch=False,languageUnverified=False)]))
            target['aiRepairIndices']=[1];target['aiRepairActions']={1:'retry'}
            donor=dict(engine='gpt-sovits',language='yue',folder=folder,id=target['id'],report=dict(duration=2.))
            audio_fallback.repair(dict(aiAutoFix=True,ffmpeg=ffmpeg,selectedEngines=['gpt-sovits']),root,[target],run,Mock(),donor_tracks=[donor])
            self.assertEqual(target['report']['channelSummary']['unresolved'],[])
            self.assertEqual(target['report']['audioFallbacks'][0]['sourceEngine'],'gpt-sovits')
            self.assertEqual((target['folder']/'native.mp4').read_bytes(),before)
            raw=run([ffmpeg,'-v','error','-i',target['output'],'-map','0:a:0','-f','s16le','-'])
            self.assertGreater(max(abs(x) for x in array.array('h',raw)),100)

    def test_full_selected_bilingual_result_repairs_before_mux_and_emits_summary(self):
        import shutil
        import multitrack,worker
        ffmpeg=shutil.which('ffmpeg');ffprobe=shutil.which('ffprobe')
        if not ffmpeg or not ffprobe:self.skipTest('FFmpeg unavailable')
        def run(args):return subprocess.run([str(x) for x in args],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'source.mp4';audio=wav(root/'voice.wav',seconds=2.)
            run([ffmpeg,'-v','error','-y','-f','lavfi','-i','color=s=64x64:r=10:d=2','-i',audio,'-map','0:v','-map','1:a','-map','1:a','-c:v','libx264','-c:a','aac','-t','2',source])
            cue=dict(start=0.,end=1.,text='出発しよう',japanese='出発しよう',cantonese='出發啦',english='Go!',speakerId='actor')
            cfg=dict(storage=str(root/'storage'),video=str(source),duration=2.,ffmpeg=ffmpeg,ffprobe=ffprobe,port=1,model=ai.MODEL,selectedEngines=['gpt-sovits'],ttsBackend='gpt-sovits',dubLanguages=['yue','en'],subtitleOutput='separate',includeOriginal=True,voiceStyleMode='natural',aiAutoFix=True)
            review=root/'review.json';write(review,dict(config=cfg,cues=[cue],meta=dict(streams=[dict(codec_type='video'),dict(codec_type='audio')])))
            def native(request):
                path=Path(request['review']);child=json.loads(path.read_text());folder=path.parent;language=child['config']['targetLanguage'];missing=language=='yue'
                output=folder/'native.mp4';shutil.copyfile(source,output)
                row=dict(index=1,start=0.,end=1.,text=child['cues'][0]['cantonese'],speakerId='actor',renderedStart=0.,renderedEnd=1.,skipped=missing,renderedSeconds=0. if missing else 1.,renderedAudio=str(audio))
                write(folder/'timing.json',[row]);write(folder/'validation.json',dict(contentReviewIndices=[1] if missing else []))
                write(folder/'final-speech-check.json',dict(rows=[] if missing else [dict(index=1,textMatches=True,requiresReview=False,languageMismatch=False,languageUnverified=False)]))
                worker.save_srt(folder/'cantonese.srt',child['cues'])
                write(folder/'report.json',dict(output=str(output),duration=2.,qualityStatus='needs-review' if missing else 'automatic-checks-passed',gsvVersion='v4'))
            w=SimpleNamespace(run=run,atomic_json=write,emit=Mock(),render_review=Mock(side_effect=native),ollama_chat=Mock(return_value='{"1":{"action":"retry","reason":"缺聲，同稿重錄"}}'),parse_srt=worker.parse_srt,save_srt=worker.save_srt)
            candidate=wav(root/'retry.wav')
            with patch.object(dubbing,'gsv_audio',return_value=[candidate]) as generate,patch('speechcheck.inspect',return_value=[dict(textMatches=True,requiresReview=False,languageMismatch=False,languageUnverified=False)]):
                multitrack.render(w,dict(review=str(review)))
            self.assertEqual(generate.call_count,1)
            report=json.loads((root/'report.json').read_text())
            self.assertEqual(len(report['tracks']),2)
            self.assertEqual((report['aiAutoFix']['repaired'],report['aiAutoFix']['unresolved']),(1,0))
            meta=json.loads(run([ffprobe,'-v','error','-show_streams','-of','json',report['output']]))
            self.assertEqual(sum(s['codec_type']=='audio' for s in meta['streams']),3)
            self.assertEqual(sum(s['codec_type']=='subtitle' for s in meta['streams']),2)
            summaries=[c for c in w.emit.call_args_list if c.args[0]=='結果摘要']
            self.assertTrue(summaries[-1].kwargs['autoRepair'])
            self.assertFalse(summaries[-1].kwargs['partial'])
            self.assertIn('已修復 1 段',summaries[-1].args[1])


if __name__=='__main__':unittest.main()
