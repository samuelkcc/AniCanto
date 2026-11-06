"""Verify native-rate sentence joins without changing chosen source recordings."""
import array,copy,hashlib,json,shutil,subprocess,sys,tempfile,unittest,wave
from pathlib import Path
from unittest.mock import Mock
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows')]
import pcm_mix,dubbing
from desktop_state import Store,read

def run(args):return subprocess.check_output([str(x) for x in args],stderr=subprocess.PIPE)

class SentenceEdges378(unittest.TestCase):
 def test_short_original_and_voice_edges_preserve_interior_and_length(self):
  for rate in [24000,32000,44100,48000]:
   for original in [False,True]:
    for frames in [0,1,3,40,rate]:
     before=array.array('h',[12000])*frames;out,count=pcm_mix.edge_envelope(before,rate,original)
     self.assertEqual(len(out),frames);self.assertEqual(before,array.array('h',[12000])*frames)
     if count:self.assertEqual(out[0],0);self.assertEqual(out[-1],0);self.assertEqual(out[count:-count],before[count:-count])
     else:self.assertEqual(out,before)
 def test_new_submission_freezes_policy_and_resume_keeps_old_request(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source=root/'fixture.mkv';source.write_bytes(b'isolated fixture');store=Store(root);store.add([source]);row=store.queue[0];path=store.submit(row)
   request=read(path);self.assertEqual(request['audioEdgeEnvelopeRevision'],pcm_mix.EDGE_REVISION)
   for key in ['aiAutoFix','repairExcessiveAudibleOverlap','strictSpeechTiming']:self.assertFalse(request.get(key,False))
   request.pop('audioEdgeEnvelopeRevision');request['recoverySpentSeconds']=77;path.write_text(json.dumps(request));before=path.read_bytes();row['status']='paused';self.assertEqual(store.submit(row),path);self.assertEqual(path.read_bytes(),before)
 @unittest.skipUnless(shutil.which('ffmpeg'),'Actual PCM decoding needs FFmpeg')
 def test_actual_render_reduces_opposite_polarity_join_without_trim_or_retake(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);rate=24000;paths=[]
   for i,value in enumerate([12000,-12000]):
    path=root/f'take{i}.wav'
    with wave.open(str(path),'wb') as f:f.setparams((1,2,rate,0,'NONE','not compressed'));f.writeframes((array.array('h',[value])*9600).tobytes())
    paths.append(path)
   hashes=[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
   cues=[dict(start=.2+i*.4,end=.6+i*.4,cantonese='一齊出發',speakerId='own'+str(i)) for i in range(2)]
   snapshots=[]
   for name,enabled in [('legacy',False),('current',True)]:
    job=root/name;job.mkdir();cfg=dict(duration=1.4,ffmpeg=shutil.which('ffmpeg'),audioSampleRate=rate,speechRatePolicy='natural',autoFit=False)
    if enabled:cfg['audioEdgeEnvelopeRevision']=pcm_mix.EDGE_REVISION
    report=[dict(index=i+1,start=c['start'],end=c['end'],seconds=.4,slot=.4) for i,c in enumerate(cues)]
    out,_=dubbing.render_complete_preview(cfg,job,copy.deepcopy(cues),paths,report,run,Mock())
    with wave.open(str(out),'rb') as f:self.assertEqual(f.getnframes(),33600);samples=array.array('h');samples.frombytes(f.readframes(f.getnframes()))
    snapshots.append(samples)
    self.assertTrue(all(row['renderedSeconds']==.4 and row['rate']==1 for row in report))
   boundary=14400
   self.assertEqual(snapshots[0][boundary]-snapshots[0][boundary-1],-24000)
   self.assertEqual(snapshots[1][boundary]-snapshots[1][boundary-1],0)
   self.assertEqual(snapshots[1][6000:13000],snapshots[0][6000:13000])
   self.assertEqual([hashlib.sha256(p.read_bytes()).hexdigest() for p in paths],hashes)
if __name__=='__main__':unittest.main()
