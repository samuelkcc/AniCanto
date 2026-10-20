import copy,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import source_evidence as s
import hybrid_script as h

class AlignmentTests(unittest.TestCase):
 def test_real_partial_clause_duplication_requests_reconciliation_of_both_turns(self):
  cues=json.loads((Path(__file__).parent/'fixtures/shared-caption-clause-drift.json').read_text())
  before=copy.deepcopy(cues);source=[h.evidence(c,i) for i,c in enumerate(cues)]
  allocation={str(i+1):c['captionAllocation'] for i,c in enumerate(cues)}
  errors=s.allocation_errors(allocation,source,list(allocation))
  self.assertEqual(errors,{'1':'duplicated-caption-clause','2':'duplicated-caption-clause','3':'duplicated-caption-clause'})
  rows=s.audit_allocations(cues)
  self.assertEqual([r['index'] for r in rows],[1,2,3]);self.assertEqual(cues,before)
  # An approved manual fix remains untouched even if source metadata is stale.
  cues[1]['cantonese']='聽日繼續加油！';s.audit_allocations(cues)
  self.assertEqual(cues[1]['cantonese'],'聽日繼續加油！')
  allocation['2']=dict(content='明天也继续加油吧！',caption_ids=['caption_117'],uncertain=False)
  allocation['3']=dict(content='嗯！当然！',caption_ids=['caption_118'],uncertain=False)
  self.assertEqual(s.allocation_errors(allocation,source,list(allocation)),{})
 def test_partial_caption_overlap_preserves_actual_repeated_speech(self):
  cap=dict(id='c',start=0,end=4,text='一起加油')
  other=dict(id='d',start=2,end=4,text='明天再来')
  turns=[dict(id='1',start=0,end=2,japanese='頑張りましょう',caption_records=[cap]),dict(id='2',start=2,end=4,japanese='頑張りましょう',caption_records=[cap,other])]
  allocation={'1':dict(content='一起加油',caption_ids=['c'],uncertain=False),'2':dict(content='一起加油 明天再来',caption_ids=['c','d'],uncertain=False)}
  self.assertEqual(s.allocation_errors(allocation,turns,['1','2']),{})
 def test_no_caption_allocation_is_not_an_audit_failure(self):
  self.assertEqual(s.audit_allocations([dict(start=0,end=1,japanese='こんにちは',cantonese='你好')]),[])
 def test_partial_caption_overlap_preserves_variant_repeated_name_calls(self):
  cap=dict(id='c',start=0,end=4,text='特尔缇娜')
  other=dict(id='d',start=2,end=4,text='回来')
  turns=[dict(id='1',start=0,end=2,japanese='テルテラ',caption_records=[cap]),dict(id='2',start=2,end=4,japanese='テルテラー',caption_records=[cap,other])]
  allocation={'1':dict(content='特尔缇娜',caption_ids=['c'],uncertain=False),'2':dict(content='特尔缇娜 回来',caption_ids=['c','d'],uncertain=False)}
  self.assertEqual(s.allocation_errors(allocation,turns,['1','2']),{})
 def real_scene(self):
  rows=json.loads((Path(__file__).parent/'fixtures/subtitle-timing-drift.json').read_text())
  source=[h.evidence(r['cue'],r['index']-1) for r in rows]
  allocation={str(r['index']):copy.deepcopy(r['cue']['captionAllocation']) for r in rows}
  return rows,source,allocation
 def test_real_0426_failure_rejects_valid_quote_from_0415(self):
  rows,source,allocation=self.real_scene();row=next(r['cue'] for r in rows if r['index']==32)
  self.assertEqual(row['cantonese'],'玲玲？')
  self.assertFalse(s.grounded_line('32',row['hybridEvidence'],source,allocation))
  self.assertEqual(s.allocation_errors(allocation,source,list(allocation))['32'],'caption-outside-speech-interval')
 def test_real_scene_repairs_exclusive_captions_without_shifting_audio(self):
  rows,source,allocation=self.real_scene();before=copy.deepcopy(source)
  changes=s.anchor_allocation(allocation,source,list(allocation))
  self.assertTrue(any(r['id']=='32' for r in changes))
  self.assertEqual(allocation['32']['caption_ids'],['caption_34','caption_35'])
  self.assertIn('你...你要好好想想啊',allocation['32']['content'])
  self.assertIn('俺好歹也算是你的父亲啊',allocation['32']['content'])
  self.assertNotIn('玲玲',allocation['32']['content']);self.assertEqual(source,before)
  self.assertTrue(s.grounded_line('32',dict(evidence_id='32',quote=allocation['32']['content']),source,allocation))
  # Citing one clause cannot certify a two-clause allocation.
  self.assertFalse(s.grounded_line('32',dict(evidence_id='caption_35',quote='俺好歹也算是你的父亲啊'),source,allocation))
 def test_shared_caption_keeps_split_and_does_not_copy_whole_caption(self):
  cap=dict(id='c',start=0,end=4,text='阿甲 阿乙')
  turns=[dict(id='1',start=0,end=2,japanese='',caption_records=[cap]),dict(id='2',start=2,end=4,japanese='',caption_records=[cap])]
  allocation={'1':dict(content='阿甲',caption_ids=['c'],uncertain=False),'2':dict(content='阿乙',caption_ids=['c'],uncertain=False)}
  self.assertEqual(s.allocation_errors(allocation,turns,['1','2']),{})
  allocation['1']['caption_ids']=['outside'];before=copy.deepcopy(allocation)
  self.assertEqual(s.anchor_allocation(allocation,turns,['1','2']),[]);self.assertEqual(allocation,before)
 def test_uncaptioned_reaction_does_not_borrow_neighbour_caption(self):
  turn=dict(id='1',start=10,end=11,japanese='え？',caption_records=[dict(id='c',start=7,end=9,text='父亲')])
  a={'1':dict(content='父亲',caption_ids=['c'],uncertain=False)}
  s.anchor_allocation(a,[turn],['1']);self.assertEqual(a['1']['content'],'え？');self.assertEqual(a['1']['caption_ids'],[])
 def test_real_misplaced_script_is_retried_and_old_fallback_refused(self):
  _,source,a=self.real_scene();s.anchor_allocation(a,source,list(a))
  bad=dict(cantonese='玲玲？',evidence_id='caption_32',quote='玲玲吗',uncertain=False)
  good=dict(cantonese='你要好好諗下，我點都算係你個爹啊。',evidence_id='32',quote=a['32']['content'],uncertain=False)
  with tempfile.TemporaryDirectory() as d:
   w=SimpleNamespace(emit=Mock(),traditional_cantonese=lambda cfg,t:t,atomic_json=lambda p,x:p.write_text(json.dumps(x)),ollama_chat=Mock(return_value=json.dumps({'32':good})),parse_editor_response=json.loads)
   result=h.complete_lines(w,dict(port=1,model='test'),Path(d),'script','prompt',dict(dialogue=source,allocation=a),{'32':bad},['32'],[{}]*32,dict(properties={'32':{}},required=['32']),{'32':bad})
   self.assertEqual(result['32'],good);self.assertEqual(w.ollama_chat.call_count,1)
   w.ollama_chat=Mock(return_value='{}')
   result=h.complete_lines(w,dict(port=1,model='test',continueOnError=True),Path(d),'script2','prompt',dict(dialogue=source,allocation=a),{'32':bad},['32'],[{}]*32,dict(properties={'32':{}},required=['32']),{'32':bad})
   self.assertTrue(result['32']['captionRescue']);self.assertNotIn('玲玲',result['32']['cantonese'])
   self.assertEqual(result['32']['quote'],a['32']['content']);self.assertTrue(s.grounded_line('32',result['32'],source,a));self.assertEqual(w.ollama_chat.call_count,1,'The prior successful correction consumed one of the two persistent repair attempts')
 def test_visual_observations_are_context_not_permission_to_move_dialogue(self):
  c=dict(start=2,end=3,text='え',visualEvidence=dict(visualId='v4',speaking=True,mouthChanged=True,confidence=.99,index=90))
  e=h.evidence(c,0);self.assertEqual(e['visual_speaker']['visualId'],'v4');self.assertNotIn('index',e['visual_speaker'])
  self.assertFalse(s.grounded_line('1',dict(evidence_id='2',quote='え'),[e,dict(e,id='2')],{}))
 def test_scene_pipeline_rejects_displaced_cached_draft_and_resumes_fixed_cache(self):
  rows,_,_=self.real_scene();cues=[copy.deepcopy(r['cue']) for r in rows if r['index'] in (32,33,34)]
  captions={r['id']:r for c in cues for r in c['captionRecords']}
  subtitle_rows=[dict(start=-10,end=-9,text='padding') for _ in range(37)]
  for ident,row in captions.items():subtitle_rows[int(ident.split('_')[1])-1]=row
  calls=[]
  def chat(port,model,messages,schema,**kw):
   calls.append(messages);props=schema['properties']
   if 'summary' in props:return json.dumps(dict(summary='父親與前夫的爭論',uncertainties=[]))
   if 'content' in next(iter(props.values())).get('properties',{}):
    return json.dumps({str(i+1):c['captionAllocation'] for i,c in enumerate(cues)})
   result={k:dict(cantonese='你諗清楚啲，我點都算係你老豆。' if k=='1' else '只係前任啫。',evidence_id=k,quote=p['properties']['quote']['enum'][0],uncertain=False) for k,p in props.items()}
   if len(props)==3:result['1']=dict(cantonese='玲玲？',evidence_id='caption_32',quote='玲玲吗',uncertain=False)
   return json.dumps(result)
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);(job/'subtitle-context.json').write_text(json.dumps(subtitle_rows))
   w=SimpleNamespace(emit=Mock(),traditional_cantonese=lambda cfg,t:t,atomic_json=lambda p,x:p.write_text(json.dumps(x)),parse_editor_response=json.loads,ollama_chat=chat)
   before=[(c['start'],c['end']) for c in cues]
   h.render(w,dict(port=0,model='test',storage=d),job,cues)
   self.assertIn('老豆',cues[0]['cantonese']);self.assertNotIn('玲玲',cues[0]['cantonese'])
   self.assertEqual(cues[0]['hybridRevision'],h.REVISION);self.assertEqual([(c['start'],c['end']) for c in cues],before)
   self.assertTrue(json.loads((job/'hybrid-report.json').read_text())['alignmentChanges'])
   count=len(calls);h.render(w,dict(port=0,model='test',storage=d),job,cues);self.assertEqual(len(calls),count)
