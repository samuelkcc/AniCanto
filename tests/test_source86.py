import copy,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import primary_source as primary,source_workflow as workflow,worker,normal_mode

class SubtitleOnlyTests(unittest.TestCase):
 def fixture(self,root,revision=None,choice='subtitles-speech'):
  cfg=dict(sourcePolicyRevision=primary.REVISION,sourceAllocationRevision=primary.ALLOCATION_REVISION,sourceWorkflowRevision=revision or workflow.REVISION,sourceWorkflowEffective=choice,sourceContentPriority='subtitles' if choice=='subtitles-speech' else 'speech',translationSource='audio-and-subtitles',subtitleSource='embedded',duration=10,model='m',port=0,targetLanguage='yue',dubLanguages=['yue'],subtitleModes=['yue'])
  worker.atomic_json(root/'subtitle-context.json',[dict(start=0,end=1,text='不要開窗')])
  cues=[dict(start=0,end=1,text='窓を開けて',japanese='窓を開けて',cantonese=''),dict(start=1.05,end=1.2,text='ふ',japanese='ふ',cantonese='錯誤嘅舊補稿'),dict(start=2,end=3,text='こっちへ来て',japanese='こっちへ来て',cantonese='')]
  w=SimpleNamespace(atomic_json=worker.atomic_json,emit=Mock(),ollama_chat=Mock(return_value='{"0":"唔好開窗。"}'),traditional_cantonese=lambda cfg,s:s)
  return cfg,cues,w
 def test_both_short_cry_and_lexical_subtitle_gaps_keep_source_in_every_mode(self):
  for mode in ['performance','balanced','quality']:
   with self.subTest(mode=mode),tempfile.TemporaryDirectory() as d:
    root=Path(d);cfg,cues,w=self.fixture(root);cfg['workMode']=mode;before=[(c['text'],c['japanese'],c['start'],c['end']) for c in cues]
    primary.prepare(w,cfg,root,cues)
    for c in cues[1:]:
     self.assertTrue(c['subtitleContentOnlyGap']);self.assertTrue(c['preserveOriginalSpeech']);self.assertEqual(primary.content(c),'');self.assertEqual(c['cantonese'],'');self.assertNotIn('missingScript',c)
     self.assertEqual(c['originalSpeechReason'],'subtitle-content-only-gap');self.assertNotIn('sourcePrimaryFallback',c)
    self.assertEqual(before,[(c['text'],c['japanese'],c['start'],c['end']) for c in cues]);self.assertEqual(primary.content(cues[0]),'不要開窗')
    report=json.loads((root/'source-policy.json').read_text());self.assertEqual(report['primaryFallbacks'],[]);self.assertEqual(report['preservedSubtitleGaps'],[2,3])
 def test_original_speech_is_not_a_second_translation_source(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cfg,cues,w=self.fixture(root);primary.prepare(w,cfg,root,cues)
   with patch('normal_mode.glossary',return_value=[]):normal_mode.translate(w,cfg,root,cues)
   self.assertEqual(cues[0]['cantonese'],'唔好開窗。');self.assertEqual(cues[1]['cantonese'],'');self.assertEqual(cues[2]['cantonese'],'')
   request=json.loads(w.ollama_chat.call_args.args[2][1]['content']);raw=json.dumps(request,ensure_ascii=False);self.assertNotIn('窓を開けて',raw);self.assertNotIn('こっちへ来て',raw);self.assertNotIn('ふ',raw)
   self.assertIn('ONLY translation content',primary.rules(cfg))
 def test_authored_caption_without_asr_has_explicit_display_clock_not_lost_content(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cfg,cues,w=self.fixture(root);worker.atomic_json(root/'subtitle-context.json',[dict(start=5,end=6,text='你好')]);primary.prepare(w,cfg,root,cues)
   added=[c for c in cues if c.get('subtitleClockFallbackID')];self.assertEqual(len(added),1);self.assertEqual(primary.content(added[0]),'你好');self.assertEqual(added[0]['sourceClockFallback'],'authored-subtitle-display');self.assertEqual(added[0]['japanese'],'');self.assertEqual((added[0]['start'],added[0]['end']),(5,6))
   primary.prepare(w,cfg,root,cues);self.assertEqual(len([c for c in cues if c.get('subtitleClockFallbackID')]),1);self.assertEqual(len(json.loads((root/'cues.json').read_text())),len(cues))
 def test_legacy_v1_and_speech_first_keep_their_frozen_fallback_policy(self):
  for rev,choice in [(workflow.LEGACY_REVISION,'subtitles-speech'),(workflow.REVISION,'speech-subtitles')]:
   with self.subTest(rev=rev,choice=choice),tempfile.TemporaryDirectory() as d:
    root=Path(d);cfg,cues,w=self.fixture(root,rev,choice);primary.prepare(w,cfg,root,cues);self.assertEqual(primary.content(cues[2]),'こっちへ来て');self.assertFalse(cues[2].get('subtitleContentOnlyGap'))
 def test_gap_blank_is_valid_source_preservation_and_not_missing_dubbing(self):
  from dubbing import required_dialogue
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cfg,cues,w=self.fixture(root);primary.prepare(w,cfg,root,cues);cues[0]['cantonese']='唔好開窗。';selected=worker.validate_review(cues,copy.deepcopy(cues),10)
   self.assertEqual(len(selected),3);self.assertEqual([n for n,c in required_dialogue(cfg,selected)],[1])
 def test_manual_take_is_not_rewritten_by_gap_preservation(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cfg,cues,w=self.fixture(root);cues[2].update(editorAudio='manual.wav',cantonese='人工台詞');primary.prepare(w,cfg,root,cues);self.assertEqual(cues[2]['cantonese'],'人工台詞');self.assertEqual(cues[2]['editorAudio'],'manual.wav')

if __name__=='__main__':unittest.main()
