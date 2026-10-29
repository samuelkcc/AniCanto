"""One durable retry for automatic encode/mux/validation, never user pause."""
import errno,hashlib,json,time
from pathlib import Path


def digest_file(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()

def storage_failure(error):
 if isinstance(error,OSError) and error.errno in (errno.ENOSPC,errno.EROFS):return True
 return any(x in str(error).lower() for x in ('no space left','disk full','磁碟空間不足','磁盘空间不足'))

def terminal(error):
 if isinstance(error,OSError) and error.errno in (errno.ENOSPC,errno.EACCES,errno.EPERM,errno.EROFS,errno.ENOENT):return True
 text=str(error).lower()
 return any(x in text for x in ('no space left','permission denied','read-only file system','disk full','no such file or directory','磁碟空間不足','磁盘空间不足'))

def run(cfg,job,cmd,execute,emit,validate):
 from delivery_policy import bounded_delivery
 from video_acceleration import encode
 from track_control import UserSkipped
 if not bounded_delivery(cfg) or cfg.get('editorRender'):
  encode(execute,cmd,cfg,emit);return validate()
 from worker import atomic_json
 from repair_limits import read
 job=Path(job);inputs=[]
 for i,arg in enumerate(cmd[:-1]):
  if str(arg)=='-i':
   p=Path(cmd[i+1])
   if p.is_file():inputs.append([str(p),digest_file(p) if p.suffix.lower() in ('.wav','.srt','.ass','.vtt') else [p.stat().st_size,p.stat().st_mtime_ns]])
 key=hashlib.sha256(json.dumps([list(map(str,cmd)),inputs,cfg.get('audioRerunToken')],sort_keys=True).encode()).hexdigest()[:24]
 path=job/'export-retry.json';ledger=read(path);record=ledger.setdefault(key,dict(maximumAttempts=2,attempts=[],status='pending'))
 if record.get('status')=='complete' and Path(cmd[-1]).is_file():return validate()
 if __import__('basic_flow').enabled(cfg) and record.get('status')=='complete' and record.get('completedSHA256') and not Path(cmd[-1]).exists():
  final=Path(read(job/'report.json').get('output') or '/nonexistent')
  if final.is_file() and final.resolve().is_relative_to(job.resolve()) and digest_file(final)==record['completedSHA256']:
   import shutil
   shutil.copy2(final,Path(cmd[-1]));return validate()

 while len(record['attempts'])<2:
  attempt=dict(number=len(record['attempts'])+1,status='reserved',startedAt=time.time());record['attempts'].append(attempt);atomic_json(path,ledger)
  try:
   encode(execute,cmd,cfg,emit);result=validate();attempt['status']='complete';record['status']='complete'
   if __import__('basic_flow').enabled(cfg):record['completedSHA256']=digest_file(Path(cmd[-1]))
   atomic_json(path,ledger);return result
  except UserSkipped:raise
  except (OSError,RuntimeError,ValueError) as error:
   attempt.update(status='failed',error=str(error)[:1000]);record['status']='terminal-error' if terminal(error) else 'failed';atomic_json(path,ledger)
   if terminal(error) or len(record['attempts'])>=2:raise
   emit('匯出重試','合成／字幕包裝未完成；沿用現有錄音，自動再試一次，不重新配音。',.96)
 raise RuntimeError('本次合成／字幕包裝已用完一次自動重試；錄音及工作保留。')
