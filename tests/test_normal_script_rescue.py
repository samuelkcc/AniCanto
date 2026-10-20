"""EP11: batch translator omits a named call; recover before TTS/hash/mux."""
import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import normal_mode
from worker import atomic_json

class NormalScriptRescueTests(unittest.TestCase):
    def setup_worker(self):
        w=Mock();w.atomic_json=atomic_json;w.traditional_cantonese.side_effect=lambda cfg,t:t;return w
    def test_episode11_missing_named_call_after_two_batch_responses_is_translated_alone(self):
        w=self.setup_worker();w.ollama_chat.side_effect=['{"0":"はい"}','{"0":""}','{"text":"阿博倫式緊急羈絆傳送！"}']
        cue=dict(start=329.88,end=333.16,japanese='アーボルン式緊急絆ワープ',text='アーボルン式緊急絆ワープ',cantonese='',speakerId='own-line-41')
        cfg=dict(productionMode='normal',dubLanguages=['yue'],subtitleModes=[],model='qwen9b',port=1)
        with tempfile.TemporaryDirectory() as d,patch.object(normal_mode,'glossary',return_value=[]):
            normal_mode.translate(w,cfg,Path(d),[cue])
            self.assertEqual(cue['cantonese'],'阿博倫式緊急羈絆傳送！');self.assertEqual(cue['speakerId'],'own-line-41')
            normal_mode.ensure_scripts(w,cfg,Path(d),[cue]);self.assertEqual(w.ollama_chat.call_count,3)
            rescue=json.loads((Path(d)/'normal-script-rescue.json').read_text());self.assertEqual(rescue['rows'][0]['method'],'isolated-source-translation')
    def test_english_missing_script_has_independent_rescue_without_overwriting_cantonese(self):
        w=self.setup_worker();w.ollama_chat.return_value='{"text":"Emergency Bond Warp!"}'
        cue=dict(start=1,end=3,japanese='緊急絆ワープ',cantonese='緊急羈絆傳送！',english='')
        with tempfile.TemporaryDirectory() as d:
            normal_mode.ensure_scripts(w,dict(productionMode='normal',dubLanguages=['yue','en'],model='qwen',port=1),Path(d),[cue])
        self.assertEqual(cue['english'],'Emergency Bond Warp!');self.assertEqual(cue['cantonese'],'緊急羈絆傳送！');self.assertEqual(w.ollama_chat.call_count,1)
    def test_audio_only_never_reads_caption_fallback_and_failure_budget_survives_boundaries(self):
        w=self.setup_worker();w.ollama_chat.return_value='{"text":""}'
        cue=dict(start=1,end=3,japanese='未知の声',cantonese='',subtitleHint='不應讀到字幕')
        cfg=dict(productionMode='normal',translationSource='audio-only',dubLanguages=['yue'],model='qwen',port=1)
        with tempfile.TemporaryDirectory() as d:
            for _ in range(3):normal_mode.ensure_scripts(w,cfg,Path(d),[cue])
        self.assertLessEqual(w.ollama_chat.call_count,4);self.assertEqual(cue['cantonese'],'');self.assertNotIn('subtitleHint',cue)
        self.assertFalse(any('不應讀到字幕' in str(c) for c in w.ollama_chat.call_args_list))
    def test_fast_manual_and_disabled_lines_are_not_rewritten(self):
        w=self.setup_worker()
        with tempfile.TemporaryDirectory() as d:
            for cfg,cue in [(dict(productionMode='fast'),dict(start=0,end=1)),(dict(productionMode='normal',editorRender=True),dict(start=0,end=1)),(dict(productionMode='normal',dubLanguages=['yue']),dict(start=0,end=1,enabled=False))]:normal_mode.ensure_scripts(w,cfg,Path(d),[cue])
        w.ollama_chat.assert_not_called()

if __name__=='__main__':unittest.main()
