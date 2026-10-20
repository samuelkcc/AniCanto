import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import speakers


class TurnTests(unittest.TestCase):
    def cue(self,a,b,role,text):
        return dict(start=a,end=b,speechStart=a,speechEnd=b,deliveryEnd=b+.1,
                    sourceStart=a+180,sourceEnd=b+180,text=text,japanese=text,speakerId=role,
                    cantonese='',subtitleHint=text,enabled=True)

    def test_whole_speaker_turn_keeps_every_source_part_and_the_original_window(self):
        raw=[self.cue(1,2,'a','甲'),self.cue(2,3,'a','乙'),self.cue(3,4,'b','丙')]
        grouped=speakers.group_turns(raw)
        self.assertEqual(len(grouped),2)
        self.assertEqual(grouped[0]['text'],'甲 乙')
        self.assertEqual((grouped[0]['start'],grouped[0]['end'],grouped[0]['deliveryEnd']),(1,3,3.1))
        self.assertEqual(sum(len(c['sourceParts']) for c in grouped),3)
        self.assertEqual(raw[0]['text'],'甲')

    def test_no_grouping_across_pause_mixed_voices_disabled_line_or_long_turn(self):
        for update in [dict(previousSpeakerSimilarity=.27),dict(start=2.4),dict(enabled=False),dict(speakerNote='同一句可能包含多個聲線'),dict(end=12)]:
            cues=[self.cue(1,2,'a','甲'),dict(self.cue(2,3,'a','乙'),**update)]
            self.assertEqual(len(speakers.group_turns(cues)),2)
