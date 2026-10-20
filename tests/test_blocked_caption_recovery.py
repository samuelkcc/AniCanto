import copy,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import hybrid_script as h

class BlockedCaptionRecoveryTests(unittest.TestCase):
 def test_ep07_blocked_allocation_recovers_from_own_japanese_not_neighbour(self):
  with tempfile.TemporaryDirectory() as d:
   calls=[];cue=dict(start=1,end=2,text='以上です。',japanese='以上です。')
   data=dict(dialogue=[dict(id='1',japanese='以上です。',caption='先唔好講呢個，以上',caption_records=[],allowed_caption_ids=[])],allocation={'1':dict(blocked=True,content='',caption_ids=[])})
   original=copy.deepcopy(data)
   def chat(*a,**kw):
    calls.append(json.loads(a[2][-1]['content']))
    return json.dumps({'1':dict(cantonese='講完啦。',quote='以上です。',evidence_id='1',uncertain=True)})
   w=SimpleNamespace(emit=lambda *a,**kw:None,ollama_chat=chat,parse_editor_response=json.loads,traditional_cantonese=lambda cfg,t:t,atomic_json=lambda p,x:p.write_text(json.dumps(x)))
   schema=dict(type='object',properties={'1':dict(type='object')},required=['1'])
   result=h.complete_lines(w,dict(model='test',port=1,continueOnError=True),Path(d),'script','prompt',data,{'1':dict(cantonese='先唔好講呢個',quote='先唔好講呢個',evidence_id='1',uncertain=True)},['1'],[cue],schema)
   self.assertEqual(len(calls),1);self.assertEqual(result['1']['cantonese'],'講完啦。');self.assertEqual(result['1']['sourceRecovery'],'own-japanese');self.assertEqual(data,original)
   self.assertEqual(calls[0]['dialogue'][0]['caption'],'');self.assertEqual(calls[0]['allocation']['1']['caption_ids'],[])
   # The optional conflict pass must retain this valid repair without another call.
   result2=h.complete_lines(w,dict(model='test',port=1,continueOnError=True),Path(d),'conflicts','prompt',data,{},['1'],[cue],schema,fallback=result)
   self.assertEqual(result2['1']['cantonese'],'講完啦。');self.assertEqual(len(calls),1)
