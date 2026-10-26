"""App-owned, loopback-only MLX text backend. No cloud inference or remote code."""
import argparse,gc,json,os,re,time,hashlib
from pathlib import Path
from http.server import HTTPServer,BaseHTTPRequestHandler
MODEL_ID='mlx:qwen3.5-35b-a3b:4bit'

def model_dir(root,ident=MODEL_ID):
    from model_catalog import folder,choice
    return folder(root,choice(ident))

def chat_messages(body):
    """Qwen accepts one leading system turn; keep dialogue as untrusted user data."""
    messages=[dict(message) for message in (body.get('messages') or
              [dict(role='user',content=body.get('prompt',''))])]
    instructions=[]
    while messages and messages[0].get('role')=='system':
        instructions.append(messages.pop(0)['content'])
    # Do not move later system turns across dialogue or change conversation order.
    if any(message.get('role')=='system' for message in messages):
        raise ValueError('System instructions must precede the conversation.')
    schema=body.get('format')
    if schema:
        instruction='Reply with valid JSON only. No Markdown fences, explanations or reasoning.'
        if isinstance(schema,dict):
            instruction+=' Required JSON schema: '+json.dumps(schema,ensure_ascii=False)
        instructions.append(instruction)
    if instructions:
        messages.insert(0,dict(role='system',content='\n\n'.join(instructions)))
    return messages

