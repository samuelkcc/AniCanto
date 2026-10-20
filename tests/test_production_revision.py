import copy,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import cantonese_pronunciation as pronunciation
import script_revision,project_edit,voice_samples,multitrack


class PronunciationTests(unittest.TestCase):
    def test_longest_nonrecursive_reading_preserves_text_alignment(self):
        entries=pronunciation.rules('銀行 = ngan4 hong4\n行 = haang4')
        text='銀行,行!'
        actual=pronunciation.replace(text,['ngan4','haang4',',','hong4','!'],entries)
        self.assertEqual(actual,['ngan4','hong4',',','haang4','!'])
        self.assertEqual(len(actual),len(text))
        self.assertEqual(pronunciation.matching('銀行 = ngan4 hong4','下一句'),{})

    def test_bad_tone_or_count_and_conflicting_rules_fail_closed(self):
        for text in ['銀行 = ngan4','行 = haang9','行 = haang4 hong4','行 = haang4\n行 = hong4','bank = baang1','行']:
            with self.subTest(text=text),self.assertRaises(ValueError):pronunciation.rules(text)
        with self.assertRaises(ValueError):pronunciation.replace('銀行',['ngan4'],{'銀行':['ngan4','hong4']})

    def test_reference_and_next_line_are_not_patched(self):
        frontend=SimpleNamespace(get_jyutping=lambda text:['waa2'])
        original=frontend.get_jyutping
        with pronunciation.override(frontend,{'話':['waa6']}):self.assertEqual(frontend.get_jyutping('話'),['waa6'])
        self.assertIs(frontend.get_jyutping,original)

    def test_model_hook_only_wraps_target_preprocessing(self):
        frontend=SimpleNamespace(get_jyutping=lambda text:['waa2'])
        original=frontend.get_jyutping
        preprocessor=SimpleNamespace(preprocess=lambda text:frontend.get_jyutping(text),segment_and_extract_feature_for_text=lambda text:frontend.get_jyutping(text))
        model=SimpleNamespace(text_preprocessor=preprocessor,_canto_readings={'話':['waa6']})
        with patch.dict(sys.modules,{'text':SimpleNamespace(cantonese=frontend)}):
            pronunciation.install(model)
            self.assertEqual(preprocessor.segment_and_extract_feature_for_text('話'),['waa2'])
            self.assertEqual(preprocessor.preprocess('話'),['waa6'])
            self.assertEqual(preprocessor.segment_and_extract_feature_for_text('話'),['waa2'])
            model._canto_readings={}
            self.assertEqual(preprocessor.preprocess('話'),['waa2'])
        self.assertEqual(frontend.get_jyutping('話'),['waa2'])
        with self.assertRaises(RuntimeError):
            with pronunciation.override(frontend,{'話':['waa6']}):raise RuntimeError('failed inference')
        self.assertIs(frontend.get_jyutping,original)


