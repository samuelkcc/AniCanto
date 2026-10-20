"""Real common UI boundary: imports, frozen jobs, edit versions and ownership.

No model inference is mocked as a successful conversion. Native hardware
acceptance remains separate from the desktop/data contract.
"""
import copy,hashlib,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'studio'),str(ROOT/'windows'),str(ROOT/'Resources')]
from backend import Studio
from desktop_state import write,read,defaults

class SharedStudioTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'SamCantoSync';self.root.mkdir()
        self.video=self.root/'日本語 episode.mp4';self.video.write_bytes(b'fixture source')
        self.helper=self.root/'native-helper';self.helper.write_text('fixture executable')
        self.app=Studio(self.root,ROOT/'Resources',platform='darwin',helper=self.helper)
        from use_terms import document
        self.app.dispatch('accept-use-terms',dict(accepted=True,sha256=document()['sha256'],language='en'))
    def tearDown(self):self.tmp.cleanup()
    def add(self):
        return self.app.dispatch('add',dict(paths=[str(self.video)]))['selected']
    def project(self):
        ident=self.add();folder=self.root/'jobs/example';folder.mkdir(parents=True)
        cfg=dict(defaults(),video=str(self.video),duration=6,voiceProfiles=[])
        review=dict(config=cfg,cues=[dict(start=1.,end=3.,text='こんにちは',japanese='こんにちは',cantonese='你好呀。',english='Hello.',speakerId='R01')])
        write(folder/'review.json',review);row=self.app.row(ident);row.update(job=str(folder),review=str(folder/'review.json'));self.app.store.save()
        return ident,folder
    def test_new_drama_conversion_cannot_pick_retired_installed_voice(self):
        ident=self.add();write(self.root/'model-selections.json',dict(voice='drama3-small-iq3'))
        with self.assertRaisesRegex(ValueError,'retired'):self.app.dispatch('start',dict(id=ident))
        self.assertFalse(self.app.row(ident).get('request'))
    def test_existing_output_retries_only_reported_lines_unless_new_version_requested(self):
        ident,folder=self.project();output=folder/'existing.mp4';output.write_bytes(b'earlier export')
        row=self.app.row(ident);row.update(status='attention',output=str(output));self.app.store.save()
        issues=[dict(index=1,language='yue',engine='drama3',status='unresolved')]
        with patch('backend.job_snapshot',return_value=dict(issues=issues)),patch('review_retry.submission',return_value=dict(id='a'*32,settings=defaults())),patch.object(self.app,'task',return_value=dict(action='render-project')) as task,patch.object(self.app.store,'submit',side_effect=AssertionError('full conversion restarted')):
            self.assertEqual(self.app.dispatch('start',dict(id=ident)),dict(action='render-project'))
            self.assertEqual(task.call_args.args[0],'render-project')
        self.assertEqual(output.read_bytes(),b'earlier export')
        with patch('backend.job_snapshot',return_value=dict(issues=[])),self.assertRaisesRegex(ValueError,'already has an output'):
            self.app.dispatch('start',dict(id=ident))
    def test_retired_voice_not_in_new_model_choices(self):
        self.assertNotIn('drama3-small-iq3',{r['id'] for r in self.app.dispatch('model-choices',{})})
    def test_both_views_share_one_setting_and_request(self):
        ident=self.add();self.app.dispatch('configure',dict(mode='expert',settings={'ttsBackend':'gpt-sovits-v2'}))
        other=Studio(self.root,ROOT/'Resources',helper=self.helper)
        s=other.dispatch('configure',dict(mode='basic',settings={}))
        self.assertEqual(s['settings']['selectedEngines'],['gpt-sovits-v2'])
        spec=other.dispatch('start',{'id':ident});cfg=read(Path(spec['args'][-1]))
        self.assertEqual(cfg['translationSource'],'audio-and-subtitles');self.assertEqual(cfg['ttsBackend'],'gpt-sovits-v2')
        self.assertNotEqual(cfg['roleAnalysisMode'],'audiovisual')
    def test_english_welcome_defaults_and_explicit_subtitle_choice(self):
        self.app.dispatch('configure',dict(language='zh-HK',settings={}))
        state=self.app.dispatch('configure',dict(language='en',settings={}))
        self.assertEqual(state['settings']['dubLanguages'],['yue','en'])
        self.assertEqual(state['settings']['subtitleModes'],['yue','english','dual','original']);self.assertTrue(state['settings']['includeOriginal'])
        self.assertEqual(self.app.dispatch('configure',dict(settings={'subtitleModes':['yue']}))['settings']['subtitleModes'],['yue'])
    def test_basic_submit_uses_automatic_captions_and_preserves_japanese_and_background(self):
        ident=self.add()
        self.app.dispatch('configure',dict(mode='expert',settings=dict(subtitleModes=[],dubLanguages=['en'],includeOriginal=False,selectedEngines=['drama3','gpt-sovits-v2'],mixOriginal=.5,separateBackground=False)))
        self.app.dispatch('configure',dict(mode='basic',settings={}))
        cfg=read(Path(self.app.dispatch('start',dict(id=ident))['args'][-1]))
        self.assertEqual(cfg['subtitleModes'],['english','original'])
        self.assertTrue(cfg['includeOriginal']);self.assertTrue(cfg['separateBackground'])
        self.assertEqual(cfg['mixOriginal'],0);self.assertEqual(cfg['selectedEngines'],['drama3'])
        self.assertEqual(self.app.store.settings['subtitleModes'],[],'Basic projection overwrote expert preferences')
    def test_automatic_expert_defaults_follow_language_but_custom_choices_survive(self):
        self.app.dispatch('configure',dict(mode='expert',settings=dict(dubLanguages=['en'])))
        self.assertEqual(self.app.store.settings['subtitleModes'],['english','original'])
        self.app.dispatch('configure',dict(settings=dict(subtitleModes=['dual'])))
        self.app.dispatch('configure',dict(settings=dict(dubLanguages=['yue'])))
        self.assertEqual(self.app.store.settings['subtitleModes'],['dual'])
        self.app.dispatch('configure',dict(settings=dict(subtitleSelection='automatic')))
        self.assertEqual(self.app.store.settings['subtitleModes'],['yue','original'])
    def test_experimental_source_requires_specific_confirmation_and_sets_english_recognition(self):
        ident=self.add()
        result=dict(language='en',stream=1,name='English',needsConfirmation=True,supported=True,token='source-token')
        with patch('source_language.preflight',return_value=result):
            self.assertEqual(self.app.dispatch('source-language',dict(id=ident)),result)
        with self.assertRaisesRegex(ValueError,'Confirm'):self.app.dispatch('start',dict(id=ident))
        spec=self.app.dispatch('start',dict(id=ident,sourceConfirmed='source-token'))
        cfg=read(Path(spec['args'][-1]))
        self.assertEqual(cfg['sourceLanguage'],'en');self.assertEqual(cfg['dubLanguages'],['yue'])
        self.assertEqual(cfg['subtitleModes'],['yue']);self.assertEqual(cfg['sourceAudioStream'],1)
    def test_unsupported_source_cannot_start_with_a_confirmation_token(self):
        ident=self.add();self.app.row(ident)['sourcePreflight']=dict(language='fr',needsConfirmation=True,supported=False,token='token',reason='Unsupported voice reference')
        self.app.store.save()
        with self.assertRaisesRegex(ValueError,'Unsupported'):self.app.dispatch('start',dict(id=ident,sourceConfirmed='token'))
    def test_removed_model_is_not_listed_from_another_variants_shared_file(self):
        from model_ownership import mark_removed
        import model_maintenance
        base=self.root/'models/shared';base.mkdir(parents=True);(base/'encoder').write_bytes(b'common')
        rows=[dict(id=i,title=i,category='voice',engine='gpt-sovits',bytes=10,revision='pinned',files=[dict(path='encoder',size=6,sha='0'*64),dict(path=i,size=4,sha='1'*64)]) for i in ('a','b')]
        with patch.object(model_maintenance,'catalog_paths',return_value=(rows,lambda root,row:base)):
            self.assertEqual({r['id'] for r in self.app.model_inventory()},{'a','b'})
            mark_removed(self.root,rows[0]);self.assertEqual({r['id'] for r in self.app.model_inventory()},{'b'})
            mark_removed(self.root,rows[1]);self.assertEqual(self.app.model_inventory(),[])
    def test_rpc_does_not_recover_owned_running_job_each_poll(self):
        ident=self.add();self.app.dispatch('start',dict(id=ident))
        second=Studio(self.root,ROOT/'Resources',helper=self.helper)
        self.assertEqual(second.row(ident)['status'],'running')
    def test_fast_original_voice_policy_not_changed_by_visual_toggle(self):
        ident=self.add();self.app.dispatch('configure',dict(mode='expert',settings={'productionMode':'fast','visualRoleAnalysisEnabled':True}))
        spec=self.app.dispatch('start',{'id':ident});cfg=read(Path(spec['args'][-1]))
        self.assertEqual(cfg['roleAnalysisMode'],'independent');self.assertFalse(cfg['fallbackToRoleVoice']);self.assertFalse(cfg['autoValidate'])
    def test_unknown_translation_modes_do_not_reach_native_worker(self):
        with self.assertRaises(ValueError):self.app.dispatch('configure',dict(settings={'translationSource':'other'}))
        self.app.dispatch('configure',dict(settings={'translationSource':'combined'}))
        self.assertEqual(self.app.store.settings['translationSource'],'audio-and-subtitles')
    def test_audio_only_does_not_remove_selected_output_languages(self):
        self.app.dispatch('configure',dict(mode='expert',settings={'translationSource':'audio-only','subtitleModes':['yue','english']}))
        cfg=self.app.store.settings
        self.assertEqual(cfg['subtitleModes'],['yue','english']);self.assertEqual(cfg['subtitleSource'],'none')
    def test_resume_frozen_audiovisual_request_unchanged(self):
        ident=self.add();path=self.root/'requests/old.json';write(path,dict(defaults(),roleAnalysisMode='audiovisual',model='frozen',storage=str(self.root)))
        row=self.app.row(ident);row.update(status='paused',request=str(path));self.app.store.save();before=path.read_bytes()
        self.app.dispatch('configure',dict(mode='basic',settings={'roleAnalysisMode':'audio'}))
        self.app.dispatch('start',dict(id=ident));self.assertEqual(path.read_bytes(),before)
    def test_import_is_read_only_for_original_projects_and_inflight_request(self):
        # A separate existing library, before any shared studio migration.
        root=Path(self.tmp.name)/'old';root.mkdir();folder=root/'jobs/x';folder.mkdir(parents=True)
        review=dict(config=dict(video=str(self.video),duration=6),cues=[]);write(folder/'review.json',review)
        write(root/'batch-inflight.json',dict(productionMode='fast',videos=[dict(video=str(self.video))]))
        before={p:p.read_bytes() for p in (folder/'review.json',root/'batch-inflight.json')}
        self.assertEqual(len(Studio(root,helper=self.helper).store.queue),1)
        for p,data in before.items():self.assertEqual(p.read_bytes(),data)
    def test_every_retake_is_a_distinct_immutable_version(self):
        ident,folder=self.project();draft=self.app.dispatch('snapshot',dict(id=ident))['draft']
        a=self.app.dispatch('render',dict(id=ident,draft=draft,segment=draft['segments'][0]['id']))
        b=self.app.dispatch('render',dict(id=ident,draft=draft,segment=draft['segments'][0]['id']))
        first=read(read(Path(a['args'][-1]))['submission']);second=read(read(Path(b['args'][-1]))['submission'])
        self.assertNotEqual(first['id'],second['id']);self.assertEqual(first['previewLanguage'],'yue')
        self.assertEqual(read(folder/'review.json')['cues'][0]['cantonese'],'你好呀。')
    def test_stale_draft_cannot_replace_new_translation(self):
        ident,folder=self.project();draft=self.app.dispatch('snapshot',dict(id=ident))['draft']
        review=read(folder/'review.json');review['cues'][0]['cantonese']='唔同咗';write(folder/'review.json',review)
        with self.assertRaisesRegex(ValueError,'changed'):self.app.dispatch('save-draft',dict(id=ident,draft=draft))
    def test_stale_draft_is_archived_once_across_repeated_background_refreshes(self):
        ident,folder=self.project();draft=self.app.dispatch('snapshot',dict(id=ident))['draft']
        self.app.dispatch('save-draft',dict(id=ident,draft=draft));review=read(folder/'review.json');review['cues'][0]['cantonese']='新稿';write(folder/'review.json',review)
        for _ in range(4):self.app.dispatch('snapshot',dict(id=ident))
        self.assertEqual(len(list(folder.glob('editor-draft-studio-superseded-*.json'))),1)
    def test_new_running_job_does_not_show_previous_job_voices(self):
        ident,old=self.project();new=self.root/'jobs/new-attempt';new.mkdir()
        self.app.row(ident).update(status='running',job=str(new));self.app.store.save()
        snapshot=self.app.dispatch('snapshot',dict(id=ident))
        self.assertEqual(snapshot['root'],str(new));self.assertNotIn('draft',snapshot);self.assertEqual(snapshot['review'],{})
    def test_previous_output_cannot_hide_current_failure(self):
        ident=self.add();old=self.root/'exports/old.mp4';old.parent.mkdir(exist_ok=True);old.write_bytes(b'old output')
        self.app.row(ident)['output']=str(old);self.app.dispatch('start',dict(id=ident,freshVersion=True))
        self.app.dispatch('finish',dict(id=ident,code=1,stderr='generation failed'))
        row=self.app.row(ident);self.assertEqual(row['status'],'attention');self.assertIn('generation failed',row['lastError']['message']);self.assertTrue(old.is_file())
    def test_basic_visual_option_cannot_enter_new_submission(self):
        ident=self.add();self.app.dispatch('configure',dict(mode='expert',settings={'visualRoleAnalysisEnabled':True}))
        self.assertEqual(self.app.store.settings['roleAnalysisMode'],'audiovisual')
        self.app.dispatch('configure',dict(mode='basic',settings={}))
        spec=self.app.dispatch('start',dict(id=ident));self.assertEqual(read(Path(spec['args'][-1]))['roleAnalysisMode'],'independent')
    def test_expert_multi_engine_request_and_basic_submission_are_explicit(self):
        ident=self.add();engines=['drama3','gpt-sovits-v2','voxcpm2']
        self.app.dispatch('configure',dict(mode='expert',settings=dict(selectedEngines=engines,dubLanguages=['yue','en'])))
        spec=self.app.dispatch('start',dict(id=ident));cfg=read(Path(spec['args'][-1]))
        self.assertEqual(cfg['selectedEngines'],engines)
        from multitrack import selected
        self.assertEqual(selected(cfg),engines);self.assertEqual(cfg['defaultAudioEngine'],'drama3')
        self.app.row(ident)['status']='complete'
        self.app.dispatch('configure',dict(mode='basic',settings={}))
        basic=self.app.dispatch('start',dict(id=ident));self.assertEqual(read(Path(basic['args'][-1]))['selectedEngines'],['drama3'])
        self.assertEqual(self.app.store.settings['selectedEngines'],engines)
    def test_invalid_engine_list_cannot_be_persisted(self):
        before=copy.deepcopy(self.app.store.settings)
        for engines in ([],['other'],['cosyvoice3'],'drama3',[{}]):
            with self.assertRaises(ValueError):self.app.dispatch('configure',dict(settings=dict(selectedEngines=engines)))
            self.assertEqual(self.app.store.settings,before)
    def test_single_model_repair_is_owned_task_without_changing_selection(self):
        import model_maintenance
        row=dict(id='test',files=[dict(path='weights',size=4,sha='a'*64)],legacy='models/test',title='Test')
        before=copy.deepcopy(self.app.store.settings)
        with patch.object(model_maintenance,'catalog_paths',return_value=([row],lambda root,r:root/r['legacy'])):
            spec=self.app.dispatch('maintain-model',dict(id='test',mode='repair'))
            self.assertEqual(spec['action'],'model-maintenance');self.assertIn('--id',spec['args']);self.assertIn('test',spec['args'])
            self.assertEqual(self.app.store.settings,before)
            ident=self.add();self.app.row(ident)['status']='running'
            with self.assertRaisesRegex(ValueError,'Pause'):self.app.dispatch('maintain-model',dict(id='test',mode='repair'))
        with self.assertRaises(ValueError):self.app.dispatch('maintain-model',dict(id='test',mode='delete'))
    def test_model_inventory_uses_platform_folder_and_lists_missing_files(self):
        import model_maintenance
        row=dict(id='test-native',title='Native',category='voice',engine='drama3',bytes=8,files=[dict(path='one',size=4,sha=hashlib.sha256(b'data').hexdigest()),dict(path='two',size=4,sha=hashlib.sha256(b'next').hexdigest())])
        base=self.root/'models/variants/test-native';base.mkdir(parents=True);(base/'one').write_bytes(b'data')
        self.app.platform='win32'
        with patch.object(model_maintenance,'catalog_paths',return_value=([row],lambda root,r:base)) as source:
            result=self.app.dispatch('models',{})
        source.assert_called_with('win32');self.assertEqual(len(result),1);self.assertFalse(result[0]['installed'])
        self.assertEqual(result[0]['missingBytes'],4);self.assertEqual(result[0]['missingFiles'][0]['path'],'two')
    def test_mac_about_keeps_bundled_and_downloaded_runtime_notices(self):
        bundled=self.root/'bundle';bundled.mkdir()
        write(bundled/'license-inventory.json',[dict(name='Bundled library',version='1',license='MIT',notices=[dict(text='Bundled notice')])])
        write(self.root/'runtime-license-inventory.json',[dict(name='Downloaded library',version='2',license='Apache-2.0',notices=[dict(text='Runtime notice')])])
        self.app.shared=bundled
        rows=self.app.dispatch('licenses',{})
        self.assertEqual({r['name'] for r in rows},{'Bundled library','Downloaded library'})
        self.assertEqual(rows[-1]['text'],'Runtime notice')
    def test_debug_export_includes_raw_evidence_not_only_terminal_view(self):
        ident,job=self.project();attempt=self.root/'attempts'/ident/'one';attempt.mkdir(parents=True)
        (attempt/'process.log').write_text('stdout\nTraceback: WinError 5 Access is denied\n')
        write(attempt/'attempt.json',dict(status='failed',exitCode=1))
        (self.root/'mlx-text.log').write_text('MLX model loaded')
        (job/'drama3-request.log').write_text('model diagnostic')
        self.app.row(ident).update(attempt=dict(path=str(attempt)),lastError=dict(message='Access is denied'))
        self.app.store.settings['apiKey']='do-not-export'
        report=self.app.dispatch('export-logs',{})
        for text in ('WinError 5','MLX model loaded','model diagnostic','exitCode','Access is denied'):self.assertIn(text,report)
        self.assertNotIn('do-not-export',report)
        sources=self.app.dispatch('log-sources',{});self.assertEqual(len(sources),9)
        self.assertTrue(any(r['id']=='@conversion' for r in sources))
        self.assertIn('MLX model loaded',self.app.dispatch('logs',dict(source='mlx-text.log')))
        with self.assertRaises(ValueError):self.app.dispatch('logs',dict(source='../private-file'))
        outside=Path(self.tmp.name)/'private.log';outside.write_text('never export outside data')
        (job/'outside.log').symlink_to(outside)
        self.assertNotIn('never export outside data',self.app.dispatch('export-logs',{}))
    def test_remove_completed_project_cleans_work_and_keeps_source_exports_and_models(self):
        ident,folder=self.project();row=self.app.row(ident)
        external=self.root/'finished.mp4';external.write_bytes(b'export outside project')
        (folder/'completed.mp4').write_bytes(b'export inside project')
        (folder/'working.wav').write_bytes(b'temporary audio')
        model=self.root/'models/weights';model.parent.mkdir();model.write_bytes(b'model')
        row.update(status='complete',output=str(external));self.app.store.save()
        result=self.app.dispatch('remove',dict(id=ident))
        self.assertEqual(result['state']['queue'],[]);self.assertIsNone(result['state']['selected'])
        self.assertFalse(folder.exists());self.assertEqual(self.video.read_bytes(),b'fixture source')
        self.assertEqual(external.read_bytes(),b'export outside project');self.assertEqual(model.read_bytes(),b'model')
        self.assertEqual(result['preservedExports'],[]) # external final exists; do not duplicate intermediate movies
        self.assertEqual(Studio(self.root,ROOT/'Resources',helper=self.helper).state()['queue'],[])
    def test_remove_unselected_and_running_project_behaviour(self):
        first=self.add();second=self.root/'second.mp4';second.write_bytes(b'second source')
        self.app.dispatch('add',dict(paths=[str(second)]));ident=self.app.store.queue[-1]['id']
        self.app.row(ident)['status']='running';self.app.store.save()
        with self.assertRaisesRegex(ValueError,'Pause'):self.app.dispatch('remove',dict(id=ident))
        self.app.row(ident)['status']='waiting';self.app.store.save()
        result=self.app.dispatch('remove',dict(id=ident))
        self.assertEqual(result['state']['selected'],first);self.assertTrue(second.is_file())