def structured_reply(text,schema,rejected=None):
    """Unwrap formatting only; never invent missing values or repair broken JSON."""
    text=text.strip()
    fence=re.fullmatch(r'```(?:json)?\s*\n(.*?)\n\s*```',text,re.S|re.I)
    if fence:text=fence.group(1)
    def unique_pairs(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('Duplicate JSON key: '+key)
            result[key]=value
        return result
    def invalid_constant(value):raise ValueError('Invalid JSON number: '+value)
    value=json.loads(text,object_pairs_hook=unique_pairs,parse_constant=invalid_constant)
    if isinstance(schema,dict):
        properties=schema.get('properties',{})
        # Explicitly enabled only for numbered dialogue rows. Each accepted row
        # still passes its complete schema; callers enforce evidence and timing.
        if schema.get('x-partial-rows') is True and schema.get('type')=='object' and properties and all(str(k).isdigit() for k in properties):
            if not isinstance(value,dict):raise ValueError('$: expected object')
            accepted={}
            for key,row_schema in properties.items():
                try:
                    if key not in value:raise ValueError('missing row')
                    accepted[key]=checked_value(value[key],row_schema,'$.'+key)
                except (ValueError,TypeError) as exc:
                    if rejected is not None:rejected.append(dict(id=key,reason=str(exc)))
            value=accepted
        else:value=checked_value(value,schema)
    return json.dumps(value,ensure_ascii=False)

def checked_value(value,schema,path='$'):
    kind=schema.get('type')
    types={'object':dict,'array':list,'string':str,'boolean':bool,'integer':int,'number':(int,float),'null':type(None)}
    if kind in types and (not isinstance(value,types[kind]) or (kind in ('integer','number') and isinstance(value,bool))):
        raise ValueError(f'{path}: expected {kind}')
    if 'enum' in schema and value not in schema['enum']:raise ValueError(f'{path}: invalid enum')
    if isinstance(value,dict):
        missing=set(schema.get('required',[]))-set(value)
        if missing:raise ValueError(f'{path}: missing keys '+', '.join(sorted(missing)))
        properties=schema.get('properties',{})
        # Discard only fields the caller explicitly forbids (e.g. context turns).
        value={k:checked_value(v,properties[k],path+'.'+k) if k in properties else v
               for k,v in value.items() if k in properties or schema.get('additionalProperties') is not False}
    elif isinstance(value,list) and isinstance(schema.get('items'),dict):
        value=[checked_value(v,schema['items'],f'{path}[{i}]') for i,v in enumerate(value)]
    elif isinstance(value,str) and len(value)<schema.get('minLength',0):
        raise ValueError(f'{path}: string too short')
    return value

class ModelReplyError(ValueError):pass

def install(root,ident=MODEL_ID):
    from model_catalog import install as download_model
    download_model(root,ident)
    if ident==MODEL_ID:(Path(root)/'mlx-text-ready.json').write_text(json.dumps(dict(model=ident)))
    print(json.dumps(dict(stage='完成',message=ident+' 已下載；請測試本機生成。',progress=1),ensure_ascii=False),flush=True)

class Backend:
    def __init__(self,root):self.root=root;self.model=None;self.tokenizer=None;self.last=0;self.loaded_id=None;self.recovered_models={};self.last_recovery=None;self.prompt_cache=None;self.last_metrics=None
    def unload(self):
        import mlx.core as mx
        mx.synchronize()
        self.model=None;self.tokenizer=None;self.loaded_id=None;self.prompt_cache=None;gc.collect()
        mx.clear_cache()
    def generate(self,body):
        if body.get('keep_alive')==0:self.unload();return ''
        if body.get('strict_model'):
            self.last_recovery=None
            return self._generate(body)
        original=body.get('model',MODEL_ID);self.last_recovery=None
        request=dict(body,model=self.recovered_models.get(original,original))
        try:return self._generate(request)
        except (RuntimeError,MemoryError) as error:
            from runtime_recovery import recoverable
            if not isinstance(error,MemoryError) and not recoverable(error):raise
            self.unload()
            from model_catalog import catalog,choice,resolve
            current=choice(request['model']);candidate=None
            for row in sorted((r for r in catalog() if r['category']=='text' and r['id'].startswith('mlx:') and r['estimatedMemoryGB']<current['estimatedMemoryGB']),key=lambda r:r['estimatedMemoryGB'],reverse=True):
                try:resolve(self.root,row['id']);candidate=row['id'];break
                except (OSError,ValueError):pass
            # Keep the full source context; callers can split a rejected batch.
            retry=dict(request,model=candidate or request['model'],options=dict(request.get('options',{}),num_predict=min(1024,request.get('options',{}).get('num_predict',2048))))
            audit=dict(previous=original,selected=retry['model'],reason=str(error),status='retrying',strategy='smaller-installed-text-model' if candidate else 'unload-and-restart')
            path=Path(self.root)/'text-runtime-recovery.json'
            try:
                text=self._generate(retry);audit['status']='generated-needs-review';self.last_recovery=audit
                if candidate:self.recovered_models[original]=candidate
                return text
            except Exception:
                audit['status']='failed';raise
            finally:
                tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(audit,ensure_ascii=False));tmp.replace(path)
    def _generate(self,body):
        from model_catalog import choice,resolve
        ident=body.get('model',MODEL_ID)
        if choice(ident)['category']!='text':raise ValueError('未知 MLX 文字模型。')
        if body.get('keep_alive')==0:self.unload();return ''
        from compute_policy import mlx_device
        mlx_device(self.root,'text-translation')
        from mlx_lm import load,stream_generate
        from mlx_lm.sample_utils import make_sampler
        if self.loaded_id!=ident and self.model is not None:self.unload()
        load_started=time.monotonic();load_seconds=0
        if self.model is None:
            os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
            self.model,self.tokenizer=load(str(resolve(self.root,ident)))
            self.loaded_id=ident;load_seconds=time.monotonic()-load_started
        messages=chat_messages(body)
        schema=body.get('format')
        opts=body.get('options',{});maximum=min(4096,max(16,int(opts.get('num_predict',2048))))
        request_started=time.monotonic();attempt_metrics=[]
        for attempt in range(2 if schema else 1):
            prompt=self.tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=False)
            bos=getattr(self.tokenizer,'bos_token',None)
            tokens=self.tokenizer.encode(prompt,add_special_tokens=not (isinstance(bos,str) and bos and prompt.startswith(bos)))
            if len(tokens)>24000:raise ValueError('台詞上下文太長（超過 24,000 tokens），請縮短批次。')
            from text_prompt_cache import PrefixBank
            if self.prompt_cache is None:self.prompt_cache=PrefixBank()
            # The phase instruction identifies a slot; exact token matching,
            # never this key alone, decides whether cached state is reusable.
            phase=hashlib.sha256(str((body.get('messages') or [{}])[0].get('content',''))[:200].encode()).hexdigest()
            started=time.monotonic()
            cache,rest=self.prompt_cache.prepare(self.model,tokens,phase)
            prepare_seconds=time.monotonic()-started
            cache_options={'prompt_cache':cache} if cache is not None else {}
            if body.get('constrained_json') and isinstance(schema,dict):
                # Constrain tokens during generation, rather than relying only
                # on a prompt and rejecting malformed output afterwards. Each
                # retry needs a fresh matcher; its state cannot share the cache.
                from mlx_vlm.structured import build_json_schema_logits_processor
                tokenizer=getattr(self.tokenizer,'_tokenizer',self.tokenizer)
                cache_options['logits_processors']=[build_json_schema_logits_processor(tokenizer,schema)]
            parts=[];response=None
            for response in stream_generate(self.model,self.tokenizer,prompt=rest if cache is not None else prompt,**cache_options,max_tokens=maximum if not attempt else min(4096,int(opts.get('num_predict',4096))),sampler=make_sampler(temp=float(opts.get('temperature',.3)) if not attempt else 0)):
                parts.append(response.text)
            result=''.join(parts).strip();self.last=time.monotonic()
            def number(key):
                value=getattr(response,key,0)
                return round(float(value),3) if isinstance(value,(int,float)) else 0
            metrics=dict(promptTokens=len(tokens),cachedTokens=self.prompt_cache.reused,cachePreparationSeconds=round(prepare_seconds,3),elapsedSeconds=round(self.last-started,3),prefillTokens=number('prompt_tokens'),prefillTokensPerSecond=number('prompt_tps'),generationTokens=number('generation_tokens'),generationTokensPerSecond=number('generation_tps'))
            attempt_metrics.append(metrics)
            self.last_metrics=dict(metrics,attempts=len(attempt_metrics),attemptMetrics=list(attempt_metrics),loadSeconds=round(load_seconds,3),requestSeconds=round(self.last-request_started+load_seconds,3),model=ident)
            print('MLX performance: '+str(self.last_metrics),flush=True)
            if not schema:return result
            try:
                rejected=[];text=structured_reply(result,schema,rejected)
                # Totals include every generation attempt, not just the final
                # response, so validation retries remain visible in timing QA.
                for key in ('promptTokens','cachedTokens','generationTokens','prefillTokens','cachePreparationSeconds'):
                    self.last_metrics[key]=sum(row.get(key,0) for row in attempt_metrics)
                for count,speed in (('generationTokens','generationTokensPerSecond'),('prefillTokens','prefillTokensPerSecond')):
                    seconds=sum(row.get(count,0)/row[speed] for row in attempt_metrics if row.get(speed,0)>0)
                    self.last_metrics[speed]=round(self.last_metrics[count]/seconds,3) if seconds else 0
                if rejected:
                    self.last_metrics['rejectedRows']=rejected
                    print('MLX partial rows: retained valid dialogue; rejected '+str(rejected),flush=True)
                    try:
                        folder=Path(self.root)/'logs';folder.mkdir(parents=True,exist_ok=True)
                        (folder/'mlx-text-last-partial.json').write_text(json.dumps(dict(rejected=rejected,raw=result),ensure_ascii=False,indent=2))
                    except OSError:pass
                return text
            except (ValueError,TypeError) as exc:
                diagnostic=dict(error=str(exc),attempt=attempt+1,raw=result)
                try:
                    folder=Path(self.root)/'logs';folder.mkdir(parents=True,exist_ok=True)
                    (folder/'mlx-text-last-invalid.json').write_text(json.dumps(diagnostic,ensure_ascii=False,indent=2))
                except OSError:pass
                if attempt:raise ModelReplyError('模型兩次未交回完整有效 JSON；已保留進度，詳見 logs/mlx-text-last-invalid.json。') from exc
                print('MLX structured reply invalid; retrying once: '+str(exc),flush=True)
                messages[0]['content']+='\nYour previous response failed validation: '+str(exc)[:300]+'. Return a COMPLETE compact JSON object containing every required key. Context-only turns must not be output. No Markdown.'

