import importlib.util
import unittest
from unittest.mock import patch
import io
import json
import tempfile
import urllib.error
from pathlib import Path

spec = importlib.util.spec_from_file_location("worker", Path(__file__).parents[1] / "Resources/worker.py")
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


class WorkerTests(unittest.TestCase):
    def test_batch_uses_selected_external_subtitle_over_same_name_sidecar(self):
        with tempfile.TemporaryDirectory() as folder:
            directory=Path(folder);video=directory/'episode.mp4';video.write_bytes(b'video')
            sidecar=directory/'episode.srt';sidecar.write_text('wrong',encoding='utf-8')
            selected=directory/'translation.ass';selected.write_text('chosen',encoding='utf-8')
            configs=[]
            with patch.object(worker,'convert',side_effect=lambda cfg:configs.append(cfg)),patch.object(worker,'emit'):
                worker.batch_convert(dict(videos=[dict(id='first',video=str(video))],subtitleSource='external',
                                          subtitle=str(selected),batchAutoSubtitles=False,batchExplicitSubtitle=True))
            self.assertEqual(len(configs),1)
            self.assertEqual(configs[0]['subtitle'],str(selected))

    def test_critical_action_must_be_corroborated_by_audio_and_caption(self):
        dead=dict(japanese='彼は死んじゃった',subtitleHint='他死了')
        self.assertTrue(worker.meaning_issues(dead,'佢唔喺咗'))
        self.assertFalse(worker.meaning_issues(dead,'佢死咗'))
        self.assertFalse(worker.meaning_issues(dict(japanese='必死です',subtitleHint='很拼命'),'佢好搏命'))
        anger=dict(japanese='ママを怒らせりゃ',subtitleHint='惹妈妈生气')
        self.assertTrue(worker.meaning_issues(anger,'唔該唔該'))
        self.assertFalse(worker.meaning_issues(anger,'激嬲咗媽媽'))
        self.assertEqual(worker.spoken_cantonese('餵，點解呀？'),'喂，點解呀？')
        self.assertEqual(worker.spoken_cantonese('餵狗'),'餵狗')
        self.assertEqual(worker.spoken_cantonese('惹到爸爸生氣，就算是親生仔'),'激嬲咗爸爸，就算係親生仔')

    def test_editor_metadata_removed_but_spoken_name_not_deleted(self):
        self.assertEqual(worker.clean_spoken_line('{"意思":"食物","改寫":"阿健：你嘅咖啡。"}'),'阿健，你嘅咖啡。')
        self.assertEqual(worker.clean_spoken_line('你好，等埋我。'),'你好，等埋我。')
        with self.assertRaises(ValueError):worker.clean_spoken_line('{"意思":"只有資料"}')

    def test_scene_understanding_keeps_chronological_speakers_and_global_turns(self):
        cues=[dict(start=i,end=i+.8,text=f'原文{i}',japanese=f'日文{i}',speakerId=f'role-{i%2}',subtitleHint='字幕') for i in range(14)]
        requests=[]
        def reply(port,model,messages,schema,**kw):
            payload=json.loads(messages[-1]['content']);requests.append(payload)
            return json.dumps({k:dict(meaning='叫阿健',speech_act='call',names=['阿健']) for k in payload['requested_turns']})
        with tempfile.TemporaryDirectory() as folder, patch.object(worker,'ollama_chat',side_effect=reply), patch.object(worker,'emit'):
            worker.plan_dialogue_scenes({'port':1,'model':'qwen3:14b'},Path(folder),cues,[])
            self.assertEqual([c['turnId'] for c in cues],list(range(1,15)))
            self.assertEqual([c['speaker'] for c in requests[0]['dialogue'][:3]],['role-0','role-1','role-0'])
            self.assertEqual(requests[1]['requested_turns'],['13','14'])
            self.assertEqual(requests[1]['dialogue'][0]['turn'],9)
            worker.plan_dialogue_scenes({'port':1,'model':'qwen3:14b'},Path(folder),cues,[])
            self.assertEqual(len(requests),2)
            source=dict(cues[0],cantonese='阿健！')
            edited={k:source[k] for k in ('start','end','text','cantonese')}
            selected=worker.validate_review([edited],[source],20)[0]
            self.assertEqual(selected['scenePlan'],source['scenePlan'])
            self.assertEqual(selected['turnId'],1)

    def test_scene_glossary_rejects_terms_without_caption_evidence(self):
        terms={'terms':[{'japanese':'ケン','cantonese':'阿健','kind':'person','caption_evidence':'阿健'}, {'japanese':'未知','cantonese':'亂加人物','kind':'person','caption_evidence':'冇出現過'}, {'japanese':'空耳','cantonese':'憑空加名','kind':'person','caption_evidence':'阿健'}]}
        with tempfile.TemporaryDirectory() as folder, patch.object(worker,'ollama_chat',return_value=json.dumps(terms)), patch.object(worker,'emit'):
            result=worker.scene_glossary({'port':1,'model':'qwen3:14b'},Path(folder),[{'text':'ケン！','japanese':'ケン！','subtitleHint':'阿健！'}])
            self.assertEqual([t['cantonese'] for t in result],['阿健'])

    def test_ocr_variants_are_not_presented_as_repeated_spoken_dialogue(self):
        self.assertEqual(worker.caption_evidence('呢杯咖啡，謝謝。呢杯茶 ／ 謝謝。呢杯茶。呢杯咖啡'),'呢杯咖啡；謝謝；呢杯茶')

    def test_duration_edit_preserves_spoken_names_and_call_intention(self):
        self.assertEqual(worker.preserve_brief('歡迎嚟餐廳！','歡迎嚟餐廳！',{'names':['餐廳'],'speech_act':'call'}),'歡迎嚟餐廳！')
        self.assertEqual(worker.preserve_brief('知喇！','知喇，健太。',{'names':['健太'],'speech_act':'statement'}),'知喇，健太。')
        self.assertEqual(worker.preserve_brief('得啦！','健太！',{'names':['健太'],'speech_act':'call'}),'健太！')
        self.assertEqual(worker.preserve_brief('健太，走！','健太，快啲走！',{'names':['健太'],'speech_act':'statement'}),'健太，走！')

    def test_removed_system_voice_never_falls_back_to_macos_speech(self):
        for backend in ("system", "unknown", None):
            with patch.object(worker, "run") as run:
                with self.assertRaisesRegex(ValueError, "系統聲線已移除"):
                    worker.synthesize({"ttsBackend":backend}, Path("unused"), [])
                run.assert_not_called()
    def test_multiline_markup_and_crlf_subtitles(self):
        text = "\ufeff1\r\n00:00:01,250 --> 00:00:03,000\r\n<i>你去邊呀？</i>\r\n{\\an8}等埋我！\r\n\r\n2\r\n00:00:05,000 --> 00:00:04,000\r\ninvalid\r\n"
        self.assertEqual(worker.parse_srt(text), [{"start":1.25,"end":3.0,"text":"你去邊呀？ 等埋我！"}])

    def test_reject_missing_duplicate_and_blank_model_lines(self):
        for text in ['{"lines":[]}', '{"lines":[{"id":0,"text":"甲"},{"id":0,"text":"乙"}]}', '{"lines":[{"id":0,"text":""},{"id":1,"text":"乙"}]}']:
            with self.assertRaises(ValueError):
                worker.validate_translation(text, 2)

    def test_subtitle_time_carries(self):
        self.assertEqual(worker.srt_time(59.9999), "00:01:00,000")
        self.assertEqual(worker.srt_time(3600.25), "01:00:00,250")

    def test_retry_http500_retains_error_and_recovers(self):
        error = urllib.error.HTTPError("http://127.0.0.1", 500, "Error", {}, io.BytesIO(b'{"error":"runner failed"}'))
        response = io.BytesIO(b'{"message":{"content":"recovered"}}')
        with patch.object(worker.urllib.request, "urlopen", side_effect=[error, response]) as request, patch.object(worker.time, "sleep"), patch.object(worker, "emit") as events:
            self.assertEqual(worker.ollama_chat(11439, "qwen3:4b", []), "recovered")
            self.assertEqual(request.call_count, 2)
            self.assertEqual(events.call_args.args[0], "重試")

    def test_empty_reasoning_response_retries_without_discarding_request(self):
        empty=io.BytesIO(b'{"message":{"content":"","thinking":"unfinished"},"done_reason":"length"}')
        complete=io.BytesIO(json.dumps({'message':{'content':'{"ok":true}'}}).encode())
        with patch.object(worker.urllib.request,'urlopen',side_effect=[empty,complete]) as request, patch.object(worker,'emit'):
            self.assertEqual(worker.ollama_chat(1,'qwen3:14b',[],True,think=True),'{"ok":true}')
            self.assertEqual(request.call_count,2)
            self.assertFalse(json.loads(request.call_args.args[0].data)['think'])

    def test_review_blocks_synthesis_until_approval(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            video = root / "video.mp4"
            video.write_bytes(b"fixture")
            cfg = {"video":str(video), "storage":folder, "ffprobe":"ffprobe", "translate":False, "autoApprove":False}
            meta = {"format":{"duration":"5"}, "streams":[{"codec_type":"video"}]}
            cues = [{"start":0.5, "end":2, "text":"原文"}]
            with patch.object(worker, "run", return_value=json.dumps(meta).encode()), patch.object(worker, "extract_cues", return_value=cues), patch.object(worker, "render_review") as render, patch.object(worker, "emit"):
                worker.convert(cfg)
                render.assert_not_called()
                review = next((root / "jobs").glob("*/review.json"))
                self.assertEqual(json.loads(review.read_text())["status"], "pending")
                self.assertFalse((review.parent / "cantonese.wav").exists())
                cfg["autoApprove"] = True
                worker.convert(cfg)
                render.assert_called_once_with({"review":str(review),"lockScript":True})
                render.reset_mock()
                cfg.pop("autoApprove")
                worker.convert(cfg)
                render.assert_called_once_with({"review":str(review),"lockScript":True})

    def test_review_uses_edits_skips_disabled_and_rejects_blank(self):
        original = [{"start":0, "end":1, "text":"甲"}, {"start":2, "end":3, "text":"乙"}]
        draft = [dict(original[0], cantonese="  修改咗嘅台詞  "), dict(original[1], cantonese="", enabled=False)]
        result = worker.validate_review(draft, original, 5)
        self.assertEqual([c["cantonese"] for c in result], ["修改咗嘅台詞"])
        draft[1]["enabled"] = True
        with self.assertRaisesRegex(ValueError, "第 2 句"):
            worker.validate_review(draft, original, 5)
        # Incomplete saved drafts must survive reloading without silently resetting edits.
        self.assertEqual(len(worker.validate_review(draft, original, 5, require_ready=False)), 2)
        draft[0]["start"] = 0.1
        with self.assertRaisesRegex(ValueError, "時間或原文"):
            worker.validate_review(draft, original, 5)

    def test_split_translation_keeps_completed_checkpoint(self):
        batch = [{"start":0,"end":1,"text":"甲"}, {"start":1,"end":2,"text":"乙"}]
        with patch.object(worker, "ollama_chat", side_effect=[RuntimeError("500"), '{"line_0":"第一句"}', RuntimeError("500")]), patch.object(worker, "emit"):
            snapshots = []
            with self.assertRaises(RuntimeError):
                worker.translate_batch({"continueOnError":False,"port":11439,"model":"qwen3:4b"}, batch, [], lambda: snapshots.append(json.dumps(batch)))
            self.assertEqual(batch[0]["cantonese"], "第一句")
            self.assertEqual(len(snapshots), 1)
            self.assertNotIn("cantonese", batch[1])

    def test_ocr_region_rejects_outside_bottom_and_bad_color(self):
        for cfg in [{"ocrTop":0.1}, {"ocrTop":0.95,"ocrBottom":0.9}, {"ocrMargin":0.5}, {"ocrColor":"unknown"}]:
            with self.assertRaises(ValueError):
                worker.ocr_filter(cfg)
        self.assertTrue(worker.ocr_filter({}).startswith("crop="))
        self.assertNotIn("geq", worker.ocr_filter({"ocrColor":"original"}))

    def test_ocr_stability_keeps_short_subtitles_reviewable(self):
        rows = [{"index":0,"text":"呢句保持唔郁"}, {"index":1,"text":"呢句保持唔郁"}, {"index":3,"text":"快速字幕"}]
        cues = worker.merge_ocr_rows(rows, 5)
        self.assertEqual(len(cues), 2)
        self.assertEqual(cues[0]["end"], 1)
        self.assertNotIn("enabled", cues[0])
        self.assertFalse(cues[1]["enabled"])
        self.assertTrue(worker.merge_ocr_rows(rows, 5, stable=False)[1].get("enabled",True))

    def test_persistent_ocr_text_is_flagged_not_deleted(self):
        rows = [{"index":i,"text":"固定水印"} for i in range(44)]
        cues = worker.merge_ocr_rows(rows, 22)
        self.assertEqual(len(cues), 1)
        self.assertFalse(cues[0]["enabled"])
        self.assertIn("水印", cues[0]["reviewNote"])

    def test_post_op_window_and_end_clipping(self):
        self.assertEqual(worker.processing_window(300, 90, 60), (90,60))
        self.assertEqual(worker.processing_window(130, 90, 60), (90,40))
        self.assertEqual(worker.processing_window(300, 90, 0), (90,210))
        for start in [-1, 300, float('nan'), float('inf')]:
            with self.assertRaises(ValueError):
                worker.processing_window(300,start,60)

    def test_subtitles_skip_op_and_rebase_crossing_boundaries(self):
        cues = [{"start":0,"end":80,"text":"OP"}, {"start":89,"end":93,"text":"跨起點"}, {"start":110,"end":115,"text":"正文"}, {"start":149,"end":155,"text":"跨終點"}, {"start":150,"end":160,"text":"範圍外"}]
        self.assertEqual(worker.window_subtitles(cues,90,60), [
            {"start":0,"end":3,"text":"跨起點"}, {"start":20,"end":25,"text":"正文"}, {"start":59,"end":60,"text":"跨終點"}])

    def test_ocr_and_stt_seek_to_op_end(self):
        cfg = {"video":"input.mp4","ffmpeg":"ffmpeg","executable":"helper","ocr":True,"startOffset":90,"duration":60}
        with tempfile.TemporaryDirectory() as folder:
            frames = Path(folder)/'frames-pts'
            frames.mkdir()
            for pts in (0,208): (frames/f'{pts:012d}.jpg').touch()
            with patch('subtitle_ocr.discover'), patch.object(worker, "run", side_effect=[b'','[{"index":0,"text":"正文"},{"index":1,"text":"正文"}]'.encode()]) as run, patch.object(worker, "emit"):
                cues = worker.extract_cues(cfg, Path(folder), {})
                args = run.call_args_list[0].args[0]
                self.assertEqual(args[args.index("-ss")+1], '90')

                self.assertEqual(args[args.index("-t")+1], '60')
                self.assertEqual(cues[0]["start"], 0)
            model = Path(folder)/'models/whisper-small';model.mkdir(parents=True);(model/'model.bin').touch()
            cfg["storage"] = folder
            # Verify seek arguments before loading the optional STT library.
            with patch("model_catalog.resolve",return_value=model), patch.object(worker, "run", side_effect=RuntimeError("stop before model load")) as run, patch.object(worker, "emit"):
                with self.assertRaises(RuntimeError): worker.transcribe(cfg,Path(folder),'ffmpeg')
                args=run.call_args.args[0]
                self.assertEqual(args[args.index("-ss")+1], '90')

    def test_ocr_uses_real_pts_and_does_not_merge_across_blank(self):
        rows = [dict(index=0,time=.015,text='甲'), dict(index=1,time=.223,text='甲'),
                dict(index=2,time=.432,text=''), dict(index=3,time=.640,text='甲'),
                dict(index=4,time=.848,text='乙')]
        cues = worker.merge_ocr_rows(rows, 3, stable=False, interval=.2)
        self.assertEqual([c['start'] for c in cues], [.015,.640,.848])
        self.assertLessEqual(cues[0]['end'], .432)
        self.assertLessEqual(cues[1]['end'], .848)

    def test_auto_op_requires_explicit_opening_at_start(self):
        def meta(title,start=0,end=90):
            return {'chapters':[dict(start_time=start,end_time=end,tags={'title':title})]}
        for title in ('OP','OP 1','Opening','片頭','オープニング'):
            self.assertEqual(worker.opening_end(meta(title)),90)
        for m in (meta('Episode'),meta('Shopping'),meta('OP',60,150),meta('OP',0,900),meta('OP',0,float('nan')),{}):
            self.assertIsNone(worker.opening_end(m))

    def test_batch_failure_does_not_stop_next_video(self):
        def convert(cfg):
            if cfg['video']=='bad.mp4': raise ValueError('bad file')
            worker.emit('等待批准','ok',review='/tmp/good-review.json')
        with patch.object(worker,'convert',side_effect=convert), patch.object(worker,'emit') as events:
            worker.batch_convert({'videos':[dict(id='a',video='bad.mp4'),dict(id='b',video='good.mp4')]})
            statuses=[c.kwargs.get('batchStatus') for c in events.call_args_list]
            self.assertIn('需要處理',statuses)
            self.assertIn('等待校稿',statuses)
            self.assertIs(worker.emit,events)

    def test_drawn_rectangle_accepts_asymmetric_crop_and_rejects_invalid(self):
        cfg={"ocrRect":{"x":0.15,"y":0.84,"width":0.62,"height":0.10}, "ocrColor":"original"}
        self.assertIn("crop=iw*0.62:ih*0.1:iw*0.15:ih*0.84:exact=1", worker.ocr_filter(cfg))
        for region in [{"x":0,"y":0.9,"width":1,"height":0.2}, {"x":float('nan'),"y":0.8,"width":0.5,"height":0.1}, {"x":0.1,"y":0.8,"width":0.4,"height":0}, {"x":0.1}, []]:
            with self.assertRaises(ValueError): worker.ocr_filter({"ocrRect":region})


if __name__ == "__main__":
    unittest.main()
