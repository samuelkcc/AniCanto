import sys,json,tempfile,unittest,copy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows'),str(ROOT/'studio')]
from atomic_files import write_json
import translation_source as source
import desktop_debug as debug
import source_performance as performance

class ReliabilityTests(unittest.TestCase):
 def test_resume_recovers_ocr_without_changing_approved_script_clock_or_audio(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);write_json(job/'input-source.json',dict(ocrError='Vision failed'))
   old=[dict(start=2,end=3,cantonese='已接受',english='Accepted',speakerId='same',editorAudio='saved.wav')]
   w=SimpleNamespace(atomic_json=write_json,emit=lambda *a,**k:None,extract_cues=lambda *a:[dict(start=2,end=2.5,text='字幕')])
   cfg=dict(ocr=True);new=source.refresh_saved_evidence(w,cfg,job,old,{})
   for k,v in old[0].items():self.assertEqual(new[0][k],v)
   self.assertEqual(new[0]['subtitleHint'],'字幕');self.assertNotIn('_ocrSpeechWindows',cfg)
   self.assertIsNone(json.loads((job/'input-source.json').read_text())['ocrError'])
 def test_resume_failures_have_a_persistent_budget(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);write_json(job/'ocr-status.json',dict(status='failed'));calls=[]
   def fail(*a):calls.append(1);raise RuntimeError('bad helper')
   w=SimpleNamespace(atomic_json=write_json,emit=lambda *a,**k:None,extract_cues=fail)
   for _ in range(4):source.refresh_saved_evidence(w,dict(ocr=True),job,[dict(start=0,end=1)],{})
   self.assertEqual(len(calls),2)
 def test_large_json_is_parseable_and_declares_omitted_complete_entries(self):
  value=dict(error='critical',rows=[dict(index=i,data='x'*100) for i in range(100)])
  text,omitted=debug.bounded_json(value,2500);result=json.loads(text)
  self.assertLessEqual(len(text.encode()),2500);self.assertTrue(omitted);self.assertEqual(result['data']['error'],'critical')
  self.assertEqual(value['rows'][-1]['index'],99)
 def test_windows_receipts_capture_different_voice_backend_driver_and_failure(self):
  from backend import Studio
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);a=Studio(root,ROOT/'Resources',platform='win32')
   write_json(root/'native-ready.json',dict(backend='cuda',voiceBackend='cpu',cudaFailure='voice allocation failed',hardware=dict(acceleratorName='GPU',cudaDriverVersion='580.1',physicalMemoryBytes=123)))
   write_json(root/'gpu-runtime-selection.json',dict(torchIndex='cu126',kernelPassed=True))
   a.store.settings['apiKey']='PRIVATE_KEY';text=a.debug_report()
   for v in ['voice allocation failed','580.1','cu126','voiceBackend','physicalMemoryBytes']:self.assertIn(v,text)
   self.assertNotIn('PRIVATE_KEY',text);self.assertIn('@export-manifest',text)
 def test_ocr_failure_in_previous_attempt_is_exported(self):
  from backend import Studio
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);a=Studio(root,ROOT/'Resources',platform='darwin');row=dict(id='one',job=str(root/'jobs/one'),attempt={})
   a.store.queue=[row];a.store.selected='one'
   write_json(root/'jobs/one/input-source.json',dict(ocrError='CRImageReaderError'))
   p=root/'attempts/one/previous';p.mkdir(parents=True);(p/'process.log').write_text('{"stage":"OCR 提示","message":"failed"}\n')
   text=a.debug_report();self.assertIn('CRImageReaderError',text);self.assertIn('previous',text)
 def test_repeated_vowels_need_paired_sound_evidence_and_meaningful_captions_veto(self):
  c=dict(start=1,end=3,japanese='ああああ')
  rows=[dict(start=0,duration=4,screaming=.9,speech=.01,singing=.01)]
  self.assertEqual(performance.decision(c,rows,rows,{}),'confirmed-nonlexical-performance')
  self.assertIsNone(performance.decision(c,rows,[],{}))
  self.assertIsNone(performance.decision(dict(c,subtitleHint='救命啊'),rows,rows,{}))
 def test_singing_needs_paired_evidence_and_respects_translate_songs(self):
  c=dict(start=1,end=3,japanese='好きよ好きよ')
  rows=[dict(start=0,duration=4,singing=.9,speech=.01)]
  self.assertEqual(performance.decision(c,rows,rows,{}),'confirmed-source-song')
  self.assertIsNone(performance.decision(c,rows,rows,dict(translateOPED=True)))
 def test_zero_length_edge_tokens_keep_complete_name(self):
  import dialogue
  rows=[dict(start=1,end=2,text='ヤッ太郎',words=[dict(start=1,end=1,word='ヤッ',probability=.9),dict(start=1,end=2,word='太',probability=.9),dict(start=2,end=2,word='郎',probability=.9)])]
  cues=dialogue.build_cues(rows,[dict(start=1,end=2)],[],5)
  self.assertEqual(cues[0]['japanese'],'ヤッ太郎')
 def test_ultrashort_source_is_not_invented_into_full_tts(self):
  import dialogue
  cues=dialogue.build_cues([dict(words=[dict(start=1,end=1.08,word='o',probability=.5)])],[dict(start=1,end=2)],[],5)
  self.assertTrue(cues[0]['sourceClockUnconfirmed']);self.assertTrue(cues[0]['preserveOriginalSpeech'])
