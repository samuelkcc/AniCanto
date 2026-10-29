import errno,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import export_retry,delivery_policy
class ExportRetryTests(unittest.TestCase):
 def cfg(self):return dict(deliveryPolicyRevision=delivery_policy.REVISION)
 def test_one_transient_encode_failure_retries_without_regeneration(self):
  with tempfile.TemporaryDirectory() as d,patch('video_acceleration.encode',side_effect=[RuntimeError('encoder crashed'),None]) as encode:
   check=Mock(return_value='valid');emit=Mock();self.assertEqual(export_retry.run(self.cfg(),d,['ffmpeg','out.mp4'],Mock(),emit,check),'valid');self.assertEqual(encode.call_count,2);self.assertEqual(check.call_count,1);self.assertEqual(emit.call_count,1)
 def test_mux_validation_failure_also_has_one_retry(self):
  with tempfile.TemporaryDirectory() as d,patch('video_acceleration.encode') as encode:
   check=Mock(side_effect=[RuntimeError('missing subtitle stream'),'valid']);self.assertEqual(export_retry.run(self.cfg(),d,['ffmpeg','out.mp4'],Mock(),Mock(),check),'valid');self.assertEqual(encode.call_count,2)
 def test_terminal_storage_error_is_not_retried(self):
  with tempfile.TemporaryDirectory() as d,patch('video_acceleration.encode',side_effect=OSError(errno.ENOSPC,'disk full')) as encode:
   with self.assertRaises(OSError):export_retry.run(self.cfg(),d,['ffmpeg','out.mp4'],Mock(),Mock(),Mock())
   self.assertEqual(encode.call_count,1)
 def test_resume_after_two_failures_does_not_refill_attempts(self):
  with tempfile.TemporaryDirectory() as d,patch('video_acceleration.encode',side_effect=RuntimeError('transient')) as encode:
   for n in range(2):
    with self.assertRaises(RuntimeError):export_retry.run(self.cfg(),d,['ffmpeg','out.mp4'],Mock(),Mock(),Mock())
   self.assertEqual(encode.call_count,2)
 def test_user_skip_is_never_retried(self):
  from track_control import UserSkipped
  with tempfile.TemporaryDirectory() as d,patch('video_acceleration.encode',side_effect=UserSkipped('skip')) as encode:
   with self.assertRaises(UserSkipped):export_retry.run(self.cfg(),d,['ffmpeg','out.mp4'],Mock(),Mock(),Mock())
   self.assertEqual(encode.call_count,1)
if __name__=='__main__':unittest.main()
