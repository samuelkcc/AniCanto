import array,copy,json,sys,tempfile,unittest,wave
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import take_reuse as reuse
import dubbing

def wav(path):
 path.parent.mkdir(parents=True,exist_ok=True)
 with wave.open(str(path),'wb') as f:
  f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(array.array('h',[1000,-1000]*12000).tobytes())

class TakeReuseTests(unittest.TestCase):
 def fixture(self,root):
  job=root/'jobs/episode';before=job/'tracks/drama3-old';after=job/'tracks/drama3-new';after.mkdir(parents=True)
  ref=root/'reference.wav';wav(ref);audio=before/'drama3-old.wav';wav(audio)
  item=dict(text='一齊出發啦！',approvedText='一齊出發啦！',reviewIndex=0,seed=42,deliveryStyle='normal',targetSeconds=None,profile=dict(id='R1',reference=str(ref),promptText='原聲',language='ja'),output=str(audio))
  old=dict(job=str(before),drama3Model='model-a',targetLanguage='yue',items=[item])
  (before/'drama3-request.json').write_text(json.dumps(old))
  new=copy.deepcopy(old);new['job']=str(after);new['items'][0]['output']=str(after/'drama3-new.wav')
  return job,audio,old,new
 def test_policy_folder_upgrade_reuses_full_take_and_preserves_source(self):
  with tempfile.TemporaryDirectory() as d:
   job,audio,old,new=self.fixture(Path(d));before=audio.read_bytes();emit=Mock()
   reuse.recover(new['job'],new,'drama3',emit)
   target=Path(new['items'][0]['output']);self.assertEqual(target.read_bytes(),before);self.assertEqual(audio.read_bytes(),before)
   self.assertTrue(target.with_suffix('.reuse.json').exists());self.assertEqual(reuse.plan(new['job'],new,'drama3'),([],1))
 def test_changed_words_seed_model_reference_language_or_explicit_rerun_do_not_reuse(self):
  for field,value in [('text','另一句'),('seed',173),('targetSeconds',2.1),('deliveryStyle','plain-whole')]:
   with self.subTest(field=field),tempfile.TemporaryDirectory() as d:
    job,audio,old,new=self.fixture(Path(d));new['items'][0][field]=value
    self.assertEqual(reuse.plan(new['job'],new,'drama3'),([],0))
  for field,value in [('targetLanguage','en'),('drama3Model','model-b'),('audioRerunToken','explicit-new-take')]:
   with self.subTest(field=field),tempfile.TemporaryDirectory() as d:
    job,audio,old,new=self.fixture(Path(d));new[field]=value
    self.assertEqual(reuse.plan(new['job'],new,'drama3'),([],0))
  with tempfile.TemporaryDirectory() as d:
   job,audio,old,new=self.fixture(Path(d));other=Path(d)/'new-reference.wav';wav(other);other.write_bytes(other.read_bytes()+b'changed')
   new['items'][0]['profile']['reference']=str(other);self.assertEqual(reuse.plan(new['job'],new,'drama3'),([],0))
 def test_failed_capped_fragmentary_and_silent_audio_never_become_full_completed_takes(self):
  for kind in ['failure','cap','fragment','silence']:
   with self.subTest(kind=kind),tempfile.TemporaryDirectory() as d:
    job,audio,old,new=self.fixture(Path(d))
    if kind=='failure':audio.with_suffix('.failure.json').write_text('{}')
    if kind=='cap':audio.with_suffix('.generation.json').write_text('{"status":"generation-limit"}')
    if kind=='fragment':
     old['items'][0]['text']='一齊';(audio.parent/'drama3-request.json').write_text(json.dumps(old))
    if kind=='silence':
     with wave.open(str(audio),'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(bytes(48000))
    self.assertEqual(reuse.plan(new['job'],new,'drama3'),([],0))
 def test_all_reused_takes_skip_model_load_in_real_orchestration_boundary(self):
  with tempfile.TemporaryDirectory() as d:
   job,audio,old,new=self.fixture(Path(d))
   with patch.object(dubbing,'_run_model_job') as execute,patch('recording_history.preserve_request'):
    dubbing._model_job({},'drama3',new,Mock())
   execute.assert_not_called()
 def test_later_repair_request_cannot_erase_original_take_inputs(self):
  with tempfile.TemporaryDirectory() as d:
   job,audio,old,new=self.fixture(Path(d));reuse.archive(old['job'],old,'drama3')
   (audio.parent/'drama3-request.json').write_text('{"items":[]}')
   self.assertEqual(len(reuse.plan(new['job'],new,'drama3')[0]),1)
   # Reusing the same mutable reference path after a user edit must not make
   # old audio appear to have been generated from the new reference bytes.
   reference=Path(new['items'][0]['profile']['reference']);reference.write_bytes(reference.read_bytes()+b'new reference')
   self.assertEqual(reuse.plan(new['job'],new,'drama3'),([],0))
