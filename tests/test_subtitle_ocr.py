import json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import subtitle_ocr as ocr,translation_source as source,dialogue,source_evidence


class AutomaticOCRTests(unittest.TestCase):
 def test_discovery_uses_speech_across_episode_and_is_bounded(self):
  times=ocr.sample_times(1200,[dict(start=i,end=i+1) for i in range(10,1190,10)])
  self.assertLessEqual(len(times),18);self.assertGreater(max(times),1000)
  self.assertTrue(all(0<=t<1200 for t in times));self.assertEqual(times,sorted(set(times)))
 def test_two_line_subtitles_locate_lower_band_and_static_corner_logo_does_not(self):
  rows=[dict(index=i,boxes=[dict(x=.27,y=.62,width=.5,height=.06,text=text,confidence=.9),
     dict(x=.35,y=.72,width=.4,height=.06,text=text+'呀',confidence=.9),
     dict(x=.01,y=.01,width=.12,height=.04,text='CHANNEL',confidence=.99)])
        for i,text in enumerate(['開始啦','出發去邊','一齊行'])]
  region,found=ocr.choose_region(rows);self.assertTrue(found)
  self.assertLess(region['y'],.55+.62*.445);self.assertGreater(region['y']+region['height'],.55+.78*.445)
  self.assertGreater(region['y'],.7);self.assertLessEqual(region['y']+region['height'],1)
 def test_empty_or_old_helper_without_boxes_uses_wide_lower_band(self):
  for rows in ([],[dict(index=0,text='subtitle')],[dict(index=0,boxes=[dict(x=0,y=0,width=1,height=1,text='logo')])]):
   self.assertEqual(ocr.choose_region(rows),(ocr.SEARCH,False))
 def test_forced_screen_mode_cannot_inherit_soft_subtitles_or_manual_rectangle(self):
  cfg=source.configure(dict(translationSource=source.SCREEN,subtitle='old.srt',subtitleSource='external',
     ocrRect=dict(x=0,y=0,width=1,height=1),batchAutoSubtitles=True,captionSourceReview='old.json'))
  self.assertEqual(cfg['subtitleSource'],'burned');self.assertTrue(cfg['ocr']);self.assertTrue(cfg['ocrAutoRegion'])
  self.assertFalse(cfg['batchAutoSubtitles']);self.assertIsNone(cfg['subtitle']);self.assertNotIn('ocrRect',cfg)
  self.assertNotIn('captionSourceReview',cfg)
 def test_automatic_region_probe_uses_source_clock_and_falls_back_without_manual_crop(self):
  with tempfile.TemporaryDirectory() as tmp:
   calls=[]
   def run(args):calls.append(args);return b'[]' if '--ocr' in args else b''
   w=SimpleNamespace(run=run,emit=lambda *a,**kw:None,ocr_filter=lambda cfg,masked:'crop',atomic_json=lambda p,d:p.write_text(json.dumps(d)))
   cfg=dict(duration=60,startOffset=90,video='demo.mkv',ffmpeg='ffmpeg',executable='helper')
   ocr.discover(w,cfg,Path(tmp))
   seeks=[float(a[a.index('-ss')+1]) for a in calls if '-ss' in a]
   self.assertEqual(seeks,[90+t for t in ocr.sample_times(60)])
   self.assertEqual(cfg['ocrRect'],ocr.SEARCH);self.assertTrue(cfg['ocrEvidenceOnly'])
   self.assertFalse(json.loads((Path(tmp)/'ocr-region.json').read_text())['detected'])
 def test_full_japanese_is_recognised_once_before_ocr_and_no_ocr_does_not_drop_dialogue(self):
  for captions in ([],[dict(start=1,end=2,text='你好')]):
   with self.subTest(captions=captions),tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);events=[];cue=dict(start=1,end=2,text='こんにちは',japanese='こんにちは',asrConfidence=.9)
    def analyze(cfg,job,caps,*args):
     self.assertEqual(caps,[]);events.append('asr')
     (job/'japanese-analysis.json').write_text(json.dumps(dict(segments=[],spans=[])))
     return [dict(cue)]
    def extract(cfg,job,meta):events.append('ocr');return captions
    w=SimpleNamespace(run=lambda args:b'',emit=lambda *a,**kw:None,extract_cues=extract,
        atomic_json=lambda p,data:p.write_text(json.dumps(data)))
    cfg=dict(ocr=True,duration=4,subtitleSource='burned',translationSource=source.SCREEN)
    with patch.object(dialogue,'analyze',side_effect=analyze) as asr,patch.object(dialogue,'build_cues',return_value=[dict(cue)]):
     result=source.analyze_sources(w,cfg,root,{})
    self.assertEqual(events,['asr','ocr']);asr.assert_called_once();self.assertEqual(result[0]['text'],'こんにちは')
    self.assertNotIn('_ocrSpeechWindows',cfg);self.assertTrue(cfg['ocrEvidenceOnly'])
    self.assertEqual(json.loads((root/'input-source.json').read_text())['captionCount'],len(captions))
 def test_missing_ocr_at_a_heard_line_never_authorises_deleting_that_line(self):
  cue=dict(start=5,end=6,text='ありがとう',asrConfidence=.9)
  cfg=dict(ocr=True,ocrEvidenceOnly=True,duration=10)
  source_evidence.apply_caption_policy(cfg,[dict(start=1,end=2,text='你好')],[cue])
  self.assertTrue(cue.get('enabled',True));self.assertFalse(cue.get('captionPolicyExcluded'))
  self.assertEqual(cfg['_captionPreserveRanges'],[])
 def test_ocr_helper_failure_is_retained_and_audio_translation_continues(self):
  with tempfile.TemporaryDirectory() as tmp:
   job=Path(tmp);cue=dict(start=1,end=2,text='ありがとう')
   (job/'japanese-analysis.json').write_text(json.dumps(dict(segments=[],spans=[])))
   events=[]
   def fail(*args):raise RuntimeError('OCR runtime unavailable')
   w=SimpleNamespace(run=lambda a:b'',extract_cues=fail,emit=lambda *a,**kw:events.append(kw),atomic_json=lambda p,d:p.write_text(json.dumps(d)))
   with patch.object(dialogue,'analyze',return_value=[cue]),patch.object(dialogue,'build_cues',return_value=[]):
    result=source.analyze_sources(w,dict(ocr=True,duration=4),job,{})
   self.assertEqual(result[0]['text'],'ありがとう');self.assertTrue(result[0]['captionEvidenceOnly'])
   self.assertTrue(any(e.get('warningCode')=='ocr-unavailable-audio-used' for e in events))
   self.assertIn('OCR runtime unavailable',json.loads((job/'input-source.json').read_text())['ocrError'])
 def test_sparse_repeat_samples_do_not_repeat_ocr_hint_in_translation(self):
  with tempfile.TemporaryDirectory() as tmp:
   job=Path(tmp);cue=dict(start=1,end=6,text='ありがとう')
   captions=[dict(start=1,end=2,text='多謝你。'),dict(start=4,end=5,text='多 謝 你。')]
   w=SimpleNamespace(run=lambda a:b'',extract_cues=lambda *a:captions,emit=lambda *a,**k:None,atomic_json=lambda p,d:p.write_text(json.dumps(d)))
   with patch.object(dialogue,'analyze',return_value=[cue]):
    result=source.analyze_sources(w,dict(ocr=True,duration=10),job,{})
   self.assertEqual(result[0]['subtitleHint'],'多謝你。')

 def test_full_review_does_not_pin_bad_ocr_or_hide_low_confidence_japanese(self):
  import hybrid_script
  cue=dict(start=1,end=2,japanese='ありがとう',asrConfidence=.4,captionEvidenceOnly=True,
      subtitleHint='錯誤字幕',captionRecords=[dict(id='c1',start=1,end=2,text='錯誤字幕')])
  row=hybrid_script.evidence(cue,0)
  self.assertEqual(row['japanese'],'ありがとう');self.assertEqual(row['allowed_caption_ids'],[])
  allocation={'1':dict(content='ありがとう',caption_ids=[],uncertain=True)}
  self.assertTrue(source_evidence.grounded_line('1',dict(evidence_id='1',quote='ありがとう'),[row],allocation))
  self.assertFalse(source_evidence.grounded_line('1',dict(evidence_id='1',quote='錯誤字幕'),[row],allocation))

 def test_wrong_ocr_cannot_replace_retime_merge_or_add_heard_turns(self):
  with tempfile.TemporaryDirectory() as tmp:
   job=Path(tmp)
   cues=[dict(start=1,end=2,japanese='ありがとう',text='ありがとう'),
         dict(start=3,end=4,japanese='行こう',text='行こう')]
   captions=[dict(start=0,end=9,text='錯誤字幕及不相干標題')]
   w=SimpleNamespace(run=lambda a:b'',extract_cues=lambda *a:captions,emit=lambda *a,**k:None,
       atomic_json=lambda p,d:p.write_text(json.dumps(d)))
   with patch.object(dialogue,'analyze',return_value=cues),patch.object(dialogue,'build_cues') as rebuild:
    result=source.analyze_sources(w,dict(ocr=True,duration=10),job,{})
   rebuild.assert_not_called()
   self.assertEqual([(c['start'],c['end'],c['japanese']) for c in result],[(1,2,'ありがとう'),(3,4,'行こう')])
   self.assertTrue(all(c['captionEvidenceOnly'] for c in result))

 def test_recovery_never_reads_wrong_ocr_when_translation_model_is_unavailable(self):
  import script_gap_recovery as gaps
  from unittest.mock import Mock
  cue=dict(start=1,end=3,text='明日ここで会おう',japanese='明日ここで会おう',cantonese='',
       subtitleHint='錯誤字幕',captionRecords=[dict(id='c1',start=1,end=3,text='錯誤字幕')],
       captionAllocation=dict(content='錯誤字幕',caption_ids=['c1']))
  with tempfile.TemporaryDirectory() as tmp:
   w=Mock();w.ollama_chat.side_effect=RuntimeError('offline')
   w.atomic_json.side_effect=lambda p,d:p.write_text(json.dumps(d))
   result=gaps.recover(w,dict(ocr=True,model='test',port=1),Path(tmp),[cue])
  self.assertEqual(result,[]);self.assertEqual(cue['cantonese'],'')
  self.assertEqual(w.ollama_chat.call_count,2)
  src=gaps.evidence(cue)
  self.assertEqual(src['captions'],[]);self.assertEqual(src['ownedMeaning'],'')
  self.assertEqual(src['japanese'],'明日ここで会おう');self.assertTrue(src['ocrContext'])
  self.assertIn(source.AUDIO_PRIORITY_PROMPT,w.ollama_chat.call_args.args[2][0]['content'])

 def test_name_glossary_uses_heard_names_not_ocr_only_names(self):
  import normal_mode
  from unittest.mock import Mock
  w=Mock();w.traditional_cantonese.side_effect=lambda cfg,text:text
  w.atomic_json.side_effect=lambda p,d:p.write_text(json.dumps(d))
  w.ollama_chat.return_value=json.dumps(dict(names=[
      dict(source='アキラ',cantonese='阿基拉',english='Akira'),
      dict(source='錯名',cantonese='錯名',english='Wrong')]))
  with tempfile.TemporaryDirectory() as tmp:
   names=normal_mode.glossary(w,dict(ocr=True,model='test',port=1),Path(tmp),
       [dict(japanese='アキラ、行こう',subtitleHint='錯名')])
  self.assertEqual(names,[dict(source='アキラ',cantonese='阿基拉',english='Akira')])
  self.assertIn(source.AUDIO_PRIORITY_PROMPT,w.ollama_chat.call_args.args[2][0]['content'])

 def test_english_and_isolated_bilingual_rescue_keep_audio_priority(self):
  import dub_languages,normal_mode
  from unittest.mock import Mock
  w=Mock();w.traditional_cantonese.side_effect=lambda cfg,text:text
  w.atomic_json.side_effect=lambda p,d:p.write_text(json.dumps(d))
  cfg=dict(ocr=True,model='test',port=1,productionMode='normal',dubLanguages=['yue','en'])
  cue=dict(start=1,end=3,text='明日会おう',japanese='明日会おう',captionEvidenceOnly=True,
      subtitleHint='錯誤字幕',captionAllocation=dict(content='錯誤字幕'),cantonese='')
  with tempfile.TemporaryDirectory() as tmp:
   w.ollama_chat.side_effect=['{"0":"See you tomorrow."}','{"0":"See you tomorrow."}']
   dub_languages.english_script(w,cfg,Path(tmp),[dict(cue)])
   for call in w.ollama_chat.call_args_list:
    messages=call.args[2];self.assertIn(source.AUDIO_PRIORITY_PROMPT,messages[0]['content'])
    payload=json.loads(messages[1]['content'])
    rows=payload['lines'] if isinstance(payload,dict) else payload
    self.assertEqual(rows[0]['ownedMeaning'],'')
   w.ollama_chat.reset_mock();w.ollama_chat.side_effect=['{"text":"See you tomorrow."}','{"text":"聽日見啦。"}']
   normal_mode.ensure_scripts(w,cfg,Path(tmp),[dict(cue)])
   self.assertEqual(w.ollama_chat.call_count,2)
   for call in w.ollama_chat.call_args_list:
    self.assertIn(source.AUDIO_PRIORITY_PROMPT,call.args[2][0]['content'])
    self.assertEqual(json.loads(call.args[2][1]['content'])['source']['ownedMeaning'],'')

 def test_semantic_review_cannot_use_wrong_ocr_as_proof_to_reject_audio_translation(self):
  import worker,semantic_review
  items={'0':dict(source=dict(japanese='ありがとう',caption='我要離開'),candidate='多謝你。')}
  verdict={'0':dict(faithful=False,reason='OCR conflict',defects=[dict(kind='wrong-action',source_quote='我要離開',candidate_quote='多謝',explanation='wrong OCR')])}
  with patch.object(worker,'ollama_chat',return_value=json.dumps(verdict)) as call:
   result=semantic_review.audit(dict(ocr=True,model='test',port=1),items)
  self.assertTrue(result['0']['invalidEvidence']);self.assertEqual(result['0']['groundedDefects'],[])
  self.assertIn(source.AUDIO_PRIORITY_PROMPT,call.call_args.args[2][0]['content'])

if __name__=='__main__':unittest.main()
