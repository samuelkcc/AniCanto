import json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'windows'),str(ROOT/'Resources')]
from desktop_cleanup import remove
from desktop_state import write
from studio_preview import folder
class ProjectCleanupTests(unittest.TestCase):
    def test_remove_finished_project_keeps_external_movie_and_cleans_owned_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'original.mkv';source.write_bytes(b'original');job=root/'jobs/a';job.mkdir(parents=True)
            final=root/'export.mp4';final.write_bytes(b'final');write(job/'review.json',{});write(job/'report.json',dict(output=str(job/'work.mp4'),exportedOutput=str(final)))
            (job/'work.mp4').write_bytes(b'mixed');(job/'tracks').mkdir();(job/'tracks/intermediate.mp4').write_bytes(b'work')
            request=root/'requests/submitted-x.json';write(request,{})
            attempt=root/'attempts/row/attempt/attempt.json';write(attempt,dict(request=str(request)))
            cache=folder(root,source);write(cache/'status.json',dict(source=str(source)));(cache/'preview.mp4').write_bytes(b'preview')
            other=root/'cache/studio-preview/other';write(other/'status.json',dict(source=str(root/'other.mkv')))
            write(final.with_suffix('.processing-time.json'),dict(output=str(final),excludesPausedTime=True))
            self.assertEqual(remove(root,dict(id='row',video=str(source),review=str(job/'review.json'),output=str(final),request=str(request))),[])
            self.assertFalse(job.exists());self.assertFalse(request.exists());self.assertFalse((root/'attempts/row').exists());self.assertFalse(cache.exists());self.assertTrue(other.exists())
            self.assertEqual(final.read_bytes(),b'final');self.assertEqual(source.read_bytes(),b'original');self.assertFalse(final.with_suffix('.processing-time.json').exists());self.assertFalse((root/'exports').exists())
    def test_waiting_item_without_review_still_removes_attempt_and_request(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'original.mkv';source.touch();request=root/'requests/submitted-x.json';write(request,{})
            write(root/'attempts/row/x/attempt.json',dict(request=str(request)))
            remove(root,dict(id='row',video=str(source),request=str(request)))
            self.assertFalse(request.exists());self.assertFalse((root/'attempts/row').exists());self.assertTrue(source.exists())
    def test_other_project_shared_data_and_user_sidecar_are_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'original.mkv';source.touch();job=root/'jobs/shared';write(job/'review.json',{})
            exported=root/'final.mp4';exported.touch();write(exported.with_suffix('.processing-time.json'),dict(userData=True))
            remove(root,dict(id='a',video=str(source),job=str(job),output=str(exported)),[dict(id='b',video=str(source),job=str(job))])
            self.assertTrue(job.exists());self.assertTrue(exported.with_suffix('.processing-time.json').exists())
if __name__=='__main__':unittest.main()
