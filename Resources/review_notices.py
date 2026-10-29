"""Read-only human summaries; raw diagnostics stay in saved job/debug files."""
import json
from pathlib import Path

def read(path):
 try:value=json.loads(Path(path).read_text());return value if isinstance(value,dict) else {}
 except (OSError,ValueError):return {}

def project(root):
 root=Path(root);notices=[]
 def metric(label,value):return dict(label=label,value=len(value) if isinstance(value,list) else value)
 ocr=read(root/'ocr-status.json');source=read(root/'input-source.json')
 if ocr.get('status') in ('failed','partial') or source.get('ocrError'):
  notices.append(dict(code='ocr-incomplete',title='OCR needs attention',message='Some screen subtitles could not be read. Audio transcription was used; existing recordings are retained.',metrics=[metric('Unread subtitle frames',ocr.get('failedFrames',0))],detail=ocr.get('error') or source.get('ocrError') or str(ocr.get('failedFrames',0))))
 fragments=read(root/'source-fragment-report.json')
 if fragments.get('suspectSegments'):
  notices.append(dict(code='source-fragments',title='Source timing review',message='Some original speech boundaries remain uncertain. Compare the original audio at these passages; this does not confirm incorrect dubbing.',metrics=[metric(k,fragments.get(field,0)) for k,field in [('Source fragments checked','suspectSegments'),('Local listening windows','windows'),('Recovered source boundaries','recoveredSegments'),('Source boundaries not confirmed','unconfirmedSegments')]],detail=str(fragments)))
 alignment=read(root/'caption-alignment.json')
 if alignment.get('issues'):
  notices.append(dict(code='caption-allocation',title='Subtitle allocation review',message='Some captions span multiple spoken turns. This is an alignment note, not a confirmed missing or incorrect recording.',metrics=[metric('Spoken turns with shared captions',alignment['issues'])],detail=str(alignment['issues'])))
 policy=read(root/'source-policy.json');fields=('unresolved','fallbackTurns','continuationTurns','primaryFallbacks','subtitleClockGaps')
 if any(policy.get(k) for k in fields):
  uncertain=bool(policy.get('unresolved') or policy.get('subtitleClockGaps'))
  notices.append(dict(code='primary-source-allocation',title='Subtitle source alignment',message='Some subtitle passages still need a confirmed speech clock. Original audio and subtitle evidence are retained.' if uncertain else 'Shared subtitle content is assigned to a main spoken turn. Continuation fragments avoid repeating the same translation; this alone is not missing dubbing.',metrics=[metric(label,policy.get(field,[])) for label,field in [('Unresolved subtitle passages','unresolved'),('Subtitles assigned to a main turn','fallbackTurns'),('Continuation fragments','continuationTurns'),('Auxiliary content used','primaryFallbacks'),('Subtitle clock gaps','subtitleClockGaps')]],detail=str({k:policy.get(k,[]) for k in fields})))
 return notices
