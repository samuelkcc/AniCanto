import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import opening

class OpeningTests(unittest.TestCase):
    def test_optional_classifier_failure_keeps_verified_chapter_and_does_not_cache_success(self):
        import tempfile
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as directory:
            video=Path(directory)/'demo.mkv';video.touch()
            cfg=dict(video=str(video),storage=directory,ffmpeg='ffmpeg',executable='helper')
            meta={'format':{'duration':'1400'},'chapters':[{'start_time':'0','end_time':'90','tags':{'title':'OP'}}]}
            def run(args):
                if '--classify-opening' in args:raise RuntimeError('Classifier unavailable')
                return b''
            emit=Mock();found=opening.detect(cfg,meta,run,emit)
            self.assertEqual([r['kind'] for r in found],['OP'])
            self.assertEqual(cfg['openingDetectionWarnings'][0]['kind'],'ED')
            self.assertEqual(len(list(Path(directory).glob('openings/*/result.json'))),0)
            self.assertEqual(len(list(Path(directory).glob('openings/*/classification-errors.json'))),1)
            self.assertEqual(emit.call_args.kwargs['warningCode'],'opening-classifier-unavailable')
    def rows(self, singing=.9, speech=.05):
        return [dict(start=i*1.5,duration=3,music=.95,singing=singing,speech=speech) for i in range(59)]
    def test_music_alone_and_spoken_background_never_skip_dialogue(self):
        self.assertEqual(opening.candidates(self.rows(singing=0)),[])
        self.assertEqual(opening.candidates(self.rows(speech=.8)),[])
    def test_sustained_song_and_short_sting(self):
        song=opening.candidates(self.rows())
        self.assertEqual((song[0]['start'],song[0]['end']),(0,90))
        self.assertEqual(opening.candidates(self.rows()[:10]),[])
    def test_ranges_intersect_selected_window_without_changing_source_clock(self):
        cfg=dict(startOffset=60,duration=60,opRanges=[dict(start=0,end=90)])
        self.assertEqual(opening.local_ranges(cfg),[dict(start=0,end=30)])
        self.assertTrue(opening.excludes(dict(start=5,end=8),opening.local_ranges(cfg)))
        self.assertFalse(opening.excludes(dict(start=35,end=38),opening.local_ranges(cfg)))
    def test_song_with_brief_spoken_lyrics_remains_one_range(self):
        rows=self.rows()
        for r in rows:
            if 15<=r['start']<24:r['speech']=.52;r['singing']=.1
        found=opening.candidates(rows)
        self.assertEqual((found[0]['start'],found[0]['end']),(0,90))
    def test_chapters_keep_both_opening_and_ending(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            video=Path(directory)/'video.mkv';video.touch()
            cfg=dict(video=str(video),storage=directory)
            meta={'format':{'duration':'1400'},'chapters':[{'start_time':'0','end_time':'140','tags':{'title':'OP'}},{'start_time':'1250','end_time':'1340','tags':{'title':'ED'}}]}
            def unexpected(*args):self.fail('Explicit OP and ED chapters need no classifier')
            found=opening.detect(cfg,meta,unexpected,unexpected)
            self.assertEqual([r['kind'] for r in found],['OP','ED'])
            self.assertEqual(opening.local_ranges(dict(duration=200,startOffset=1200,opRanges=found)),[dict(start=50,end=140)])

    def test_translate_keeps_dialogue_even_inside_false_positive_song_range(self):
        cfg=dict(duration=1400,autoSkipOP=True,translateOPED=True,opRanges=[dict(start=0,end=90),dict(start=1280,end=1370)])
        self.assertEqual(len(opening.detected_local_ranges(cfg)),2)
        self.assertEqual(opening.local_ranges(cfg),[])
        self.assertFalse(opening.excludes(dict(start=15,end=24),opening.local_ranges(cfg)))

    def test_translation_does_not_jump_sample_past_opening(self):
        from unittest.mock import patch,Mock
        for translate,expected in ((False,90),(True,0)):
            cfg=dict(autoSkipOP=True,translateOPED=translate,limit=60,startOffset=0)
            with patch.object(opening,'detect',return_value=[dict(start=0,end=90,kind='OP')]):
                opening.prepare(cfg,{},Mock(),Mock())
            self.assertEqual(cfg['startOffset'],expected)

    def test_disabling_detection_discards_saved_ranges(self):
        from unittest.mock import Mock
        cfg=dict(autoSkipOP=False,duration=100,opRanges=[dict(start=0,end=90)])
        self.assertEqual(opening.local_ranges(cfg),[])
        opening.prepare(cfg,{},Mock(),Mock())
        self.assertNotIn('opRanges',cfg)

    def test_translate_subtracts_only_detected_ranges_from_caption_preservation(self):
        cfg=dict(duration=100,startOffset=60,autoSkipOP=True,translateOPED=True,
                 opRanges=[dict(start=70,end=90),dict(start=140,end=150)],
                 _captionPreserveRanges=[dict(start=0,end=100)])
        self.assertEqual(opening.local_ranges(cfg),[dict(start=0,end=10),dict(start=30,end=80),dict(start=90,end=100)])

    def test_op_dialogue_without_chinese_caption_can_translate_but_body_cannot(self):
        from source_evidence import apply_caption_policy
        captions=[dict(id='body',start=100,end=110,text='正文字幕')]
        cfg=dict(duration=200,autoSkipOP=True,translateOPED=True,opRanges=[dict(start=0,end=90)])
        cues=[dict(start=15,end=18,japanese='今から出発する',enabled=True),
              dict(start=95,end=98,japanese='出発する',enabled=True),
              dict(start=40,end=43,japanese='未来へ行こう',enabled=False)]
        policy=apply_caption_policy(cfg,captions,cues)
        self.assertTrue(cues[0]['enabled']);self.assertTrue(cues[0]['openingTranslation'])
        self.assertFalse(cues[1]['enabled']);self.assertFalse(cues[2]['enabled'])
        self.assertEqual(policy['preservedRanges'],[dict(start=90,end=100),dict(start=110,end=200)])

    def test_changing_policy_restores_only_automatically_disabled_cue(self):
        from source_evidence import apply_caption_policy
        cfg=dict(duration=200,autoSkipOP=True,opRanges=[dict(start=0,end=90)])
        cues=[dict(start=15,end=18,japanese='今から出発する',enabled=True),dict(start=20,end=23,japanese='未来へ行こう',enabled=False)]
        captions=[dict(start=100,end=110,text='正文字幕')]
        apply_caption_policy(cfg,captions,cues)
        self.assertFalse(cues[0]['enabled'])
        cfg['translateOPED']=True
        apply_caption_policy(cfg,captions,cues)
        self.assertTrue(cues[0]['enabled']);self.assertFalse(cues[1]['enabled'])
