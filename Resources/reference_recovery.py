"""Recover automatic nonlexical role references from same-role separated dialogue.

Imported/per-engine references are left alone. Never changes the role card or
borrows another role. A signal score cannot approve singing as spoken reference.
"""
import hashlib,json,re,math
from pathlib import Path

def lexical(text):
 text=re.sub(r'[^\wぁ-んァ-ヶ一-龥]','',str(text or ''))
 return len(text)>=4 and not re.search(r'(.)\1{3,}',text) and not re.fullmatch(r'[あぁアァうぅウゥおぉオォえぇエェーっッ]+',text)

def spoken_evidence(rows):
 if not rows:return False
 bad=sum(max(r.get('singing',0),r.get('choir_singing',0))>=.55 and r.get('speech',0)<.5 for r in rows)
 return bad/max(1,len(rows))<.4 and max(r.get('speech',0) for r in rows)>=.35

def expressive_reference(path,profile,rows):
 """A speech classifier is not a veto on witnessed, continuous acting.

 Laughing/crying and music probabilities overlap with animated dialogue. Keep
 those diagnostics, but require real signal and lexical original evidence.
 Strong singing, mixed voices and nonlexical samples remain ineligible.
 """
 if not rows or profile.get('mixedReference') or len(profile.get('referenceRanges',[]))!=1 or not lexical(profile.get('promptText')):return False
 if any(max(r.get('singing',0),r.get('choir_singing',0))>=.55 and r.get('speech',0)<.5 for r in rows):return False
 from reference_quality import read,measure
 try:
  quality=measure(*read(path))
  return (quality.get('activeRMSDB',-180)>-50 and quality.get('activeFraction',0)>=.15
          and quality.get('clippedFraction',1)<.03 and 'insufficient-speech' not in quality.get('warnings',[]))
 except (OSError,ValueError,__import__('wave').Error):return False

