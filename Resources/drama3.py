"""Pinned Fish Audio Drama 3 MLX inference, isolated from existing voice engines."""
from fast_mode import enabled as one_pass

import contextlib
import json
import os
import re
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parent
DEFAULT='drama3-35b-4bit'
REVISION='fish-drama3-5-explicit-shared-sampling'
RATE=44100
SAMPLING=dict(temperature=.7,top_p=.7,top_k=30)


class GenerationLimit(ValueError):
    """Retain rejected audio for diagnosis, never as a playable accepted take."""
    def __init__(self,audio):
        super().__init__('generation-limit：Drama 3 達到解碼上限，未將可能截句錄音當成功。')
        self.audio=audio


def complete_clauses(text):
    """Keep every character while retrying long, prematurely ended turns.

    A separate model completion per clause prevents an early end-of-turn token
    after one clause from silently discarding all remaining approved clauses.
    The same original/role-bank voice conditions every piece.
    """
    pieces=re.findall(r'[^，,。！？!?；;]+[，,。！？!?；;]*|[，,。！？!?；;]+',text)
    if ''.join(pieces)!=text or len(pieces)<2:return [text]
    if len(pieces)>8:pieces=pieces[:7]+[''.join(pieces[7:])]
    return pieces


def language_hint(language,style):
    """Two textual Yue cues; Drama 3 has no hard Cantonese language ID."""
    if language=='en':return 'Speak natural English'
    if style in ('cantonese-yue','cantonese-yue-clauses'):
        return '請用粵語讀出以下台詞，唔好用普通話或日文。完整讀出每個字，保留原聲語氣，唔好加字或重複。'
    if style in ('cantonese-strict','cantonese-strict-clauses'):
        return '用香港廣東話講，唔好日文或普通話。完整讀出指定台詞，唔好加字、重複、拖長尾音或額外停頓，保留自然情緒'
    return '用香港廣東話講，自然語氣'


CLAUSE_STYLES=('complete-clauses','plain-clauses','cantonese-strict-clauses','cantonese-yue-clauses')


def generation_budget(text,target=None):
    """Generation must finish the words before the renderer fits their timing.

    The previous len(text)/6 * 2 ceiling silently assumed >=3 characters/sec.
    Cloned voices can be slower. A Japanese slot is not a safe stop condition
    for a Cantonese decoder; exceeding it is handled by measured time fitting.
    """
    count=sum(ch.isalnum() for ch in text)
    seconds=max(6.,count*.6+6.,2*float(target or 0))
    return min(1024,max(128,round(seconds*RATE/2048)))


def selection(cfg):return cfg.get('drama3Model') or DEFAULT


def validate(cfg):
    if cfg.get('targetLanguage','yue') not in ('yue','en'):
        raise ValueError('Drama 3 此工作流程提供廣東話及英文音軌。')
    from voice_models import choice
    return choice('drama3',selection(cfg))


def vendor_modules():
    """Extend only this child process; never replace the shared installed runtime."""
    import importlib
    base=ROOT/'tts-vendor/drama3/mlx_audio'
    for name,relative in [('mlx_audio.tts.models','tts/models'),('mlx_audio.lm.models','lm/models'),('mlx_audio.codec.models','codec/models')]:
        module=importlib.import_module(name);path=str(base/relative)
        if path not in module.__path__:module.__path__.insert(0,path)
    importlib.invalidate_caches()
    from mlx_audio.tts.models import fish_drama3
    if not Path(fish_drama3.__file__).resolve().is_relative_to(base):
        raise ValueError('Drama 3 未使用已固定的推理程式碼。')


