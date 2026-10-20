"""An export audit must distinguish silent PCM from a successfully written WAV."""
import array
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import wave

spec = importlib.util.spec_from_file_location('fast_output_audit', Path(__file__).parents[1]/'scripts/audit_fast_output.py')
audit_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_module)


class FastOutputAuditTests(unittest.TestCase):
    def test_completed_decoder_with_near_silent_pcm_is_reported_and_job_is_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audible, quiet = root/'audible.wav', root/'quiet.wav'
            for path, amplitude in [(audible, 4000), (quiet, 8)]:
                with wave.open(str(path), 'wb') as stream:
                    stream.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
                    stream.writeframes(array.array('h', [amplitude, -amplitude]*8000).tobytes())
            review = dict(config=dict(productionMode='fast', ttsBackend='drama3'), cues=[
                dict(start=i, end=i+1, cantonese=text, japanese='はい')
                for i, text in enumerate(['你好呀', '好呀', ''])])
            timing = [dict(index=i+1, renderedAudio=str(path), renderedSeconds=1,
                           renderedEnd=i+1, rate=rate, skipped=False)
                      for i, (path, rate) in enumerate([(audible, 1), (quiet, 3)])]
            files = {'review.json': review, 'timing.json': timing,
                     'report.json': dict(output=str(root/'output.mp4')),
                     'take.generation.json': dict(status='completed')}
            for name, data in files.items():
                (root/name).write_text(json.dumps(data))
            before = {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in files}
            result = audit_module.audit(root)['tracks'][0]
            self.assertEqual(result['missingScripts'], [3])
            self.assertEqual(result['missingOrNearSilentAudio'], [2, 3])
            self.assertEqual(result['completedDecoders'], 1)
            self.assertEqual(result['compressionCounts']['2'], 1)
            self.assertEqual(result['deadlineViolations'], [])
            self.assertEqual(before, {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in files})

    def test_missing_and_unreadable_takes_do_not_count_as_success(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'not-a-wave.wav'
            path.write_text('not audio')
            self.assertEqual(audit_module.signal(path)['status'], 'unreadable')
            self.assertEqual(audit_module.signal(path.parent/'missing.wav')['status'], 'unreadable')


if __name__ == '__main__':
    unittest.main()
