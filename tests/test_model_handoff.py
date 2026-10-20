import io,json,sys,unittest,urllib.error
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
from model_handoff import release_text

class ModelHandoffTests(unittest.TestCase):
 def response(self,value):return io.BytesIO(json.dumps(value).encode())
 def test_mlx_release_is_acknowledged_without_loading_another_model(self):
  with patch('urllib.request.urlopen',return_value=self.response(dict(memoryReleased=True))) as http,patch('worker.text_port',return_value=3):release_text(dict(model='mlx:chosen',port=2),Mock())
  body=json.loads(http.call_args.args[0].data);self.assertEqual(body['keep_alive'],0);self.assertTrue(body['strict_model'])
 def test_missing_acknowledgement_is_bounded_and_stops_next_load(self):
  with patch('urllib.request.urlopen',side_effect=lambda *a,**kw:self.response(dict(done=True))) as http,patch('worker.text_port',return_value=3):
   with self.assertRaisesRegex(RuntimeError,'could not be confirmed'):release_text(dict(model='mlx:chosen',port=2),Mock())
   self.assertEqual(http.call_count,2)
 def test_ollama_checks_actual_resident_models_not_only_done_reply(self):
  with patch('urllib.request.urlopen',side_effect=[self.response(dict(done=True)),self.response(dict(models=[dict(name='qwen:9b')]))]*2),patch('worker.text_port',return_value=3):
   with self.assertRaises(RuntimeError):release_text(dict(model='qwen:9b',port=2),Mock())
 def test_ollama_unload_with_empty_residency_list_passes(self):
  with patch('urllib.request.urlopen',side_effect=[self.response(dict(done=True)),self.response(dict(models=[]))]),patch('worker.text_port',return_value=3):release_text(dict(model='qwen:9b',port=2),Mock())
 def test_refused_local_service_is_not_a_resident_model(self):
  with patch('urllib.request.urlopen',side_effect=urllib.error.URLError(ConnectionRefusedError())),patch('worker.text_port',return_value=3):release_text(dict(model='mlx:chosen',port=2),Mock())
 def test_timeout_is_not_mistaken_for_no_model(self):
  with patch('urllib.request.urlopen',side_effect=TimeoutError()),patch('worker.text_port',return_value=3):
   with self.assertRaises(RuntimeError):release_text(dict(model='mlx:chosen',port=2),Mock())
