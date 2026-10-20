import sys,tempfile,json,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import hybrid_script as h
class HybridTests(unittest.TestCase):
 def test_blocks_cover_all_ids_and_silence(self):
  cues=[dict(start=i,end=i+.8) for i in range(40)]+[dict(start=60,end=61)]
  spans=h.blocks(cues)
  self.assertEqual([i for a,b in spans for i in range(a,b)],list(range(41)))
  self.assertTrue(all(b-a<=18 for a,b in spans));self.assertEqual(spans[-1],(40,41))
 def test_low_confidence_evidence_and_cache_preserve_times(self):
  with tempfile.TemporaryDirectory() as d:
   calls=[];events=[]
   def chat(*args,**kwargs):
    calls.append(args)
    return json.dumps({'summary':'叫名','uncertainties':[]} if len(calls)==1 else {'1':{'cantonese':'阿明！','evidence_id':'1','quote':'阿明','uncertain':True}})
   w=SimpleNamespace(emit=lambda *a,**kw:events.append((a,kw)),parse_editor_response=json.loads,ollama_chat=chat,atomic_json=lambda p,x:p.write_text(json.dumps(x)),traditional_cantonese=lambda cfg,t:t)
   c=[dict(start=2,end=3,text='これ',japanese='これ',subtitleHint='阿明',asrConfidence=.01,cantonese='呢個！')]
   h.render(w,{'model':'test','port':1},Path(d),c)
   self.assertEqual((c[0]['start'],c[0]['end']),(2,3));self.assertEqual(c[0]['preHybridCantonese'],'呢個！');self.assertTrue(c[0]['hybridNeedsReview'])
   self.assertTrue(any(kw.get('workID')=='scene-script' and kw.get('workCompleted')==1 and kw.get('workTotal')==1 for _,kw in events))
   self.assertTrue(any(kw.get('workID')=='scene-context' and kw.get('workCompleted')==1 for _,kw in events))
   h.render(w,{'model':'test','port':1},Path(d),c);self.assertEqual(len(calls),3)
   self.assertTrue(any(kw.get('workCached') for _,kw in events),'Reused scene results must be excluded from model timing history')