if __name__=='__main__':unittest.main()

class DiagnosticParityTests(unittest.TestCase):
    def test_windows_native_ollama_is_discovered_with_same_categories_as_mac(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);windows=Studio(root,ROOT/'Resources',platform='win32');mac=Studio(root,ROOT/'Resources',platform='darwin')
            path=root/'logs/native-ollama.log';path.parent.mkdir(exist_ok=True);path.write_text('CUDA model loaded on GPU 0\n')
            ws=windows.log_sources();ms=mac.log_sources()
            self.assertEqual([r['title'] for r in ws],[r['title'] for r in ms])
            ollama=next(r for r in ws if r['title']=='Ollama translation');self.assertTrue(ollama['available'])
            self.assertIn('CUDA model loaded',windows.dispatch('logs',dict(source=ollama['id'])))
            self.assertIn('CUDA model loaded',windows.debug_report())
            self.assertEqual(windows.dispatch('logs',dict(source='mlx-text.log')),'')
    def test_runtime_notice_uses_its_application_support_root_and_blocks_escape(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'data';root.mkdir();bundle=Path(d)/'bundle';bundle.mkdir();notice=root/'runtime/license.txt';notice.parent.mkdir();notice.write_text('ACTUAL DOWNLOADED MIT NOTICE')
            outside=Path(d)/'private.txt';outside.write_text('NOT A NOTICE');(root/'runtime/private').symlink_to(outside)
            write(bundle/'license-inventory.json',[])
            write(root/'runtime-license-inventory.json',[dict(name='Runtime example',version='1',license='MIT',fileRoot='applicationSupport',files=['runtime/license.txt','runtime/private','../private.txt'])])
            rows=Studio(root,bundle,platform='darwin').dispatch('licenses',{})
            self.assertEqual(rows[0]['text'],'ACTUAL DOWNLOADED MIT NOTICE')
