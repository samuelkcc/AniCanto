import array,copy,json,math,shutil,subprocess,sys,tempfile,unittest,wave
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import fast_mode,worker,dubbing,quality

HERE=Path(__file__).parents[1]
FF=shutil.which('ffmpeg') or str(HERE/'dist/AniCanto.app/Contents/Resources/bin/ffmpeg')
PROBE=shutil.which('ffprobe') or str(HERE/'dist/AniCanto.app/Contents/Resources/bin/ffprobe')

class FastModeTests(unittest.TestCase):
    def test_policy_is_explicit_and_restores_standard(self):
        normal=dict(aiAutoFix=True,roleAnalysisMode='audiovisual',autoValidate=True,requireCompleteDubbing=True)
        self.assertEqual(fast_mode.configure(copy.deepcopy(normal)),normal)
        cfg=dict(normal,productionMode='fast');fast_mode.configure(cfg)
        self.assertFalse(cfg['aiAutoFix']);self.assertFalse(cfg['requireCompleteDubbing'])
        self.assertEqual(cfg['roleAnalysisMode'],'independent')
        fast_mode.configure(cfg)
        cfg['productionMode']='standard';fast_mode.configure(cfg)
        self.assertEqual(cfg,dict(normal,productionMode='standard'))

    def test_translation_is_one_pass_per_language_and_missing_is_not_retried(self):
        w=Mock();w.ollama_chat.side_effect=['{"0":"Let us go."}','{"0":"出發啦。"}'];w.traditional_cantonese.side_effect=lambda c,t:t
        cues=[dict(start=0,end=2,japanese='行こう',text='行こう',subtitleHint='出發'),dict(start=2,end=3,text='はい')]
        with tempfile.TemporaryDirectory() as folder:
            fast_mode.translate(w,dict(model='qwen',port=1,dubLanguages=['yue','en']),Path(folder),cues)
        self.assertEqual(w.ollama_chat.call_count,2)
        self.assertEqual(cues[0]['english'],'Let us go.')
        self.assertEqual(cues[0]['cantonese'],'出發啦。')
        self.assertEqual(cues[1]['cantonese'],'')
        self.assertIn('missing-cantonese',cues[1]['fastDefects'])

    def test_gpt_fast_is_one_inference_without_health_rejection_or_cpu_retry(self):
        import numpy as np,dubbing_runner
        model=Mock();model.run.return_value=iter([(24000,np.zeros(2400,dtype=np.float32))])
        cpu=Mock(side_effect=AssertionError('CPU quality retry'))
        with patch('dubbing_runner.gsv_level',side_effect=AssertionError('Quality audit')):
            sr,audio,attempts=dubbing_runner.gsv_take(model,cpu,dict(text='試音',seed=42),device='mps',fast=True)
        self.assertEqual(model.run.call_count,1);cpu.assert_not_called()
        self.assertEqual(attempts[-1]['problems'],[])
        self.assertFalse(attempts[-1]['qualityChecked'])
        self.assertTrue(fast_mode.basic_problems([float('nan')],sr))

    def test_gpt_fast_failure_is_recorded_without_retry(self):
        import dubbing_runner
        model=Mock();model.run.side_effect=RuntimeError('inference failed')
        cpu=Mock(side_effect=AssertionError('CPU retry'))
        sr,audio,attempts=dubbing_runner.gsv_take(model,cpu,dict(text='試音',seed=42),fast=True)
        self.assertEqual(model.run.call_count,1);cpu.assert_not_called()
        self.assertEqual(audio,[])
        self.assertEqual(attempts[-1]['problems'],['generation-exception'])
        self.assertFalse(attempts[-1]['qualityChecked'])

    def test_model_job_does_not_enter_quality_or_runtime_repair(self):
        with patch('dubbing._model_job',return_value='done') as execute,patch('runtime_recovery.run',side_effect=AssertionError('recovery')):
            self.assertEqual(dubbing.model_job(dict(productionMode='fast'),'tts',dict(items=[]),Mock()),'done')
            self.assertEqual(execute.call_args.args[2]['productionMode'],'fast')

    def test_fast_mux_with_failed_line_outputs_and_never_calls_review(self):
        self.check_one_pass_mux('fast')

    def test_normal_mux_repairs_one_missing_line_without_entering_full_QA(self):
        self.check_one_pass_mux('normal')

    def test_normal_missing_script_is_rescued_before_tts_and_final_movie_is_complete(self):
        self.check_one_pass_mux('normal',missing_script=True)

    def test_exhausted_normal_repair_exports_labelled_preview_with_original_audio(self):
        self.check_one_pass_mux('normal',preview=True)

    def check_one_pass_mux(self, mode,missing_script=False,preview=False):
        from contextlib import ExitStack
        with tempfile.TemporaryDirectory() as folder,ExitStack() as stack:
            job=Path(folder);video=job/'source.mp4'
            worker.run([FF,'-v','error','-y','-f','lavfi','-i','color=c=blue:s=160x90:r=12:d=3','-f','lavfi','-i','sine=frequency=200:duration=3','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest',video])
            bg=job/'background.wav';voice=job/'dialogue.wav'
            for path in (bg,voice):worker.run([FF,'-v','error','-y','-i',video,'-vn','-ar','24000','-ac','2','-c:a','pcm_s16le',path])
            cfg=dict(productionMode=mode,video=str(video),storage=str(job/'storage'),ffmpeg=FF,ffprobe=PROBE,duration=3,ttsBackend='cosyvoice3',selectedEngines=['cosyvoice3'],dubLanguages=['yue','en'],includeOriginal=True,subtitleModes=['yue','english'],interfaceMode='simple',model='qwen',port=1,backgroundPath=str(bg),dialoguePath=str(voice),exportFolder=str(job/'export'))
            if preview:cfg.update(speechRatePolicy='natural',automaticRecovery=False)
            (job/'export').mkdir();(job/'storage').mkdir()
            cues=[dict(start=0,end=.7,speechStart=.1,speechEnd=.7,text='行こう',japanese='行こう',cantonese='出發啦。',english='Let us go.',enabled=True),dict(start=.8,end=1.5,text='はい',japanese='はい',cantonese='好呀。',english='Yes.',enabled=True),dict(start=1.6,end=2.6,text='待って',japanese='待って',cantonese='等陣。',english='Wait.',enabled=True)]
            if missing_script:cues[1]['cantonese']=''
            original=copy.deepcopy(cues)
            worker.atomic_json(job/'cues.json',cues)
            meta=json.loads(worker.run([PROBE,'-v','error','-show_streams','-show_format','-of','json',video]))
            worker.atomic_json(job/'review.json',dict(config=cfg,meta=meta,cues=cues,status='approved'))
            def audio(cfg,folder,cues,run,emit):
                paths=[]
                for i,c in enumerate(cues):
                    p=Path(folder)/('skipped-line.wav' if i==1 else f'take-{i}.wav')
                    samples=array.array('h',(round(6000*math.sin(n*2*math.pi*330/24000)) for n in range(48000)))
                    with wave.open(str(p),'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(samples.tobytes())
                    paths.append(p)
                return paths
            stack.enter_context(patch('dubbing.gsv_audio',side_effect=audio))
            stack.enter_context(patch('dubbing.separate',return_value=(bg,voice)))
            stack.enter_context(patch('fast_mode.prepare_references'))
            stack.enter_context(patch('model_recovery.recover'))
            if missing_script:
                stack.enter_context(patch('normal_mode.glossary',return_value=[]))
                rescued=stack.enter_context(patch.object(worker,'ollama_chat',return_value='所需 JSON'))
                rescued.return_value=json.dumps({'text':'好呀。'})
            emit=stack.enter_context(patch.object(worker,'emit'))
            for name in ['asr_verify.recheck','script_preflight.repair','script_gap_recovery.recover','caption_span_recovery.recover','caption_timing_alignment.audit','dub_languages.english_script','mixed_speech_check.inspect_tracks','mixed_speech_check.recover_background','audio_fallback.repair','ai_result_repair.run','quality.check_voice','quality.inspect_rendered_voice','delivery.synthesize']:
                stack.enter_context(patch(name,side_effect=AssertionError('Fast called '+name)))
            worker.render_review(dict(review=str(job/'review.json')))
            report=json.loads((job/'report.json').read_text())
            output=Path(report['exportedOutput']);self.assertTrue(output.is_file())
            self.assertEqual(report['qualityStatus'],'incomplete-preview' if preview else 'targeted-checks-only' if mode=='normal' else 'not-checked-fast-mode')
            self.assertEqual(json.loads((job/'review.json').read_text())['status'],'partial' if mode=='fast' or preview else 'complete')
            result=json.loads(worker.run([PROBE,'-v','error','-show_streams','-of','json',output]))
            self.assertEqual(len([s for s in result['streams'] if s['codec_type']=='audio']),3)
            self.assertEqual(len([s for s in result['streams'] if s['codec_type']=='subtitle']),2)
            for track in report['tracks']:
                rows=json.loads((Path(track['report']).parent/'timing.json').read_text())
                self.assertEqual(rows[1]['skipped'],mode=='fast' or preview)
                if preview:continue
                for row,cue in zip(rows,original):
                    self.assertLessEqual(row['renderedEnd'],cue.get('speechEnd',cue['end']))
                self.assertGreater(rows[0]['hardSlotCompression'],2)
            if missing_script:
                self.assertEqual(rescued.call_count,3)
                self.assertIn('好呀。',(Path(report['tracks'][0]['report']).parent/'cantonese.srt').read_text())
                self.assertEqual(len(report['normalScriptRescue']['recovered']),1)
                self.assertEqual(report['dialogueDelivery']['status'],'audio-present')
            if preview:
                self.assertTrue(str(output).endswith('-AniCanto-Preview.mp4'));self.assertEqual(report['deliveryKind'],'preview')
                self.assertTrue(report['previewDelivery']['missingDialogue']>0)
                self.assertEqual([s for s in result['streams'] if s['codec_type']=='audio'][-1]['disposition']['default'],1)
            else:self.assertIn(fast_mode.warning(cfg),(job/'result-summary.txt').read_text())
            self.assertTrue(any(args[0][0]=='完成' and args[1].get('partial') is (mode=='fast' or preview) for args in emit.call_args_list))

    def test_structural_errors_still_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                fast_mode.validation(dict(duration=1,ffprobe='probe'),Path(folder),[],'invalid',lambda x:json.dumps(dict(streams=[],format=dict(duration=1))),Mock())

if __name__=='__main__':unittest.main()
