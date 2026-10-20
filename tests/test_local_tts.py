import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import wave
from contextlib import nullcontext
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import local_tts,engine_policy,voice_models,model_catalog,audio_format,multitrack


class LocalTTSTests(unittest.TestCase):
    def test_supported_language_pairs_match_eleven_actual_dubs(self):
        self.assertEqual(len(engine_policy.pairs(engine_policy.ACTIVE,['yue','en'])),11)
        self.assertNotIn(('en','wsyue'),engine_policy.pairs(engine_policy.ACTIVE,['yue','en']))
        with self.assertRaises(ValueError):engine_policy.pairs(['wsyue'],['en'])
        self.assertEqual(engine_policy.pairs(['voxcpm2','wsyue'],['en']),[('en','voxcpm2')])

    def test_selected_new_engines_survive_retired_engine_migration(self):
        cfg=dict(selectedEngines=['voxcpm2','wsyue','gpt-sovits-v3'],ttsBackend='gpt-sovits-v3')
        engine_policy.migrate(cfg)
        self.assertEqual(cfg['selectedEngines'],['voxcpm2','wsyue'])
        self.assertEqual(multitrack.selected(cfg),['voxcpm2','wsyue'])

    def test_models_are_pinned_complete_and_engine_selections_are_independent(self):
        rows=[r for r in voice_models.catalog() if r['engine'] in local_tts.ENGINES]
        self.assertEqual(len(rows),5)
        for row in rows:
            self.assertEqual(len(row['revision']),40)
            self.assertTrue(row['files'])
            self.assertEqual(sum(f['size'] for f in row['files']),row['bytes'])
            self.assertTrue(all(len(f['sha'])==64 and '..' not in Path(f['path']).parts for f in row['files']))
            self.assertEqual(model_catalog.choice(row['id'])['files'],row['files'])
        with self.assertRaises(ValueError):local_tts.validate(dict(voxcpmModel='wsyue-cosy2-base'),'voxcpm2')
        with self.assertRaises(ValueError):local_tts.validate(dict(targetLanguage='en'),'wsyue')
        self.assertEqual(local_tts.selection(dict(wsyueModel='wsyue-cosy2-base'),'wsyue'),'wsyue-cosy2-base')
        self.assertEqual(audio_format.delivery_rate(dict(ttsBackend='voxcpm2')),48000)
        self.assertEqual(audio_format.delivery_rate(dict(ttsBackend='wsyue')),24000)
        self.assertEqual(audio_format.delivery_rate(dict(ttsBackend='drama3')),44100)

    def test_missing_weights_never_resolve_as_ready(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):voice_models.resolve(d,'voxcpm2')
            with self.assertRaises(ValueError):voice_models.resolve(d,'wsyue')

    def test_inference_yaml_omits_training_only_modules(self):
        import yaml
        path=Path(__file__).parents[1]/'.build/qa249/upstream/Cosyvoice2-Yue.yaml'
        if not path.exists():self.skipTest('Official source config fixture unavailable')
        loader=Mock(return_value={})
        with patch.dict(sys.modules,{'hyperpyyaml':type('Module',(),{'load_hyperpyyaml':staticmethod(loader)})}):
            local_tts.inference_config(path)
        data=loader.call_args.args[0].getvalue()
        self.assertIn('Qwen2LM',data);self.assertIn('get_qwen_tokenizer',data)
        self.assertNotIn('HiFiGan',data);self.assertNotIn('dataset.processor',data)
        self.assertTrue(loader.call_args.kwargs['overrides']['qwen_pretrain_path'].endswith('CosyVoice-BlankEN'))

    def test_atomic_audio_preserves_native_rate_and_resume_does_not_generate(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'take.wav'
            cfg=dict(targetLanguage='yue',items=[dict(text='出發啦',output=str(path),profile={},reviewIndex=None)])
            raw=np.sin(np.arange(48000)*.031).astype(np.float32)*.15
            with patch.object(local_tts,'load',return_value=object()),patch.object(local_tts,'generate',return_value=(raw,48000)) as generate,patch.object(local_tts,'torch_inference',return_value=nullcontext()),patch('tts_health.problems',return_value=[]):
                local_tts.synthesize(cfg,Mock(),'voxcpm2')
                self.assertTrue(path.is_file());self.assertFalse(path.with_suffix('.partial.wav').exists())
                with wave.open(str(path)) as stream:self.assertEqual(stream.getframerate(),48000)
                original=path.read_bytes();local_tts.synthesize(cfg,Mock(),'voxcpm2')
                self.assertEqual(generate.call_count,1);self.assertEqual(path.read_bytes(),original)

    def test_failed_native_generation_never_writes_a_successful_take(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'take.wav';cfg=dict(items=[dict(text='出發啦',output=str(path),profile={},reviewIndex=None)])
            with patch.object(local_tts,'load',return_value=object()),patch.object(local_tts,'generate',return_value=(np.zeros(24000),24000)),patch.object(local_tts,'torch_inference',return_value=nullcontext()):
                with self.assertRaises(ValueError):local_tts.synthesize(cfg,Mock(),'wsyue')
            self.assertFalse(path.is_file())

    def test_unsupported_english_stops_before_loading_or_generating_wenet(self):
        with patch.object(local_tts,'load') as load:
            with self.assertRaises(ValueError):local_tts.synthesize(dict(targetLanguage='en',items=[]),Mock(),'wsyue')
            load.assert_not_called()


if __name__=='__main__':unittest.main()

class LocalTTSMuxTests(unittest.TestCase):
    def test_all_six_engines_mux_eleven_dubs_original_and_engine_subtitles(self):
        import array,math,shutil,subprocess
        from types import SimpleNamespace
        import worker
        ffmpeg=shutil.which('ffmpeg');ffprobe=shutil.which('ffprobe')
        if not ffmpeg or not ffprobe:self.skipTest('FFmpeg unavailable')
        def run(args):return subprocess.run([str(a) for a in args],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
        def write(path,value):Path(path).write_text(json.dumps(value,ensure_ascii=False))
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);audio=root/'voice.wav';source=root/'source.mp4'
            with wave.open(str(audio),'wb') as stream:
                stream.setparams((1,2,24000,0,'NONE','not compressed'))
                stream.writeframes(array.array('h',(round(3000*math.sin(i*.07)) for i in range(48000))).tobytes())
            run([ffmpeg,'-v','error','-y','-f','lavfi','-i','color=s=64x64:r=10:d=2','-i',audio,'-map','0:v','-map','1:a','-map','1:a','-c:v','libx264','-c:a','aac','-t','2',source])
            cue=dict(start=0.,end=1.,text='出発しよう',japanese='出発しよう',cantonese='出發啦',english='Go!',speakerId='actor')
            cfg=dict(storage=str(root/'storage'),video=str(source),duration=2.,ffmpeg=ffmpeg,ffprobe=ffprobe,selectedEngines=list(engine_policy.ACTIVE),ttsBackend='voxcpm2',dubLanguages=['yue','en'],subtitleOutput='separate',includeOriginal=True,voiceStyleMode='natural',aiAutoFix=True,voxcpmModel='voxcpm2-2b-bf16',wsyueModel='wsyue-cosy2-zjg')
            review=root/'review.json';write(review,dict(config=cfg,cues=[cue],meta=dict(streams=[dict(codec_type='video'),dict(codec_type='audio')])))
            def native(request):
                path=Path(request['review']);child=json.loads(path.read_text());folder=path.parent;output=folder/'native.mp4'
                shutil.copyfile(source,output)
                write(folder/'timing.json',[dict(index=1,start=0.,end=1.,text=child['cues'][0]['cantonese'],speakerId='actor',renderedStart=0.,renderedEnd=1.,renderedSeconds=1.,renderedAudio=str(audio))])
                write(folder/'validation.json',{})
                write(folder/'final-speech-check.json',dict(rows=[dict(index=1,textMatches=True,requiresReview=False,languageMismatch=False,languageUnverified=False)]))
                worker.save_srt(folder/'cantonese.srt',child['cues'])
                write(folder/'report.json',dict(output=str(output),duration=2.,qualityStatus='automatic-checks-passed'))
            w=SimpleNamespace(run=run,atomic_json=write,emit=Mock(),render_review=Mock(side_effect=native),ollama_chat=Mock(),parse_srt=worker.parse_srt,save_srt=worker.save_srt)
            multitrack.render(w,dict(review=str(review)))
            report=json.loads((root/'report.json').read_text());self.assertEqual(len(report['tracks']),11)
            pairs={(t['engine'],t['language']) for t in report['tracks']}
            self.assertIn(('drama3','yue'),pairs);self.assertIn(('drama3','en'),pairs);self.assertIn(('voxcpm2','en'),pairs);self.assertIn(('wsyue','yue'),pairs);self.assertNotIn(('wsyue','en'),pairs)
            self.assertEqual(w.render_review.call_count,11);w.ollama_chat.assert_not_called()
            meta=json.loads(run([ffprobe,'-v','error','-show_streams','-of','json',report['output']]))
            self.assertEqual(sum(s['codec_type']=='audio' for s in meta['streams']),12)
            self.assertEqual(sum(s['codec_type']=='subtitle' for s in meta['streams']),2)
            titles=[s.get('tags',{}).get('handler_name','') for s in meta['streams'] if s['codec_type']=='audio']
            self.assertTrue(any('VoxCPM2' in title for title in titles));self.assertTrue(any('WenetSpeech' in title for title in titles))
            self.assertTrue(any('Drama 3' in title for title in titles))
            self.assertEqual(report['aiAutoFix']['unresolved'],0)
