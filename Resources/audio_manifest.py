"""Cumulative auditions: a one-line retry must not hide the rest of a film."""
import json
from pathlib import Path

def publish(job, engine, language, cues, paths):
    path=Path(job)/'audio-preview.json'
    try:previous=json.loads(path.read_text())
    except (ValueError,OSError):previous={}
    rows=previous.get('rows',[]) if previous.get('engine')==engine and previous.get('language')==language else []
    def key(row):
        return (row.get('start'),row.get('end'),row.get('speakerId'),row.get('cantonese'),row.get('_seed',42),row.get('editorRate',1),row.get('editorTrimStart',0),row.get('editorTrimEnd',0))
    merged={key(row):row for row in rows}
    for cue,audio in zip(cues,paths):merged[key(cue)]=dict(cue,audio=str(audio),modelVersion=__import__('gsv_versions').VERSIONS.get(engine,engine))
    from worker import atomic_json
    atomic_json(path,dict(engine=engine,language=language,rows=list(merged.values()),revision=2))
