import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import qwen_recovery,qwen_voice,dubbing

class RecoveryTests(unittest.TestCase):
 def test_punctuation_retry_keeps_words_and_is_bounded(self):
  item=dict(text="Gum Gum...",seed=42);before=copy.deepcopy(item)
  rows=qwen_voice.attempt_parameters(item)
  self.assertEqual(len(rows),3);self.assertEqual(rows[-1]['text'],'Gum Gum.');self.assertEqual(rows[-1]['seed'],104)
  self.assertEqual(len(qwen_voice.attempt_parameters(item,True)),1);self.assertEqual(item,before)
 def test_source_scream_preserved_in_english_but_not_mixed_dialogue(self):
  self.assertTrue(dubbing.is_vocalization(dict(japanese='ああ！',cantonese='Aaaah!')))
  self.assertFalse(dubbing.is_vocalization(dict(japanese='3時に俺は アーッ!',cantonese="At three o'clock, I'll... Aaaah!")))
  self.assertFalse(dubbing.is_vocalization(dict(japanese='ああ！',cantonese='Stop!')))
 def test_recovery_only_retries_missing_failed_take_and_audits_reference(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);done=p/'done.wav';done.write_bytes(b'keep');missing=p/'missing.wav';calls=[]
   items=[dict(output=str(x),profile=dict(id='role',language='ja',reference='ja.wav'),text='Mm-hmm.',reviewIndex=i) for i,x in enumerate((done,missing))]
   def run(cfg,action,request,emit):
    calls.append(copy.deepcopy(request))
    if len(calls)==1:
     (p/'qwen-results.json').write_text(json.dumps(dict(requestId=request['requestId'],items=[dict(output=str(done),status='cached'),dict(output=str(missing),status='failed')])));raise RuntimeError('generation-limit')
    missing.write_bytes(b'new')
   with patch('qwen_reference.prepare',return_value=dict(language='en',reference='en.wav',referenceProvenance='audit.json')) as prep:
    qwen_recovery.generate(dict(targetLanguage='en',qwenReferenceMode='cantonese-bridge'),p,dict(items=items),Mock(),run)
   self.assertEqual(len(calls),2);self.assertEqual(len(calls[1]['items']),1);self.assertTrue(calls[1]['recoveryAttempt']);self.assertEqual(done.read_bytes(),b'keep');self.assertTrue(prep.call_args.kwargs['allow_english'])
   audit=json.loads((p/'qwen-recovery.json').read_text());self.assertEqual(audit['items'][0]['originalReference'],'ja.wav');self.assertEqual(audit['status'],'audio-generated-needs-content-check')
 def test_original_only_and_stale_failure_do_not_trigger_reference_recovery(self):
  for mode,nonce in [('original',None),('cantonese-bridge','stale')]:
   with tempfile.TemporaryDirectory() as d:
    p=Path(d);item=dict(output=str(p/'a.wav'),profile=dict(language='ja'))
    def run(cfg,action,request,emit):
     (p/'qwen-results.json').write_text(json.dumps(dict(requestId=nonce or request['requestId'],items=[dict(output=item['output'],status='failed')])));raise RuntimeError('original error')
    with patch('qwen_reference.prepare') as prep,self.assertRaisesRegex(RuntimeError,'original error'):
     qwen_recovery.generate(dict(targetLanguage='en',qwenReferenceMode=mode),p,dict(items=[item]),Mock(),run)
    prep.assert_not_called()
 def test_reference_failure_is_visible_and_preserves_prior_takes(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);item=dict(output=str(p/'a.wav'),profile=dict(language='ja'))
   def run(cfg,action,request,emit):
    (p/'qwen-results.json').write_text(json.dumps(dict(requestId=request['requestId'],items=[dict(output=item['output'],status='failed')])));raise RuntimeError('generation-limit')
   with patch('qwen_reference.prepare',side_effect=ValueError('bad reference')),self.assertRaisesRegex(RuntimeError,'bad reference'):
    qwen_recovery.generate(dict(targetLanguage='en',qwenReferenceMode='cantonese-bridge'),p,dict(items=[item]),Mock(),run)
   self.assertEqual(json.loads((p/'qwen-recovery.json').read_text())['status'],'failed')

class BatchRecoveryStatusTests(unittest.TestCase):
 def test_manual_repair_updates_only_matching_batch_row(self):
  from multitrack import batch_completion
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);review=p/'review.json'
   (p/'batch-queue.json').write_text(json.dumps([dict(id='other',review='another.json'),dict(id='target',review=str(review),status='需要處理')]))
   self.assertEqual(batch_completion(dict(storage=d),review,False),dict(batchId='target',batchStatus='完成',review=str(review)))
   self.assertEqual(batch_completion(dict(storage=d),review,True)['batchStatus'],'需要處理')
   self.assertEqual(batch_completion(dict(storage=d),p/'unrelated.json',False),{})
 def test_batch_forward_accepts_repaired_completion_metadata(self):
  import worker
  with tempfile.TemporaryDirectory() as d:
   events=[]
   def convert(cfg):worker.emit('完成','done',1,batchId='nested',batchStatus='完成',output='fixed.mp4',review='review.json',partial=False)
   with patch.object(worker,'convert',side_effect=convert),patch.object(worker,'emit',side_effect=lambda *args,**kw:events.append((args,kw))):
    worker.batch_convert(dict(storage=d,videos=[dict(id='owner',video='a.mp4')]))
   result=next(kw for args,kw in events if args[0]=='完成')
   self.assertEqual(result['batchId'],'owner');self.assertEqual(result['batchStatus'],'完成')
