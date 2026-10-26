"""Test subtitle import through a packaged host, using isolated project state."""
import json,os,sys,tempfile,subprocess,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];binary=Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory(prefix='anicanto-subtitle-native-') as d:
 root=Path(d);env=dict(os.environ,CANTOSYNC_STUDIO_DATA=d,PYTHONDONTWRITEBYTECODE='1');calls=[]
 def call(op,success=True,**params):
  p=subprocess.run([str(binary),'--verify-desktop-operation'],input=json.dumps(dict(op=op,params=params))+'\n',capture_output=True,text=True,env=env,timeout=30)
  result=json.loads(p.stdout);assert result['ok'] is success,(op,result,p.stderr)
  assert 'Unsupported desktop operation' not in result.get('error',''),(op,result)
  calls.append(dict(operation=op,passed=True));return result.get('result') if success else result['error']
 ff=Path(os.environ.get('ANICANTO_TEST_FFMPEG','/opt/homebrew/bin/ffmpeg'));video=root/'fixture 030.mkv'
 subprocess.run([str(ff),'-v','error','-y','-f','lavfi','-i','color=s=64x64:r=10:d=1','-c:v','libx264',str(video)],check=True)
 first=call('add',paths=[str(video)])['selected'];other=root/'fixture 031.mkv';other.write_bytes(video.read_bytes());second=next(x['id'] for x in call('add',paths=[str(other)])['queue'] if x['video']==str(other.resolve()))
 source=Path(os.environ['ANICANTO_TEST_SUBTITLE']) if os.environ.get('ANICANTO_TEST_SUBTITLE') else root/'中文 captions.srt'
 if not source.exists():source.write_text('1\n00:00:00,100 --> 00:00:00,900\n原裝中文字幕\n',encoding='utf-8')
 original=source.read_bytes();sha=hashlib.sha256(original).hexdigest()
 state=call('set-external-subtitle',id=first,path=str(source));rows={x['id']:x for x in state['queue']}
 assert rows[first]['externalSubtitle']==str(source.resolve());assert 'externalSubtitle' not in rows[second]
 assert call('state')['queue'][0]['externalSubtitle']==str(source.resolve())
 # Public host -> saved per-film metadata -> frozen worker submission.
 sys.path[:0]=[str(ROOT/'windows'),str(ROOT/'Resources')]
 from desktop_state import Store,read
 store=Store(root/'studio',recover_running=False);store.root=root;store.path=root/'studio/desktop-state.json'
 request=read(store.submit(store.row(first)));assert Path(request['subtitle']).read_bytes()==original
 assert request['subtitleSnapshot']['sha256']==sha and request['subtitleSource']=='external'
 assert request['batchExplicitSubtitle'] and not request['batchAutoSubtitles']
 second_request=read(store.submit(store.row(second)));assert second_request['batchAutoSubtitles'] and 'subtitleSnapshot' not in second_request
 from subtitle_snapshot import verify
 verify(request)
 store.row(first)['status']='paused';store.save()
 assert 'finish this conversion' in call('set-external-subtitle',False,id=first,path=None)
 store.row(first)['status']='waiting';store.save()
 for ext in ('ass','ssa','vtt'):
  target=root/('converted subtitles.'+ext)
  subprocess.run([str(ff),'-v','error','-y','-i',str(source),str(target)],check=True)
  imported=call('set-external-subtitle',id=first,path=str(target));assert imported['queue'][0]['externalSubtitle']==str(target.resolve())
 assert 'SRT, ASS, SSA or VTT' in call('set-external-subtitle',False,id=first,path=str(video))
 empty=root/'empty.srt';empty.touch();assert 'empty' in call('set-external-subtitle',False,id=first,path=str(empty))
 cleared=call('set-external-subtitle',id=first,path=None);assert 'externalSubtitle' not in cleared['queue'][0]
 assert Path(request['subtitle']).read_bytes()==original;verify(request)
 assert source.read_bytes()==original
 report=dict(nativeSubtitleImport=True,allFourFormats=True,perFilmOnly=True,persistsOnReopen=True,workerSnapshotSHA256=sha,pausedJobProtected=True,invalidAndEmptyRejected=True,removalRestoresAuto=True,priorFrozenEvidencePreserved=True,sourceModified=False,windowsNativeRuntimeTested=False,calls=len(calls))
 if os.environ.get('ANICANTO_TEST_REPORT'):Path(os.environ['ANICANTO_TEST_REPORT']).write_text(json.dumps(report,indent=2))
 print(json.dumps(report))
