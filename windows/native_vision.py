"""Ollama image provider for shared character/portrait validation."""
import base64,json,urllib.request
from pathlib import Path
class NativeVision:
 def __init__(self,cfg):self.model=cfg['model'];self.port=int(cfg.get('port',11445))
 def reply(self,prompt,images,schema,max_tokens):
  body=dict(model=self.model,messages=[dict(role='user',content=prompt,images=[base64.b64encode(Path(p).read_bytes()).decode() for p in images])],format=schema,stream=False,think=False,keep_alive='5m',options=dict(temperature=0,num_ctx=8192,num_predict=max_tokens))
  request=urllib.request.Request(f'http://127.0.0.1:{self.port}/api/chat',json.dumps(body).encode(),{'Content-Type':'application/json'})
  with urllib.request.urlopen(request,timeout=1200) as response:result=json.load(response)
  if result.get('error'):raise RuntimeError(str(result['error']))
  content=result.get('message',{}).get('content','').strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
  return content

def model_id(cfg):
 ident=cfg.get('visualModel') or cfg.get('model')
 if not str(ident).startswith('qwen3.5:'):raise ValueError('Select an installed native Qwen3.5 vision model.')
 return ident,ident
