"""Primary caption aliases remain valid names; neighbours do not supply names."""
import unittest
import name_evidence,primary_source,script_preflight
class NameEvidenceTests(unittest.TestCase):
 def setUp(self):self.term=dict(japanese='ルフィ',cantonese='路飛',mandarin='路飞',english='Luffy',aliases=['草帽小子'])
 def cue(self,text):return dict(start=0,end=2,cantonese='路飛，快啲走！',japanese='隣の話',requiredNames=[],primarySource=dict(revision=primary_source.REVISION,kind='external',text=text))
 def test_primary_chinese_or_english_alias_is_not_an_invented_name(self):
  for text in ['路飛快走','路飞快走','LUFFY, go!','ルフィ行け','草帽小子快走']:
   with self.subTest(text=text):self.assertTrue(name_evidence.grounded(self.term,text))
 def test_chinese_authored_name_remains_required_during_shortening(self):
  cue=self.cue('路飛快走')
  self.assertEqual(script_preflight.grounded_names(cue,[self.term]),['路飛'])
  self.assertIn('missing-name:路飛',script_preflight.rewrite_conflicts(cue,'快啲走！',[self.term]))
 def test_nearby_caption_is_not_primary_name_evidence(self):
  cue=self.cue('快走');cue['subtitleHint']='路飛快走'
  self.assertEqual(script_preflight.grounded_names(cue,[self.term]),[])
 def test_empty_or_malformed_aliases_are_not_evidence(self):
  self.assertFalse(name_evidence.grounded(dict(aliases=[None,{}]),'Something'))
 def test_mapping_aliases_are_accepted(self):
  self.assertTrue(name_evidence.grounded(dict(aliases=dict(ja=['ルフィ'],en='Luffy')),'Luffy'))

 def test_english_name_does_not_match_inside_another_word(self):
  self.assertFalse(name_evidence.grounded(dict(english='Luffy'),'a fluffy cloud'))
  self.assertFalse(name_evidence.grounded(dict(english='Law'),'a lawyer'))
  self.assertTrue(name_evidence.grounded(dict(english='Law'),'Law, come here!'))
 def test_spaced_full_names_match_without_case_noise(self):
  self.assertTrue(name_evidence.grounded(dict(english='Monkey D Luffy'),'MONKEY D LUFFY is here.'))

class DynamicNameGlossaryTests(unittest.TestCase):
 def glossary(self,root,cues,rows):
  from types import SimpleNamespace
  from unittest.mock import Mock
  import json,normal_mode,worker,repair_permissions
  w=SimpleNamespace(emit=Mock(),traditional_cantonese=lambda cfg,text:text,ollama_chat=Mock(return_value=dict(names=rows)),atomic_json=worker.atomic_json)
  cfg=dict(repairPermissionsRevision=repair_permissions.REVISION,model='test',port=1,sourceLanguage='ja')
  from unittest.mock import patch
  with patch('caption_alignment.glossary',side_effect=lambda *a:w.ollama_chat()):names=normal_mode.glossary(w,cfg,root,cues)
  return names,w,cfg
 def cue(self,text):
  c=dict(start=0,end=1,text='Raw speech',japanese='違う名前',subtitleHint=text,enabled=True)
  primary_source.attach(c,'external',text);return c
 def test_ai_keeps_name_in_primary_chinese_and_records_evidence(self):
  import tempfile
  from pathlib import Path
  with tempfile.TemporaryDirectory() as d:
   names,w,cfg=self.glossary(Path(d),[self.cue('路飛快走')],[dict(source='路飛',cantonese='路飛',english='Luffy')])
   self.assertEqual(names[0]['evidenceIndices'],[1]);self.assertFalse(names[0]['identityCertified']);self.assertEqual(w.ollama_chat.call_count,1)
 def test_ai_cannot_use_japanese_memory_instead_of_primary_caption(self):
  import tempfile
  from pathlib import Path
  with tempfile.TemporaryDirectory() as d:
   names,_,_=self.glossary(Path(d),[self.cue('路飛快走')],[dict(source='ルフィ',cantonese='路飛',english='Luffy')]);self.assertEqual(names,[])
 def test_ai_cannot_pair_a_name_with_an_unrelated_caption_row(self):
  import tempfile
  from pathlib import Path
  with tempfile.TemporaryDirectory() as d:
   names,_,_=self.glossary(Path(d),[self.cue('路飛快走'),self.cue('山治過嚟')],[dict(source='路飛',cantonese='山治',english='Sanji')]);self.assertEqual(names,[])
 def test_same_input_reuses_cached_ai_without_another_call(self):
  import tempfile,normal_mode
  from pathlib import Path
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cues=[self.cue('路飛快走')];names,w,cfg=self.glossary(root,cues,[dict(source='路飛',cantonese='路飛',english='Luffy')])
   self.assertEqual(normal_mode.glossary(w,cfg,root,cues),names);self.assertEqual(w.ollama_chat.call_count,1)

 def test_evidence_indices_keep_real_cue_ids_after_filtering(self):
  import tempfile
  from pathlib import Path
  with tempfile.TemporaryDirectory() as d:
   skipped=self.cue('另一個人');skipped['enabled']=False
   own=self.cue('路飛快走');own['reviewIndex']=17
   names,_,_=self.glossary(Path(d),[skipped,own],[dict(source='路飛',cantonese='路飛',english='Luffy')]);self.assertEqual(names[0]['evidenceIndices'],[18])
