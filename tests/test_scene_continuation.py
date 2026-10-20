import copy,json,sys,tempfile,unittest,subprocess,wave,math,array
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import hybrid_script as h,source_evidence as s,worker,dubbing

class SceneContinuationTests(unittest.TestCase):
 def test_whitespace_does_not_invalidate_same_timed_quote(self):
  cap=dict(id='caption_2',start=155.5,end=159.5,text='以及独一无二的大秘宝 「ONE PIECE」')
  turn=dict(id='2',start=155.52,end=155.86,caption=cap['text'],caption_records=[cap],japanese='そして、')
  assignment={'2':dict(content='以及独一无二的大秘宝「ONE PIECE」',caption_ids=['caption_2'])}
  quote=dict(evidence_id='2',quote=assignment['2']['content'])
  self.assertTrue(s.grounded_line('2',quote,[turn],assignment))
  self.assertTrue(s.grounded_line('2',dict(quote,evidence_id='caption_2'),[turn],assignment))
  self.assertFalse(s.grounded_line('2',dict(quote,quote='以及其他大秘宝「ONE PIECE」'),[turn],assignment))
  self.assertFalse(s.grounded_line('2',dict(quote,evidence_id='3'),[turn],assignment))
  self.assertFalse(s.grounded_line('2',quote,[dict(turn,start=160,end=161)],assignment))

 def test_saved_response_revalidated_without_another_model_request(self):
  context=[dict(id='1',start=1,end=2,japanese='はい。',caption='')]
  good=dict(cantonese='係呀。',evidence_id='1',quote='はい。',uncertain=False)
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);(job/'script-invalid-0.json').write_text(json.dumps(dict(response={'1':good})))
   w=SimpleNamespace(emit=Mock(),traditional_cantonese=worker.traditional_cantonese,atomic_json=worker.atomic_json,parse_editor_response=json.loads,ollama_chat=Mock(side_effect=AssertionError('Unexpected model request')))
   result=h.complete_lines(w,{},job,'script','prompt',dict(dialogue=context),{'1':dict(cantonese='',uncertain=True,skipped=True)},['1'],[{}],dict(properties={'1':{}},required=['1']))
   self.assertEqual(result['1'],good);w.ollama_chat.assert_not_called()

 def test_actual_strict_text_cleaner_does_not_stop_later_scenes(self):
  cues=[dict(start=0,end=1,text='はい。',japanese='はい。',asrConfidence=.9),dict(start=2,end=3,text='え？',japanese='え？',asrConfidence=.9),dict(start=10,end=11,text='進め。',japanese='進め。',asrConfidence=.9)]
  before=[(c['start'],c['end']) for c in cues]
  def chat(port,model,messages,schema,**kw):
   if 'summary' in schema['properties']:return json.dumps(dict(summary='場景',uncertainties=[]))
   data=json.loads(messages[1]['content']);turns={r['id']:r for r in data['dialogue']}
   return json.dumps({k:dict(cantonese='' if k=='2' else '繼續。',evidence_id=k,quote=turns[k]['japanese'],uncertain=False) for k in schema['properties']})
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);w=SimpleNamespace(emit=Mock(),traditional_cantonese=worker.traditional_cantonese,atomic_json=worker.atomic_json,parse_editor_response=json.loads,ollama_chat=chat)
   h.render(w,dict(port=1,model='test',continueOnError=True),job,cues)
   self.assertEqual(cues[1]['cantonese'],'');self.assertTrue(cues[1]['hybridEvidence']['skipped'])
   self.assertEqual(cues[2]['cantonese'],'繼續。');self.assertEqual([(c['start'],c['end']) for c in cues],before)
   self.assertEqual(len(json.loads((job/'cues.json').read_text())),3)
   self.assertEqual(json.loads((job/'hybrid-report.json').read_text())['blocks'],2)

 def test_empty_script_requires_an_explicit_original_fallback(self):
  source=[dict(start=0,end=1,text='原文')];blank=dict(source[0],cantonese='')
  with self.assertRaises(ValueError):worker.validate_review([blank],source,1)
  fallback=dict(blank,preserveOriginalSpeech=True,originalSpeechReason='missing-script')
  selected=worker.validate_review([fallback],source,1)
  self.assertEqual(len(selected),1);self.assertTrue(selected[0]['preserveOriginalSpeech'])

 def test_render_submission_keeps_missing_script_instead_of_disabling_audio(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);cues=[dict(start=0,end=1,text='',japanese='',cantonese='',captionRecords=[])]
   cfg=dict(storage=d,duration=1,video=str(job/'source.mp4'),ttsBackend='cosyvoice3',_singleEngine=True,continueOnError=True)
   (job/'cues.json').write_text(json.dumps(cues));(job/'review.json').write_text(json.dumps(dict(config=cfg,meta={},cues=cues)))
   def synthesize(cfg,job,selected):
    self.assertEqual(len(selected),1);self.assertFalse(selected[0]['preserveOriginalSpeech']);self.assertTrue(selected[0]['missingScript'])
    self.assertEqual(selected[0]['originalSpeechReason'],'missing-script')
    self.assertTrue(selected[0].get('enabled',True));raise RuntimeError('Reached synthesis with original fallback')
   with patch.object(worker,'synthesize',side_effect=synthesize),patch('project_store.record_issue') as issue,patch('project_store.clear_issues'),patch.object(worker,'emit'):
    with self.assertRaisesRegex(RuntimeError,'Reached synthesis'):worker.render_review(dict(review=str(job/'review.json')))
    self.assertEqual(issue.call_args.args[3],'missing-script')

 def test_missing_script_never_silently_uses_japanese_even_if_source_is_audible(self):
  res=Path(__file__).parents[1]/'dist/AniCanto.app/Contents/Resources/bin'
  if not (res/'ffmpeg').is_file():self.skipTest('bundled ffmpeg required')
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);source=job/'source.wav'
   with wave.open(str(source),'wb') as w:
    w.setparams((1,2,24000,0,'NONE','not compressed'))
    # Only the correctly offset source window contains sound.
    w.writeframes(array.array('h',[0 if n<12000 else round(5000*math.sin(n*2*math.pi*440/24000)) for n in range(48000)]).tobytes())
   cfg=dict(storage=d,ffmpeg=str(res/'ffmpeg'),ffprobe=str(res/'ffprobe'),video=str(source),startOffset=.5,duration=1,ttsBackend='cosyvoice3',continueOnError=True,autoFit=True,previewLooseTiming=True,voiceProfiles=[])
   cue=dict(start=0,end=.4,text='はい',japanese='はい',cantonese='',preserveOriginalSpeech=True,originalSpeechReason='missing-script')
   def run(args):return subprocess.run([str(a) for a in args],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
   with patch.object(dubbing,'model_job',side_effect=AssertionError('No TTS should generate an empty script')):
    audio,warnings=dubbing.synthesize(cfg,job,[cue],run,Mock())
   with wave.open(str(audio),'rb') as wav:pcm=array.array('h');pcm.frombytes(wav.readframes(wav.getnframes()))
   self.assertEqual(max(abs(x) for x in pcm),0)
   timing=json.loads((job/'timing.json').read_text());self.assertTrue(timing[0]['skipped']);self.assertEqual(timing[0]['renderedSeconds'],0)
