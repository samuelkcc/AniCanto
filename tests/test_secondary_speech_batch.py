import json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import secondary_speech as speech
import cantonese_review as review
from speechcheck import evidence

class SecondaryBatchTests(unittest.TestCase):
 def test_uncached_witnesses_share_one_model_process_and_resume_uses_evidence(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);items=[]
   for i in range(30):
    folder=root/str(i);folder.mkdir();audio=folder/'audio.wav';audio.write_bytes(('unique'+str(i)).encode());items.append((folder,audio))
   def write(p,o):Path(p).write_text(json.dumps(o))
   requests=[]
   def run(args):
    request=json.loads(Path(args[-1]).read_text());requests.append(request)
    self.assertEqual(set(request),{'items','model','language'})
    self.assertTrue(all(set(i)=={'audio'} for i in request['items']))
    return json.dumps([dict(heard='原本嘅聲音',language='zh') for i in request['items']])
   w=SimpleNamespace(atomic_json=write,run=run)
   with patch('model_catalog.resolve',return_value=root),patch('runtime_paths.python_for',return_value='python'):
    first=speech.transcribe_batch(w,dict(storage=d),items,True)
    again=speech.transcribe_batch(w,dict(storage=d),items,True)
    self.assertEqual(first,again);self.assertEqual(len(requests),1)
    items[0][1].write_bytes(b'changed audio')
    speech.transcribe_batch(w,dict(storage=d),items,True)
   self.assertEqual(len(requests),2);self.assertEqual(len(requests[1]['items']),1)
 def test_review_batches_major_differences_and_preserves_same_decision_on_resume(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);audio=[];cues=[];checks=[]
   for i in range(20):
    path=root/f'{i}.wav';path.write_bytes(('audio'+str(i)).encode());audio.append(path)
    cue=dict(cantonese='我哋唔可以將佢留喺呢度然後一齊走');cues.append(cue)
    checks.append(evidence(cue['cantonese'],'我哋可以將佢留喺呢度然後一齊走','cantonese'))
   with patch('cantonese_alignment.verify',return_value=dict(accepted=False)),patch.object(speech,'transcribe_batch',return_value=[dict(heard=c['cantonese'],language='zh') for c in cues]) as batch,patch.object(speech,'transcribe') as single:
    one=review.review(dict(targetLanguage='yue'),root,cues,audio,checks,Mock())
    two=review.review(dict(targetLanguage='yue'),root,cues,audio,checks,Mock())
   self.assertEqual(one,two);batch.assert_called_once();single.assert_not_called()
   self.assertTrue(all(not r['confirmedContentFailure'] for r in one))
