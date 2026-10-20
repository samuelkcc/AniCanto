import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import multitrack

class MultiTrackTests(unittest.TestCase):
    def test_export_never_overwrites_and_only_exports_mp4(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); source=root/'source';source.mkdir();out=root/'out';out.mkdir()
            video=source/'動畫-AniCanto.mp4';video.write_bytes(b'valid')
            (out/video.name).write_bytes(b'existing')
            srt=source/'yue.srt';srt.write_text('字幕')
            result=multitrack.export_copy(video,{'exportFolder':str(out)},[(srt,'.yue.srt')])
            self.assertEqual(result.name,'動畫-AniCanto (1).mp4')
            self.assertEqual((out/video.name).read_bytes(),b'existing')
            self.assertEqual(result.read_bytes(),b'valid')
            self.assertEqual(sorted(p.suffix for p in out.iterdir()),['.mp4','.mp4'])
            self.assertEqual(srt.read_text(),'字幕')
    def test_reject_unknown_engine(self):
        with self.assertRaises(ValueError):multitrack.selected({'selectedEngines':['../../x']})
        self.assertEqual(multitrack.selected({'selectedEngines':['cosyvoice3','cosyvoice3','gpt-sovits']}),['cosyvoice3','gpt-sovits'])
    def test_english_resume_and_reject_empty(self):
        with tempfile.TemporaryDirectory() as d:
            w=SimpleNamespace(emit=Mock(),ollama_chat=Mock(return_value='{"0":"Let’s go!"}'),atomic_json=lambda p,obj:p.write_text(json.dumps(obj)))
            cfg={'model':'qwen3:14b','port':1};cues=[{'cantonese':'出發啦！'}]
            self.assertEqual(multitrack.english_lines(w,cfg,Path(d),cues),['Let’s go!'])
            multitrack.english_lines(w,cfg,Path(d),cues)
            self.assertEqual(w.ollama_chat.call_count,1)
            w.ollama_chat.return_value='{"0":""}'
            with self.assertRaises(ValueError):multitrack.english_lines(w,cfg,Path(d),[{'cantonese':'另一句'}])
    def test_scream_does_not_call_model_and_invalid_json_splits(self):
        with tempfile.TemporaryDirectory() as d:
            w=SimpleNamespace(emit=Mock(),ollama_chat=Mock(side_effect=[RuntimeError('HTTP 422'),'{"1":"Go!"}','{"2":"Wait!"}']),atomic_json=lambda p,obj:p.write_text(json.dumps(obj)))
            cues=[{'cantonese':'啊'*30+'！'},{'cantonese':'走啦！'},{'cantonese':'等陣！'}]
            self.assertEqual(multitrack.english_lines(w,{'model':'test','port':1},Path(d),cues),['Ah!','Go!','Wait!'])
            self.assertEqual(w.ollama_chat.call_count,3)
            multitrack.english_lines(w,{'model':'test','port':1},Path(d),cues)
            self.assertEqual(w.ollama_chat.call_count,3)
    def test_partial_good_rows_saved_and_no_unbounded_retry(self):
        with tempfile.TemporaryDirectory() as d:
            w=SimpleNamespace(emit=Mock(),ollama_chat=Mock(side_effect=['{"0":"Go!","1":""}','{"1":""}']),atomic_json=lambda p,obj:p.write_text(json.dumps(obj)))
            with self.assertRaisesRegex(ValueError,'第 2 句'):
                multitrack.english_lines(w,{'model':'test','port':1},Path(d),[{'cantonese':'走啦'},{'cantonese':'你好'}])
            self.assertEqual(w.ollama_chat.call_count,2)
            self.assertEqual(json.loads(next(Path(d).glob('english-*.json')).read_text()),{'0':'Go!'})
