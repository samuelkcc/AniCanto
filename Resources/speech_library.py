"""Independent speech documents and immutable takes, outside video projects."""
import base64,binascii,copy,hashlib,json,math,re,shutil,time,uuid
from pathlib import Path

FOLDER='speech-studio'
NAMES={'en':'Dubbing studio','zh-HK':'配音器','zh-CN':'配音器','ja':'吹き替えスタジオ'}
MIMES={'audio/webm':'webm','audio/ogg':'ogg','audio/mp4':'m4a','audio/wav':'wav','audio/x-wav':'wav'}
DRAFT_FIELDS={'projectID','mode','source','cantonese','sourceLanguage','detectedLanguage','title','engine','textModel','rate','voice','ownVoice','inputID','recognitionID','translationID','referenceText','parameters','autoRepair'}

def root(storage):
 p=Path(storage).resolve()/'studio'/FOLDER;p.mkdir(parents=True,exist_ok=True);return p

def identifier(value):
 if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{32}',value):raise ValueError('Invalid speech clip identifier.')
 return value

def owned(storage,kind,ident):
 base=root(storage)/kind;p=(base/identifier(ident)).resolve()
 if not p.is_relative_to(base.resolve()) or p==base.resolve():raise ValueError('Speech clip path leaves its library.')
 return p

def folder(storage,ident):return owned(storage,'clips',ident)

def read(path,default=None):
 try:return json.loads(Path(path).read_text(encoding='utf-8'))
 except (OSError,ValueError):return default

def write(path,data):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.partial.json');tmp.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8');tmp.replace(path)

def digest(path):
 with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def clip_file(job,name):
 if not isinstance(name,str) or Path(name).name!=name or name.startswith('.') or '/' in name or '\\' in name:raise ValueError('Invalid recording file.')
 p=(Path(job)/name).resolve()
 if not p.is_relative_to(Path(job).resolve()) or not p.is_file():raise ValueError('The recording file is missing.')
 return p

def verified_audio(storage,ident,source=False):
 job=folder(storage,ident);row=read(job/'result.json',{})
 name=row.get('sourceFilename') if source else 'voice.wav'
 if not name:raise ValueError('No source recording was saved for this take.')
 p=clip_file(job,name);expected=row.get('sourceSHA256' if source else 'audioSHA256')
 if expected and digest(p)!=expected:raise ValueError('The recording changed. Earlier review results are no longer valid.')
 if not source:
  from audio_fallback import healthy
  if not healthy(p):raise ValueError('The recording is empty or unreadable.')
 return p

def input_audio(storage,ident):
 p=owned(storage,'inputs',ident);files=list(p.glob('source.*'))
 if len(files)!=1 or not files[0].is_file() or not files[0].resolve().is_relative_to(p):raise ValueError('Record or import audio first.')
 return files[0]

def new_document(storage,settings=None):
 settings=settings or {};draft=dict(projectID=uuid.uuid4().hex,mode='text',source='',cantonese='',sourceLanguage='auto',title='',rate=1,voice='yue-mid',ownVoice=False,parameters={},autoRepair=True)
 for k in ('engine','textModel'):
  if isinstance(settings.get(k),str):draft[k]=settings[k]
 write(root(storage)/'draft.json',draft);return draft

def save_draft(storage,data):
 if not isinstance(data,dict) or set(data)-DRAFT_FIELDS or len(json.dumps(data))>50000:raise ValueError('Invalid speech draft.')
 value=copy.deepcopy(data)
 if value.get('projectID'):identifier(value['projectID'])
 else:value['projectID']=uuid.uuid4().hex
 write(root(storage)/'draft.json',value);return value

def listing(storage,language='en'):
 base=root(storage);clips=[];projects={}
 for file in (base/'clips').glob('*/result.json'):
  if not file.resolve().is_relative_to(base/'clips'):continue
  row=read(file,{})
  if not isinstance(row,dict) or row.get('id')!=file.parent.name:continue
  job=file.parent;row=dict(row)
  output=job/'voice.wav'
  if row.get('audio') and output.is_file() and output.resolve().is_relative_to(job.resolve()):
   if row.get('audioSHA256') and digest(output)!=row['audioSHA256']:
    row.pop('audio',None);row.update(status='failed',quality=dict(status='not-checked',qualityCertified=False),error='The recording changed. Earlier review results are no longer valid.')
   else:row['audio']=str(output)
  else:row.pop('audio',None)
  if row.get('sourceFilename'):
   try:
    source=clip_file(job,row['sourceFilename'])
    if not row.get('sourceSHA256') or digest(source)==row['sourceSHA256']:row['sourceAudio']=str(source)
   except ValueError:row.pop('sourceAudio',None)
  project=row.get('projectID') or row['id'];row['projectID']=project
  try:identifier(project)
  except ValueError:continue
  meta=read(owned(storage,'documents',project)/'document.json',{})
  row['title']=meta.get('title',row.get('title',''));row['selected']=meta.get('selectedTake')==row['id']
  row['saved']=(job/'saved.json').is_file();row.setdefault('quality',dict(status='not-checked',qualityCertified=False))
  clips.append(row)
  if row.get('saved') and row.get('audio'):
   group=projects.setdefault(project,dict(id=project,title=row['title'],takeIDs=[],selectedTake=meta.get('selectedTake'),created=0))
   group['takeIDs'].append(row['id']);group['created']=max(group['created'],row.get('created',0))
 draft=read(base/'draft.json',{})
 if not isinstance(draft,dict):draft={}
 if not draft.get('projectID'):
  draft=dict(draft,projectID=uuid.uuid4().hex);write(base/'draft.json',draft)
 if draft.get('inputID'):
  try:draft['inputPath']=str(input_audio(storage,draft['inputID']))
  except ValueError:pass
 from natural_voices import catalog
 from voice_parameters import SPECS
 return dict(folder=dict(id=FOLDER,name=NAMES.get(language,NAMES['en'])),clips=sorted(clips,key=lambda r:r.get('created',0),reverse=True)[:500],projects=sorted(projects.values(),key=lambda r:r['created'],reverse=True),voices=[dict(id=v['id'],title=v['title']) for v in catalog() if v['language']=='yue'],parameters={e:{k:dict(default=v[0],minimum=v[1],maximum=v[2],integer=v[3] is int) for k,v in rows.items()} for e,rows in SPECS.items()},draft=draft)

