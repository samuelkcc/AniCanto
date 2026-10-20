"""A failed retry must not erase the recording that the user could compare."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Resources'))
import recording_history as history
import dubbing


def audio(path, value):
    with wave.open(str(path), 'wb') as out:
        out.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
        out.writeframes(struct.pack('<h', value) * 2400)


class RecordingHistoryTests(unittest.TestCase):
    def test_decoder_stopped_before_all_clauses_records_only_submitted_excerpt(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);source=root/'fragment.wav';audio(source,100)
            item=dict(reviewIndex=159,text='唔好走！人類，唔好諗逃！')
            saved=history.preserve(root,'drama3','yue',item,source,'generation-limit',generation=dict(submittedText='唔好走！',plannedParts=3,parts=[{}]))
            row=json.loads((saved/'take.json').read_text())
            self.assertEqual(row['text'],item['text'])
            self.assertEqual(row['spokenText'],'唔好走！')
            self.assertFalse(row['automaticallyAccepted'])

    def fixture(self, root):
        output=root/'voice.wav'
        cue=dict(start=1.,end=2.,editorID='cue-a',cantonese='唔該。',speakerId='role-a')
        (root/'review.json').write_text(json.dumps(dict(cues=[cue])))
        output.with_suffix('.failure.json').write_text(json.dumps(dict(error='generation-limit')))
        return output,dict(job=str(root),targetLanguage='yue',items=[dict(output=str(output),reviewIndex=0,text='唔該。',profile=dict(id='role-a'),seed=42)])

    def test_every_failed_version_survives_source_overwrite_and_duplicate_scan(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);output,request=self.fixture(root)
            source=output.with_suffix('.rejected.raw.wav')
            audio(source,100);first=source.read_bytes()
            history.preserve_request(dict(ttsBackend='drama3'),'drama3',request)
            history.preserve_request(dict(ttsBackend='drama3'),'drama3',request)
            self.assertEqual(len(list((root/'recording-history').glob('*/take.json'))),1)
            audio(source,200);second=source.read_bytes()
            history.preserve_request(dict(ttsBackend='drama3'),'drama3',request)
            records=[json.loads(p.read_text()) for p in (root/'recording-history').glob('*/take.json')]
            self.assertEqual(len(records),2)
            self.assertEqual({(p.parent/'audio.wav').read_bytes() for p in (root/'recording-history').glob('*/take.json')},{first,second})
            for row in records:
                self.assertEqual((row['index'],row['editorID'],row['language'],row['engine'],row['text']),(1,'cue-a','yue','drama3','唔該。'))
                self.assertFalse(row['automaticallyAccepted'])

    def test_parent_archives_before_and_after_an_isolated_failed_retry(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);output,request=self.fixture(root)
            source=output.with_suffix('.rejected.raw.wav');audio(source,100)
            def attempt(*args):
                audio(source,300)
                raise RuntimeError('model failed again')
            with patch.object(dubbing,'_run_model_job',side_effect=attempt):
                with self.assertRaisesRegex(RuntimeError,'failed again'):
                    dubbing._model_job(dict(ttsBackend='drama3'),'drama3',request,lambda *a:None)
            self.assertEqual(len(list((root/'recording-history').glob('*/audio.wav'))),2)

    def test_single_line_repair_preserves_original_index_and_clock(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);output,request=self.fixture(root)
            cue=json.loads((root/'review.json').read_text())['cues'][0];cue['reviewIndex']=101
            (root/'review.json').write_text(json.dumps(dict(cues=[cue])))
            request['items'][0]['reviewIndex']=101;audio(output.with_suffix('.rejected.raw.wav'),100)
            history.preserve_request(dict(ttsBackend='drama3'),'drama3',request)
            row=json.loads(next((root/'recording-history').glob('*/take.json')).read_text())
            self.assertEqual((row['index'],row['start'],row['end'],row['editorID']),(102,1.,2.,'cue-a'))

    def test_successful_raw_is_not_mislabeled_and_bad_sidecars_do_not_break_work(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);output,request=self.fixture(root)
            output.with_suffix('.failure.json').unlink()
            audio(output,100);audio(output.with_suffix('.raw.wav'),100)
            output.with_suffix('.health.json').write_text('null')
            output.with_suffix('.generation.json').write_text('[]')
            history.preserve_request(dict(ttsBackend='drama3'),'drama3',request)
            self.assertFalse((root/'recording-history').exists())

    def test_missing_cue_identity_never_borrows_another_lines_recording(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);output,request=self.fixture(root)
            audio(output.with_suffix('.rejected.raw.wav'),100)
            request['items'][0].pop('reviewIndex')
            history.preserve_request(dict(ttsBackend='drama3'),'drama3',request)
            self.assertFalse((root/'recording-history').exists())

    def test_same_audio_in_another_language_remains_a_separate_history(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);output,request=self.fixture(root)
            audio(output.with_suffix('.rejected.raw.wav'),100)
            for language in ['yue','en']:
                request['targetLanguage']=language
                history.preserve_request(dict(ttsBackend='drama3'),'drama3',request)
            rows=[json.loads(p.read_text()) for p in (root/'recording-history').glob('*/take.json')]
            self.assertEqual({row['language'] for row in rows},{'yue','en'})


if __name__=='__main__':
    unittest.main()
