"""One authored caption has one spoken owner. Do not add a duplicate source voice."""
REVISION='caption-owner-no-duplicate-263'
def owners(cues,index):
 cue=cues[index];ids=set(cue.get('primarySource',{}).get('captionIDs',[]))
 if not ids:return []
 found=[];covered=set()
 for n,other in enumerate(cues):
  if n==index or not other.get('enabled',True) or not str(other.get('cantonese') or other.get('primarySource',{}).get('text','')).strip():continue
  shared=ids.intersection(other.get('primarySource',{}).get('captionIDs',[]))
  if shared:covered.update(shared);found.append(n)
 return found if covered==ids else []
def apply(cfg,cues):
 if cfg.get('captionContinuationRevision')!=REVISION or cfg.get('editorRender'):return
 from dubbing import is_vocalization
 for n,cue in enumerate(cues):
  if cue.get('editorAudio') or cue.get('editorDecisions') or cue.get('originalSpeechReason')!='subtitle-continuation' or is_vocalization(cue):continue
  adjacent=owners(cues,n)
  if not adjacent:continue
  cue.update(captionCovered=True,captionCoverageOwners=[cues[i].get('reviewIndex',i)+1 for i in adjacent],captionCoverageRevision=REVISION,
   captionPolicyWasEnabled=cue.get('enabled',True),captionPolicyExcluded='caption-owned-by-neighbour',enabled=False,preserveOriginalSpeech=False)
  cue['originalSpeechReason']='caption-covered-continuation'
  cue['reviewNote']='字幕內容已分配到相鄰對白；不重複配音或加入日文碎段，原聲仍可獨立試聽。'
