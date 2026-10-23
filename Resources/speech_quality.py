"""Bounded standalone speech review using the video's independent listeners.

Uncertain ASR spelling is a note, never automatic permission to change a voice.
All initial/candidate audio and decisions are retained under this one take.
"""
import hashlib,json
from pathlib import Path
from speech_library import read,write,digest

REVISION='speech-studio-two-witnesses-1'

def signal_problems(path,text):
 from audio_fallback import healthy
 p=Path(path)
 if p.name.startswith('skipped-') or not healthy(p):return ['missing-or-silent']
 import soundfile as sf
 from tts_health import problems
 audio,rate=sf.read(p,dtype='float32',always_2d=True)
 found=problems(audio.mean(axis=1),rate,text)
 if sum(c.isalnum() for c in text)>=6 and len(audio)/rate<max(.3,min(2.,sum(c.isalnum() for c in text)*.04)):found.append('implausibly-short')
 return list(dict.fromkeys(found))

def verdict(cue,path,evidence):
 from normal_mode import major_omission,extra_repetition
 from speechcheck import similarity
 physical=signal_problems(path,cue['cantonese']);notes=[]
 if physical:notes+=physical
 confirmed=evidence.get('languageFailure') or ('confirmed-content-problem' if evidence.get('contentFailure') else '')
 if confirmed:notes.append(confirmed)
 if not evidence:notes.append('listening-unavailable')
 elif evidence.get('decision')!='cantonese':notes.append('language-unconfirmed')
 if evidence and (major_omission(cue['cantonese'],evidence.get('heard','')) or extra_repetition(cue['cantonese'],evidence.get('heard','')) or similarity(cue['cantonese'],evidence.get('heard',''))<.45):notes.append('words-need-review')
 return dict(status='passed' if not notes else 'needs-review',notes=list(dict.fromkeys(notes)),confirmedFailure=bool(physical or confirmed),check=evidence,physicalProblems=physical,qualityCertified=False)

def review(cfg,job,cues,paths,run,emit):
 from normal_mode import inspect,audio_present
 from dubbing import gsv_audio
 from track_control import check,UserSkipped
 job=Path(job);paths=list(map(Path,paths))
 if len(paths)!=len(cues):raise ValueError('The voice engine did not return every script part.')
 checks=inspect(cfg,job,cues,paths,emit)
 report=dict(revision=REVISION,status='running',maximumAdditionalAttempts=2,qualityCertified=False,parts=[])
 selected=list(paths)
 for n,(cue,original) in enumerate(zip(cues,paths)):
  initial=verdict(cue,original,checks.get(n+1,{}));record=dict(index=n+1,text=cue['cantonese'],initialAudio=str(original),selectedAudio=str(original),initial=initial,selected=initial,attempts=[])
  report['parts'].append(record)
  for attempt in range(2):
   if not cfg['speechStudio'].get('autoRepair',True) or not record['selected']['confirmedFailure']:break
   # A receipt is written before invoking a model; reopening cannot replenish
   # an interrupted take's persistent two-attempt budget.
   candidate_folder=job/'repairs'/str(n+1)/str(attempt+1);candidate_folder.mkdir(parents=True,exist_ok=True)
   receipt=candidate_folder/'attempt.json';saved=read(receipt,{})
   candidate_paths=[]
   if saved:
    candidate_paths=[Path(p) for p in saved.get('paths',[])]
   else:
    write(receipt,dict(status='attempted',paths=[]));check(cfg)
    emit('Dubbing',f'Repairing confirmed problem · part {n+1}/{len(cues)} · attempt {attempt+1}/2',.7)
    pending=dict(cue,reviewIndex=n,_seed=(int(cfg['speechStudio']['id'][:8],16)+104729*(attempt+1)+n)%2147483647,_deliveryStyle='cantonese-yue-clauses' if cfg['ttsBackend']=='drama3' else 'cantonese-strict-clauses')
    try:
     candidate_paths=gsv_audio(dict(cfg,editorCache=str(candidate_folder),audioRerunToken=f'speech-repair-{n}-{attempt}',_normalRepair=True),candidate_folder,[pending],run,emit)
     write(receipt,dict(status='finished',paths=[str(p) for p in candidate_paths]))
    except UserSkipped:raise
    except (OSError,RuntimeError,ValueError) as error:
     if getattr(error,'abortVoiceTrack',False):raise
     write(receipt,dict(status='failed',paths=[],error=str(error)))
   if not candidate_paths:
    record['attempts'].append(dict(attempt=attempt+1,status='failed',adopted=False));continue
   candidate=Path(candidate_paths[0]);second=inspect(cfg,candidate_folder,[dict(cue,reviewIndex=n)],[candidate],emit)
   state=verdict(cue,candidate,second.get(n+1,{}))
   adopt=state['status']=='passed' or not audio_present(selected[n]) and not state['physicalProblems']
   record['attempts'].append(dict(attempt=attempt+1,audio=str(candidate),review=state,adopted=bool(adopt)))
   if adopt:selected[n]=candidate;record.update(selectedAudio=str(candidate),selected=state)
   write(job/'speech-review.json',report)
  if selected[n].is_file():record['selectedSHA256']=digest(selected[n])
 report['status']='passed' if all(p['selected']['status']=='passed' for p in report['parts']) else 'needs-review'
 report['notes']=list(dict.fromkeys(note for part in report['parts'] for note in part['selected']['notes']))
 report['repairedParts']=[p['index'] for p in report['parts'] if any(a.get('adopted') for a in p['attempts'])]
 write(job/'speech-review.json',report)
 return selected,report
