import io,json,sys,tempfile,unittest,urllib.error
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import cantonese_style,semantic_review,worker,duration_fit,asr_verify
from nonverbal import missing_events
from speakers import audit_references


class EditorEvidenceTests(unittest.TestCase):
 def test_register_preserves_negation_names_quotes_and_meaning_words(self):
  self.assertEqual(cantonese_style.rewrite('佢死了啊，唔好動！'),'佢死咗啊，唔好郁！')
  self.assertEqual(cantonese_style.rewrite('特爾緹娜公主，讓我為您遮蔭！'),'特爾緹娜公主，等我幫你遮蔭！')
  self.assertEqual(cantonese_style.rewrite('我冇拿到，「拿到」係書名。'),'我冇攞到，「拿到」係書名。')
  self.assertEqual(cantonese_style.rewrite('歡迎來到這個世界',['這個世界']),'歡迎嚟到這個世界')
  self.assertEqual(cantonese_style.rewrite('你來得真快，佢站喺門口'),'你嚟得真快，佢企喺門口')
 def test_register_pass_is_idempotent_and_human_lock_is_respected(self):
  with tempfile.TemporaryDirectory() as d:
   cues=[dict(cantonese='請收下')];p=Path(d)
   cantonese_style.apply(dict(scriptLocked=True),p,cues,[])
   self.assertEqual(cues[0]['cantonese'],'請收下')
   cantonese_style.apply({},p,cues,[]);cantonese_style.apply({},p,cues,[])
   self.assertEqual(cues[0]['cantonese'],'唔該收低')
   self.assertEqual(len(json.loads((p/'register-edits.json').read_text())),1)
 def test_semantic_auditor_cannot_invent_a_source_quote(self):
  item={'0':dict(source=dict(japanese='動くな'),candidate='唔好郁')}
  result={'0':dict(faithful=True,reason='claimed',defects=[dict(kind='omission',source_quote='走れ',candidate_quote='',explanation='fabricated')])}
  with patch.object(worker,'ollama_chat',return_value=json.dumps(result)):
   row=semantic_review.audit(dict(port=1,model='test'),item)['0']
  self.assertFalse(row['faithful']);self.assertTrue(row['invalidEvidence'])
 def test_semantic_auditor_accepts_no_defect_without_particle_translation(self):
  result={'0':dict(faithful=True,reason='same death event',defects=[])}
  with patch.object(worker,'ollama_chat',return_value=json.dumps(result)):
   row=semantic_review.audit(dict(port=1,model='test'),{'0':dict(source=dict(japanese='彼が死んだよ'),candidate='佢死咗啊')})['0']
  self.assertTrue(row['faithful'])
 def test_duration_retry_budget_survives_restart(self):
  with tempfile.TemporaryDirectory() as d:
   cues=[dict(text='ありがとう',cantonese='真係好多謝你呀')];rows=[dict(index=1,seconds=4,slot=2,needsReview=True)]
   with patch.object(worker,'ollama_chat',return_value=json.dumps(dict(line_0=cues[0]['cantonese']))) as model,patch.object(duration_fit.urllib.request,'urlopen'):
    for _ in range(4):self.assertFalse(duration_fit.shorten(dict(port=1,model='test'),Path(d),cues,rows,1,lambda *a,**k:None))
   self.assertEqual(model.call_count,2)
 def test_missing_performance_coverage_uses_union_not_sum(self):
  rows=[dict(start=0,duration=2,laughter=.9,speech=.5)]
  events=[dict(start=0,end=1),dict(start=.5,end=1.2)]
  missing=missing_events(rows,events,2)
  self.assertAlmostEqual(missing[0]['missingSeconds'],.8)
  self.assertEqual(missing_events(rows,[dict(start=0,end=2)],2),[])
 def test_padded_short_reference_cannot_count_as_certain_identity(self):
  result=audit_references([dict(speakerId='a',speakerNote='短句',reviewIndex=8)],[dict(id='a',shortReference=True,promptText='はい')])
  self.assertEqual(result['reviewIndices'],[9]);self.assertIn('short-source-reference',result['rows'][0]['reasons'])
 def test_isolated_asr_is_cached_and_never_replaces_timing_or_source(self):
  import dubbing
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'asr-ready.json').write_text('{}');audio=root/'voice.wav';audio.write_bytes(b'audio')
   cues=[dict(start=1,end=2,text='東京に来た',japanese='東京に来た',asrAgreement=.1)]
   def job(cfg,action,request,emit):worker.atomic_json(root/'isolated-asr-result.json',dict(rows=[dict(text='大阪に来た')]))
   cfg=dict(storage=d,dialoguePath=str(audio),ffmpeg='ffmpeg')
   with patch.object(dubbing,'model_job',side_effect=job) as model:
    for _ in range(2):asr_verify.recheck(cfg,root,cues,lambda args:b'',lambda *a:None)
   self.assertEqual(model.call_count,1);self.assertEqual(cues[0]['japanese'],'東京に来た')
   self.assertEqual((cues[0]['start'],cues[0]['end']),(1,2));self.assertTrue(cues[0]['sourceReviewReasons'])
 def test_http_retry_keeps_request_dictionary_after_server_error(self):
  failure=urllib.error.HTTPError('http://localhost',503,'busy',{},io.BytesIO(b'{"error":"busy"}'))
  empty=io.BytesIO(b'{"message":{"content":""}}');success=io.BytesIO(b'{"message":{"content":"ok"}}')
  with patch.object(worker.urllib.request,'urlopen',side_effect=[failure,empty,success]),patch.object(worker.time,'sleep'),patch.object(worker,'emit'):
   self.assertEqual(worker.ollama_chat(1,'test',[],think=True),'ok')