def upload(storage,data,mime):
 kind=MIMES.get(str(mime).split(';')[0])
 if kind is None or not isinstance(data,str) or len(data)>16*1024*1024:raise ValueError('Use a supported audio recording smaller than 12 MB.')
 try:raw=base64.b64decode(data,validate=True)
 except (ValueError,binascii.Error):raise ValueError('The recording could not be read.')
 if not raw or len(raw)>12*1024*1024:raise ValueError('The recording is empty or too large.')
 ident=uuid.uuid4().hex;p=owned(storage,'inputs',ident);p.mkdir(parents=True)
 path=p/('source.'+kind);path.write_bytes(raw);return dict(id=ident,path=str(path))

def import_audio(storage,path):
 source=Path(path)
 if source.suffix.lower() not in ('.wav','.mp3','.m4a','.flac','.webm','.ogg') or not source.is_file() or source.stat().st_size>12*1024*1024:raise ValueError('Choose an audio file smaller than 12 MB.')
 ident=uuid.uuid4().hex;p=owned(storage,'inputs',ident);p.mkdir(parents=True)
 target=p/('source'+source.suffix.lower());shutil.copyfile(source,target);return dict(id=ident,path=str(target))

def submit(storage,settings,params):
 mode=params.get('mode','text');action=params.get('action','translate')
 if mode not in ('text','recording') or action not in ('recognize','translate','generate'):raise ValueError('Unknown speech studio operation.')
 source=str(params.get('source','')).strip();text=str(params.get('cantonese','')).strip()
 if len(source)>4000 or len(text)>4000:raise ValueError('Use up to 4,000 characters per clip.')
 if action=='recognize' and mode!='recording':raise ValueError('Record or import audio before recognition.')
 if action=='generate' and not text:raise ValueError('Enter or translate the Cantonese script first.')
 if action=='translate' and not source:raise ValueError('Recognise and check the source transcript before translating.')
 language=params.get('sourceLanguage','auto')
 if language not in ('auto','ja','en','yue','zh'):raise ValueError('Unknown source-language option.')
 cfg=copy.deepcopy(settings);engine=params.get('engine') or cfg.get('ttsBackend','drama3')
 from desktop_state import ENGINES
 if engine not in dict(ENGINES):raise ValueError('Unknown voice engine.')
 controls=params.get('parameters',{})
 from voice_parameters import keys,validate
 if not isinstance(controls,dict) or set(controls)-keys():raise ValueError('Unknown voice control.')
 cfg.update(controls);validate(cfg)
 rate=float(params.get('rate',1))
 if not math.isfinite(rate) or not .8<=rate<=1.2:raise ValueError('Speech speed must be between 0.8 and 1.2.')
 if params.get('textModel'):cfg['model']=params['textModel']
 project=identifier(params['projectID']) if params.get('projectID') else uuid.uuid4().hex
 spec=dict(schemaVersion=2,projectID=project,mode=mode,action=action,source=source,cantonese=text,title=str(params.get('title','')).strip()[:100],rate=rate,voice=params.get('voice','yue-mid'),ownVoice=bool(params.get('ownVoice',mode=='recording')),autoRepair=bool(params.get('autoRepair',True)))
 cfg.update(aiAutoFix=False,ttsBackend=engine,selectedEngines=[engine],targetLanguage='yue',sourceLanguage=None if language=='auto' else language,speechStudio=spec)
 if mode=='recording':spec.update(inputID=params.get('inputID'),inputAudio=str(input_audio(storage,params.get('inputID'))))
 parent=(params.get('recognitionID') or params.get('translationID')) if mode=='recording' else None
 if parent:
  previous=folder(storage,parent);result=read(previous/'result.json',{});request=read(previous/'request.json',{}).get('speechStudio',{})
  if request.get('inputID') and request.get('inputID')!=spec.get('inputID'):raise ValueError('The reference belongs to an earlier input. Recognise this recording first.')
  if result.get('reference') and (previous/'reference.wav').is_file():
   reference=clip_file(previous,'reference.wav')
   if result.get('referenceSHA256') and digest(reference)!=result['referenceSHA256']:raise ValueError('The reference recording changed. Recognise the recording again.')
   prompt=params.get('referenceText',result.get('referenceText',''))
   if not isinstance(prompt,str) or len(prompt)>1200:raise ValueError('Invalid reference transcript.')
   spec.update(profile=dict(reference=str(reference),promptText=prompt,language=result.get('detectedLanguage','auto')),recognitionID=parent,detectedLanguage=result.get('detectedLanguage','auto'))
 if action=='generate':
  from natural_voices import catalog
  if spec['voice'] not in {v['id'] for v in catalog() if v['language']=='yue'}:raise ValueError('Unknown Cantonese voice.')
  if spec['ownVoice'] and not spec.get('profile'):raise ValueError('Recognise the recording before using its voice.')
 ident=uuid.uuid4().hex;job=folder(storage,ident)
 if action=='generate':
  spec['version']=1+sum(1 for f in (root(storage)/'clips').glob('*/request.json') if (old:=read(f,{}).get('speechStudio',{})).get('projectID')==project and old.get('action')=='generate')
 job.mkdir(parents=True)
 cfg.update(storage=str(Path(storage).resolve()),job=str(job));spec.update(id=ident,created=time.time())
 write(job/'request.json',cfg);write(job/'result.json',dict(id=ident,projectID=project,version=spec.get('version'),created=spec['created'],status='waiting',action=action,title=spec['title'],mode=mode))
 doc=owned(storage,'documents',project)/'document.json';meta=read(doc,{})
 write(doc,dict(meta,id=project,title=spec['title'] or meta.get('title',''),updated=time.time()))
 return job/'request.json'

