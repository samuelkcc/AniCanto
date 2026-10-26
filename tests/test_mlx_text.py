import unittest,json,sys,os,tempfile
from pathlib import Path
from unittest.mock import patch,MagicMock
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import mlx_text,worker
class MLXTextTests(unittest.TestCase):
 def setUp(self):
  device=patch('compute_policy.mlx_device');device.start();self.addCleanup(device.stop)

 def test_explicit_json_constraint_gets_fresh_matcher_after_retry(self):
  with tempfile.TemporaryDirectory() as folder:
   backend=mlx_text.Backend(folder);backend.model=object();backend.loaded_id=mlx_text.MODEL_ID;backend.tokenizer=MagicMock()
   backend.tokenizer.encode.return_value=[1];backend.tokenizer.apply_chat_template.return_value='prompt'
   builder=MagicMock(side_effect=[object(),object()]);calls=[]
   def generate(*a,**kwargs):
    calls.append(kwargs);return iter([SimpleNamespace(text='invalid' if len(calls)==1 else '{"choice":"keep"}')])
   modules={'mlx_lm':MagicMock(stream_generate=generate),'mlx_lm.sample_utils':MagicMock(),'mlx_vlm.structured':SimpleNamespace(build_json_schema_logits_processor=builder)}
   schema=dict(type='object',properties=dict(choice=dict(type='string',enum=['keep'])),required=['choice'])
   with patch.dict(sys.modules,modules):
    self.assertEqual(json.loads(backend.generate(dict(model=mlx_text.MODEL_ID,format=schema,constrained_json=True))),{'choice':'keep'})
   self.assertEqual(builder.call_count,2);self.assertIsNot(calls[0]['logits_processors'][0],calls[1]['logits_processors'][0])
 def test_fenced_scene_discards_only_forbidden_context_keys(self):
  schema={'type':'object','properties':{'1':{'type':'object','properties':{'meaning':{'type':'string'}},'required':['meaning'],'additionalProperties':False}},'required':['1'],'additionalProperties':False}
  raw='```json\n{"1":{"meaning":"保留完整意思"},"2":{"meaning":"只供上下文"}}\n```'
  self.assertEqual(json.loads(mlx_text.structured_reply(raw,schema)),{'1':{'meaning':'保留完整意思'}})
 def test_invalid_reply_never_fabricates_or_accepts_partial_data(self):
  schema={'type':'object','properties':{'text':{'type':'string','minLength':1}},'required':['text']}
  for raw in ['', '```json\n{"text":"未完', '{}', '{"text":2}', '{"text":""}', '{"text":"a","text":"b"}', '{"text":NaN}', 'Here is JSON: {"text":"hi"}', '{"text":"hi"} trailing']:
   with self.subTest(raw=raw),self.assertRaises(ValueError):mlx_text.structured_reply(raw,schema)
 def test_enum_and_array_validation(self):
  schema={'type':'array','items':{'type':'string','enum':['question','call']}}
  self.assertEqual(json.loads(mlx_text.structured_reply('["call"]',schema)),['call'])
  with self.assertRaises(ValueError):mlx_text.structured_reply('["invented"]',schema)
 def test_structured_retry_is_bounded_and_preserves_single_system_message(self):
  with tempfile.TemporaryDirectory() as folder:
   backend=mlx_text.Backend(folder);backend.model=object();backend.loaded_id=mlx_text.MODEL_ID;backend.tokenizer=MagicMock()
   backend.tokenizer.encode.return_value=[1];backend.tokenizer.apply_chat_template.return_value='prompt'
   generation=MagicMock(side_effect=['{"text":','```json\n{"text":"得喇"}\n```'])
   modules={'mlx_lm':MagicMock(stream_generate=lambda *a,**kw: iter([SimpleNamespace(text=generation(*a,**kw),prompt_tokens=2,prompt_tps=100,generation_tokens=3,generation_tps=20)])),'mlx_lm.sample_utils':MagicMock()}
   body={'model':mlx_text.MODEL_ID,'messages':[{'role':'system','content':'香港口語'},{'role':'user','content':'test'}],'format':{'type':'object','required':['text'],'properties':{'text':{'type':'string'}}}}
   with patch.dict(sys.modules,modules):
    self.assertEqual(json.loads(backend.generate(body)),{'text':'得喇'})
    self.assertEqual(generation.call_count,2)
    self.assertEqual(generation.call_args.kwargs['max_tokens'],4096)
    self.assertEqual([m['role'] for m in backend.tokenizer.apply_chat_template.call_args.args[0]],['system','user'])
    generation.reset_mock();generation.side_effect=None;generation.return_value='bad'
    with self.assertRaises(mlx_text.ModelReplyError):backend.generate(body)
    self.assertEqual(generation.call_count,2)
    self.assertTrue((Path(folder)/'logs/mlx-text-last-invalid.json').exists())
 def test_structured_editor_keeps_one_system_turn_and_input_unchanged(self):
  for format in ('json',{'type':'object','properties':{'text':{'type':'string'}}}):
   with self.subTest(format=format):
    body={'messages':[{'role':'system','content':'香港配音編輯。'},
                      {'role':'user','content':'日語及中文字幕資料'}],'format':format}
    before=json.dumps(body,ensure_ascii=False)
    messages=mlx_text.chat_messages(body)
    self.assertEqual([m['role'] for m in messages],['system','user'])
    self.assertIn('香港配音編輯。',messages[0]['content'])
    self.assertIn('valid JSON',messages[0]['content'])
    self.assertEqual(messages[1],body['messages'][1])
    self.assertEqual(json.dumps(body,ensure_ascii=False),before)
    if isinstance(format,dict):self.assertIn(json.dumps(format),messages[0]['content'])
    else:self.assertNotIn('Required JSON schema:',messages[0]['content'])
 def test_conversation_order_and_unstructured_requests(self):
  turns=[{'role':'system','content':'first'},{'role':'system','content':'second'},
         {'role':'user','content':'input'},{'role':'assistant','content':'reply'},
         {'role':'user','content':'followup'}]
  messages=mlx_text.chat_messages({'messages':turns})
  self.assertEqual(messages[0]['content'],'first\n\nsecond')
  self.assertEqual(messages[1:],turns[2:])
  self.assertEqual(mlx_text.chat_messages({'prompt':'hello'}),[{'role':'user','content':'hello'}])
  self.assertEqual(mlx_text.chat_messages({'messages':turns[2:]}),turns[2:])
 def test_does_not_promote_late_system_instructions(self):
  with self.assertRaises(ValueError):
   mlx_text.chat_messages({'messages':[{'role':'user','content':'data'},
                                      {'role':'system','content':'late'}]})
 def test_port_routing_does_not_change_ollama(self):
  with patch.dict(os.environ,{'CANTOSYNC_MLX_PORT':'12345'}):
   self.assertEqual(worker.text_port(11439,mlx_text.MODEL_ID),12345)
   self.assertEqual(worker.text_port(11439,'qwen3:14b'),11439)
 def test_wrong_model_is_rejected_before_loading(self):
  with self.assertRaises(ValueError):mlx_text.Backend('/tmp').generate({'model':'wrong'})
 def test_json_checked_and_thinking_disabled(self):
  backend=mlx_text.Backend('/tmp');backend.model=object();backend.loaded_id=mlx_text.MODEL_ID;backend.tokenizer=MagicMock()
  backend.tokenizer.encode.return_value=[1,2];backend.tokenizer.apply_chat_template.return_value='prompt'
  generation=MagicMock(return_value='{"text":"你好"}')
  modules={'mlx_lm':MagicMock(stream_generate=lambda *a,**kw: iter([SimpleNamespace(text=generation(*a,**kw),prompt_tokens=2,prompt_tps=100,generation_tokens=3,generation_tps=20)])),'mlx_lm.sample_utils':MagicMock()}
  with patch.dict(sys.modules,modules):
   self.assertEqual(json.loads(backend.generate({'model':mlx_text.MODEL_ID,'messages':[{'role':'user','content':'hi'}],'format':'json'}))['text'],'你好')
   self.assertFalse(backend.tokenizer.apply_chat_template.call_args.kwargs['enable_thinking'])
   generation.return_value='bad output'
   with self.assertRaises(ValueError):backend.generate({'model':mlx_text.MODEL_ID,'format':'json'})
 def test_one_invalid_turn_does_not_regenerate_valid_batch(self):
  with tempfile.TemporaryDirectory() as folder:
   backend=mlx_text.Backend(folder);backend.model=object();backend.loaded_id=mlx_text.MODEL_ID;backend.tokenizer=MagicMock()
   backend.tokenizer.encode.return_value=[1,2];backend.tokenizer.apply_chat_template.return_value='prompt'
   row=dict(type='object',properties=dict(text=dict(type='string',minLength=1)),required=['text'])
   schema=dict(type='object',properties={str(i):row for i in range(10,26)},required=[str(i) for i in range(10,26)],**{'x-partial-rows':True})
   reply={str(i):dict(text='有效台詞' if i!=18 else '') for i in range(10,26)}
   generation=MagicMock(return_value=json.dumps(reply))
   modules={'mlx_lm':MagicMock(stream_generate=lambda *a,**kw:iter([SimpleNamespace(text=generation(*a,**kw),prompt_tokens=20,prompt_tps=100,generation_tokens=30,generation_tps=20)])),'mlx_lm.sample_utils':MagicMock()}
   with patch.dict(sys.modules,modules):
    accepted=json.loads(backend.generate(dict(model=mlx_text.MODEL_ID,format=schema)))
   self.assertEqual(len(accepted),15);self.assertNotIn('18',accepted);self.assertEqual(generation.call_count,1)
   self.assertEqual(backend.last_metrics['rejectedRows'][0]['id'],'18')
 def test_manifest_pins_weights_and_hashes(self):
  m=json.loads((Path(__file__).parents[1]/'Resources/mlx-text-model.json').read_text())
  self.assertEqual(len(m['revision']),40)
  self.assertEqual(len([f for f in m['files'] if f['path'].endswith('.safetensors')]),4)
  self.assertTrue(all(len(f['sha'])==64 for f in m['files']))