def prepare(cfg,job,profile,run,emit):
 if cfg.get('voiceStyleMode')!='clone' or profile.get('language')!='ja' or profile.get('transcriptSource')!='original-japanese-words' or not profile.get('referenceRanges'):return profile
 folder=Path(cfg.get('_referenceRecoveryRoot') or job)/'reference-recovery';folder.mkdir(parents=True,exist_ok=True)
 primary=Path(profile['reference'])
 pool_path=Path(cfg.get('_referenceCueFile') or Path(job)/'cues.json')
 try:pool_bytes=pool_path.read_bytes();pool=json.loads(pool_bytes)
 except (OSError,ValueError):pool_bytes=b'';pool=[]
 stem=Path(cfg.get('dialoguePath',''))
 signature=[str(stem),stem.stat().st_size,stem.stat().st_mtime_ns] if stem.is_file() else [str(stem)]
 identity=hashlib.sha256(primary.read_bytes()+json.dumps([profile,signature,hashlib.sha256(pool_bytes).hexdigest(),cfg.get('referenceSpeechModel'),'complete-same-role-reference-3-expressive'],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
 selection_cache=folder/(identity+'-selected.json')
 if selection_cache.exists():
  saved=json.loads(selection_cache.read_text());path=Path(saved['profile']['reference'])
  if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==saved['audioSHA']:return saved['profile']
 def save(result,method):
  from worker import atomic_json
  atomic_json(selection_cache,dict(profile=result,audioSHA=hashlib.sha256(Path(result['reference']).read_bytes()).hexdigest(),role=profile['id'],previous=str(primary),method=method))
  return result
 def check(path,allow_expressive=False):
  if not cfg.get('executable'):return False
  key=hashlib.sha256(Path(path).read_bytes()+b'speech-evidence-1').hexdigest()
  cache=folder/(key+'-performance.json')
  if cache.exists():evidence=json.loads(cache.read_text())
  else:
   evidence=json.loads(run([cfg['executable'],'--classify-performance',str(path)]));cache.write_text(json.dumps(evidence))
  if spoken_evidence(evidence):return True
  if allow_expressive and expressive_reference(path,profile,evidence):
   profile['referenceAdvisory']=dict(reason='continuous-lexical-acting; classifier-only rejection retained as warning',performance=evidence)
   emit('參考錄音提示',f"{profile.get('name','角色')}：原聲有表演／背景聲分類提示；有連續日語台詞及有效人聲，先保留原角色模仿，按生成錄音判斷。")
   return True
  return False
 # Spoken audio can still be an invalid concatenation. A successful singing
 # check must not bypass the later continuous-original requirement.
 continuous=len(profile.get('referenceRanges',[]))==1
 profile=dict(profile)
 if continuous and lexical(profile.get('promptText')) and check(primary,allow_expressive=True):return save(profile,'existing-continuous-lexical-reference')
 if not continuous:
  from gsv_reference import prepare as continuous_original
  analysis=pool_path.parent/'japanese-analysis.json'
  verified=continuous_original(dict(cfg,ttsBackend='gpt-sovits',gsvReferenceMode='original',_referenceAnalysisFile=str(analysis)),folder,[profile],run,emit).get(profile['id'])
  if verified and check(verified['reference']):return save(verified,'verified-continuous-original')
 if not stem.is_file():raise ValueError(f"{profile.get('name','角色')} 自動參考含非語言發聲或歌聲，未有分離原聲可重新取樣；請匯入同角色完整對白。")
 choices=[]
 for cue in pool:
  text=cue.get('japanese') or cue.get('text','');a,b=cue.get('speechStart',cue.get('start')),cue.get('speechEnd',cue.get('end'))
  if cue.get('speakerId')!=profile['id'] or not cue.get('enabled',True) or cue.get('mixedVoices') or not lexical(text):continue
  if not isinstance(a,(int,float)) or not isinstance(b,(int,float)) or not math.isfinite(a+b) or not 2.5<=b-a<=8:continue
  # Exclude known other-role overlap; never lengthen a reference by borrowing
  # a neighbouring voice or repeatedly looping a short utterance.
  if any(other.get('enabled',True) and other.get('speakerId')!=profile['id'] and min(b,other['end'])-max(a,other['start'])>.04 for other in pool):continue
  choices.append((abs((b-a)-5),a,b,text))
 for _,a,b,text in sorted(choices)[:4]:
  key=hashlib.sha256(json.dumps([str(stem),stem.stat().st_mtime_ns,a,b,text,'spoken-reference-3']).encode()).hexdigest()[:20]
  path=folder/(key+'.wav')
  if not path.exists():run([cfg['ffmpeg'],'-v','error','-y','-ss',str(a),'-i',str(stem),'-af',f'atrim=duration={b-a},asetpts=PTS-STARTPTS,apad=whole_dur=3.1','-t',str(max(3.1,b-a)),'-ar','32000','-ac','1','-c:a','pcm_s16le',str(path)])
  if not check(path):continue
  # Independently check the actual recording against the saved Japanese source.
  cache=folder/(key+'.json')
  if cache.exists():row=json.loads(cache.read_text())
  else:
   from model_catalog import selected
   from runtime_paths import python_for
   req=folder/(key+'-request.json');req.write_text(json.dumps(dict(storage=cfg['storage'],model=cfg.get('referenceSpeechModel') or selected(cfg['storage'],'referenceSpeech'),items=[dict(reference=str(path),expectedText=text)])))
   row=json.loads(run([python_for(Path(cfg['storage']),'runtime'),Path(__file__).with_name('gsv_reference.py'),str(req)]))['rows'][0]
   cache.write_text(json.dumps(row,ensure_ascii=False))
  from gsv_reference import transcript_check
  valid,_=transcript_check(text,row.get('promptText',''))
  if not row.get('verified') or not valid or not lexical(row.get('promptText','')):continue
  evidence=dict(role=profile['id'],source=str(stem),range=[a,b],expected=text,promptText=row['promptText'],previous=str(primary),reference=str(path),method='Same-role separated lexical speech; singing filter and independent Japanese transcript check')
  (folder/('selected-'+profile['id']+'.json')).write_text(json.dumps(evidence,ensure_ascii=False,indent=2))
  emit('參考錄音已更換',f"{profile.get('name','角色')}：略過拼接／不適用參考，改用同角色 {a:.2f}–{b:.2f} 秒完整對白。原人物卡同舊錄音保留。")
  return save(dict(profile,reference=str(path),promptText=row['promptText'],referenceRanges=[[a,b]],referenceCandidates=[],mixedReference=False,shortReference=False,transcriptSource='verified-same-role-spoken-reference',originalReference=str(primary)),'same-role-full-utterance-with-independent-ASR')
 raise ValueError(f"{profile.get('name','角色')} 參考不適合說話；其他同角色候選亦未通過核對，請在角色卡選擇完整清晰對白。")
