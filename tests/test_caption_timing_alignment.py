import copy,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import caption_timing_alignment as alignment,worker

class CaptionTimingAuditTests(unittest.TestCase):
 def test_whole_caption_in_short_utterance_is_logged_without_unverified_rewrite(self):
  caption=dict(id='shared',start=0.,end=3.,text='资格，你也要认证吗？')
  cues=[dict(start=0.,end=1.,speechStart=0.,speechEnd=1.,japanese='資格',cantonese='資格？連你都要資格認證嗎？',speakerId='a',captionRecords=[caption]),dict(start=1.,end=3.,japanese='君も資格が必要なの',cantonese='你要？',speakerId='b',captionRecords=[caption])]
  before=copy.deepcopy(cues);w=SimpleNamespace(atomic_json=worker.atomic_json,emit=Mock(),ollama_chat=Mock())
  with tempfile.TemporaryDirectory() as temp:
   rows=alignment.audit(w,{},temp,cues)
   self.assertEqual([r['index'] for r in rows],[1]);self.assertGreater(rows[0]['charactersPerSecond'],10)
   self.assertEqual(rows[0]['captions'],[caption]);self.assertEqual(cues,before);w.ollama_chat.assert_not_called()
   self.assertEqual(json.loads((Path(temp)/'caption-timing-audit.json').read_text())['status'],'allocation-warning')
 def test_short_reaction_healthy_script_and_manual_editor_text_are_not_automatically_flagged(self):
  cues=[dict(start=0.,end=1.,japanese='はい',cantonese='係。'),dict(start=1.,end=4.,japanese='君も資格が必要なの',cantonese='連你都要資格？'),dict(start=4.,end=5.,japanese='資格',cantonese='手動確認過嘅完整長對白唔可以自動改動',editorID='manual')]
  self.assertEqual(alignment.suspects(cues),[])

if __name__=='__main__':unittest.main()
