"""Native model identities are explicit; never relabel MLX weights as Torch/GGUF."""
import copy,json
from pathlib import Path

ENGINES=['drama3','gpt-sovits-v2','gpt-sovits','cosyvoice3','voxcpm2','wsyue']

def missing_setup(root,engines,allow_cpu_drama=False):
    """Reject an undeployed selection before recognising an entire episode."""
    root=Path(root);missing=[]
    if (root/'setup-invalidated.json').exists():return list(engines)
    def ready(name):
        try:return json.loads((root/(name+'-windows-ready.json')).read_text(encoding='utf-8'))
        except (OSError,ValueError):return {}
    for engine in engines:
        if engine=='drama3' and not allow_cpu_drama:
            native=ready('drama3')
            if native.get('variant') in ('drama3-small-iq3','drama3-native-q2') and native.get('speechInferencePassed'):
                if native.get('variant')=='drama3-native-q2' and native.get('backend')=='cuda':
                    from drama_full_cuda import ready as cuda_ready
                    if not cuda_ready(root,require_speech=True):missing.append(engine)
                continue
            from drama_cuda import capable
            if capable():missing.append(engine);continue
            marker=ready('gpt')
            if not marker.get('modelLoadPassed') or not marker.get('speechInferencePassed') or not any(v in marker.get('speechVersions',[]) for v in ('v2ProPlus','v4')):missing.append(engine)
            continue
        kind='gpt' if engine.startswith('gpt-sovits') else 'cosy' if engine=='cosyvoice3' else 'local' if engine in ('voxcpm2','wsyue') else 'drama3'
        marker=ready(kind)
        if not marker.get('modelLoadPassed') or not marker.get('speechInferencePassed'):missing.append(engine);continue
        if kind=='gpt' and ('v2ProPlus' if engine=='gpt-sovits-v2' else 'v4') not in marker.get('speechVersions',[]):missing.append(engine)
        if kind=='local' and engine not in marker.get('verifiedEngines',[]):missing.append(engine)
    return missing

def recover(cfg,emit):
    root=Path(cfg['storage']);explicit_legacy_small=cfg.get('drama3Model')=='drama3-small-iq3'
    cfg.setdefault('asrModel','asr-native-1.7b');cfg.setdefault('cosyModel','cosy-native-0.5b')
    cfg.setdefault('drama3Model','drama3-native-q2');cfg['nativeDramaFormat']='gguf-cpu'
    for key in ('model','visualModel'):
        if str(cfg.get(key,'')).startswith('mlx:'):raise ValueError('This job selects an incompatible MLX model. Choose an installed Windows model in the model centre.')
    for key,default in [('asrModel','asr-native-1.7b'),('cosyModel','cosy-native-0.5b'),('drama3Model','drama3-native-q2')]:
        if cfg.get(key) is None:cfg[key]=default
    requested=cfg.get('selectedEngines') or [cfg.get('ttsBackend','drama3')]
    try:drama_ready=json.loads((root/'drama3-windows-ready.json').read_text())
    except (OSError,ValueError):drama_ready={}
    small_ready=explicit_legacy_small and drama_ready.get('variant')=='drama3-small-iq3' and drama_ready.get('modelLoadPassed') and drama_ready.get('speechInferencePassed')
    full_cpu_ready=drama_ready.get('variant')=='drama3-native-q2' and drama_ready.get('backend')=='cpu' and drama_ready.get('modelLoadPassed') and drama_ready.get('speechInferencePassed')
    full_cuda_ready=False
    if drama_ready.get('variant')=='drama3-native-q2' and drama_ready.get('backend')=='cuda' and drama_ready.get('modelLoadPassed') and drama_ready.get('speechInferencePassed'):
        from drama_full_cuda import ready
        if not ready(root,require_speech=True):raise ValueError('The full Drama 3 CUDA runtime needs repair in One-click setup. Existing recordings are retained.')
        full_cuda_ready=True
    if full_cuda_ready and 'drama3' in requested:
        cfg.update(drama3Model='drama3-native-q2',drama3Backend='cuda',nativeDramaCPU=False,nativeDramaFormat='gguf-cuda',drama3Memory=drama_ready.get('memory'))
    if full_cpu_ready and 'drama3' in requested:
        cfg['drama3Model']='drama3-native-q2';cfg['drama3Backend']='cpu';cfg['nativeDramaCPU']=True;cfg['nativeDramaFormat']='gguf-cpu'
    if small_ready and 'drama3' in requested:
        cfg['drama3Model']='drama3-small-iq3';cfg['drama3Backend']=drama_ready.get('backend','cpu');cfg['nativeDramaCPU']=cfg['drama3Backend']=='cpu'
        cfg['nativeDramaFormat']='gguf-'+cfg['drama3Backend']
    if 'drama3' in requested and not small_ready and not full_cuda_ready and not cfg.get('nativeDramaCPU'):
        # An older, undeployed job may retain an explicit GPT fallback. A CUDA
        # device name alone is never evidence of a working Drama runtime.
        marker=root/'gpt-windows-ready.json'
        ready=json.loads(marker.read_text()) if marker.is_file() else {}
        available=ready.get('speechVersions',ready.get('modelVersions', [ready.get('modelVersion')]))
        replacement='gpt-sovits-v2' if 'v2ProPlus' in available else 'gpt-sovits' if 'v4' in available else None
        if not replacement or not ready.get('modelLoadPassed'):raise ValueError('Install the native GPT fallback before starting a Drama 3 job on this GPU.')
        cfg.setdefault('requestedEngines',list(requested))
        cfg['selectedEngines']=list(dict.fromkeys(replacement if e=='drama3' else e for e in requested))
        for key in ('ttsBackend','defaultAudioEngine'):
            if cfg.get(key)=='drama3':cfg[key]=replacement
        reason='Drama 3 has not passed deployment on this PC; using the previously installed GPT fallback. Deploy Drama 3 in One-click setup to enable it.'
        cfg['nativeEngineFallback']=dict(requested='drama3',selected=replacement,reason=reason)
        emit('Windows voice fallback',reason,nativeEngineFallback=cfg['nativeEngineFallback'])
    if cfg.get('ttsBackend')=='gpt-sovits-v2':cfg['gsvVersion']='v2ProPlus'
    if cfg.get('gsvDevice') in (None,'mps'):cfg['gsvDevice']='auto'
    if cfg.get('voxcpmDevice') in (None,'mps'):cfg['voxcpmDevice']='cuda' if cfg.get('nativeComputeBackend') in ('nvidia','amd') else 'cpu'
    if cfg.get('separationDevice') in (None,'mps'):cfg['separationDevice']='auto'
