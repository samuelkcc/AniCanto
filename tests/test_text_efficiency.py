import json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
from mlx_text import structured_reply
from text_prompt_cache import PrefixBank
from hybrid_script import nearby_context
from text_request_meter import TextRequestMeter

class TextEfficiencyTests(unittest.TestCase):
 def test_numbered_batch_retains_valid_rows_and_rejects_missing_empty_displaced(self):
  row=dict(type='object',properties=dict(cantonese=dict(type='string',minLength=1),quote=dict(type='string',enum=['同時段原文'])),required=['cantonese','quote'],additionalProperties=False)
  schema=dict(type='object',properties={k:row for k in ['1','2','3','4']},required=['1','2','3','4'],**{'x-partial-rows':True})
  rejected=[]
  reply=structured_reply(json.dumps({'1':dict(cantonese='你好',quote='同時段原文'),'2':dict(cantonese='',quote='同時段原文'),'3':dict(cantonese='錯配',quote='其他時間原文'),'99':dict(cantonese='未要求',quote='同時段原文')}),schema,rejected)
  self.assertEqual(json.loads(reply),{'1':dict(cantonese='你好',quote='同時段原文')})
  self.assertEqual([r['id'] for r in rejected],['2','3','4'])
  with self.assertRaises(ValueError):structured_reply('{"1":',schema)
  with self.assertRaises(ValueError):structured_reply('{"1":{},"1":{}}',schema)
 def test_non_dialogue_schemas_remain_strict_even_when_flagged(self):
  schema=dict(type='object',properties=dict(summary=dict(type='string',minLength=1)),required=['summary'],**{'x-partial-rows':True})
  with self.assertRaises(ValueError):structured_reply('{}',schema)
 def test_phase_bank_preserves_exact_matching_across_alternating_requests(self):
  bank=PrefixBank(slots=2,max_bytes=100)
  bank.prepare(None,[1,2],'script');entry=bank.entries['script'];entry.tokens=[1];entry.cache=[dict(state=[10])]
  bank.prepare(None,[8,9],'allocation')
  work,rest=bank.prepare(None,[1,3],'script');self.assertEqual(rest,[3]);work[0]['state'][0]=99;self.assertEqual(entry.cache[0]['state'],[10])
  bank.prepare(None,[4,5],'summary');self.assertEqual(list(bank.entries),['script','summary'])
  self.assertEqual(sum(c.max_bytes for c in bank.entries.values()),100)
  work,rest=bank.prepare(None,[2,3],'script');self.assertIsNone(work);self.assertEqual(rest,[2,3])
 def test_context_is_bounded_and_contains_current_neighbour_scenes(self):
  summaries=[dict(first=i*18+1,last=(i+1)*18,summary='文'*1200,uncertainties=['疑點']*6) for i in range(31)]
  context=nearby_context(summaries,15)
  self.assertEqual([r['first'] for r in context],[1,253,271,289])
  self.assertLess(len(json.dumps(context,ensure_ascii=False)),4000)
  self.assertGreater(len(json.dumps(summaries,ensure_ascii=False)),38000)
 def test_meter_records_timings_without_dialogue_and_resume_does_not_duplicate(self):
  with tempfile.TemporaryDirectory() as root:
   worker=SimpleNamespace(ollama_chat=lambda *a,**kw:'private response',atomic_json=lambda p,x:p.write_text(json.dumps(x)),emit=lambda *a,**kw:None,_last_llm_metrics=dict(promptTokens=100,generationTokens=20,generationTokensPerSecond=10))
   meter=TextRequestMeter(worker,Path(root));meter.ollama_chat(0,'model',[dict(content='private input')]);meter.report()
   logs=(Path(root)/'llm-performance.jsonl').read_text();self.assertNotIn('private',logs)
   meter=TextRequestMeter(worker,Path(root));meter.report();self.assertEqual(meter.persist()['requests'],1)
   def fail(*a,**kw):raise RuntimeError('private failure')
   worker.ollama_chat=fail;worker._last_llm_metrics={}
   with self.assertRaises(RuntimeError):meter.ollama_chat()
   self.assertEqual(meter.persist()['failedRequests'],1)
