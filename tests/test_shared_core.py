"""Real Rust IPC tests. No model downloads, private media or installed-app mutation."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Resources'))
import studio_core as core
import engine_policy
import ai_result_repair as repair
import role_reanalysis
import runtime_paths

class SharedCoreTests(unittest.TestCase):
    def test_catalog_matches_compiled_binary(self):
        self.assertEqual(core.call('catalog')['catalog'],core.catalog())

    def test_order_is_shared_with_python(self):
        self.assertEqual(engine_policy.ACTIVE,('drama3','gpt-sovits-v2','gpt-sovits','cosyvoice3','voxcpm2','wsyue'))

    def test_basic_and_expert_have_identical_job_identity(self):
        cfg=dict(selectedEngines=['drama3'],ttsBackend='drama3',dubLanguages=['yue'],subtitleModes=['original','yue'],originalSubtitleStreams=[3])
        basic=core.production_plan(dict(cfg,interfaceMode='simple'))
        expert=core.production_plan(dict(cfg,interfaceMode='professional'))
        self.assertEqual(basic,expert)
        self.assertEqual(basic['dubbedTrackCount'],1)
        self.assertEqual(basic['maximumAudioTrackCount'],2)
        self.assertFalse(basic['burnSubtitles'])

    def test_all_engines_both_languages_have_eleven_dubs(self):
        plan=core.production_plan(dict(selectedEngines=list(engine_policy.ACTIVE),dubLanguages=['en','yue']))
        self.assertEqual(plan['dubbedTrackCount'],11)
        self.assertEqual(plan['maximumAudioTrackCount'],12)
        self.assertNotIn('en:wsyue',[t['id'] for t in plan['tracks']])

    def test_unselected_english_is_not_in_plan(self):
        self.assertEqual({t['language'] for t in core.production_plan(dict(ttsBackend='drama3',dubLanguages=['yue']))['tracks']},{'yue'})

    def test_invalid_selections_fail_before_work(self):
        for cfg in [dict(dubLanguages=[]),dict(selectedEngines=[]),dict(dubLanguages=['ja']),dict(ttsBackend='invented'),
                    dict(ttsBackend='wsyue',dubLanguages=['en']),dict(interfaceMode='simple',selectedEngines=['drama3','cosyvoice3'])]:
            with self.subTest(cfg=cfg),self.assertRaises(ValueError):core.production_plan(cfg)

    def test_retired_engines_migrate_without_selecting_extra_tracks(self):
        for engine,expected in [('gpt-sovits-v3','gpt-sovits'),('qwen-tts','cosyvoice3')]:
            self.assertEqual(core.production_plan(dict(ttsBackend=engine))['engines'],[expected])
        self.assertEqual(core.production_plan(dict(selectedEngines=['qwen-tts','drama3']))['engines'],['drama3'])

    def test_plan_is_immutable_when_draft_changes(self):
        cfg=dict(ttsBackend='drama3',dubLanguages=['yue'])
        original=core.freeze(cfg);old=copy.deepcopy(original)
        cfg['dubLanguages'].append('en');cfg['ttsBackend']='gpt-sovits'
        self.assertEqual(original,old)
        self.assertNotEqual(original['identity'],core.production_plan(cfg)['identity'])

    def test_subtitles_are_independent_of_voice_language(self):
        p=core.production_plan(dict(ttsBackend='drama3',dubLanguages=['yue'],subtitleModes=['english','original'],originalSubtitleStreams=[6,3,6]))
        self.assertEqual(p['subtitles'],['english','original'])
        self.assertEqual(p['originalSubtitleStreams'],[3,6])
        self.assertEqual(p['languages'],['yue'])

    def test_learning_subtitle_plan_has_stable_order_in_both_modes(self):
        for mode in ('simple','professional'):
            p=core.production_plan(dict(ttsBackend='drama3',interfaceMode=mode,dubLanguages=['yue'],subtitleModes=['original','dual','english','yue']))
            self.assertEqual(p['subtitles'],['yue','english','dual','original'])
            self.assertEqual(p['languages'],['yue'])

    def test_automatic_subtitle_plan_follows_languages_and_expert_custom_is_exact(self):
        for languages,expected in [(['yue'],['yue','original']),(['en'],['english','original']),(['en','yue'],['yue','english','dual','original'])]:
            p=core.production_plan(dict(ttsBackend='drama3',dubLanguages=languages,subtitleSelection='automatic',subtitleModes=[]))
            self.assertEqual(p['subtitles'],expected)
        self.assertEqual(core.production_plan(dict(ttsBackend='drama3',subtitleSelection='custom',subtitleModes=[]))['subtitles'],[])

    def test_unknown_protocol_operation_rejected(self):
        with self.assertRaises(ValueError):core.call('execute-shell',command='ignored')

    def test_stale_binary_and_catalog_are_rejected(self):
        core.verify.cache_clear()
        with patch.object(core,'_invoke',return_value={'sha256':'stale'}):
            with self.assertRaises(RuntimeError):core.verify()
        core.verify.cache_clear();core.verify()

    def hardware(self,ram,**changes):
        return dict(dict(platform='macos',architecture='aarch64',memoryGB=ram,backend='metal',acceleratorBudgetGB=(ram or 0)*.75),**changes)

    def test_explicit_download_choice_and_single_model_categories(self):
        models=json.loads((ROOT/'Resources/model-options.json').read_text())
        selected='mlx:qwen3.5-35b-a3b:4bit';requested='mlx:qwen3.5-9b:4bit'
        p=core.call('deployment',hardware=self.hardware(64),models=models,engine='drama3',installedModels=[selected],selectedModels={'text':selected},requestedModels={'text':requested},singleModelPerCategory=True)
        self.assertEqual(p['roles']['text'],requested)
        self.assertEqual(p['roles']['visual'],requested)
        self.assertEqual(p['roles']['referenceSpeech'],p['roles']['speech'])
        with self.assertRaises(ValueError):
            core.call('deployment',hardware=self.hardware(12),models=models,engine='drama3',requestedModels={'text':selected})

    def test_memory_tiers_do_not_promote_back_to_35b(self):
        for ram,expected in [(12,None),(16,'9b'),(24,'9b'),(64,'35b-a3b')]:
            p=core.deployment_plan(self.hardware(ram))
            if expected is None:
                self.assertIsNone(p['text']);self.assertFalse(p['canDeployModels']);continue
            self.assertEqual(p['text']['id'],f'mlx:qwen3.5-{expected}:4bit')
            if ram==16:self.assertNotIn('visual',p['roles'])
            self.assertLessEqual(p['text']['estimatedMemoryGB'],p['memoryBudgetGB'])

    def test_existing_higher_precision_asr_is_reused_without_download(self):
        installed=['mlx:qwen3.5-35b-a3b:4bit','drama3-35b-4bit','whisper-large-v3','asr-1.7b-8bit','asr-1.7b-4bit']
        selected=dict(text=installed[0],speech='whisper-large-v3',referenceSpeech='whisper-large-v3',asr='asr-1.7b-8bit')
        p=core.deployment_plan(self.hardware(64),installed=installed,selected=selected)
        self.assertEqual(p['roles']['asr'],'asr-1.7b-8bit')
        self.assertEqual(p['roles']['referenceSpeech'],'whisper-large-v3')
        self.assertEqual(p['modelDownloadBytes'],0)
        self.assertTrue(all(m['installed'] for m in p['downloads']))

    def test_installed_asr_is_used_even_without_saved_selection(self):
        p=core.deployment_plan(self.hardware(64),installed=['asr-1.7b-8bit','asr-1.7b-4bit'])
        self.assertEqual(p['roles']['asr'],'asr-1.7b-8bit')

    def test_installed_small_text_is_not_upgraded_on_large_machine(self):
        ident='mlx:qwen3.5-9b:4bit'
        p=core.deployment_plan(self.hardware(64),installed=[ident],selected={'text':ident})
        self.assertEqual(p['roles']['text'],ident)
        self.assertEqual(p['roles']['visual'],ident)
        self.assertFalse(any('35b' in m['id'] for m in p['downloads'] if m['id'].startswith('mlx:')))

    def test_oversized_existing_model_does_not_bypass_memory_budget(self):
        ident='mlx:qwen3.5-35b-a3b:4bit'
        p=core.deployment_plan(self.hardware(16),installed=[ident],selected={'text':ident})
        self.assertEqual(p['roles']['text'],'mlx:qwen3.5-9b:4bit')

    def test_eight_gb_does_not_offer_unfitting_four_b(self):
        p=core.deployment_plan(self.hardware(8))
        self.assertIsNone(p['text']);self.assertFalse(p['canDeployModels'])

    def test_gpu_budget_overrides_large_system_ram(self):
        for gpu,expected in [(6,None),(12,'9b'),(32,'35b-a3b')]:
            h=self.hardware(128);h['acceleratorBudgetGB']=gpu
            p=core.deployment_plan(h)
            if expected is None:
                self.assertIsNone(p['text']);self.assertFalse(p['canDeployModels']);self.assertNotIn('visual',p['roles']);continue
            self.assertEqual(p['text']['id'],f'mlx:qwen3.5-{expected}:4bit')
            self.assertLessEqual(p['text']['estimatedMemoryGB'],gpu)
            if gpu==6:self.assertNotIn('visual',p['roles'])

    def test_drama3_uses_authorized_gpt_fallback_when_memory_is_insufficient(self):
        p=core.deployment_plan(self.hardware(16))
        self.assertIsNotNone(p['text']);self.assertEqual(p['voice']['id'],'v2ProPlus')
        self.assertEqual(p['requestedEngine'],'drama3');self.assertEqual(p['engine'],'gpt-sovits-v2')
        self.assertIn('drama3-memory-budget-fallback-gpt-v2-pro-plus',p['warnings'])
        self.assertTrue(p['canDeployModels'])

    def test_retired_drama_small_is_never_an_automatic_fallback(self):
        p=core.deployment_plan(self.hardware(16))
        self.assertEqual(p['engine'],'gpt-sovits-v2');self.assertEqual(p['voice']['id'],'v2ProPlus')
        self.assertNotIn('drama3-small-cpu-fallback',p['warnings'])

    def test_sufficient_memory_keeps_drama3(self):
        p=core.deployment_plan(self.hardware(64))
        self.assertEqual(p['engine'],'drama3')
        self.assertEqual(p['voice']['id'],'drama3-35b-4bit')
        self.assertNotIn('drama3-memory-budget-fallback-gpt-v2-pro-plus',p['warnings'])

    def test_explicit_other_engine_is_not_silently_replaced(self):
        p=core.deployment_plan(self.hardware(12),engine='voxcpm2')
        self.assertEqual(p['engine'],'voxcpm2');self.assertFalse(p['canDeployModels'])

    def test_complete_download_list_and_deduplicated_bytes(self):
        p=core.deployment_plan(self.hardware(64))
        self.assertTrue(p['canDeployModels'])
        self.assertFalse(p['fullWorkflowReady'])
        self.assertEqual(set(p['roles'].values()),{m['id'] for m in p['downloads']})
        self.assertEqual(p['modelDownloadBytes'],sum(m['bytes'] for m in p['downloads']))
        self.assertIsNone(p['runtimeDownloadBytes'])

    def test_intel_mac_is_not_given_mlx(self):
        p=core.deployment_plan(self.hardware(64,architecture='x86_64',backend='cpu'))
        self.assertIsNone(p['text']);self.assertFalse(p['canDeployModels'])
        self.assertIn('automatic-platform-adapter-not-integrated',p['blockers'])

    def test_windows_gpu_does_not_imply_mlx_or_drama_support(self):
        for backend in ['cuda','rocm','xpu','cpu','unprobed']:
            p=core.deployment_plan(self.hardware(128,platform='windows',architecture='x86_64',backend=backend,acceleratorMemoryGB=24))
            self.assertFalse(p['canDeployModels']);self.assertIsNone(p['voice'])

    def test_missing_ram_never_assumed_large_machine(self):
        for value in [None,0,-1]:
            with self.assertRaises(ValueError):core.deployment_plan(self.hardware(value,acceleratorBudgetGB=0))

    def test_hardware_probe_reports_actual_host_without_claiming_inference(self):
        h=core.call('hardware');self.assertGreater(h['memoryGB'],0)
        self.assertFalse(h['inferenceVerified']);self.assertEqual(h['backend'],'unprobed')

    def test_windows_runtime_path_does_not_point_to_mlx_or_bin_python(self):
        with patch.object(runtime_paths.sys,'platform','win32'):
            self.assertEqual(runtime_paths.python_for('/data','drama3-runtime'),Path('/data/runtimes/drama3-runtime/Scripts/python.exe'))
        with self.assertRaises(ValueError):runtime_paths.python_for('/data','../other')

    def test_repair_uses_small_model_and_keeps_action_allowlist(self):
        for model in ['mlx:qwen3.5-4b:4bit','mlx:qwen3.5-9b:4bit']:
            with tempfile.TemporaryDirectory() as d:
                worker=Mock();worker.ollama_chat.return_value=json.dumps({'1':dict(action='delete',reason='invalid')})
                worker.atomic_json=lambda p,data:Path(p).write_text(json.dumps(data))
                rows=[dict(index=1,allowedActions=['keep'])]
                answer=repair.decisions(worker,dict(model=model,port=1),Path(d),rows,'')
                self.assertEqual(worker.ollama_chat.call_args.args[1],model)
                self.assertEqual(answer[0]['action'],'keep')

    def test_role_analysis_accepts_pinned_small_qwen_only(self):
        for model in ['mlx:qwen3.5-4b:4bit','mlx:qwen3.5-9b:4bit']:
            self.assertEqual(role_reanalysis.selected_models(dict(model=model)),(model,model))
        with self.assertRaises(ValueError):role_reanalysis.selected_models(dict(model='invented'))

if __name__=='__main__':unittest.main()
