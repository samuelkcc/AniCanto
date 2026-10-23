"""Real desktop RPCs; explicitly synthetic completion fixtures, never inference QA."""
import json,os,sys,math,struct,wave,shutil,threading
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from urllib.parse import urlparse,parse_qs
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'studio'),str(ROOT/'windows'),str(ROOT/'Resources')]
from backend import Studio
from speech_library import folder,read,write
storage=Path(os.environ.get('ANICANTO_QA_ROOT',str(ROOT/'.build/speech-ui-qa'))).resolve();storage.mkdir(parents=True,exist_ok=True)
helper=storage/'fixture-helper';helper.touch();app=Studio(storage,ROOT/'Resources',helper=helper)
app.store.settings['model']='mlx:fixture-qwen';app.store.save()
from use_terms import document
app.dispatch('accept-use-terms',dict(accepted=True,sha256=document()['sha256'],language='en'))
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT/'studio/web'),**kw)
 def log_message(self,*a):pass
 def do_GET(self):
  if urlparse(self.path).path=='/media':
   p=Path(parse_qs(urlparse(self.path).query)['path'][0]).resolve()
   if not p.is_relative_to(storage):self.send_error(403);return
   self.translate_path=lambda _:str(p)
  super().do_GET()
 def do_POST(self):
  try:
   p=json.loads(self.rfile.read(int(self.headers['Content-Length'])));name=p['name'];a=p.get('args',{})
   if name=='studio_status':result=dict(runtimeReady=True,running=None)
   elif name=='studio_rpc':
    result=app.dispatch(a['op'],a.get('params',{}))
    if a['op'] in ('speech-library','speech-save','speech-select','speech-load','speech-delete','speech-rename'):
     for engine in result.get('engines',[]):engine['installed']=True # Explicit UI fixture; no native inference claim.
   elif name=='qa_export':
    info=app.dispatch('speech-export-file',dict(id=a['id']));target=storage/'exports'/(a['id']+'.wav');target.parent.mkdir(exist_ok=True);shutil.copyfile(info['path'],target);result=dict(cancelled=False,path=str(target))
   elif name=='studio_start':result=app.dispatch(a['op'],a['params']);result['id']=result['speechClipID']
   elif name=='qa_finish':
    job=folder(storage,a['id']);cfg=read(job/'request.json');spec=cfg['speechStudio'];row=read(job/'result.json')
    if a.get('fail'):row.update(status='failed',error='Explicit QA model failure fixture')
    elif spec['action']=='recognize':
     reference=job/'reference.wav'
     with wave.open(str(reference),'wb') as f:f.setparams((1,2,44100,0,'NONE','not compressed'));f.writeframes(b'\x00\x10'*176400)
     from speech_library import digest
     row.update(status='recognized',source='Hello wrongname, let us learn Cantonese.',detectedLanguage='en',reference=str(reference),referenceText='Hello Alice.',referenceSHA256=digest(reference))
    elif spec['action']=='translate':row.update(status='translated',source=spec['source'],cantonese='你好呀，我哋一齊學廣東話。')
    else:
     audio=job/'voice.wav'
     with wave.open(str(audio),'wb') as f:f.setparams((1,2,44100,0,'NONE','not compressed'));f.writeframes(b''.join(struct.pack('<h',round(4000*math.sin(i*.03))) for i in range(44100)))
     from speech_library import digest
     review=dict(status='needs-review' if a.get('needsReview') else 'passed',notes=['language-unconfirmed'] if a.get('needsReview') else [],qualityCertified=False,audioSHA256=digest(audio),parts=[])
     row.update(status='needs-review' if a.get('needsReview') else 'complete',audio=str(audio),audioSHA256=digest(audio),quality=review,source=spec['source'],cantonese=spec['cantonese'],seconds=1,segments=[dict(start=0,end=1,text=spec['cantonese'])],engine=cfg['ttsBackend'])
     if spec['mode']=='recording':
      source=Path(spec['inputAudio']);copied=job/('source'+source.suffix);shutil.copyfile(source,copied);row.update(sourceFilename=copied.name,sourceSHA256=digest(copied))
    write(job/'result.json',row);result=row
   else:raise ValueError('Unsupported fixture operation '+name)
   raw=json.dumps(dict(result=result)).encode();self.send_response(200)
  except Exception as e:raw=json.dumps(dict(error=str(e))).encode();self.send_response(400)
  self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
if __name__=='__main__':
 ThreadingHTTPServer.request_queue_size=64;ThreadingHTTPServer(('127.0.0.1',18743),Handler).serve_forever()
