import json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows')]
import subtitle_ocr as ocr

class OCRSamplingTests(unittest.TestCase):
 def test_sparse_plan_keeps_short_turns_and_spreads_long_turns(self):
  files=[Path(f'{i*400:012d}.jpg') for i in range(4500)]
  speech=[dict(start=i*6+.2,end=i*6+2.5) for i in range(300)]
  chosen=ocr.select_speech_frames(files,speech,1800)
  self.assertLessEqual(len(chosen),1200)
  self.assertEqual(chosen,sorted(set(chosen)))
  times=[int(p.stem)/1000 for p in chosen]
  for c in speech:self.assertTrue(any(c['start']<=t<=c['end'] for t in times))
  short=ocr.select_speech_frames(files,[dict(start=1.05,end=1.25)],1800)
  self.assertEqual([int(p.stem)/1000 for p in short],[1.2])
 def test_scan_uses_actual_pts_caches_completed_results_and_invalidates_on_media_change(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);video=job/'video.mkv';video.write_bytes(b'synthetic input');calls=[];events=[]
   def run(args):
    calls.append(args)
    if '--ocr' in args:
     files=sorted(Path(args[-1]).glob('*.jpg'))
     return json.dumps([dict(index=i,text='字幕') for i,p in enumerate(files)]).encode()
    for t in range(0,10000,400):(job/'frames-pts'/f'{t:012d}.jpg').write_bytes(b'frame')
    return b''
   def discover(w,cfg,job):cfg['ocrRect']=dict(ocr.SEARCH)
   def merge(rows,duration,stable,interval):
    self.assertFalse(stable);self.assertEqual(interval,.4)
    return [dict(start=row['time'],end=row['time']+interval,text=row['text']) for row in rows]
   w=SimpleNamespace(run=run,emit=lambda *a,**k:events.append(k),ocr_filter=lambda cfg:'crop',merge_ocr_rows=merge,atomic_json=lambda p,o:p.write_text(json.dumps(o)))
   cfg=dict(video=str(video),ffmpeg='ffmpeg',executable='helper',duration=10,ocrEvidenceOnly=True,_ocrSpeechWindows=[dict(start=1,end=2)])
   with patch.object(ocr,'discover',side_effect=discover):
    result=ocr.scan(w,cfg,job);first=len(calls);again=ocr.scan(w,cfg,job)
    self.assertEqual(result,again);self.assertEqual(len(calls),first)
    self.assertTrue(any(e.get('ocrCacheReused') for e in events))
    video.write_bytes(b'changed source media');ocr.scan(w,cfg,job);self.assertGreater(len(calls),first)
   self.assertTrue(all(1<=c['start']<=2.12 for c in result))
   metrics=json.loads((job/'ocr-metrics.json').read_text());self.assertEqual(metrics['mode'],'speech-guided')
   self.assertLess(metrics['recognisedFrames'],metrics['extractedFrames'])
 def test_pure_ocr_remains_dense_and_incomplete_helper_does_not_create_success_cache(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);video=job/'v';video.write_bytes(b'v');calls=[]
   def run(args):
    calls.append(args)
    if '--ocr' in args:return b'[]'
    (job/'frames-pts/000000000000.jpg').write_bytes(b'frame');return b''
   w=SimpleNamespace(run=run,emit=lambda *a,**k:None,ocr_filter=lambda c:'crop',merge_ocr_rows=lambda *a,**k:[],atomic_json=lambda p,o:p.write_text(json.dumps(o)))
   cfg=dict(video=str(video),ffmpeg='ffmpeg',executable='helper',duration=3)
   with patch.object(ocr,'discover'):
    with self.assertRaisesRegex(ValueError,'incomplete'):ocr.scan(w,cfg,job)
   self.assertIn('0.2',calls[0][calls[0].index('-vf')+1]);self.assertFalse((job/'ocr-scan.json').exists())
 def test_windows_single_model_and_exact_duplicate_reuse_preserve_each_frame_index(self):
  from PIL import Image
  import native_tools
  with tempfile.TemporaryDirectory() as d:
   folder=Path(d)
   for i in range(3):Image.new('RGB',(100,30),'white' if i<2 else 'black').save(folder/f'{i:03d}.png')
   engine=SimpleNamespace(__call__=None)
   from unittest.mock import MagicMock
   engine=MagicMock(return_value=([[[[1,1],[90,1],[90,20],[1,20]],'字幕',.9]],None))
   factory=MagicMock(return_value=engine)
   with patch.dict(sys.modules,{'rapidocr_onnxruntime':SimpleNamespace(RapidOCR=factory)}):rows=native_tools.ocr(folder)
   factory.assert_called_once();self.assertEqual(engine.call_count,2)
   self.assertEqual([row['index'] for row in rows],[0,1,2])
   progress=json.loads((folder/'ocr-progress.json').read_text());self.assertEqual(progress['completed'],3);self.assertEqual(progress['reused'],1)

if __name__=='__main__':unittest.main()
