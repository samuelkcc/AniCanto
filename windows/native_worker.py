"""Windows process entry for the same conversion/editor worker used by macOS.

The submitted settings file is immutable. Native paths and verified model IDs
are projected into a separate invocation snapshot before shared plan freezing.
"""
import argparse
import contextlib
import copy
import json
import os
from pathlib import Path
import sys
import uuid

HERE=Path(__file__).resolve().parent
SHARED=HERE/'shared' if (HERE/'shared').is_dir() else HERE.parent/'Resources'
for folder in (SHARED,HERE):
    if str(folder) not in sys.path:sys.path.insert(0,str(folder))


def configure(submitted,ready,package=HERE,emit=lambda *a,**k:None):
    from workflow_settings import validated
    cfg=validated(submitted)
    if submitted.get('translationSource')=='combined':emit('Windows settings compatibility','Normalized the legacy translation source for this attempt; the saved request is unchanged.')
    if ready.get('modelLoadPassed') is not True or ready.get('speechInferencePassed') is not True:
        raise ValueError('Complete Windows setup and its model/speech probes before starting production.')
    for key in ('ffmpeg','ffprobe'):
        path=Path(ready.get(key,''))
        if not path.is_file():raise ValueError(f'The verified native {key} is missing; repair setup.')
        cfg[key]=str(path)
    from source_access import accessible, cloud_or_remote
    def local_video(video):
        if not cloud_or_remote(video,cfg['storage']):return video
        local_source,_=accessible(video,cfg['ffprobe'],cfg['storage'],emit)
        return str(local_source)
    if cfg.get('video'):
        original=cfg['video'];cfg['video']=local_video(original)
        if cfg['video']!=original:cfg['sourceMediaOriginal']=original
    for item in cfg.get('videos',[]):
        original=item['video'];item['video']=local_video(original)
        if item['video']!=original:item['sourceMediaOriginal']=original
    helper=Path(package)/'tools/AniCanto-helper.exe'
    if not helper.is_file():raise ValueError('The packaged Windows media helper is missing.')
    cfg['executable']=str(helper)
    cfg['port']=11445
    cfg['nativeComputeBackend']=ready.get('backend','cpu')
    cfg['nativeWorkflowVersion']=1
    cfg.setdefault('nativeDramaCPU',bool(ready.get('allowDramaCPU')))
    cfg.setdefault('ttsBackend',(cfg.get('selectedEngines') or ['drama3'])[0])
    cfg.setdefault('defaultAudioEngine',cfg['ttsBackend'])
    roles=ready.get('roles',{})
    cfg.setdefault('roleAnalysisMode','audio')
    alias=ready.get('textModel')
    if not alias or str(alias).startswith('mlx:'):raise ValueError('Windows setup has not verified a native translation model.')
    previous=cfg.get('model')
    if not previous or str(previous).startswith('mlx:'):
        cfg['model']=alias
        if previous:cfg['nativeModelMigration']=dict(previous=previous,selected=alias,reason='Use the verified native model; MLX weights cannot run on Windows.')
    if not cfg.get('visualModel') or str(cfg.get('visualModel','')).startswith('mlx:'):
        cfg['visualModel']=alias if roles.get('visual') or roles.get('vision') else None
    # Only migrate known platform-specific defaults. An explicitly selected
    # native alternative is retained and validated by the shared catalog.
    for key,role,legacy in [('asrModel','asr',('asr-1.7b-bf16','asr-1.7b-4bit')),
                            ('speechModel','speech',()),('referenceSpeechModel','referenceSpeech',()),
                            ('cosyModel','cosyvoice3',('cosy-0.5b-4bit','cosy-0.5b-bf16')),
                            ('drama3Model','drama3',('drama3-35b-4bit',)),
                            ('voxcpmModel','voxcpm2',()),('wsyueModel','wsyue',())]:
        if not cfg.get(key) or cfg.get(key) in legacy:
            replacement=roles.get(role)
            if key=='cosyModel':replacement='cosy-native-0.5b'
            if key=='drama3Model':replacement='drama3-native-q2'
            if replacement:cfg[key]=replacement
    cfg.setdefault('exportFolder',str(Path(cfg['storage'])/'exports'))
    if cfg.get('exportFolder'):Path(cfg['exportFolder']).mkdir(parents=True,exist_ok=True)
    from native_models import recover
    recover(cfg,emit) # Selected engine is resolved before the common core freezes it.
    return cfg


def run(action,submitted):
    if sys.platform!='win32':raise RuntimeError('Run this production entry on Windows x64.')
    from process_job import install
    install()
    os.environ.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',ORT_DISABLE_TELEMETRY='1',
                      CANTOSYNC_WINDOWS_PACKAGE=str(HERE))
    os.environ['PYTHONPATH']=os.pathsep.join([str(HERE),str(SHARED),os.environ.get('PYTHONPATH','')])
    import worker
    from shared_backend import bind
    from native_service import service
    root=Path(submitted['storage']);ready=json.loads((root/'native-ready.json').read_text(encoding='utf-8'))
    requests=root/'requests';requests.mkdir(parents=True,exist_ok=True)
    cfg=project_request(action,submitted,ready,requests,emit=worker.emit)
    from native_models import missing_setup
    check=cfg
    if action=='render-project':check=json.loads(Path(cfg['submission']).read_text(encoding='utf-8'))['settings']
    absent=missing_setup(root,check.get('selectedEngines') or [check['ttsBackend']],check.get('nativeDramaCPU',False))
    if absent:raise ValueError('Deploy the selected native engine before processing this episode: '+', '.join(absent))
    snapshot=requests/('native-'+uuid.uuid4().hex+'.json')
    snapshot.write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
    previous=list(sys.argv)
    try:
        sys.argv=[str(SHARED/'worker.py'),action,str(snapshot)]
        with service(root,port=cfg['port']),bind():worker.main()
    finally:sys.argv=previous


def project_request(action,submitted,ready,requests,package=HERE,emit=lambda *a,**k:None):
    """Project editor settings too: project_edit merges them before plan freezing.

    Never mutate a submitted draft or an existing review merely to change OS.
    """
    cfg=configure(submitted,ready,package,emit)
    if action=='render-project':
        draft=copy.deepcopy(json.loads(Path(submitted['submission']).read_text(encoding='utf-8')))
        review=Path(draft['review'])
        base=review.parent/'editor-base.json'
        source=json.loads((base if base.is_file() else review).read_text(encoding='utf-8'))
        settings=dict(source['config'],**draft.get('settings',{}),storage=submitted['storage'])
        draft['settings']=configure(settings,ready,package,emit)
        if draft.get('previewEngine')=='drama3' and draft['settings'].get('nativeEngineFallback'):
            draft['previewEngine']=draft['settings']['nativeEngineFallback']['selected']
        path=Path(requests)/('draft-native-'+uuid.uuid4().hex+'.json')
        path.write_text(json.dumps(draft,ensure_ascii=False,indent=2),encoding='utf-8')
        cfg['submission']=str(path)
    return cfg


def main():
    parser=argparse.ArgumentParser();parser.add_argument('action');parser.add_argument('config')
    args=parser.parse_args()
    try:run(args.action,json.loads(Path(args.config).read_text(encoding='utf-8')))
    except Exception as error:
        import traceback
        traceback.print_exc(file=sys.stderr)
        print(json.dumps(dict(stage='錯誤',message=str(error)),ensure_ascii=False),flush=True)
        return 1
    return 0

if __name__=='__main__':sys.exit(main())
