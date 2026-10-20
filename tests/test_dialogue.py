import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import dialogue

class DialogueTests(unittest.TestCase):
    def test_transcription_counters_are_monotonic_and_finish_trailing_silence(self):
        from types import SimpleNamespace
        events=[]
        emit=lambda stage,message,progress,**extra:events.append(extra)
        rows=[SimpleNamespace(end=v) for v in (20,19,35)]
        self.assertEqual(list(dialogue.timed_segments(iter(rows),60,emit)),rows)
        self.assertEqual([e['workCompleted'] for e in events],[0,20,20,35,60])
        self.assertTrue(all(e['workTotal']==60 and e['workID']=='japanese-transcription' for e in events))

    def test_transcription_failure_does_not_report_full_completion(self):
        from types import SimpleNamespace
        def broken():
            yield SimpleNamespace(end=20)
            raise RuntimeError('decoder failed')
        events=[]
        with self.assertRaises(RuntimeError):
            list(dialogue.timed_segments(broken(),60,lambda *a,**kw:events.append(kw)))
        self.assertEqual([e['workCompleted'] for e in events],[0,20])

    def test_grammatical_fragments_join_before_voice_matching_without_using_caption_times(self):
        def cue(a,b,t):return dict(start=a,end=b,japanese=t,text=t,subtitleHint='我今日嚟係想同你講件事')
        r=dialogue.consolidate_fragments([cue(1,3,'今日あなたに'),cue(4.5,7,'話そうと思い'),cue(7,8,'ここへ')])
        self.assertEqual(len(r),1)
        self.assertEqual((r[0]['start'],r[0]['end']),(1,8))
        self.assertEqual(len(r[0]['recognitionParts']),3)
        self.assertEqual(len(dialogue.consolidate_fragments([cue(1,2,'はい。'),cue(2,3,'いいえ。')])),2)

    def test_tiny_recognizer_tail_not_translated_as_separate_sentence(self):
        rows=[dict(words=[self.words(1,3,'やめないよな')]),dict(words=[self.words(3,3.18,'ぁ')])]
        cues=dialogue.build_cues(rows,[dict(start=1,end=3.3)],[],5)
        self.assertEqual(len(cues),1)
        self.assertEqual(cues[0]['japanese'],'やめないよな')
        self.assertGreater(cues[0]['end'],3.18)

    def test_zero_duration_internal_tokens_do_not_delete_name_syllables(self):
        words=[self.words(0,.1,'カ'),self.words(.1,.1,'ズ'),self.words(.1,.1,'キ'),self.words(.1,.8,'です。')]
        cues=dialogue.build_cues([dict(words=words)],[dict(start=0,end=1)],[],2)
        self.assertEqual(cues[0]['japanese'],'カズキです。')
        self.assertEqual(dialogue.build_cues([dict(words=[self.words(1,1,'幻覚')])],[],[],2),[])

    def test_vad_never_cuts_japanese_into_stray_kana(self):
        words=[self.words(1,1.3,'ピ'),self.words(1.4,1.6,'ザ'),self.words(2,2.4,'キャット')]
        cues=dialogue.build_cues([dict(words=words)],[dict(start=1.5,end=2.5)],[],4)
        self.assertEqual(len(cues),1)
        self.assertEqual(cues[0]['japanese'],'ピザキャット')
        self.assertLess(cues[0]['start'],1)
    def test_partial_support_does_not_leave_a_hallucinated_prefix(self):
        cues=dialogue.build_cues([dict(words=[self.words(1,2,'ご視聴'),self.words(2,4,'ありがとうございました')])],[dict(start=.8,end=1.4)],[],5)
        self.assertEqual(cues,[])
    def test_missing_voice_coverage_is_rechecked_without_duplicate_ranges(self):
        spans=[dict(start=0,end=3),dict(start=2,end=5),dict(start=8,end=12)]
        covered=[dict(start=2,end=4),dict(start=9,end=12)]
        self.assertEqual(dialogue.uncovered_spans(spans,covered),[dict(start=0,end=2),dict(start=4,end=5),dict(start=8,end=9)])
    def words(self,a,b,text):
        return dict(start=a,end=b,word=text,probability=.9)
    def test_ocr_variants_do_not_create_or_shorten_speech(self):
        captions=[dict(start=i*.2,end=(i+1)*.2,text=t) for i,t in enumerate([
            '這是黃尾魚比薩，好的，這是雞蛋比薩','好的，這是雞蛋比薩。這是黃尾魚比薩',
            '這是黃尾魚比薩！好的！這是雞蛋比薩'])]
        cues=dialogue.build_cues([dict(words=[self.words(.1,1.5,'こちらはピザです。')])],[dict(start=0,end=2)],captions,3)
        self.assertEqual(len(cues),1)
        self.assertGreater(cues[0]['end']-cues[0]['start'],1.4)
        self.assertEqual(cues[0]['text'],'こちらはピザです。')
        self.assertIn('比薩',cues[0]['subtitleHint'])
    def test_speech_pause_splits_even_if_subtitle_is_unchanged(self):
        cues=dialogue.build_cues([dict(words=[self.words(1,2,'はい。'),self.words(3,4,'ありがとう。')])],
            [dict(start=.9,end=2.1),dict(start=2.9,end=4.1)],[dict(start=0,end=5,text='好的，謝謝。')],5,90)
        self.assertEqual(len(cues),2)
        self.assertLessEqual(cues[0]['deliveryEnd'],cues[1]['start'])
        self.assertEqual(cues[0]['sourceStart'],90+cues[0]['start'])
        self.assertTrue(all(c['timingSource']=='japanese-audio' for c in cues))
    def test_repeated_real_utterance_is_not_deleted(self):
        cues=dialogue.build_cues([dict(words=[self.words(1,2,'はい。'),self.words(3,4,'はい。')])],
            [dict(start=0,end=5)],[],5)
        self.assertEqual(len(cues),2)
    def test_subtitle_alone_never_creates_voice(self):
        self.assertEqual(dialogue.build_cues([],[],[dict(start=0,end=10,text='長時間畫面文字')],10),[])
    def test_no_vad_support_discards_hallucination(self):
        word=dict(self.words(1,2,'ありがとうございます'),probability=.1)
        self.assertEqual(dialogue.build_cues([dict(words=[word])],[],[],5),[])
    def test_confident_cartoon_voice_survives_vad_false_negative(self):
        cues=dialogue.build_cues([dict(words=[self.words(1,2,'やったろ')])],[],[],5)
        self.assertEqual(cues[0]['japanese'],'やったろ')
        self.assertTrue(cues[0]['enabled'])
    def test_delivery_never_overlaps_next_speaker_or_video_end(self):
        cues=dialogue.build_cues([dict(words=[self.words(0,1,'甲')]),dict(words=[self.words(1.05,2,'乙')])],
            [dict(start=0,end=2)],[],2)
        self.assertEqual(cues[0]['deliveryEnd'],cues[1]['start'])
        self.assertLessEqual(cues[-1]['deliveryEnd'],2)
    def test_low_confidence_is_visible(self):
        word=dict(self.words(1,2,'なに？'),probability=.1)
        cue=dialogue.build_cues([dict(words=[word])],[dict(start=0,end=3)],[],3)[0]
        self.assertIn('信心',cue['reviewNote'])
