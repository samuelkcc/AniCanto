import array
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch
import wave

sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import normal_mode,fast_mode,opening


def audio(path,level=5000):
    with wave.open(str(path),'wb') as stream:
        stream.setparams((1,2,16000,0,'NONE','not compressed'))
        stream.writeframes(array.array('h',[level,-level]*8000).tobytes())
    return path


class NormalModeTests(unittest.TestCase):
    def test_modes_do_not_reintroduce_generic_role_fallback_or_whole_workflow_QA(self):
        for mode in ('fast','normal'):
            cfg=dict(productionMode=mode,aiAutoFix=True,autoValidate=True,fallbackToRoleVoice=True)
            fast_mode.configure(cfg)
            self.assertEqual(cfg['productionMode'],mode)
            self.assertFalse(cfg['aiAutoFix']);self.assertFalse(cfg['autoValidate'])
            self.assertFalse(cfg['fallbackToRoleVoice']);self.assertEqual(cfg['roleAnalysisMode'],'independent')
        self.assertNotEqual(fast_mode.warning({'productionMode':'normal'}),fast_mode.WARNING)

    def test_generic_chinese_label_short_names_and_homophones_do_not_trigger_retake(self):
        for expected,heard,label in [('雷德','雷德','Chinese'),('你喺邊呀','你係邊呀','Chinese'),('我哋要去搵佢返嚟','我們要去找他回來','Chinese')]:
            self.assertNotEqual(normal_mode.dialect_decision(expected,heard,label),'mandarin')
        self.assertEqual(normal_mode.dialect_decision('你哋點解唔去搵佢呀','你们为什么不去找他们','Chinese'),'mandarin')
        self.assertEqual(normal_mode.dialect_decision('我哋一齊出發啦','我们一起出发吧','Mandarin'),'mandarin')
        self.assertEqual(normal_mode.dialect_decision('我哋一齊出發啦','我地一齊出發啦','Cantonese'),'cantonese')

    def test_unconfirmed_name_lists_stay_uncertain_and_trigger_bounded_repair(self):
        text='烏索普、山治、喬巴、羅賓'
        self.assertTrue(normal_mode.needs_dialect_confirmation(text,dict(decision='unconfirmed')))
        self.assertFalse(normal_mode.needs_dialect_confirmation('雷德',dict(decision='unconfirmed')))
        self.assertFalse(normal_mode.needs_dialect_confirmation(text,dict(decision='cantonese')))
        with tempfile.TemporaryDirectory() as d:
            job=Path(d);old=audio(job/'old.wav');new=audio(job/'new.wav')
            with patch.object(normal_mode,'inspect',return_value={1:dict(decision='unconfirmed',language='Chinese')}),patch('dubbing.gsv_audio',return_value=[new]):
                self.assertEqual(normal_mode.repair_paths(dict(productionMode='normal'),job,[dict(start=0,end=2,cantonese=text,speakerId='own')],[old],Mock(),Mock()),[old])
            report=json.loads((job/'normal-checks.json').read_text());self.assertEqual(report['unresolved'],[1]);self.assertEqual(report['repairs'][0]['reason'],'dialect-unconfirmed')
    def test_clear_nonlexical_cry_with_no_translation_is_not_missing_dialogue(self):
        from dubbing import is_vocalization
        self.assertTrue(is_vocalization(dict(japanese='あああああああああ',cantonese='')))
        self.assertFalse(is_vocalization(dict(japanese='知らん知らん',cantonese='')))

    def test_titles_are_not_spoken_but_real_recognized_dialogue_and_names_survive(self):
        for text in ('第 08 集 紅衣戰士','译者致谢：[译者姓名]'):
            self.assertTrue(normal_mode.metadata_only(dict(subtitleHint=text,japanese='')))
            self.assertFalse(normal_mode.metadata_only(dict(subtitleHint=text,japanese='第八話')))
        self.assertFalse(normal_mode.metadata_only(dict(subtitleHint='片岡修二',japanese='')))

    def test_translation_repairs_only_missing_rows_once_and_never_accepts_kana(self):
        w=Mock();w.traditional_cantonese.side_effect=lambda cfg,text:text
        w.ollama_chat.side_effect=['{"0":"出發啦。","1":"はい"}','{"1":"係呀。"}']
        cues=[dict(start=0,end=2,japanese='行こう',cantonese=''),dict(start=2,end=3,japanese='はい',cantonese='')]
        with tempfile.TemporaryDirectory() as d,patch.object(normal_mode,'glossary',return_value=[]):
            normal_mode.translate(w,dict(dubLanguages=['yue'],subtitleModes=[],model='qwen',port=1),Path(d),cues)
        self.assertEqual([c['cantonese'] for c in cues],['出發啦。','係呀。'])
        self.assertEqual(w.ollama_chat.call_count,2)
        self.assertEqual(set(json.loads(w.ollama_chat.call_args.args[2][1]['content'])),{'1'})

    def test_repair_is_same_source_bounded_persistent_and_never_replaces_audible_with_silence(self):
        from worker import atomic_json
        with tempfile.TemporaryDirectory() as d:
            job=Path(d);original=audio(job/'original.wav',8);good=audio(job/'good.wav')
            cues=[dict(start=0,end=1,cantonese='點解你知呀',speakerId='own-line-18')]
            cfg=dict(productionMode='normal',ttsBackend='drama3',targetLanguage='yue')
            before=original.read_bytes();seen=[]
            def generate(c,folder,rows,run,emit):
                seen.append(copy.deepcopy(rows));self.assertEqual(rows[0]['speakerId'],'own-line-18');return [good]
            with patch.object(normal_mode,'inspect',return_value={}),patch('dubbing.gsv_audio',side_effect=generate) as generate_mock:
                chosen=normal_mode.repair_paths(cfg,job,cues,[original],Mock(),Mock())
                self.assertEqual(chosen,[good]);self.assertEqual(before,original.read_bytes())
                self.assertEqual(normal_mode.repair_paths(cfg,job,cues,[original],Mock(),Mock()),[good])
                self.assertEqual(generate_mock.call_count,1)
            self.assertTrue(json.loads((job/'normal-checks.json').read_text())['repairs'][0]['repaired'])
            self.assertEqual(len(seen),1)

    def test_mandarin_retry_requires_positive_cantonese_evidence_before_adoption(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);old=audio(folder/'old.wav');new=audio(folder/'new.wav')
            cue=dict(start=0,end=1,cantonese='我哋一齊出發啦',speakerId='own')
            with patch.object(normal_mode,'inspect',side_effect=[{1:dict(decision='mandarin')},{1:dict(decision='unconfirmed')},{1:dict(decision='unconfirmed')}]),patch('dubbing.gsv_audio',return_value=[new]):
                self.assertEqual(normal_mode.repair_paths(dict(productionMode='normal'),folder,[cue],[old],Mock(),Mock()),[old])
            self.assertEqual(json.loads((folder/'normal-checks.json').read_text())['unresolved'],[1])

    def test_missing_result_cannot_drop_a_translated_line_and_retry_budget_survives_resume(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);cue=dict(start=0,end=1,cantonese='我哋而家一齊出發啦',speakerId='own')
            with patch.object(normal_mode,'inspect',return_value={}),patch('dubbing.gsv_audio',return_value=[]) as generate:
                chosen=normal_mode.repair_paths(dict(productionMode='normal'),folder,[cue],[],Mock(),Mock())
                self.assertEqual(len(chosen),1);self.assertEqual(generate.call_count,2)
                normal_mode.repair_paths(dict(productionMode='normal'),folder,[cue],[],Mock(),Mock())
                self.assertEqual(generate.call_count,2)
            report=json.loads((folder/'normal-checks.json').read_text())
            self.assertEqual(report['unresolved'],[1]);self.assertEqual(report['maximumLocalAttempts'],2)

    def test_whole_missing_clause_requires_long_prefix_not_cantonese_spelling_variations(self):
        self.assertTrue(normal_mode.major_omission('我哋而家出發，之後一齊返屋企食飯','我哋而家出發'))
        for expected,heard in [('你喺邊呀','你係邊呀'),('雷德','雷'),('我哋而家出發，之後返屋企','我地而家出發之後返屋企')]:
            self.assertFalse(normal_mode.major_omission(expected,heard))

    def test_normal_retains_nonverbal_performances_fast_stays_unchecked(self):
        self.assertTrue(fast_mode.configure(dict(productionMode='normal'))['preserveNonverbal'])
        self.assertFalse(fast_mode.configure(dict(productionMode='fast'))['preserveNonverbal'])

    def test_written_mandarin_is_retranslated_without_changing_proper_names(self):
        w=Mock();w.traditional_cantonese.side_effect=lambda cfg,text:text
        w.ollama_chat.side_effect=['{"0":"特爾公主，讓我為您遮蔭！"}','{"0":"特爾公主，等我幫你遮蔭啦！"}']
        cues=[dict(start=0,end=3,japanese='姫様',cantonese='')]
        with tempfile.TemporaryDirectory() as d,patch.object(normal_mode,'glossary',return_value=[]):
            normal_mode.translate(w,dict(dubLanguages=['yue'],subtitleModes=[],model='qwen',port=1),Path(d),cues)
        self.assertEqual(cues[0]['cantonese'],'特爾公主，等我幫你遮蔭啦！')
        self.assertEqual(w.ollama_chat.call_count,2)

    def test_repaired_generation_issue_moves_to_history_not_active_failure_list(self):
        from project_store import record_issue,resolve_issues,connect
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);cfg=dict(storage=d,ttsBackend='drama3')
            record_issue(cfg,folder,dict(start=0,end=1,reviewIndex=0),'tts-generation','decoder limit')
            record_issue(cfg,folder,dict(start=1,end=2,reviewIndex=1),'tts-generation','other failure')
            resolve_issues(cfg,folder,[1])
            self.assertEqual([r['index'] for r in json.loads((folder/'segment-issues.json').read_text())],[2])
            self.assertEqual(json.loads((folder/'resolved-segment-issues.json').read_text())[0]['status'],'repaired')
            with connect(d) as db:self.assertEqual([r[0] for r in db.execute('SELECT cue FROM issues')],[2])

    def test_local_listen_confirms_missing_clause_with_two_unprompted_witnesses(self):
        from worker import atomic_json
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);path=audio(folder/'take.wav');cue=dict(start=0,end=1,cantonese='我哋而家出發，之後一齊返屋企食飯')
            cfg=dict(storage=d,ffmpeg='ffmpeg',asrModel='chosen-asr')
            def listen(c,action,request,emit):
                self.assertEqual(request['asrModel'],'chosen-asr')
                atomic_json(request['cache'],{i['key']:dict(heard='我哋而家出發',language='Cantonese') for i in request['items']})
            with patch('dubbing.model_job',side_effect=listen) as first,patch('runtime_paths.python_for',return_value=Path(sys.executable)),patch('secondary_speech.transcribe_batch',return_value=[dict(heard='我地而家出發',language='yue')]) as second:
                result=normal_mode.inspect(cfg,folder,[cue],[path],Mock())
            self.assertTrue(result[1]['contentFailure']);self.assertEqual(first.call_count,1);self.assertEqual(second.call_count,1)
            self.assertTrue(second.call_args.kwargs['auto_language'])

    def test_sustained_singing_with_low_music_is_confirmed_but_dialogue_is_not(self):
        rows=[dict(start=231+i*1.5,duration=3,music=.4,singing=.6,speech=.12) for i in range(29)]
        chapter=[dict(start_time='231.022',end_time='276.026')]
        found=opening.source_song_ranges(rows,300,chapter)
        self.assertEqual((found[0]['start'],found[0]['end']),(231.022,276.026))
        self.assertEqual(opening.source_song_ranges([dict(r,speech=.8) for r in rows],300,chapter),[])
        self.assertEqual(opening.source_song_ranges([dict(r,singing=0) for r in rows],300,chapter),[])


if __name__=='__main__':unittest.main()