def serve(root,ready,token):
    backend=Backend(root)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            try:
                if self.path not in ('/api/chat','/api/generate'):raise ValueError('Unsupported route')
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<2_000_000:raise ValueError('Invalid request size')
                body=json.loads(self.rfile.read(size));text=backend.generate(body)
                result=dict(message=dict(role='assistant',content=text),response=text,done=True,recovery=backend.last_recovery,performance=backend.last_metrics)
                if body.get('keep_alive')==0:result['memoryReleased']=backend.model is None and backend.prompt_cache is None
                code=200
            except ModelReplyError as exc:result=dict(error=str(exc));code=422
            except Exception as exc:result=dict(error=str(exc));code=400
            data=json.dumps(result,ensure_ascii=False).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers()
            try:self.wfile.write(data)
            except (BrokenPipeError,ConnectionResetError):pass
    server=HTTPServer(('127.0.0.1',0),Handler);server.timeout=1
    ready=Path(ready);tmp=ready.with_suffix('.tmp');tmp.write_text(json.dumps(dict(port=server.server_port,token=token)));tmp.replace(ready)
    try:
        while True:
            server.handle_request()
            if backend.model is not None and time.monotonic()-backend.last>60:backend.unload()
    finally:server.server_close();ready.unlink(missing_ok=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['install','serve']);p.add_argument('root');p.add_argument('--model',default=MODEL_ID);p.add_argument('--ready');p.add_argument('--token');a=p.parse_args()
    if a.action=='install':install(a.root,a.model)
    else:serve(a.root,a.ready,a.token)
