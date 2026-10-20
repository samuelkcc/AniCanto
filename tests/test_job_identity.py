import copy,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'Resources')]
import job_identity as cache
from atomic_files import write_json

class JobIdentityTests(unittest.TestCase):
    def body(self,root):
        return dict(storage=str(root),video=str(root/'source.mkv'),sourceStat=[120,900],
            fastRevision='fast-source-voice-1',normalPolicyRevision='normal-current',
            productionMode='normal',model='text-model',drama3Model='voice-model',
            subtitleHash='captions-a',speechRatePolicy='natural',targetLanguage='yue',
            themeSession='studio',interfaceMode='basic',backgroundDucking=True,
            exportFolder=str(root/'exports'),_standardProductionSettings={'roleAnalysisMode':'audio'})
    def legacy(self,root,body):
        folder=root/'jobs'/cache.digest(body)[:16];folder.mkdir(parents=True)
        write_json(folder/'cues.json',[dict(start=0,end=1,japanese='行こう',cantonese='出發啦')])
        write_json(folder/'review.json',dict(config={k:v for k,v in body.items() if k not in ('sourceStat','fastRevision')},cues=[]))
        (folder/'kept.wav').write_bytes(b'original-recording')
        return folder
    def test_theme_interface_hidden_backup_and_final_mix_changes_resume_verified_legacy_work(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);old=self.body(root);folder=self.legacy(root,old)
            original={p.name:p.read_bytes() for p in folder.iterdir()}
            new=dict(old,themeSession='mint',interfaceMode='expert',backgroundDucking=False,
                exportFolder=str(root/'new-exports'),_standardProductionSettings={'roleAnalysisMode':'independent'})
            emit=Mock();self.assertEqual(cache.resolve(root,new,emit),folder)
            self.assertTrue(emit.call_args.kwargs['resumeMatched'])
            for name,raw in original.items():self.assertEqual((folder/name).read_bytes(),raw)
            self.assertEqual(cache.resolve(root,dict(new,themeSession='ocean')),folder)
            self.assertFalse(json.loads((folder/'resume-identity.json').read_text())['qualityCertified'])
    def test_changed_source_caption_model_policy_language_or_explicit_rerun_never_reuses(self):
        changes=[('sourceStat',[121,901]),('video','another.mkv'),('subtitleHash','captions-b'),
            ('model','another-text-model'),('drama3Model','another-voice-model'),
            ('productionMode','fast'),('normalPolicyRevision','new-policy'),
            ('fastRevision','new-pipeline'),('targetLanguage','en'),('forceRetranslate',True)]
        for key,value in changes:
            with self.subTest(key=key),tempfile.TemporaryDirectory() as d:
                root=Path(d);body=self.body(root);old=self.legacy(root,body)
                self.assertNotEqual(cache.resolve(root,dict(body,**{key:value})),old)
    def test_partial_work_without_review_survives_restart_and_theme_change(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);body=self.body(root);folder=cache.resolve(root,body)
            (folder/'japanese-partial.json').write_text('partial recognition checkpoint')
            self.assertEqual(cache.resolve(root,dict(body,themeSession='mint')),folder)
            self.assertEqual((folder/'japanese-partial.json').read_text(),'partial recognition checkpoint')
    def test_review_claim_alone_cannot_adopt_a_different_content_address(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);body=self.body(root);folder=self.legacy(root,dict(body,sourceStat=[1,1]))
            self.assertNotEqual(cache.resolve(root,body),folder)
    def test_corrupt_or_mismatched_identity_cannot_overwrite_existing_work(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);body=self.body(root);folder=cache.resolve(root,body)
            saved=json.loads((folder/'resume-identity.json').read_text());saved['identity']['model']='wrong'
            write_json(folder/'resume-identity.json',saved)
            with self.assertRaises(ValueError):cache.resolve(root,body)
    def test_read_only_match_leaves_the_user_library_untouched(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);body=self.body(root);folder=self.legacy(root,body)
            before={p.name:p.read_bytes() for p in folder.iterdir()}
            self.assertEqual(cache.resolve(root,dict(body,themeSession='mint'),persist=False),folder)
            self.assertEqual({p.name:p.read_bytes() for p in folder.iterdir()},before)
    def test_relaunch_or_interface_change_skips_real_recognition_boundary(self):
        import fast_mode
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);video=root/'source.mkv';video.write_bytes(b'video')
            cfg=dict(storage=str(root),video=str(video),ffprobe='probe',ttsBackend='drama3',
                selectedEngines=['drama3'],productionMode='normal',speechRatePolicy='natural',
                model='text-model',themeSession='studio',interfaceMode='basic')
            metadata=dict(format={'duration':'10'},streams=[dict(codec_type='video')])
            w=SimpleNamespace(run=Mock(return_value=json.dumps(metadata)),emit=Mock(),
                atomic_json=write_json,processing_window=lambda duration,start,limit:(float(start),duration),
                window_subtitles=lambda cues,start,end:cues,render_review=Mock(return_value='rendered'))
            def source(cfg,language):cfg['sourceLanguage']=language
            cues=[dict(start=1,end=2,text='行こう',japanese='行こう',cantonese='出發啦')]
            with patch('studio_core.freeze'),patch('engine_policy.migrate'),patch('model_recovery.recover'),patch('opening.prepare'),\
                 patch('source_language.metadata',return_value=dict(language='ja',stream=1)),patch('source_language.apply',side_effect=source),\
                 patch('source_language.supported',return_value=True),patch('dubbing.separate',return_value=(root/'bg.wav',root/'voice.wav')),\
                 patch('translation_source.analyze_sources',return_value=copy.deepcopy(cues)) as recognize,\
                 patch('fast_mode.translate'),patch('fast_mode.prepare_references'),patch('project_store.sync'),patch('production_progress.phase') as phase:
                self.assertEqual(fast_mode.convert(w,cfg),'rendered')
                self.assertEqual(fast_mode.convert(w,dict(cfg,themeSession='mint',interfaceMode='expert')),'rendered')
                self.assertEqual(recognize.call_count,1)
                self.assertTrue(any(c.args[1]=='recognition' and c.kwargs.get('cached') for c in phase.call_args_list))
            jobs=list((root/'jobs').iterdir());self.assertEqual(len(jobs),1)
            self.assertEqual(w.render_review.call_count,2)

if __name__=='__main__':unittest.main()