def load(cfg):
    if sys.platform=='win32' or selection(cfg)=='drama3-small-iq3':
        from drama_gguf import load as native_load
        return native_load(cfg)
    validate(cfg)
    from dubbing_runner import offline
    offline()
    from voice_models import resolve
    folder=resolve(cfg['storage'],'drama3',selection(cfg))
    cache=Path(cfg['storage'])/'models/cache/drama3';cache.mkdir(parents=True,exist_ok=True)
    os.environ.update(HF_HOME=str(cache),HF_HUB_CACHE=str(cache/'hub'))
    vendor_modules()
    from mlx_audio.tts.utils import load_model
    model=load_model(str(folder),strict=True)
    if model.model_type!='fish_drama3' or model.sample_rate!=RATE:
        raise ValueError('Drama 3 架構或原生取樣率不符。')
    return model


def install(root,variant=None):
    from runtime_paths import python_for
    from dubbing_setup import download,call,emit
    from voice_models import install_files,mark_ready
    root=Path(root);python=python_for(root,'text-runtime')
    if not python.is_file():raise ValueError('請先部署本機 MLX 執行環境。')
    row,folder=install_files(root,'drama3',variant,download,emit)
    call([python,ROOT/'drama3.py','prepare',root,row['id']])
    mark_ready(root,row)
    (root/'drama3-ready.json').write_text(json.dumps(dict(engine='drama3',variant=row['id'],revision=row['revision'],adapter=REVISION)))
    emit('Drama 3 已通過離線載入檢查，可以逐句試音。')


