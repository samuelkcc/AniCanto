"""Verify ordered operation states on different final tutorial clocks."""
import importlib.util
from pathlib import Path
import unittest
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'mobile/DemoFilm'))

SPEC=importlib.util.spec_from_file_location('tutorial_sequence',Path(__file__).resolve().parents[1]/'mobile/DemoFilm/tutorial_sequence.py')
MOD=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(MOD)

class TutorialSequence(unittest.TestCase):
    def test_all_steps_survive_different_shortened_clocks(self):
        for frames,count in [(176,5),(183,5),(214,3),(96,3),(241,4)]:
            actual=[MOD.active_step(i/frames,count) for i in range(frames)]
            changes=[v for i,v in enumerate(actual) if i==0 or actual[i-1]!=v]
            self.assertEqual(changes,list(range(count)))
            self.assertEqual(actual[0],0);self.assertEqual(actual[-1],count-1)

    def test_every_visible_control_is_required_and_no_skip_list_is_allowed(self):
        from tutorial_lessons import LESSONS
        self.assertEqual(MOD.expected_steps({'id':'reading-external'}),[0,1,2])
        self.assertEqual(LESSONS['reading-external']['controls'],['外掛字幕','字幕語言／版本','匯入字幕檔'])
        self.assertEqual(LESSONS['basic-voice']['controls'],['聲音與語言','香港廣東話','配音模型'])
        for name,spec in LESSONS.items():
            expected=MOD.expected_steps({'id':name})
            self.assertEqual(expected,list(range(len(spec['controls']))))
            actual=[MOD.active_step(i/239,len(expected))for i in range(240)]
            self.assertEqual([n for i,n in enumerate(actual)if i==0 or n!=actual[i-1]],expected)
        with self.assertRaises(ValueError):MOD.expected_steps({'id':'undefined-lesson'})

    def test_mapped_caption_clock_keeps_all_chapters(self):
        scenes=[{'id':'first'},{'id':'second'},{'id':'third'}]
        windows=MOD.scene_windows([(.35,2,'A'),(3.35,5,'B'),(6.35,8,'C')],scenes,216)
        self.assertEqual([(a,b)for _,a,b in windows],[(0,72),(72,144),(144,216)])
        with self.assertRaises(ValueError):MOD.scene_windows([(.35,1,'A')],scenes,216)

    def test_diagrams_start_at_input_and_never_activate_two_steps(self):
        for panel in ['reading-welcome','reading-recognize','reading-translate']:
            self.assertEqual(MOD.expected_steps({'id':'different-authored-scene','lesson':'basic-welcome' if panel=='welcome' else panel}),[0,1,2])
        self.assertEqual(MOD.active_step(0,3),0);self.assertEqual(MOD.active_step(.5,3),1);self.assertEqual(MOD.active_step(1,3),2)
        with self.assertRaises(ValueError):MOD.active_step(float('nan'),3)
        with self.assertRaises(ValueError):MOD.active_step(.5,0)

if __name__=='__main__':unittest.main()
