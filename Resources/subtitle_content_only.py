"""Selected subtitles are content; gaps retain audio, never ASR-generated script."""

def preserve_gap(c):
 c.update(subtitleContentOnlyGap=True,sourcePolicyBlocked=True,preserveOriginalSpeech=True,originalSpeechReason='subtitle-content-only-gap')
 c.pop('missingScript',None);c.pop('sourcePrimaryFallback',None);c.pop('sourceAllocationReview',None)
 c['captionAllocation']=dict(content='',caption_ids=[],uncertain=False)
 if not c.get('editorAudio'):
  for field in ('cantonese','english','mandarin','captionText'):c[field]=''
 c['reviewNote']='字幕空隙：保留原音；沒有新增翻譯、配音或修復，不計漏配。'

def complete_windows(cfg,job,cues,write):
 """Caption-only intervals use labelled subtitle clocks, not fabricated ASR."""
 if cfg.get('editorRender') or cfg.get('_singleEngine'):return
 from source_evidence import caption_records
 from primary_source import speech_owners
 from pathlib import Path
 import opening
 records=caption_records(job);known_duration=float(cfg.get('duration') or max([c['end'] for c in cues]+[r['end'] for r in records]+[0]))
 exclusions=opening.local_ranges(dict(cfg,duration=known_duration,_captionPreserveRanges=[]))
 existing={c.get('subtitleClockFallbackID') for c in cues}
 added=[]
 for row in records:
  if opening.excludes(row,exclusions) or row['id'] in existing or speech_owners(row,cues):continue
  a,b=float(row['start']),float(row['end']);duration=float(cfg.get('duration',b))
  if not 0<=a<b<=duration:continue
  # A display-clock fallback is explicit evidence, never a claim that ASR
  # recognized these words or that the exact acoustic start has been found.
  added.append(dict(start=a,end=b,speechStart=a,speechEnd=b,text='',japanese='',cantonese='',enabled=True,
   subtitleClockFallbackID=row['id'],sourceClockFallback='authored-subtitle-display',sourceClockUnconfirmed=True,subtitleHint=row['text'],
   reviewNote='字幕有內容但未有語音時鐘；暫用原字幕時間，原意照字幕翻譯。'))
 if added:
  cues.extend(added);cues.sort(key=lambda c:(c['start'],c['end']))
  # Persist before later render validation reads the original cue count.
  write(Path(job)/'cues.json',cues)