def save(storage,ident,accept_review=False):
 job=folder(storage,ident);row=read(job/'result.json',{})
 if row.get('status') not in ('complete','needs-review'):raise ValueError('Generate a complete recording before saving to the player.')
 verified_audio(storage,ident)
 if row['status']=='needs-review' and not accept_review:raise ValueError('Listen to the flagged recording and explicitly accept its review notes before saving.')
 write(job/'saved.json',dict(savedAt=time.time(),acceptedReview=bool(accept_review),qualityCertified=False));select(storage,ident)
 return listing(storage)

def select(storage,ident):
 job=folder(storage,ident);row=read(job/'result.json',{});verified_audio(storage,ident)
 project=identifier(row.get('projectID') or ident);doc=owned(storage,'documents',project)/'document.json';meta=read(doc,{})
 write(doc,dict(meta,id=project,title=meta.get('title',row.get('title','')),selectedTake=ident,updated=time.time()))
 return row

def rename(storage,project,title):
 title=str(title).strip()
 if not 1<=len(title)<=100:raise ValueError('Use a title between 1 and 100 characters.')
 doc=owned(storage,'documents',project)/'document.json';meta=read(doc,{})
 if not meta:raise ValueError('Unknown speech document.')
 write(doc,dict(meta,title=title,updated=time.time()));return listing(storage)

def delete(storage,ident):
 job=folder(storage,ident);row=read(job/'result.json',{})
 if row.get('action') not in ('generate',None) or row.get('status') in ('running','waiting'):raise ValueError('Stop generation before deleting this take.')
 if not row.get('audio'):raise ValueError('Only generated recordings can be removed here.')
 project=identifier(row.get('projectID') or ident);trash=owned(storage,'trash',ident);trash.parent.mkdir(parents=True,exist_ok=True)
 if trash.exists():raise ValueError('This recording is already in the removed library.')
 job.rename(trash)
 doc=owned(storage,'documents',project)/'document.json';meta=read(doc,{})
 if meta.get('selectedTake')==ident:
  remaining=[r for r in listing(storage)['clips'] if r.get('projectID')==project and r.get('audio')]
  meta['selectedTake']=next((r['id'] for r in remaining if r['saved']),remaining[0]['id'] if remaining else None);write(doc,meta)
 return listing(storage)

def load_take(storage,ident):
 job=folder(storage,ident);row=read(job/'result.json',{});verified_audio(storage,ident);cfg=read(job/'request.json',{});spec=cfg.get('speechStudio',{})
 draft={k:spec[k] for k in DRAFT_FIELDS if k in spec};draft.update(projectID=row.get('projectID') or ident,source=row.get('source',''),cantonese=row.get('cantonese',''),engine=row.get('engine',cfg.get('ttsBackend')),textModel=cfg.get('model'),parameters=row.get('parameters',{}))
 previous=read(root(storage)/'draft.json',{})
 if previous:write(root(storage)/'draft-history'/(str(time.time_ns())+'.json'),previous)
 save_draft(storage,draft);return listing(storage)
