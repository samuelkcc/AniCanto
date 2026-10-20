"""Native Windows model child, using the shared generation/health/retry loop."""
import json
import os
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
SHARED=HERE/'shared' if (HERE/'shared').is_dir() else HERE.parent/'Resources'
sys.path.insert(0,str(SHARED))


def execute(action,cfg):
    if sys.platform!='win32':raise RuntimeError('Native Windows inference must be executed and tested on Windows.')
    if action not in ('tts','separate','speakers','independent-voices','cosy','asr','normal-listen','voxcpm2','wsyue','drama3'):raise ValueError('Unintegrated Windows inference action: '+str(action))
    if action=='normal-listen':
        from normal_mode import listen
        return listen(cfg)
    if action=='asr':
        from asr_verify import verify
        return verify(cfg)
    if action=='drama3':
        from native_drama import synthesize
        from dubbing_runner import emit
        return synthesize(cfg,emit)
    from native_tts import audio_compatibility
    audio_compatibility()
    from gpu import torch_probe
    probe=torch_probe('gpt',cfg.get('device','auto'),int(cfg.get('gpuIndex',0)))
    import dubbing_runner as shared
    shared.emit('Windows inference','Native runtime kernel passed; loading the selected model.',hardware=probe)
    cfg=dict(cfg,device=probe['device'],voxcpmDevice=probe['device'])
    os.environ['CANTOSYNC_NATIVE_DEVICE']=probe['device']
    if action=='cosy':
        from cosy import synthesize
        return synthesize(cfg,shared.emit)
    if action in ('voxcpm2','wsyue'):
        if action=='wsyue':
            import torch
            torch.cuda.is_available=lambda:False
        from local_tts import synthesize
        return synthesize(cfg,shared.emit,action)
    if action=='tts':
        from native_tts import gpt_text_compatibility
        gpt_text_compatibility()
        # Keeps the shared four-attempt persistent budget, reference alternatives,
        # pronunciation overrides, rejected takes and native output-rate checks.
        return shared.tts(cfg)
    if action=='separate':return shared.separate(cfg)
    if action=='speakers':
        from speakers import analyze
        return analyze(cfg,shared.emit)
    from independent_voices import prepare
    return prepare(cfg,shared.emit)


if __name__=='__main__':
    try:execute(sys.argv[1],json.loads(Path(sys.argv[2]).read_text(encoding='utf-8')))
    except Exception as error:
        import traceback
        traceback.print_exc(file=sys.stderr)
        print(json.dumps(dict(stage='錯誤',message=str(error)),ensure_ascii=False),flush=True)
        sys.exit(1)
