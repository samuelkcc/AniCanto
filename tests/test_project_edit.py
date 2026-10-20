import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import project_edit as edit
import worker


def fixture():
    review=dict(config=dict(duration=8,video='/test/movie.mkv'),meta=dict(streams=[]),cues=[dict(start=1,end=3,text='原文',cantonese='完整台詞',speechStart=1.1,speechEnd=2.9,deliveryPlan=[dict(start=1,end=3,text='完整台詞')])])
    row=dict(id='a',sources=[0],start=1,end=3,captionStart=1,captionEnd=3,text='完整台詞',speakerId='role',take=42,rate=1,trimStart=0,trimEnd=0)
    return review,dict(id='revision-1',segments=[row],clips=[dict(start=0,end=8)])


class EditTests(unittest.TestCase):
    def test_accepted_history_is_explicit_and_never_inherited_from_old_render(self):
        review,draft=fixture();review['cues'][0].update(editorAudio='/old.wav',userAcceptedRecording='old')
        row=edit.materialize(review,draft)[0];self.assertNotIn('userAcceptedRecording',row);self.assertNotIn('editorAudio',row)
        draft['segments'][0].update(audioTake='/new.wav',audioAcceptedHistoryID='new')
        row=edit.materialize(review,draft)[0];self.assertEqual((row['editorAudio'],row['userAcceptedRecording']),('/new.wav','new'))

    def test_source_is_immutable_and_unchanged_evidence_is_preserved(self):
        review,draft=fixture();before=copy.deepcopy(review)
        result=edit.materialize(review,draft)
        self.assertEqual(review,before);self.assertEqual(result[0]['speechStart'],1.1)
        self.assertEqual(result[0]['editorID'],'a')

    def test_changed_text_invalidates_old_delivery_plan(self):
        review,draft=fixture();draft['segments'][0]['text']='新台詞'
        result=edit.materialize(review,draft)[0]
        self.assertNotIn('deliveryPlan',result);self.assertEqual(result['speechStart'],1)

    def test_split_has_explicit_source_provenance(self):
        review,draft=fixture();right=copy.deepcopy(draft['segments'][0])
        draft['segments'][0].update(end=2,captionEnd=2,text='完整')
        right.update(id='b',start=2,captionStart=2,text='台詞');draft['segments'].append(right)
        result=edit.materialize(review,draft)
        self.assertEqual(''.join(c['cantonese'] for c in result),'完整台詞')
        self.assertEqual([c['editorSources'] for c in result],[[0],[0]])
        self.assertEqual(worker.validate_review(result,result,8),[dict(c,reviewIndex=i) for i,c in enumerate(result)])

    def test_invalid_intervals_and_rates_are_rejected(self):
        for key,value in [('start',float('nan')),('end',0),('end',9),('rate',3),('trimStart',-1),('captionEnd',0)]:
            with self.subTest(key=key,value=value):
                review,draft=fixture();draft['segments'][0][key]=value
                with self.assertRaises(ValueError):edit.materialize(review,draft)

    def test_duplicate_identity_or_missing_source_rejected(self):
        review,draft=fixture();draft['segments']*=2
        with self.assertRaises(ValueError):edit.materialize(review,draft)
        review,draft=fixture();draft['segments'][0]['sources']=[100]
        with self.assertRaises(ValueError):edit.materialize(review,draft)

    def test_display_text_independent_of_spoken_text(self):
        review,draft=fixture();draft['segments'][0]['captionText']='字幕'
        row=edit.materialize(review,draft)[0]
        self.assertEqual(row['cantonese'],'完整台詞');self.assertEqual(row['captionText'],'字幕')

    def test_ripple_delete_reorders_captions(self):
        draft=dict(clips=[dict(start=0,end=2),dict(start=2,end=4,enabled=False,ripple=True),dict(start=4,end=6)])
        spans=edit.spans_for(draft,6)
        self.assertEqual([s['outputStart'] for s in spans],[0,2])
        result=edit.map_captions([dict(start=1,end=5,text='跨界')],spans)
        self.assertEqual([(r['start'],r['end']) for r in result],[(1,2),(2,3)])

    def test_blank_keeps_time_without_subtitles(self):
        spans=edit.spans_for(dict(clips=[dict(start=0,end=2,enabled=False,ripple=False),dict(start=2,end=4)]),4)
        self.assertEqual(spans[1]['outputStart'],2)
        result=edit.map_captions([dict(start=0,end=3,text='字幕')],spans)
        self.assertEqual([(r['start'],r['end']) for r in result],[(2,3)])

    def test_clip_reorder_uses_output_coordinates(self):
        spans=edit.spans_for(dict(clips=[dict(start=4,end=6),dict(start=0,end=2)]),6)
        result=edit.map_captions([dict(start=0,end=1,text='先'),dict(start=4,end=5,text='後')],spans)
        self.assertEqual([r['text'] for r in result],['後','先'])

    def test_empty_edit_rejected(self):
        with self.assertRaises(ValueError):edit.spans_for(dict(clips=[dict(start=0,end=1,enabled=False)]),1)

    def test_cache_copies_raw_takes_not_reports_or_mixed_audio(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'source';source.mkdir();target=root/'cache'
            for name in ('cosyvoice3-abc.wav','cantonese.wav','report.json','cosyvoice3-dead.rejected.wav'):(source/name).write_bytes(b'old')
            edit.seed_cache(source,target)
            self.assertEqual([p.name for p in target.iterdir()],['cosyvoice3-abc.wav'])
            (target/'cosyvoice3-abc.wav').write_bytes(b'new')
            self.assertEqual((source/'cosyvoice3-abc.wav').read_bytes(),b'old')

    def test_render_failure_preserves_source_review_and_existing_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);review,draft=fixture();review['config']['video']=str(root/'source.mp4');(root/'source.mp4').write_bytes(b'source')
            (root/'review.json').write_text(json.dumps(review));before=(root/'review.json').read_bytes()
            (root/'movie-AniCanto.mp4').write_bytes(b'previous')
            draft['review']=str(root/'review.json');submission=root/'submission.json';submission.write_text(json.dumps(draft))
            with patch.object(worker,'render_review',side_effect=RuntimeError('failed')):
                with self.assertRaises(RuntimeError):edit.render(worker,dict(submission=str(submission)))
            self.assertEqual((root/'review.json').read_bytes(),before)
            self.assertEqual((root/'movie-AniCanto.mp4').read_bytes(),b'previous')
            self.assertEqual(json.loads((root/'versions/revision-1/version.json').read_text())['status'],'failed')

    def test_take_is_scoped_to_its_voice_engine(self):
        for engine, expected in [('cosyvoice3',True),('gpt-sovits',False)]:
            with self.subTest(engine=engine),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);review,draft=fixture()
                cues=edit.materialize(review,draft)
                cues[0].update(editorAudio='/take.wav',editorAudioBackend='cosyvoice3',editorTrimStart=.2,editorTrimEnd=.1)
                review.update(cues=cues);review['config'].update(editorRender=True,ttsBackend=engine)
                (root/'review.json').write_text(json.dumps(review));(root/'cues.json').write_text(json.dumps(cues))
                def capture(cfg,job,selected):
                    self.assertEqual('editorAudio' in selected[0],expected)
                    if not expected:self.assertEqual(selected[0]['editorTrimStart'],0)
                    raise RuntimeError('captured before audio generation')
                with patch.object(worker,'synthesize',side_effect=capture):
                    with self.assertRaisesRegex(RuntimeError,'captured'):
                        worker.render_review(dict(review=str(root/'review.json'),lockScript=True))

    def test_quality_flags_follow_output_time_after_cut(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            report=dict(rows=[dict(index=3,audibleStart=4.5,audibleEnd=5.5,text='word')],contentReviewIndices=[3],timingReviewIndices=[])
            (root/'validation.json').write_text(json.dumps(report))
            spans=edit.spans_for(dict(clips=[dict(start=4,end=6)]),8)
            edit.remap_reports(worker,root,spans)
            result=json.loads((root/'validation.json').read_text())
            self.assertEqual(result['rows'][0]['audibleStart'],.5)
            self.assertEqual(result['rows'][0]['sourceIndex'],3)
            self.assertEqual(result['contentReviewIndices'],[1])
            self.assertEqual(json.loads((root/'validation-source.json').read_text()),report)

    def test_failed_take_maps_planned_time_without_inventing_audible_time(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            report=dict(rows=[dict(index=1,skipped=True,requiresTimingReview=True)],timingReviewIndices=[1])
            (root/'validation.json').write_text(json.dumps(report))
            (root/'review.json').write_text(json.dumps(dict(cues=[dict(start=4.5,end=5.5)])))
            edit.remap_reports(worker,root,edit.spans_for(dict(clips=[dict(start=4,end=6)]),8))
            result=json.loads((root/'validation.json').read_text())
            self.assertEqual(result['rows'][0]['plannedStart'],.5)
            self.assertNotIn('audibleStart',result['rows'][0]);self.assertTrue(result['rows'][0]['skipped'])
            self.assertEqual(result['timingReviewIndices'],[1])

    def test_failed_take_without_source_stays_an_explicit_unmapped_issue(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);row=dict(index=1,skipped=True)
            (root/'validation.json').write_text(json.dumps(dict(rows=[row])))
            edit.remap_reports(worker,root,[dict(start=0,end=3,outputStart=0,blank=False)])
            result=json.loads((root/'validation.json').read_text())
            self.assertEqual(result['unmappedIssues'],[row]);self.assertEqual(result['rows'],[])

if __name__=='__main__':unittest.main()
