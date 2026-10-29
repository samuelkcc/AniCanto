"""One persisted exact-input generation budget across automatic repair stages."""
import hashlib,json,re,time
from pathlib import Path
from atomic_files import write_json
REVISION='generation-input-1'

def permanent(error):
 text=str(error).lower()
 return bool(re.search(r'(?:phoneme|phones).*bert.*(?:mismatch|length)|bert.*(?:phoneme|phones).*(?:mismatch|length)|unsupported (?:source |target )?language|semantic.window.*(?:exceed|limit)|exceed.{0,60}semantic.{0,20}window|reference.*(?:3.?10|three.*ten).*second',text))

def key(cfg,item):
 profile=item.get('profile',{});reference=Path(profile.get('reference','/nonexistent'))
 sha=hashlib.sha256(reference.read_bytes()).hexdigest() if reference.is_file() else str(reference)
 identity=[REVISION,__import__('voice_parameters').overrides(cfg,cfg.get('ttsBackend','drama3')),cfg.get('ttsBackend'),cfg.get('targetLanguage'),cfg.get('drama3Model'),cfg.get('gsvVersion'),cfg.get('cosyModel'),item.get('text'),profile.get('promptText'),sha,item.get('deliveryStyle'),cfg.get('_explicitRetakeToken')]
 return hashlib.sha256(json.dumps(identity,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def reserve(cfg,request):
 root=Path(cfg.get('_generationGuardRoot') or request['job']);path=root/'generation-input-ledger.json'
 if path.is_file():
  try:ledger=json.loads(path.read_text())
  except (OSError,ValueError) as error:raise ValueError('Saved generation budget is unreadable; existing takes were kept. Use an explicit new version.') from error
  if not isinstance(ledger,dict):raise ValueError('Invalid saved generation budget.')
 else:ledger={}
 presence_path=root/'presence-call-ledger.json'
 presence=json.loads(presence_path.read_text()) if presence_path.exists() else {}
 modern=__import__('basic_flow').enabled(cfg) and not cfg.get('editorRender') and cfg.get('_generationPurpose') not in ('timing','content')
 selected=[];blocked=[];reserved=[]
 for item in request['items']:
  if Path(item['output']).is_file() and (not modern or __import__('audio_fallback').healthy(item['output'])):selected.append(item);continue
  ident=key(cfg,item);row=ledger.setdefault(ident,dict(attempts=0,maximumAttempts=3,failures=[]))
  if modern:
   line=str(item.get('reviewIndex',len(selected)+len(blocked)))
   identity=json.dumps([cfg.get('ttsBackend'),cfg.get('targetLanguage','yue'),line])
   total=presence.setdefault(identity,dict(calls=0,genericCalls=0,maximumCalls=3))
   if total['calls']>=3 or (cfg.get('_mandatoryPresence') and total['genericCalls']>=1):
    write_json(Path(item['output']).with_suffix('.failure.json'),dict(error='Saved per-line presence allowance exhausted; keep existing takes.'));blocked.append(item);continue
   total['calls']+=1
   if cfg.get('_mandatoryPresence'):total['genericCalls']+=1
  row['indices']=sorted(set(row.get('indices',[])+([item['reviewIndex']+1] if type(item.get('reviewIndex')) is int else [])))
  if row.get('permanent') or row['attempts']>=3:
   reason='Deterministic input failure; change the script/reference before retrying.' if row.get('permanent') else 'Exact-input automatic generation budget exhausted (3 attempts including first generation).'
   write_json(Path(item['output']).with_suffix('.failure.json'),dict(error=reason,guardKey=ident,guardRevision=REVISION,previousErrors=row['failures']))
   blocked.append(item);continue
  row['attempts']+=1;row['lastReservedAt']=time.time();selected.append(item);reserved.append((ident,item))
 write_json(path,ledger)
 if modern:write_json(presence_path,presence)
 return path,ledger,selected,blocked,reserved

def finish(state,error=None):
 path,ledger,selected,blocked,reserved=state
 for ident,item in reserved:
  output=Path(item['output']);row=ledger[ident]
  if output.is_file():row['completedAudio']=str(output);continue
  try:detail=json.loads(output.with_suffix('.failure.json').read_text()).get('error') or str(error or 'No output')
  except (OSError,ValueError):detail=str(error or 'No output')
  row['failures'].append(detail[:500]);row['permanent']=permanent(detail)
 write_json(path,ledger)
