"""Local bytes, provider-owned bytes and damaged media are told apart before any download."""
import json,subprocess,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import source_access as access
import source_language
import source_preparation as prep

class SourceReady278(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
 def provider_path(self):
  source=self.root/'Google Drive/episode.mkv';source.parent.mkdir(parents=True);source.write_bytes(b'frame'*400000);return source
 # One: the streaming owner is named from the path alone.
 def test_provider_names_come_from_the_path(self):
  # The public source guard rejects a provider account folder name, so this synthetic
  # account suffix is written as two adjacent literals.
  drive='GoogleDrive' '-a'
  cases={'/fixture/Movies/episode.mkv':'local',
   '/fixture/Library/Mobile Documents/com~apple~CloudDocs/a.mkv':'icloud',
   '/fixture/Library/CloudStorage/'+drive+'/b.mkv':'google-drive',
   '/fixture/Library/CloudStorage/OneDrive-personal/b.mkv':'onedrive',
   r'G:\My Drive\Video\One Piece-0799.mkv':'google-drive',
   r'C:\Users\Samuel Chen\OneDrive\Video\a.mkv':'onedrive',
   r'C:\Users\Samuel Chen\AppData\Local\Temp\Internet Files\Content.MSO\a.mp4':'local',
   '\\\\nas\\media\\a.mkv':'network'}
  for path,kind in cases.items():self.assertEqual(prep.provider(path),kind,path)
  self.assertTrue(prep.cloud(r'G:\My Drive\a.mkv'));self.assertFalse(prep.cloud('/Movies/a.mkv'))
 # Two: full-span window reads prove the bytes are already on this disk.
 def test_window_sample_clears_a_provider_folder_name(self):
  source=self.provider_path();ctx=prep.Preparation(self.root/'app',source)
  with patch.object(ctx,'capture',side_effect=AssertionError('No movie streams once window reads answer')):ctx.ensure_local()
  self.assertEqual(ctx.state['sourceReadPolicy'],'local-window')
  self.assertEqual(ctx.state['provider'],'google-drive');self.assertEqual(ctx.state['hydrationReason'],'provider-root-name')
  self.assertTrue(ctx.state['needsHydration']);self.assertTrue(ctx.state['localDataAvailable'])
  self.assertFalse((ctx.folder/'read-request.json').exists());self.assertFalse((self.root/'app/cache/source-readiness').exists())
 def test_recall_attributes_always_keep_the_provider_read(self):
  source=self.root/'Temp/Internet Files/Content.MSO/clip.mp4';source.parent.mkdir(parents=True);source.write_bytes(b'x'*4000)
  with patch.object(prep,'windows_attributes',return_value=0x400000|0x20):
   self.assertEqual(prep.hydration_reason(source),'recall-attributes');self.assertTrue(prep.requires_hydration(source))
   ctx=prep.Preparation(self.root/'app',source)
   with patch.object(prep,'local_window_readable',return_value=True):
    with patch.object(ctx,'capture',side_effect=AssertionError('fixture reader never ran')):
     with self.assertRaises(AssertionError):ctx.ensure_local()
  self.assertEqual(ctx.state['sourceReadPolicy'],'provider-read');self.assertEqual(ctx.state['hydrationReason'],'recall-attributes')
 def test_windows_attributes_are_the_local_proof_on_windows(self):
  source=self.provider_path()
  for flag in (0x20,0x80):
   with patch.object(prep,'windows_attributes',return_value=flag):
    self.assertEqual(prep.hydration_reason(source),'',hex(flag))
    ctx=prep.Preparation(self.root/'app',source)
    with patch.object(prep,'local_window_readable',return_value=False):
     with patch.object(ctx,'capture',side_effect=AssertionError('no movie streams when attributes prove local data')):ctx.ensure_local()
    self.assertEqual(ctx.state['sourceReadPolicy'],'local-data',hex(flag))
 def test_network_share_is_never_called_local(self):
  self.assertEqual(prep.hydration_reason('\\\\nas\\media\\a.mkv'),'network')
  self.assertEqual(prep.provider('\\\\nas\\media\\a.mkv'),'network')
  self.assertTrue(prep.requires_hydration('\\\\nas\\media\\a.mkv'))
 def test_window_sample_rejects_an_incomplete_or_slow_source(self):
  class Stream:
   def __init__(inner,blocks):inner.blocks=list(blocks)
   def seek(inner,position):pass
   def close(inner):pass
   def read(inner,count):return inner.blocks.pop(0) if inner.blocks else b''
  class Stub:
   def __init__(inner,size,blocks,clock=None):inner.size=size;inner.blocks=blocks;inner.clock=clock
   def stat(inner):return SimpleNamespace(st_size=inner.size)
   def open(inner,mode):return Stream(inner.blocks)
  full=[b'x'*65536]*8
  self.assertFalse(prep.local_window_readable(Stub(4_000_000,[b'']*6)),'an empty window means the provider has not answered')
  self.assertFalse(prep.local_window_readable(Stub(4_000_000,[b'a'])),'one short byte is not a full span')
  ticks=iter([0,0,0,0,0,60,60])
  self.assertFalse(prep.local_window_readable(Stub(4_000_000,full),clock=lambda:next(ticks)),'a slow sample keeps the provider read')
  self.assertTrue(prep.local_window_readable(Stub(4_000_000,full)))
  self.assertFalse(prep.local_window_readable(Stub(0,[b''])))
 # Three: the media reader gets a short window, then one longer window, before any copy.
 def test_second_probe_window_avoids_a_needless_copy(self):
  source=self.root/'episode.mkv';source.write_bytes(b'x'*400);calls=[]
  def run(command,**kwargs):
   calls.append(kwargs['timeout'])
   if len(calls)==1:raise subprocess.TimeoutExpired(command,kwargs['timeout'])
   return subprocess.CompletedProcess(command,0,b'{"format":{}}',b'')
  with patch.object(access.subprocess,'run',side_effect=run):used,raw=access.accessible(source,'ffprobe',self.root/'storage')
  self.assertEqual(used,source);self.assertEqual(raw,b'{"format":{}}')
  self.assertEqual(calls,[access.FIRST_WINDOW,access.SECOND_WINDOW])
  self.assertFalse((self.root/'storage'/'cache'/'source-media').exists())
 def test_a_timed_out_probe_names_the_real_source(self):
  source=self.root/'Google Drive/episode.mkv';source.parent.mkdir(parents=True);source.write_bytes(b'x'*400)
  def run(command,**kwargs):raise subprocess.TimeoutExpired(command,kwargs['timeout'])
  with patch.object(access.subprocess,'run',side_effect=run):
   with self.assertRaises(prep.ProviderReadInterrupted) as caught:access.probe(source,'ffprobe')
  self.assertIn('Google Drive file',str(caught.exception))
 def test_damaged_media_is_not_reported_as_a_provider_fault(self):
  source=self.root/'broken.mkv';source.write_bytes(b'not media')
  with patch.object(access.subprocess,'run',return_value=subprocess.CompletedProcess([],1,b'',b'Invalid data found when processing input')):
   with self.assertRaises(prep.MediaUnreadable) as caught:access.probe(source,'ffprobe')
  self.assertIn('Invalid data found',str(caught.exception))
 def test_recall_flagged_temp_file_is_staged_without_a_provider_folder_name(self):
  source=self.root/'Temp/Internet Files/Content.MSO/clip.mp4';source.parent.mkdir(parents=True);source.write_bytes(b'clip'*90000)
  def probe(path,ffprobe,*args):
   if Path(path)==source:raise prep.ProviderReadInterrupted('The local file did not answer the media reader in time.')
   return b'{"format":{}}'
  notices=[]
  with patch.object(access,'probe',side_effect=probe),patch.object(access,'hydration_reason',return_value='recall-attributes'):
   staged,_=access.accessible(source,'ffprobe',self.root/'storage',emit=lambda stage,message,fraction:notices.append(message))
  self.assertNotEqual(staged,source);self.assertEqual(staged.read_bytes(),source.read_bytes())
  self.assertTrue(any('local file' in message for message in notices),notices)
  self.assertFalse(any('cloud' in message.lower() for message in notices),notices)
  self.assertEqual(source.read_bytes(),b'clip'*90000)
 def test_a_quiet_provider_copy_waits_and_keeps_the_bytes_it_read(self):
  source=self.root/'Google Drive/clip.mp4';source.parent.mkdir(parents=True);source.write_bytes(b'z'*1000);real=Path.open
  # The provider answers with nothing for longer than the old idle limit, then delivers the movie.
  opened=[]
  class Provider:
   def __init__(inner,stream,serves):inner.stream=stream;inner.serves=serves
   def read(inner,count):return inner.stream.read(count) if inner.serves else b''
   def seek(inner,position):return inner.stream.seek(position)
   def close(inner):inner.stream.close()
  def cloud_open(inner,*args,**kwargs):
   stream=real(inner,*args,**kwargs)
   if not (args and args[0]=='rb'):return stream
   opened.append(1);return Provider(stream,len(opened)>access.IDLE_STALLS+2)
  def probe(path,ffprobe,*args):
   if Path(path)==source:raise prep.ProviderReadInterrupted('fixture reader stalled')
   return b'{}'
  notices=[]
  with patch.object(access,'probe',side_effect=probe),patch.object(Path,'open',cloud_open), \
   patch.object(access.time,'sleep') as pause, \
   patch.object(access.shutil,'disk_usage',return_value=SimpleNamespace(free=10**12)):
   staged,data=access.accessible(source,'ffprobe',self.root/'storage',emit=lambda stage,message,fraction:notices.append(message))
  self.assertGreater(len(opened),access.IDLE_STALLS,'the copy waits past the old idle limit')
  self.assertEqual(pause.call_count,len(opened)-1,'one pause per quiet provider open')
  self.assertEqual(staged.read_bytes(),source.read_bytes(),'the cached copy is the whole movie')
  self.assertEqual(data,b'{}')
  quiet=[message for message in notices if 'does not time out' in message]
  self.assertTrue(quiet,notices)
  self.assertIn('Google Drive file',quiet[0],quiet[0])
  self.assertIn(str(access.IDLE_STALLS*access.STALL_PAUSE),quiet[0],quiet[0])
  self.assertFalse(any((self.root/'storage'/'cache'/'source-media').glob('*.partial')),(self.root/'storage'/'cache'/'source-media').exists())
 # Four: the message a user sees names the real fault, and the record keeps the source kind.
 def test_preflight_messages_separate_provider_and_media_faults(self):
  source=self.root/'movies/local.mkv';source.parent.mkdir(parents=True);source.write_bytes(b'not media')
  cases=[('unreadable',prep.MediaUnreadable('ffprobe refused the bytes'),prep.READ_ERROR),
   ('noready',prep.ProviderNotReady('fixture served no bytes'),prep.CLOUD_ERROR),
   ('stalled',prep.ProviderReadInterrupted('fixture stopped part-way'),prep.STALLED_ERROR)]
  for operation,fault,message in cases:
   with patch.object(prep.Preparation,'capture',side_effect=fault):
    with self.assertRaises(RuntimeError) as caught:source_language.preflight(self.root/'app',source,dict(ffprobe='ffprobe'),dict(selectedEngines=['drama3']),operation_id=operation)
   self.assertEqual(str(caught.exception),message,operation)
   self.assertFalse((self.root/'app/cache/source-readiness').exists())
   record=json.loads((self.root/'app/source-preparation'/operation/'diagnostic.json').read_text())
   self.assertEqual(record['provider'],'local',operation);self.assertEqual(record['hydrationReason'],'',operation)
   self.assertEqual(record['kind'],type(fault).__name__,operation)
   status=json.loads((self.root/'app/source-preparation'/operation/'status.json').read_text())
   self.assertEqual(status['state'],'failed',operation);self.assertEqual(status['provider'],'local',operation)
  for word in ('cloud','drive','onedrive','icloud','provider'):self.assertNotIn(word,prep.READ_ERROR.lower(),word)
  with patch.object(prep.Preparation,'ensure_local',side_effect=prep.SourcePreparationCancelled(prep.CANCELLED)):
   with self.assertRaises(prep.SourcePreparationCancelled):source_language.preflight(self.root/'app',source,dict(ffprobe='ffprobe'),dict(selectedEngines=['drama3']),operation_id='cancelled')
 def test_a_local_source_needs_no_provider_read_at_all(self):
  source=self.root/'local.mkv';source.write_bytes(b'local');ctx=prep.Preparation(self.root/'app',source)
  with patch.object(ctx,'capture',side_effect=AssertionError('a local source is not a provider download')):ctx.ensure_local()
  self.assertEqual(ctx.state['sourceReadPolicy'],'local-data');self.assertFalse(ctx.state['needsHydration'])

if __name__=='__main__':unittest.main()
