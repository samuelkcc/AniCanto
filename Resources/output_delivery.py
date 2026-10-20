"""Keep intermediate per-track movies separate from a published episode."""
import copy,json
from pathlib import Path


def track_event(extra):
    result=dict(extra,artifactRole='track-workfile')
    for key in ('output','subtitles','review','job'):
        if key in result:result['track'+key[:1].upper()+key[1:]]=result.pop(key)
    return result


def is_track_workfile(root,value):
    if not isinstance(value,str) or not value:return False
    try:
        relative=Path(value).resolve().relative_to(Path(root).resolve()/'jobs')
        return 'tracks' in relative.parts[:-1]
    except (ValueError,OSError):return False


def public_event(root,event):
    if event.get('artifactRole')=='track-workfile' or is_track_workfile(root,event.get('output')):
        return track_event(event)
    return dict(event)


def presentation(root,row,default_folder=''):
    """Old saved queues may still contain a child output; never rewrite them here."""
    value=copy.deepcopy(row)
    for key in ('output','outputThisAttempt'):
        if is_track_workfile(root,value.get(key)):
            value['workingOutput']=value.pop(key)
    if value.get('workingOutput') and not value.get('output'):
        value['deliveryState']='not-exported'
        if value.get('status')=='complete':value['status']='attention'
    # Recover omitted metadata from older bounded Mac event adapters. An exact
    # report/output match is required; a filename alone is never evidence.
    if not value.get('deliveryKind') and value.get('output'):
        job=Path(value.get('review') or Path(value.get('job','/nonexistent'))/'review.json').parent.resolve()
        try:
            if job.is_relative_to((Path(root)/'jobs').resolve()):
                report=json.loads((job/'report.json').read_text())
                outputs={report.get(k) for k in ('output','exportedOutput','previewOutput')}
                if report.get('deliveryKind')=='preview' and value['output'] in outputs:
                    detail=report.get('previewDelivery',{})
                    value.update(deliveryKind='preview',missingDialogue=detail.get('missingDialogue',0),incompleteDialogue=detail.get('incompleteDialogue',0))
        except (OSError,ValueError,TypeError):pass
    if value.get('deliveryKind')=='preview' and value.get('output'):
        value['deliveryState']='preview-exported'
        value['previewOutput']=value['output']
    folder=default_folder
    request=row.get('request')
    if request:
        path=Path(request)
        try:
            if not path.is_symlink() and path.resolve().is_relative_to(Path(root).resolve()/'requests'):
                saved=json.loads(path.read_text(encoding='utf-8'));folder=saved.get('exportFolder') or folder
        except (OSError,ValueError,TypeError):pass
    value['requestedExportFolder']=folder or str(Path(root)/'exports')
    return value