class ScriptRevisionTests(unittest.TestCase):
    def fixture(self):
        cues=[dict(editorID='a',editorSources=[0],start=1,end=3,subtitleStart=.9,subtitleEnd=3.1,speakerId='role',text='日文',japanese='日文',cantonese='舊稿',english='Approved English',captionText='舊字幕'),dict(editorID='b',editorSources=[1],start=4,end=6,subtitleStart=4.1,subtitleEnd=6.1,speakerId='other',text='日文二',japanese='日文二',cantonese='',english='')]
        def translate(cfg,batch,context,checkpoint):
            for row in batch:row.update(cantonese='新稿',start=999,speakerId='wrong')
            checkpoint()
        def atomic(path,obj):Path(path).write_text(json.dumps(obj))
        w=SimpleNamespace(emit=Mock(),translate_batch=Mock(side_effect=translate),atomic_json=atomic,save_srt=Mock())
        cfg=dict(scriptLanguages=['yue'],scriptRevisionMode='missing',model='local')
        return cues,w,cfg

    def test_only_missing_translation_changes_and_clocks_roles_preserved(self):
        cues,w,cfg=self.fixture();before=copy.deepcopy(cues)
        with tempfile.TemporaryDirectory() as d:
            result,missing=script_revision.prepare(w,cfg,d,cues)
            self.assertFalse(missing);self.assertEqual(cues,before)
            self.assertEqual(result[0]['cantonese'],'舊稿');self.assertEqual(result[0]['captionText'],'舊字幕')
            self.assertEqual(result[1]['cantonese'],'新稿')
            for old,new in zip(before,result):
                for key in ('start','end','subtitleStart','subtitleEnd','speakerId','editorSources','english'):self.assertEqual(old[key],new[key])
            script_revision.prepare(w,cfg,d,cues)
            self.assertEqual(w.translate_batch.call_count,1)

    def test_all_english_does_not_clear_cantonese_or_disabled_script(self):
        cues,w,cfg=self.fixture();cues[1].update(enabled=False,english='Disabled approved English')
        cfg.update(scriptLanguages=['en'],scriptRevisionMode='all')
        def english(w,cfg,folder,rows):
            self.assertEqual(rows[0]['english'],'')
            for row in rows:row['english']='New English' if row.get('enabled',True) else ''
        with tempfile.TemporaryDirectory() as d,patch('dub_languages.english_script',side_effect=english):
            result,missing=script_revision.prepare(w,cfg,d,cues)
        self.assertFalse(missing);self.assertEqual(result[0]['cantonese'],'舊稿');self.assertEqual(result[0]['english'],'New English');self.assertEqual(result[1]['english'],'Disabled approved English')

    def test_subtitle_task_never_enters_media_render_and_leaves_review_unchanged(self):
        cues,w,cfg=self.fixture()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);review=root/'review.json'
            review.write_text(json.dumps(dict(config=dict(duration=8,video='missing-video',model='local'),cues=[dict(c,start=c['start'],end=c['end']) for c in cues])))
            original=review.read_bytes()
            draft=dict(id='new-version',created='today',review=str(review),segments=[dict(id=c['editorID'],sources=c['editorSources'],start=c['start'],end=c['end'],captionStart=c['subtitleStart'],captionEnd=c['subtitleEnd'],text=c['cantonese'],original=c['text'],speakerId=c['speakerId'],english=c['english']) for c in cues],settings=dict(cfg,subtitlesOnly=True))
            submission=root/'submission.json';submission.write_text(json.dumps(draft))
            w.render_review=Mock(side_effect=AssertionError('TTS/mux must not run'));w.run=Mock(side_effect=AssertionError('ffmpeg/ASR must not run'))
            project_edit.render(w,dict(submission=str(submission)))
            state=json.loads((root/'versions/new-version/version.json').read_text())
            self.assertEqual(state['status'],'script-ready');self.assertEqual(review.read_bytes(),original)
            self.assertTrue((root/'versions/new-version/subtitle-draft.json').exists())
            self.assertEqual(w.save_srt.call_args.args[1][0]['start'],.9)

    def test_approved_english_subtitles_are_reused_without_model_requests(self):
        rows=[dict(cantonese='你好',english='Hello.'),dict(cantonese='再見',english='Goodbye.')]
        with tempfile.TemporaryDirectory() as d:
            w=SimpleNamespace(emit=Mock(),ollama_chat=Mock(side_effect=AssertionError('approved English must be retained')),atomic_json=lambda p,o:Path(p).write_text(json.dumps(o)))
            self.assertEqual(multitrack.english_lines(w,dict(model='local',port=0),Path(d),rows),['Hello.','Goodbye.'])
        self.assertEqual(multitrack.subtitle_choices(dict(subtitleOutput='separate'))[0],['yue','english'])

    def test_fresh_audition_ignores_missing_old_take_and_does_not_need_video(self):
        cues,w,cfg=self.fixture()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);review=root/'review.json'
            review.write_text(json.dumps(dict(config=dict(duration=8,video='missing-video',model='local'),cues=cues)))
            row=dict(id='a',sources=[0],start=1,end=3,captionStart=.9,captionEnd=3.1,text='新試音台詞',original='日文',speakerId='role',audioTake=str(root/'removed.wav'))
            draft=dict(id='new-samples',review=str(review),segments=[row],settings=dict(voiceSamplesOnly=True,audioRerunToken='fresh'))
            submission=root/'submission.json';submission.write_text(json.dumps(draft))
            w.run=Mock(side_effect=AssertionError('no movie decode'));w.render_review=Mock(side_effect=AssertionError('no movie render'))
            with patch('voice_samples.generate',return_value=dict(rows=[dict(audio='fixture.wav')],errors={})) as generate:
                project_edit.render(w,dict(submission=str(submission)))
                self.assertNotIn('editorAudio',generate.call_args.args[-1][0])
            self.assertEqual(json.loads((root/'versions/new-samples/version.json').read_text())['status'],'voice-samples')


class VoiceSampleTests(unittest.TestCase):
    def test_limit_and_role_distribution_never_modify_source_cues(self):
        cues=[dict(start=i,end=i+3,speakerId=str(i//12),cantonese='呢句係固定嘅廣東話試音。',enabled=i!=1,editorID=str(i)) for i in range(36)]
        before=copy.deepcopy(cues);chosen=voice_samples.select(cues)
        self.assertEqual(len(chosen),20);self.assertEqual({c['speakerId'] for c in chosen},{'0','1','2'})
        self.assertNotIn('1',[c['editorID'] for c in chosen]);self.assertEqual(cues,before)
        chosen[0]['cantonese']='changed';self.assertEqual(cues,before)

if __name__=='__main__':unittest.main()
