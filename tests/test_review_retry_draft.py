"""A saved review must affect the targeted repair request without rerunning the film."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'Resources'), str(ROOT / 'windows')]
sys.path.insert(0, str(ROOT / 'studio'))
from desktop_state import editor_draft
from review_choices import apply
from review_retry import submission
from backend import Studio


class ReviewRetryDraftTests(unittest.TestCase):
    def test_saved_choice_and_script_edit_are_carried_into_retry(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job = root / 'jobs' / 'film'
            track = job / 'tracks' / 'yue'
            track.mkdir(parents=True)
            review_path = job / 'review.json'
            review = dict(config=dict(productionMode='normal', duration=8, video=str(root / 'film.mp4'),
                                      ttsBackend='drama3', selectedEngines=['drama3'], dubLanguages=['yue']),
                          cues=[dict(start=0, end=2, text='一', cantonese='第一句'),
                                dict(start=3, end=5, text='二', cantonese='第二句')])
            review_path.write_text(json.dumps(review))
            (job / 'report.json').write_text(json.dumps(dict(tracks=[dict(engine='drama3', language='yue', report=str(track / 'report.json'))])))
            (track / 'timing.json').write_text(json.dumps([]))
            snapshot = dict(issues=[dict(index=1, language='yue', engine='drama3', status='unresolved')])
            draft = editor_draft(review_path, review, review['config'])
            default = submission(root, review_path, snapshot, saved_draft=draft)['automaticReviewRetry']
            self.assertEqual(default['targets']['yue:drama3'], [1])

            draft['segments'][0]['reviewDecisions'] = {
                'yue:drama3': dict(action='original', engine='drama3', language='yue',
                                   text='第一句', acceptedByUser=True)}
            draft['segments'][1]['text'] = '改好嘅第二句'
            changed = submission(root, review_path, snapshot, saved_draft=draft)['automaticReviewRetry']
            self.assertEqual(changed['targets']['yue:drama3'], [2])
            self.assertEqual(changed['submittedCues'][1]['cantonese'], '改好嘅第二句')
            selected = apply(changed['submittedCues'],
                             dict(_reviewRetry=changed, _editorSourceRoot=str(job)), 'drama3', 'yue')
            self.assertTrue(selected[0]['preserveOriginalSpeech'])

    def test_affected_references_retry_only_requested_tracks_and_protect_manual_choices(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);job=root/'jobs/film';track=job/'tracks/yue';track.mkdir(parents=True)
            review_path=job/'review.json';cfg=dict(productionMode='normal',duration=6,video=str(root/'film.mp4'),ttsBackend='drama3',selectedEngines=['drama3'],dubLanguages=['yue'],voiceProfiles=[dict(id='R01',reference='old.wav')])
            review=dict(config=cfg,cues=[dict(start=0,end=2,text='一',cantonese='第一句',speakerId='R01'),dict(start=3,end=5,text='二',cantonese='第二句',speakerId='R02')]);review_path.write_text(json.dumps(review))
            (job/'report.json').write_text(json.dumps(dict(tracks=[dict(engine='drama3',language='yue',report=str(track/'report.json'))])))
            (track/'timing.json').write_text('[]');draft=editor_draft(review_path,review,cfg);draft['settings']['voiceProfiles'][0]['reference']='new.wav'
            snapshot=dict(issues=[dict(index=2,language='yue',engine='drama3',triage='checked')],staleRecordings=[dict(index=1,language='yue',engine='drama3',protected=False)])
            request=submission(root,review_path,snapshot,saved_draft=draft)
            self.assertEqual(request['automaticReviewRetry']['targets'],{'yue:drama3':[1]})
            self.assertEqual(request['settings']['voiceProfiles'][0]['reference'],'new.wav')
            self.assertEqual(json.loads(review_path.read_text())['config']['voiceProfiles'][0]['reference'],'old.wav')
            snapshot['staleRecordings'][0]['protected']=True
            with self.assertRaisesRegex(ValueError,'no reported'):submission(root,review_path,snapshot,saved_draft=draft)

    def test_split_line_requires_editorial_version(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job = root / 'jobs' / 'film'
            track = job / 'tracks' / 'yue'
            track.mkdir(parents=True)
            review_path = job / 'review.json'
            review = dict(config=dict(productionMode='normal', duration=8, video=str(root / 'film.mp4'),
                                      ttsBackend='drama3', selectedEngines=['drama3'], dubLanguages=['yue']),
                          cues=[dict(start=0, end=2, text='一', cantonese='第一句')])
            review_path.write_text(json.dumps(review))
            (job / 'report.json').write_text(json.dumps(dict(tracks=[dict(engine='drama3', language='yue', report=str(track / 'report.json'))])))
            (track / 'timing.json').write_text('[]')
            draft = editor_draft(review_path, review, review['config'])
            draft['segments'][0]['sources'] = []
            with self.assertRaises(ValueError):submission(root, review_path,
                dict(issues=[dict(index=1, language='yue', engine='drama3', status='unresolved')]),
                saved_draft=draft)

    def test_snapshot_marks_saved_choice_applied_only_by_matching_export(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            app = Studio(root, ROOT / 'Resources', platform='darwin')
            video = root / 'film.mp4'
            video.write_bytes(b'fixture')
            app.store.add([str(video)])
            row = app.store.row()
            job = root / 'jobs' / 'film'
            job.mkdir(parents=True)
            review_path = job / 'review.json'
            review = dict(config=dict(productionMode='normal', duration=5, video=str(video),
                                      ttsBackend='drama3', selectedEngines=['drama3'], dubLanguages=['yue']),
                          cues=[dict(start=0, end=2, text='一', cantonese='第一句')])
            review_path.write_text(json.dumps(review))
            draft = editor_draft(review_path, review, review['config'])
            decision = dict(action='original', engine='drama3', language='yue',
                            text='第一句', acceptedByUser=True)
            draft['segments'][0]['reviewDecisions'] = {'yue:drama3': decision}
            (job / 'editor-draft-studio.json').write_text(json.dumps(draft))
            output = root / 'new-version.mp4'
            output.write_bytes(b'fixture')
            row.update(review=str(review_path), job=str(job), output=str(output), status='complete')
            app.store.save()
            self.assertFalse(app.dispatch('snapshot', dict(id=row['id']))['reviewState']['userChoicesApplied'])
            version = job / 'versions' / 'one'
            version.mkdir(parents=True)
            (version / 'version.json').write_text(json.dumps(dict(status='complete', output=str(output))))
            (version / 'review.json').write_text(json.dumps(dict(review, cues=[dict(review['cues'][0],
                editorDecisions={'yue:drama3': decision})])))
            self.assertTrue(app.dispatch('snapshot', dict(id=row['id']))['reviewState']['userChoicesApplied'])


if __name__ == '__main__':
    unittest.main()