if __name__=='__main__':unittest.main()

class MixerAndOCRTests(unittest.TestCase):
 def test_partial_scan_saves_evidence_and_failure_but_never_success_cache(self):
  import subtitle_ocr as ocr
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);video=job/'movie';video.write_bytes(b'fixture')
   def run(args):
    if '--ocr' in args:return json.dumps([dict(index=0,text='字幕',status='complete'),dict(index=1,text='',status='failed',errors=['bad image']),dict(index=2,text='完成',status='complete')]).encode()
    for t in [0,400,800]:(job/'frames-pts'/f'{t:012d}.jpg').write_bytes(b'image')
    return b''
   w=SimpleNamespace(run=run,emit=lambda *a,**k:None,atomic_json=write_json,ocr_filter=lambda c:'crop',merge_ocr_rows=lambda rows,*a,**k:[dict(start=r['time'],end=r['time']+.2,text=r['text']) for r in rows if r['text']])
   cfg=dict(video=str(video),ffmpeg='ffmpeg',executable='helper',duration=1.2,ocrEvidenceOnly=True)
   with patch.object(ocr,'discover',side_effect=lambda w,c,j:c.update(ocrRect=ocr.SEARCH)):
    rows=ocr.scan(w,cfg,job)
   self.assertEqual(len(rows),2);self.assertFalse((job/'ocr-scan.json').exists())
   self.assertEqual(json.loads((job/'ocr-status.json').read_text())['status'],'partial')
 def test_retained_overlong_take_is_not_mixed_over_next_voice(self):
  import array,math,shutil,wave,subprocess
  import fast_mode
  ff=shutil.which('ffmpeg')
  if not ff:self.skipTest('FFmpeg required')
  with tempfile.TemporaryDirectory() as d:
   job=Path(d)
   def audio(name,seconds):
    p=job/name
    with wave.open(str(p),'wb') as f:f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(array.array('h',(int(4000*math.sin(i*.12)) for i in range(round(seconds*24000)))).tobytes())
    return p
   long=audio('long.wav',3);short=audio('short.wav',.4);original=audio('original.wav',4)
   cues=[dict(start=0,end=1,japanese='長い対白',cantonese='呢句太長'),dict(start=1.2,end=2,japanese='はい',cantonese='好')]
   cfg=dict(duration=4,productionMode='normal',normalRepairPolicy='missing-only',speechRatePolicy='natural',targetLanguage='yue',automaticDurationRewrite=True,dialoguePath=str(original),ffmpeg=ff)
   run=lambda args:subprocess.check_output([str(x) for x in args],stderr=subprocess.PIPE)
   with patch('dubbing.gsv_audio',return_value=[long,short]),patch('normal_mode.repair_paths',side_effect=lambda c,j,cs,ps,*a:ps),patch('natural_delivery.repair',side_effect=lambda c,j,cs,ps,*a,**k:ps):
    fast_mode.synthesize(cfg,job,cues,run,lambda *a,**k:None)
   rows=json.loads((job/'timing.json').read_text())
   self.assertTrue(rows[0]['originalFallback']);self.assertEqual(rows[0]['failureKind'],'introduced-dialogue-overlap')
   self.assertLessEqual(rows[0]['previewRenderedStart']+rows[0]['previewAudibleSeconds'],rows[1]['renderedStart'])
   self.assertFalse(rows[1]['skipped']);self.assertTrue(long.exists())
 def test_ocr_watchdog_kills_stalled_helper_and_keeps_error(self):
  import worker,subprocess
  from unittest.mock import MagicMock
  with tempfile.TemporaryDirectory() as d:
   proc=MagicMock();proc.communicate.side_effect=[subprocess.TimeoutExpired('ocr',1),(b'',b'')];proc.poll.return_value=None
   with patch.object(worker.subprocess,'Popen',return_value=proc),patch.object(worker.time,'monotonic',side_effect=[0,91]):
    with self.assertRaisesRegex(RuntimeError,'without progress'):worker.run_ocr_tool(['helper','--ocr',d])
   proc.kill.assert_called_once();self.assertTrue((Path(d)/'ocr-helper-error.log').is_file())
