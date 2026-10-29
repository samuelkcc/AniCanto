import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import worker,script_fit as sf,source_mora

CFG=dict(port=1,model='local',sourceMatchedScriptRevision=source_mora.REVISION)

class ScriptFitTests(unittest.TestCase):
 def cue(self):
  return dict(start=0,end=1.3,speechStart=.1,speechEnd=1.22,text='今すぐ次の目標へ',japanese='今すぐ次の目標へ',cantonese='即刻去下一個目標啦！',requiredNames=[],subtitleHint='')
 def test_other_mode_never_calls_model(self):
  with tempfile.TemporaryDirectory() as d,patch.object(worker,'ollama_chat') as model:
   self.assertEqual(sf.fit(worker,dict(CFG,sourceMatchedScriptRevision='other'),Path(d),[self.cue()],lambda *a:None),[])
   model.assert_not_called()
 def test_locked_script_is_never_rewritten(self):
  with tempfile.TemporaryDirectory() as d,patch.object(worker,'ollama_chat') as model:
   cue=self.cue()
   self.assertEqual(sf.fit(worker,dict(CFG,scriptLocked=True),Path(d),[cue],lambda *a:None),[])
   model.assert_not_called();self.assertEqual(cue['cantonese'],'即刻去下一個目標啦！')
 def test_line_that_fits_is_not_sent(self):
  with tempfile.TemporaryDirectory() as d,patch.object(worker,'ollama_chat') as model:
   cue=self.cue();cue['cantonese']='即刻去啦'
   self.assertEqual(sf.fit(worker,dict(CFG),Path(d),[cue],lambda *a:None),[])
   model.assert_not_called();self.assertFalse((Path(d)/'script-fit.json').exists())
 def test_dense_line_is_shortened_once_and_audited(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);cue=self.cue()
   with patch.object(worker,'ollama_chat',side_effect=[json.dumps({'0':'即刻去啦'})]):
    rows=sf.fit(worker,dict(CFG),job,[cue],lambda *a:None)
   self.assertEqual(cue['cantonese'],'即刻去啦');self.assertEqual(cue['originalCantonese'],'即刻去下一個目標啦！')
   self.assertEqual(cue['captionText'],'即刻去啦')
   self.assertEqual(rows[0]['accepted'],True);self.assertEqual(rows[0]['targetCharacters'],5)
   self.assertEqual(rows[0]['windowSeconds'],1.12);self.assertEqual(rows[0]['stillOverWindow'],False)
   self.assertEqual(json.loads((job/'cues.json').read_text())[0]['cantonese'],'即刻去啦')
   # A completed line is not re-checked, so a resume spends no extra model time.
   with patch.object(worker,'ollama_chat') as model:
    self.assertEqual(sf.fit(worker,dict(CFG),job,[cue],lambda *a:None),[]);model.assert_not_called()
 def test_grounded_name_cannot_be_dropped(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);(job/'scene-glossary.json').write_text(json.dumps([dict(japanese='ボビン',cantonese='波賓',kind='person',caption_evidence='波賓')]))
   cue=dict(start=240,end=243,speechStart=240.4,speechEnd=242.56,text='ボビンは懸賞金が一億です',japanese='ボビンは懸賞金が一億です',cantonese='大媽海賊團戰鬥員主教殺手波賓懸賞一億貝里',requiredNames=[],subtitleHint='')
   with patch.object(worker,'ollama_chat',side_effect=[json.dumps({'0':'懸賞金一億'})]):
    rows=sf.fit(worker,dict(CFG),job,[cue],lambda *a:None)
   self.assertEqual(cue['cantonese'],'大媽海賊團戰鬥員主教殺手波賓懸賞一億貝里')
   self.assertEqual(rows[0]['accepted'],False);self.assertIn('missing-name:波賓',rows[0]['rejectionReasons'])
 def test_a_longer_candidate_is_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   cue=self.cue()
   with patch.object(worker,'ollama_chat',side_effect=[json.dumps({'0':'我哋即刻出發去下一個目標啦好唔好'})]):
    rows=sf.fit(worker,dict(CFG),Path(d),[cue],lambda *a:None)
   self.assertEqual(cue['cantonese'],'即刻去下一個目標啦！')
   self.assertEqual(rows[0]['accepted'],False);self.assertIn('longer-than-before',rows[0]['rejectionReasons'])
 def test_written_mandarin_candidate_is_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   cue=self.cue()
   with patch.object(worker,'ollama_chat',side_effect=[json.dumps({'0':'即刻到達下一個目標請稍等'})]):
    rows=sf.fit(worker,dict(CFG),Path(d),[cue],lambda *a:None)
   self.assertEqual(cue['cantonese'],'即刻去下一個目標啦！')
   self.assertEqual(rows[0]['accepted'],False);self.assertIn('register-not-cantonese',rows[0]['rejectionReasons'])
 def test_mora_target_uses_the_japanese_window(self):
  cue=dict(start=0,end=4,speechStart=1,speechEnd=3.5,japanese='私は海賊王になる',text='私は海賊王になる')
  self.assertEqual(sf.target_characters(dict(CFG),cue),9)
  self.assertAlmostEqual(sf.window_seconds(cue),2.5)
 def test_measured_take_rate_sets_the_trigger(self):
  # Twelve characters in a 2.5 s window: the drafting rate looks safe, the real
  # engine rate does not. Measured takes decide, so the line is rewritten.
  cue=dict(start=0,end=3,speechStart=.5,speechEnd=3.0,japanese='なぜいつもそう疑うの',
         text='なぜいつもそう疑うの',cantonese='你點解成日咁樣懷疑我啦喂')
  self.assertAlmostEqual(sf.expected_seconds(cue['cantonese']),
                         12/source_mora.TAKE_CHARACTERS_PER_SECOND)
  self.assertLess(12/source_mora.CHARACTERS_PER_SECOND,
                  sf.window_seconds(cue)+source_mora.END_GRACE_SECONDS)
  self.assertTrue(sf.needs_fit(dict(CFG),cue))
 def test_next_line_shortens_the_time_a_take_may_use(self):
  # The raw speech window is not the real limit. A line that looks safe against
  # the window plus grace is still refused by the renderer when the next spoken
  # line starts earlier, so the fit pass must see the same deadline.
  cue=dict(start=0,end=3,speechStart=.5,speechEnd=3.0,japanese='なぜいつもそう疑うの',
         text='なぜいつもそう疑うの',cantonese='你點解成日咁樣懷疑我呀')
  self.assertLess(sf.expected_seconds(cue['cantonese']),sf.window_seconds(cue)+source_mora.END_GRACE_SECONDS)
  self.assertFalse(sf.needs_fit(dict(CFG),cue))
  nxt=dict(start=3.2,end=4.2,speechStart=3.2,speechEnd=4.1,japanese='それはちがう',cantonese='唔係啦')
  cfg=dict(CFG,sourceDuration=20.)
  self.assertAlmostEqual(sf.allowed_seconds(cfg,cue,[cue,nxt]),2.7,delta=.01)
  self.assertLess(sf.expected_seconds(cue['cantonese']),sf.window_seconds(cue)+source_mora.END_GRACE_SECONDS)
  self.assertTrue(sf.needs_fit(cfg,cue,[cue,nxt]))
 def test_candidate_over_the_character_ceiling_gets_one_harder_attempt(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);cue=self.cue();prompts=[]
   def answer(port,model,messages,**kw):
    prompts.append(messages[0]['content']);n=len(prompts)
    return json.dumps({'0':'即刻去下一個目標啦'}) if n==1 else json.dumps({'0':'即刻去啦'})
   with patch.object(worker,'ollama_chat',side_effect=answer):
    rows=sf.fit(worker,dict(CFG),job,[cue],lambda *a:None)
   self.assertEqual(len(prompts),2)
   self.assertIn('硬性',prompts[1]);self.assertIn('5 字',prompts[1])
   self.assertEqual(cue['cantonese'],'即刻去啦')
   self.assertEqual(rows[0]['attempts'],2);self.assertEqual(rows[0]['accepted'],True)
   self.assertEqual(rows[0]['stillOverWindow'],False)
 def test_short_line_that_copied_the_next_line_is_still_rewritten(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);cue=self.cue();cue['cantonese']='即刻去啦'
   nxt=dict(start=1.4,end=2.6,speechStart=1.5,speechEnd=2.5,japanese='今すぐ行こう',cantonese='即刻去啦',requiredNames=[],subtitleHint='')
   cues=[cue,nxt]
   self.assertTrue(sf.copied_neighbour_content(cues,0))
   self.assertLess(sf.expected_seconds(cue['cantonese']),sf.allowed_seconds(dict(CFG),cue,cues))
   self.assertTrue(sf.needs_fit(dict(CFG),cue,cues,0))
   with patch.object(worker,'ollama_chat',side_effect=[json.dumps({'0':'即刻去啦'})]) as model:
    rows=sf.fit(worker,dict(CFG),job,list(cues),lambda *a:None)
   sent=json.loads(model.call_args[0][2][1]['content'])
   self.assertEqual(sent['0']['removeDuplicated'],['即刻去啦'])
   self.assertEqual(rows[0]['copiedNeighbourContent'],['即刻去啦'])

if __name__=='__main__':unittest.main()
