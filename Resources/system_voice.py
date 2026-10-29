"""Installed OS voices as a labelled, offline last target-language fallback.

Never downloads voices, changes the selected AI engine, or claims actor cloning.
The constant PowerShell program receives user data only through a UTF-8 JSON
file. No user text/path is interpolated into shell code.
"""
import base64,hashlib,json,os,re,subprocess,sys
from repair_limits import bounded,check,RepairBudgetExceeded
from pathlib import Path

PS=r'''[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
Add-Type -AssemblyName System.Speech
$c = Get-Content -LiteralPath $env:ANICANTO_NATIVE_VOICE_REQUEST -Raw -Encoding UTF8 | ConvertFrom-Json
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
 if ($c.mode -eq 'list') {
  $a = @($s.GetInstalledVoices() | Where-Object {$_.Enabled} | ForEach-Object { @{ name=$_.VoiceInfo.Name; locale=$_.VoiceInfo.Culture.Name } })
  ConvertTo-Json -InputObject $a -Compress
 } else {
  $v = @($s.GetInstalledVoices() | Where-Object {$_.Enabled -and $_.VoiceInfo.Name -eq $c.voice})
  if ($v.Count -ne 1) { throw 'The selected installed voice is unavailable.' }
  $s.SelectVoice($c.voice)
  $s.SetOutputToWaveFile($c.output)
  $s.Speak([string]$c.text)
  $s.SetOutputToNull()
 }
} finally { $s.Dispose() }
'''

def execute(args,timeout=60,env=None):
 try:p=subprocess.run(list(map(str,args)),capture_output=True,timeout=timeout,env=env)
 except subprocess.TimeoutExpired as e:raise RuntimeError('Installed system voice timed out; its owned process was stopped.') from e
 if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace')[-700:] or 'System voice command failed')
 return p.stdout

