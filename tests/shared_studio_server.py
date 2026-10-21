"""Local UI acceptance fixture. Uses real state/draft RPC and real media.

Deployment/progress events are explicitly simulated: this is not a GPU or model
inference acceptance test. The packaged desktop has no fixture transport.
"""
import json,os,sys,threading,wave
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from urllib.parse import urlparse,parse_qs,unquote
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'studio'),str(ROOT/'windows'),str(ROOT/'Resources')]
from backend import Studio
from desktop_state import write,read,defaults
out=ROOT/'.build/shared-studio-qa';out.mkdir(exist_ok=True)
data=out/'SamCantoSync';data.mkdir(exist_ok=True)
source=ROOT/'.build/windows/desktop-qa/日本語 episode 01.mp4'
if not source.is_file():raise SystemExit('Run tests/windows_desktop_qa.py to prepare the six-second test clip.')
candidate=Path(os.environ.get('ANICANTO_QA_APP',str(ROOT/'dist/AniCanto.app')))
shared=candidate/'Contents/Resources'
helper=candidate/'Contents/MacOS/AniCanto-worker'
app=Studio(data,shared,helper=helper)
from use_terms import document
app.dispatch('accept-use-terms',dict(accepted=True,sha256=document()['sha256'],language='en'))
app.store.queue=[];app.store.selected=None;app.store.settings=defaults();app.store.add([str(source)])
row=app.store.row();folder=data/'jobs/fixture';folder.mkdir(parents=True,exist_ok=True)
cfg=dict(defaults(),video=str(source),duration=6,voiceProfiles=[dict(id='R01',name='R01 · test role',reference=str(folder/'voice.wav'),promptText='こんにちは。',identityStatus='independent')])
review=dict(config=cfg,cues=[dict(start=.25,end=2,text='こんにちは。',japanese='こんにちは。',cantonese='你好呀。',english='Hello there.',speakerId='R01'),dict(start=2.2,end=4.5,text='また会いましょう。',cantonese='我哋下次再見啦。',english='See you next time.',speakerId='R01')])
write(folder/'review.json',review)
with wave.open(str(folder/'voice.wav'),'wb') as wav:wav.setparams((1,2,24000,0,'NONE','not compressed'));wav.writeframes(b'\0\0'*48000)
write(folder/'timing.json',[dict(start=.25,end=2,audio=str(folder/'voice.wav'),index=1),dict(start=2.2,end=4.5,audio=str(folder/'voice.wav'),index=2)])
write(folder/'audio-preview.json',dict(engine='drama3',language='yue'))
write(folder/'segment-issues.json',[dict(index=1,reason='generation-limit',text='A retained incomplete test take')])
write(folder/'production-progress.json',dict(version=1,job=str(folder),progress=.55,complete=False,milestones=[dict(id=k,state='complete' if i<4 else 'running' if i==4 else 'pending',seconds=i*12.3) for i,k in enumerate(['prepare','recognition','roles','translation','voice','repair','export'])]))
write(folder/'processing-time.json',dict(seconds=215.5,currentRunSeconds=105,runs=[]))
row.update(status='paused',review=str(folder/'review.json'),job=str(folder),progress=.55);app.store.save()
lock=threading.Lock()

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kw):super().__init__(*args,directory=str(ROOT/'studio/web'),**kw)
    def log_message(self,*args):pass
    def do_GET(self):
        parsed=urlparse(self.path)
        if parsed.path=='/media':
            path=Path(parse_qs(parsed.query)['path'][0]).resolve()
            if not (path.is_relative_to(data.resolve()) or path==source.resolve()):self.send_error(403);return
            self.path='/'+path.name
            # SimpleHTTPRequestHandler supports serving an explicit resolved
            # fixture file; no arbitrary filesystem route is exposed.
            self.translate_path=lambda _:str(path)
        super().do_GET()
    def do_POST(self):
        try:
            p=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            name=p['name'];args=p.get('args',{})
            with lock:
                if name=='studio_rpc' and args.get('op')=='source-language':
                    result=dict(language='ja',name='Japanese',supported=True,needsConfirmation=False,token='fixture-japanese')
                elif name=='studio_status':result=dict(runtimeReady=True,running=None,storage=str(data))
                elif name=='studio_pick':result=[]
                elif name=='studio_start':
                    app.dispatch('configure',dict(settings=dict(ttsBackend=args.get('params',{}).get('engine','drama3'))))
                    result=dict(id='fixture-setup')
                elif name=='studio_media':result=dict(path=str(source),duration=6,streams=[])
                elif name=='studio_rpc':
                    op=args['op']
                    if op=='plan':result=dict(canDeployModels=True,memoryBudgetGB=48,systemReserveGB=9.6,systemMemoryBudgetGB=48,hardware=dict(platform='macos',backend='metal',memoryGB=64,acceleratorBudgetGB=48),roles=dict(text='mlx:qwen3.5-4b:4bit',voice='v2ProPlus'),engine=args.get('params',{}).get('engine','drama3'),modelDownloadBytes=3_200_000_000,blockers=[],downloads=[dict(id='qwen4b',title='Qwen 4B',purposeKey='text-translation',bytes=3_000_000_000,installed=False),dict(id='audio-classifier',title='AudioSet',purposeKey='audio-classification',bytes=200_000_000,installed=True)])
                    elif op=='licenses':result=[dict(name='Fixture library',version='1.0',license='MIT',text='TEST NOTICE')]
                    else:result=app.dispatch(op,args.get('params',{}))
                else:raise ValueError('This UI fixture does not execute native model tasks: '+name)
            raw=json.dumps(dict(result=result),ensure_ascii=False).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        except Exception as error:
            raw=json.dumps(dict(error=str(error))).encode();self.send_response(400);self.end_headers();self.wfile.write(raw)

if __name__=='__main__':
    # Chromium loads ES modules concurrently; the default five-connection
    # backlog can reset a module request before the app has even rendered.
    ThreadingHTTPServer.request_queue_size=64
    ThreadingHTTPServer(('127.0.0.1',int(sys.argv[1]) if len(sys.argv)>1 else 18732),Handler).serve_forever()