def generate(model,item,cfg):
    if sys.platform=='win32' or selection(cfg)=='drama3-small-iq3':
        from drama_gguf import generate as native_generate
        return native_generate(model,item,cfg)
    import mlx.core as mx
    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly
    from math import gcd
    profile=item['profile'];text=item['text']
    from voice_parameters import drama_sampling
    sampling=drama_sampling(cfg)
    reference,sr=sf.read(profile['reference'],dtype='float32')
    if reference.ndim==2:reference=reference.mean(axis=1)
    if sr!=RATE:
        divisor=gcd(sr,RATE);reference=resample_poly(reference,RATE//divisor,sr//divisor).astype(np.float32)
    if not len(reference) or not profile.get('promptText','').strip():raise ValueError('Drama 3 需要可用角色參考及逐字原文。')
    mx.random.seed(int(item.get('seed',42)))
    language=cfg.get('targetLanguage','yue')
    cue=language_hint(language,item.get('deliveryStyle'))
    # Instructions are model-only; approved captions and verification text stay intact.
    chunks=[]
    pieces=complete_clauses(text) if item.get('deliveryStyle') in CLAUSE_STYLES else [text]
    import hashlib
    trace=dict(policy=REVISION,status='generating',parts=[],seed=int(item.get('seed',42)),
               requestedText=text,plannedParts=len(pieces),
               targetLanguage=language,languageControl='textual instruction; not a guaranteed decoder constraint',
               reference=str(profile['reference']),referenceSHA256=hashlib.sha256(Path(profile['reference']).read_bytes()).hexdigest(),
               targetSeconds=item.get('targetSeconds'),referenceLanguage=profile.get('language'),sampling=sampling,modelVariant=selection(cfg),backend='mlx',
               deliveryStyle=item.get('deliveryStyle'),sampleRate=RATE)
    cfg['_dramaLastGeneration']=trace
    for piece in pieces:
        prompted=piece if item.get('deliveryStyle') in ('plain-clauses','plain-whole') else '['+cue+'] '+piece
        maximum=generation_budget(piece,item.get('targetSeconds'))
        counts={}
        for result in model.generate(text=prompted,ref_audio=reference,ref_text=profile['promptText'],stream=True,
                                     first_chunk_frames=8,max_tokens=maximum,**sampling,speed=1.):
            from track_control import check
            check(cfg)
            audio=np.asarray(result.audio,dtype=np.float32).reshape(-1)
            if audio.size:chunks.append(audio)
            segment=int(getattr(result,'segment_idx',0) or 0)
            counts[segment]=counts.get(segment,0)+int(getattr(result,'token_count',0) or 0)
        trace['parts'].append(dict(characters=sum(c.isalnum() for c in piece),promptedText=prompted,maximumFrames=maximum,
                                  maximumSeconds=maximum*2048/RATE,segmentFrames=counts))
        trace['submittedText']=''.join(pieces[:len(trace['parts'])])
        if any(count>=maximum for count in counts.values()):
            trace['status']='generation-limit'
            raise GenerationLimit(np.concatenate(chunks) if chunks else np.zeros(0,dtype=np.float32))
    trace['status']='completed'
    return np.concatenate(chunks) if chunks else np.zeros(0,dtype=np.float32)


def generate_complete(model,item,cfg,emit):
    """Recover a real decoder cap before changing the actor's reference.

    A cap is a failed completion, not an ASR opinion. Repeating the same
    instruction, seed and reference simply reproduces the same failure. Try
    the full approved phrase without the inline instruction, then lossless
    clauses, in this same loaded model. Never accept or concatenate a capped
    part. Every rejected attempt remains available to audition.
    """
    import copy
    import numpy as np
    import soundfile as sf
    from acoustics import activity
    attempts=[]
    styles=[item.get('deliveryStyle','normal')]
    alternatives=('cantonese-strict','cantonese-strict-clauses') if cfg.get('productionMode')=='normal' and cfg.get('targetLanguage','yue')=='yue' else ('plain-whole','plain-clauses')
    styles += [style for style in alternatives if style not in styles]
    for number,style in enumerate(styles):
        fresh=dict(item,deliveryStyle=style,seed=int(item.get('seed',42))+number*104729)
        try:
            with contextlib.redirect_stdout(sys.stderr):audio=generate(model,fresh,cfg)
            if attempts:cfg['_dramaLastGeneration']['recoveryAttempts']=attempts
            return audio
        except GenerationLimit as error:
            trace=cfg.setdefault('_dramaLastGeneration',{})
            spans=activity(error.audio,RATE)
            trace['signalEvidence']=dict(generatedSeconds=len(error.audio)/RATE,
                activeSeconds=sum(b-a for a,b in spans),trailingInactiveSeconds=max(0,len(error.audio)/RATE-(spans[-1][1] if spans else 0)),
                activityRegions=spans,contentCertified=False)
            # Archive before another attempt changes the trace or raw file.
            path=Path(item['output'])
            diagnostic=path.with_name(path.stem+f'-decoder-{number+1}').with_suffix('.rejected.raw.wav')
            diagnostic.parent.mkdir(parents=True,exist_ok=True)
            sf.write(diagnostic,error.audio,RATE,subtype='FLOAT')
            trace['rejectedAudio']=str(diagnostic)
            if cfg.get('job'):
                from recording_history import preserve,read
                position=item.get('reviewIndex')
                cues=read(Path(cfg['job'])/'review.json').get('cues',[])
                cue=next((c for n,c in enumerate(cues) if c.get('reviewIndex',n)==position),{})
                try:preserve(cfg['job'],'drama3',cfg.get('targetLanguage','yue'),fresh,diagnostic,str(error),cue,trace)
                except (OSError,ValueError,TypeError) as archive_error:
                    emit('錄音歷史','未能保存診斷副本；原始失敗錄音仍保留：'+str(archive_error))
            attempts.append(copy.deepcopy(trace))
            if number+1==len(styles):
                trace['recoveryAttempts']=attempts[:-1]
                raise
            emit('配音自動重試',f'解碼未完成；保留同角色參考，以不同方式重讀完整台詞（{number+1}/{len(styles)-1}）。')


def synthesize(cfg,emit):
    if sys.platform=='win32' or selection(cfg)=='drama3-small-iq3':
        from drama_gguf import synthesize as native_synthesize
        return native_synthesize(cfg,emit)
    return _synthesize(cfg,emit)

def _synthesize(cfg,emit):
    validate(cfg)
    from track_control import check
    from audio_fallback import healthy
    from tts_health import problems
    if one_pass(cfg):
        from fast_mode import basic_problems as problems
    from speech_level import condition
    import soundfile as sf
    check(cfg)
    if selection(cfg)=='drama3-small-iq3':
        from drama_gguf import native_backend
        message='Loading Drama3-small · '+('NVIDIA CUDA' if native_backend(cfg['storage'],cfg)=='cuda' else 'CPU')+' · experimental'
    else:message='載入 Drama 3；Windows 原生 CPU 生成。' if sys.platform=='win32' else '載入 Drama 3；Apple Silicon 本機生成。'
    emit('配音',message,workID='tts',workCompleted=0,workTotal=len(cfg['items']))
    with contextlib.redirect_stdout(sys.stderr):model=load(cfg)
    failures=[]
    for i,item in enumerate(cfg['items']):
        check(cfg);path=Path(item['output']);started=time.monotonic()
        failure_path=path.with_suffix('.failure.json')
        if not (path.is_file() and (path.stat().st_size>44 if one_pass(cfg) else healthy(path))):
            cfg.pop('_dramaLastGeneration',None)
            try:
                audio=generate_complete(model,item,cfg,emit)
                check(cfg);path.parent.mkdir(parents=True,exist_ok=True)
                sf.write(path.with_suffix('.raw.wav'),audio,RATE,subtype='FLOAT')
                errors=problems(audio,RATE,item['text'],item.get('targetSeconds'))
                if errors:raise ValueError(', '.join(errors))
                audio,level=condition(audio,RATE);temp=path.with_suffix('.partial.wav')
                sf.write(temp,audio,RATE,subtype='PCM_16');temp.replace(path)
                failure_path.unlink(missing_ok=True)
                path.with_suffix('.level.json').write_text(json.dumps(level))
            except (RuntimeError,ValueError,OSError) as error:
                from track_control import UserSkipped
                if isinstance(error,UserSkipped):raise
                position=item.get('reviewIndex');position=i if position is None else position
                failures.append(f'第 {position+1} 段：{error}')
                path.parent.mkdir(parents=True,exist_ok=True)
                if isinstance(error,GenerationLimit) and error.audio.size:
                    rejected=path.with_suffix('.rejected.raw.wav')
                    sf.write(rejected,error.audio,RATE,subtype='FLOAT')
                    cfg['_dramaLastGeneration']['rejectedAudio']=str(rejected)
                    cfg['_dramaLastGeneration']['generatedSeconds']=len(error.audio)/RATE
                failure_path.write_text(json.dumps(dict(index=position+1,error=str(error)),ensure_ascii=False))
                emit('配音需修正',failures[-1])
                if getattr(error,'abortVoiceTrack',False):raise
            finally:
                if cfg.get('_dramaLastGeneration'):
                    path.parent.mkdir(parents=True,exist_ok=True)
                    path.with_suffix('.generation.json').write_text(json.dumps(cfg['_dramaLastGeneration']))
        emit('配音',f'Drama 3 · 第 {i+1}/{len(cfg["items"])} 句',workID='tts',workCompleted=i+1,workTotal=len(cfg['items']),cueIndex=item.get('reviewIndex'),seconds=round(time.monotonic()-started,2))
    if failures:raise ValueError('Drama 3：'+'；'.join(failures)+'；完成錄音保留。')


if __name__=='__main__':
    try:
        if sys.argv[1]=='prepare':
            cfg=dict(storage=sys.argv[2],drama3Model=sys.argv[3],targetLanguage='yue')
            if selection(cfg)=='drama3-small-iq3':
                from drama_gguf import probe
                from dubbing_runner import emit
                probe(Path(sys.argv[2]),selection(cfg),emit)
            else:
                with contextlib.redirect_stdout(sys.stderr):load(cfg)
            print(json.dumps(dict(stage='部署配音',message='Drama 3 離線模型載入通過。'),ensure_ascii=False),flush=True)
        else:
            from dubbing_runner import emit
            synthesize(json.loads(Path(sys.argv[2]).read_text()),emit)
    except Exception as error:
        import traceback
        traceback.print_exc(file=sys.stderr)
        print(json.dumps(dict(stage='錯誤',message=str(error)),ensure_ascii=False),flush=True);sys.exit(1)