def powershell(folder,body):
 path=Path(folder)/'native-request.json';path.write_text(json.dumps(body,ensure_ascii=True),encoding='utf-8')
 env=dict(os.environ,ANICANTO_NATIVE_VOICE_REQUEST=str(path))
 return execute(['powershell.exe','-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(PS.encode('utf-16-le')).decode()],env=env)

def compatible(locale,target):
 locale=locale.replace('-','_').lower()
 return locale in ('zh_hk','yue_hk') if target=='yue' else locale.startswith('en_') if target=='en' else locale in ('zh_cn','cmn_cn','zh_sg') if target=='zh' else False

def installed(folder,target):
 folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
 if sys.platform=='darwin':
  rows=[]
  for line in execute(['/usr/bin/say','-v','?'],timeout=10).decode(errors='replace').splitlines():
   match=re.match(r'^(.+?)\s+([A-Za-z]{2,3}[_-][A-Za-z]{2,4})\s+#',line)
   if match:rows.append(dict(name=match[1].strip(),locale=match[2]))
 elif sys.platform=='win32':
  rows=json.loads(powershell(folder,dict(mode='list')))
  if isinstance(rows,dict):rows=[rows]
 else:return []
 selected=[];seen=set()
 for row in rows:
  if not isinstance(row,dict) or not isinstance(row.get('name'),str) or not compatible(str(row.get('locale','')),target):continue
  key=(row['name'],row['locale'])
  if key not in seen:selected.append(row);seen.add(key)
 return selected

def synthesize(cfg,folder,text,voice):
 folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);wave=folder/'system.wav'
 if sys.platform=='darwin':
  source=folder/'text.txt';source.write_text(text,encoding='utf-8');raw=folder/'system.aiff'
  execute(['/usr/bin/say','-v',voice['name'],'-f',source,'-o',raw])
  execute([cfg['ffmpeg'],'-v','error','-y','-i',raw,'-ac','1','-c:a','pcm_s16le',wave],timeout=30)
 elif sys.platform=='win32':powershell(folder,dict(mode='synthesize',voice=voice['name'],text=text,output=str(wave)))
 else:raise ValueError('No supported installed system speech provider.')
 return wave

@bounded('system-target-voice',phase='native')
def repair(cfg,job,cues,paths,placement,run,emit):
 from delivery_policy import bounded_delivery,confirmed_indices
 if __import__('repair_permissions').enabled(cfg) and not __import__('repair_permissions').native(cfg):return paths
 if not bounded_delivery(cfg) or cfg.get('editorRender') or not cfg.get('automaticSystemVoice',False) or cfg.get('failedVoicePolicy')=='source' or not placement:return paths
 from normal_policy import finish_requested
 if finish_requested(cfg) or __import__('track_control').requested(cfg.get('_trackControl')):return paths
 from normal_mode import audio_present
 from natural_delivery import seconds
 from natural_schedule import prepare
 from worker import atomic_json
 from repair_limits import read
 job=Path(job);marker=job/'system-voice-fallback.json';saved=read(marker);records=saved.setdefault('records',{});confirmed=confirmed_indices(cfg,job);selected=list(paths)
 pending=[i for i,c in enumerate(cues) if c.get('enabled',True) and c.get('cantonese','').strip() and not c.get('editorAudio') and not c.get('preserveOriginalSpeech') and (not audio_present(selected[i]) or not placement[i].get('fit') or c.get('reviewIndex',i)+1 in confirmed)]
 if not pending:return selected
 folder=job/'system-voice-fallback';folder.mkdir(exist_ok=True)
 try:voices=installed(folder,cfg.get('targetLanguage','yue'))
 except (OSError,ValueError,RuntimeError) as error:voices=[];saved['availabilityError']=str(error)[:300]
 saved.update(status='available' if voices else 'unavailable',provider=sys.platform,language=cfg.get('targetLanguage','yue'),installedVoices=voices,qualityCertified=False,voiceCloning=False,downloads=False);atomic_json(marker,saved)
 max_voices=2
 for i in pending:
  if finish_requested(cfg):break
  cue=cues[i];index=cue.get('reviewIndex',i)+1;text=cue['cantonese'];key=hashlib.sha256(json.dumps([index,text,cfg.get('targetLanguage','yue')],ensure_ascii=False).encode()).hexdigest()[:24];record=records.setdefault(key,dict(index=index,text=text,attempts=[]))
  if record.get('status')=='adopted':
   cached=Path(record.get('selectedAudio') or '/nonexistent')
   if audio_present(cached) and hashlib.sha256(cached.read_bytes()).hexdigest()==record.get('audioSHA256') and not __import__('delivery_policy').rejected_audio(cfg,job,index,cached):selected[i]=cached;continue
   record['status']='invalid-cached-audio'
  for number in range(len(record['attempts']),max_voices):
   if not voices:break
   try:check()
   except RepairBudgetExceeded:break
   if __import__('delivery_policy').repair_first(cfg):
    from recovery_attempts import reserve
    if not reserve(job,'native-generation',index,max_voices):break
   voice=voices[number%len(voices)]
   trial_dir=folder/key/str(len(record['attempts']));attempt=dict(voice=voice['name'],locale=voice['locale'],status='reserved');record['attempts'].append(attempt);atomic_json(marker,saved)
   try:
    emit('系統聲音後備',f'第 {index} 句：使用已安裝目標語言聲音完成交付；音色可能不同，不作口音認證。',.92)
    candidate=synthesize(cfg,trial_dir,text,voice)
    if not audio_present(candidate):raise ValueError('System voice produced no healthy audible recording')
    if __import__('delivery_policy').rejected_audio(cfg,job,index,candidate):raise ValueError('System voice returned the same confirmed-bad audio')
    trial=list(selected);trial[i]=candidate;plan=prepare(dict(cfg,naturalTimingPolicy='source-locked'),job,cues,trial,run,emit)
    if not plan[i]['fit'] or any(row.get('fit') and not plan[n]['fit'] for n,row in enumerate(placement)):
     attempt.update(status='timing-not-fit',seconds=seconds(candidate,cfg,run),availableSeconds=placement[i]['deadline']-placement[i]['start']);continue
    selected[i]=candidate;placement=plan;record.update(status='adopted',selectedAudio=str(candidate),audioSHA256=hashlib.sha256(candidate.read_bytes()).hexdigest(),voice=voice['name'],locale=voice['locale'],seconds=seconds(candidate,cfg,run),nativeTargetLanguage=True,qualityCertified=False,contentListening='not-run-native-system-text',voiceCloning=False);attempt['status']='adopted';break
   except (OSError,ValueError,RuntimeError) as error:attempt.update(status='failed',error=str(error)[:500])
   finally:atomic_json(marker,saved)
  if record.get('status')=='adopted':
   from normal_recovery import clear_confirmed
   clear_confirmed(cfg,job,{index},atomic_json)
   if cfg.get('storage'):
    from project_store import record_issue
    record_issue(cfg,job,cue,'system-voice-fallback','Installed target-language system voice used; actor similarity and accent are not certified.')
 return selected
