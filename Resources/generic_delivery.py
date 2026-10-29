from repair_limits import bounded as bounded_repair
"""Finish already-generated generic speech before considering source continuity.

Only measured, failed Normal-mode lines enter. Fitting original takes, manually
chosen audio and source performance are protected; all trial artefacts persist.
"""
import copy,hashlib,json
from pathlib import Path


def read(path,default):
 try:return json.loads(Path(path).read_text())
 except (OSError,ValueError):return default


@bounded_repair('generic_delivery.repair')
def repair(cfg,job,cues,paths,placement,run,emit):
 from delivery_policy import enabled
 if not enabled(cfg) or cfg.get('failedVoicePolicy','generic')!='generic' or not cfg.get('automaticVoiceFallback',True) or cfg.get('editorRender') or not placement:return paths
 from normal_policy import finish_requested
 if finish_requested(cfg):return paths
 from normal_mode import audio_present,inspect
 from natural_voices import resolve
 from dubbing import profile_for
 from natural_delivery import repair as repair_duration,seconds
 from natural_finish import finish
 from normal_recovery import verified_check,clear_confirmed
 from worker import atomic_json
 job=Path(job);ledger_path=job/'target-reference-recovery.json';ledger=read(ledger_path,{})
 language=cfg.get('targetLanguage','yue');selected=list(paths);drafts=copy.deepcopy(cues);trials=list(paths);targets={};profiles={}
 for key,record in ledger.items():
  if record.get('status')!='timing-not-fit':continue
  index=record.get('index');i=next((n for n,c in enumerate(cues) if c.get('reviewIndex',n)+1==index),None)
  if i is None or placement[i].get('fit') or cues[i].get('editorAudio') or cues[i].get('preserveOriginalSpeech'):continue
  candidate=Path(record.get('audio') or '/nonexistent')
  if not audio_present(candidate):continue
  # A failed timing trial is not permission to generate new wording if it has
  # already spent its persistent text/audio repair allowance.
  try:
   try:original=profile_for(cues[i],cfg)
   except (OSError,ValueError):original=dict(id=cues[i].get('speakerId') or f'generic-{index}',language=cfg.get('sourceLanguage','ja'),reference='',promptText='')
   reference=resolve(dict(original,engineReferences={},promptText=''),dict(cfg,voiceStyleMode='natural'))
   if hashlib.sha256(Path(reference['reference']).read_bytes()).hexdigest()!=record.get('referenceSHA256'):continue
  except (OSError,ValueError,KeyError):continue
  profiles[reference['id']]=reference;drafts[i].update(speakerId=reference['id'],reviewIndex=index-1)
  trials[i]=candidate;targets[i]=key
 if targets:
  for i,draft in enumerate(drafts):
   if i not in targets:draft['editorAudio']=str(trials[i])
  folder=job/'generic-measured-delivery';folder.mkdir(exist_ok=True)
  local=dict(cfg,voiceProfiles=list(profiles.values()),voiceStyleMode='clone',preferFirstAudibleTake=False,
    automaticDurationRewrite=True,_durationFitRequired=True,_genericTiming=True,editorCache=str(folder),_voiceManifest={p['id']:hashlib.sha256(Path(p['reference']).read_bytes()).hexdigest() for p in profiles.values()})
  # The full scene remains available for hard timing boundaries. Only target
  # indices may be rewritten, and only after their actual WAV is measured.
  planned=__import__('natural_schedule').prepare(local,folder,drafts,trials,run,emit)
  revised=repair_duration(local,folder,drafts,trials,run,emit,placement=planned)
  revised,new_placement=finish(local,folder,drafts,revised,run,emit,allow_tempo=True)
  candidates=[i for i in targets if new_placement and new_placement[i].get('fit') and audio_present(revised[i])]
  checks=inspect(dict(local,_forceIndependentListening=True),folder,[drafts[i] for i in candidates],[revised[i] for i in candidates],emit) if candidates else {}
  confirmed=set()
  for i in targets:
   index=cues[i].get('reviewIndex',i)+1;record=ledger[targets[i]];proof=checks.get(index,{})
   if i not in candidates or (bool(proof.get('languageFailure') or proof.get('contentFailure')) if __import__('delivery_policy').bounded_delivery(cfg) else not verified_check(proof,drafts[i].get('cantonese',''),language)):
    record['measuredDelivery']=dict(status='not-adopted',reason='timing-or-language-content-unconfirmed',check=proof)
    continue
   selected[i]=Path(revised[i]);confirmed.add(index)
   original=cues[i].get('cantonese','');text=drafts[i]['cantonese']
   cues[i].update(cantonese=text)
   if text!=original:cues[i].setdefault('preGenericFitCantonese',original)
   if language in ('en','zh'):cues[i][__import__('output_language').field(language)]=text
   if not cues[i].get('captionOverride'):cues[i]['captionText']=text
   record.update(status='adopted',selectedAudio=str(selected[i]),selectedSeconds=seconds(selected[i],cfg,run),text=text,check=proof,
      measuredDelivery=dict(status='adopted',before=original,after=text,measuredOnly=True),qualityCertified=False)
  clear_confirmed(cfg,job,confirmed,atomic_json);atomic_json(ledger_path,ledger)
 # Only the remaining objective failures may try ONE other installed engine,
 # using the target-language bank rather than another Japanese clone.
 selected,placement=finish(cfg,job,cues,selected,run,emit,allow_tempo=True)
 if not cfg.get('_skipAlternate') and ((placement and any(not row.get('fit') for row in placement)) or read(job/'normal-checks.json',{}).get('unresolved')):
  if not finish_requested(cfg):
   from normal_engine_fallback import repair as alternate
   selected=alternate(dict(cfg,_genericTargetVoice=True,_forceIndependentListening=True,_maximumAlternateEngines=1),job,cues,selected,placement,run,emit)
 review=read(job/'review.json',{})
 if review.get('cues'):
  by_index={c.get('reviewIndex',i):c for i,c in enumerate(cues)}
  for i,c in enumerate(review['cues']):
   updated=by_index.get(c.get('reviewIndex',i))
   if updated:c.update({key:updated[key] for key in ('cantonese','english','mandarin','captionText','preGenericFitCantonese') if key in updated})
  atomic_json(job/'review.json',review)
 return selected
