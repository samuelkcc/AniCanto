"""Drama sampling defaults, persisted overrides and submission isolation."""
import sys,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows'),str(ROOT/'studio')]
import voice_parameters as parameters
from desktop_state import Store
from backend import Studio
import speech_library

class DramaDefaultsTests(unittest.TestCase):
 def test_mac_and_windows_sampling_use_new_defaults_and_keep_custom_values(self):
  self.assertEqual(parameters.drama_sampling({}),dict(temperature=1.,top_p=.9,top_k=30))
  self.assertEqual(parameters.drama_sampling(dict(dramaTemperature=.7,dramaTopP=.7,dramaTopK=12)),dict(temperature=.7,top_p=.7,top_k=12))
  self.assertEqual(parameters.overrides({},'drama3'),{})
  self.assertEqual(parameters.overrides(dict(dramaTemperature=.7),'drama3'),dict(dramaTemperature=.7))
 def test_parameter_range_reports_rejected_value_without_overwriting_saved_preferences(self):
  with tempfile.TemporaryDirectory() as d:
   studio=Studio(d);studio.dispatch('configure',dict(settings=dict(dramaTemperature=.55,dramaTopP=.8,dramaTopK=18)))
   before=studio.store.path.read_bytes()
   with self.assertRaisesRegex(ValueError,'0.3–1.2; default 1'):
    studio.dispatch('configure',dict(settings=dict(dramaTemperature=.1)))
   self.assertEqual(studio.store.path.read_bytes(),before)
   again=Studio(d);self.assertEqual(parameters.drama_sampling(again.store.settings),dict(temperature=.55,top_p=.8,top_k=18))
   again.dispatch('configure',dict(settings=parameters.defaults('drama3')))
   self.assertEqual(parameters.drama_sampling(Studio(d).store.settings),dict(temperature=1.,top_p=.9,top_k=30))
 def test_new_submissions_keep_their_snapshot_when_defaults_change(self):
  with tempfile.TemporaryDirectory() as d:
   store=Store(d);store.add([str(Path(d)/'fixture.mkv')]);store.settings.update(dramaTemperature=.7,dramaTopP=.7,dramaTopK=30)
   request=store.submit(store.row());original=request.read_bytes()
   store.settings.update(parameters.defaults('drama3'));store.save()
   self.assertEqual(request.read_bytes(),original)
   self.assertEqual(parameters.drama_sampling(json.loads(original)),dict(temperature=.7,top_p=.7,top_k=30))
   store.add([str(Path(d)/'new.mkv')]);new=store.submit(store.queue[-1])
   self.assertEqual(parameters.drama_sampling(json.loads(new.read_text())),dict(temperature=1.,top_p=.9,top_k=30))
 def test_standalone_parameter_inventory_and_future_take_defaults(self):
  with tempfile.TemporaryDirectory() as d:
   listing=speech_library.listing(d)
   self.assertEqual({k:v['default'] for k,v in listing['parameters']['drama3'].items()},parameters.defaults('drama3'))
   request=speech_library.submit(d,{},dict(action='generate',cantonese='你好呀。',engine='drama3'))
   self.assertEqual(parameters.drama_sampling(json.loads(request.read_text())),dict(temperature=1.,top_p=.9,top_k=30))
   custom=speech_library.submit(d,{},dict(action='generate',cantonese='你好呀。',engine='drama3',parameters=dict(dramaTemperature=.65)))
   self.assertEqual(parameters.drama_sampling(json.loads(custom.read_text()))['temperature'],.65)
