"""Original/own-language references by default; explicit optional CosyVoice bridge.

An advanced bridge supplies a separately validated target-language reference only
when selected. Final speech still comes from the selected engine.
"""
import hashlib,json,wave
from pathlib import Path

TEXT='我哋一齊慢慢講清楚呢件事，唔好咁心急。'

def prepare(cfg,job,profile,emit,allow_english=False):
    engine=cfg.get('ttsBackend','qwen-tts')
    target=cfg.get('targetLanguage','yue')
    label='GPT-SoVITS' if engine.startswith('gpt-sovits') else 'Qwen'
    mode=cfg.get('gsvReferenceMode','original') if engine.startswith('gpt-sovits') else cfg.get('qwenReferenceMode','original')
    if target not in ('yue','en') or (not engine.startswith('gpt-sovits') and target!='yue' and not allow_english) or profile.get('language')==target or mode=='original':return profile
    text=TEXT if target=='yue' else "Let's take our time and work this out together. There's no need to rush."
    language='廣東話' if target=='yue' else '英文'
    from dubbing import model_job
    from speechcheck import inspect
    from worker import atomic_json
    root=Path(cfg['storage'])
    if not (root/'cosy-ready.json').exists() or not (root/'asr-ready.json').exists():
        raise ValueError(f'{label} 跨語言參考需要已部署 CosyVoice 3 同覆聽模型；亦可為角色匯入{language}參考，或在模型頁選擇只用原聲。')
    identity=dict(source=profile,sourceSHA=hashlib.sha256(Path(profile['reference']).read_bytes()).hexdigest(),cosyModel=cfg.get('cosyModel','cosy-0.5b-4bit'),text=text,asrModel=cfg.get('asrModel','asr-1.7b-bf16'),revision=1)
    key=hashlib.sha256(json.dumps(identity,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:24]
    folder=root/'qwen-references'/key;folder.mkdir(parents=True,exist_ok=True)
    manifest=folder/'reference.json'
    if manifest.exists():
        saved=json.loads(manifest.read_text());audio=Path(saved['reference'])
        if audio.is_file() and hashlib.sha256(audio.read_bytes()).hexdigest()==saved.get('audioSHA'):
            return dict(profile,reference=str(audio),promptText=text,language=target,referenceProvenance=str(manifest))
    emit(label+' '+language+'參考',f'{profile["name"]}：先用 CosyVoice 建立{language}參考並覆聽；正式台詞仍由 {label} 生成。')
    attempts=[]
    for seed in (42,73):
        audio=folder/f'reference-{seed}.wav'
        model_job(cfg,'cosy',dict(storage=cfg['storage'],job=str(folder),targetLanguage=target,cosyModel=cfg.get('cosyModel'),items=[dict(profile=profile,text=text,output=str(audio),seed=seed)]),emit)
        with wave.open(str(audio)) as f:seconds=f.getnframes()/f.getframerate()
        check=inspect(dict(cfg,targetLanguage=target),folder,[dict(cantonese=text)],[audio],emit)[0]
        attempts.append(dict(seed=seed,seconds=seconds,check=check))
        atomic_json(folder/'attempts.json',attempts)
        if 3<=seconds<=10.1 and not check['requiresReview']:
            saved=dict(identity,reference=str(audio),audioSHA=hashlib.sha256(audio.read_bytes()).hexdigest(),check=check,method='Validated CosyVoice-derived target-language reference; used only for conditioning; identity requires audition')
            atomic_json(manifest,saved)
            return dict(profile,reference=str(audio),promptText=text,language=target,referenceProvenance=str(manifest))
    raise ValueError(f'{profile["name"]} {language}參考未通過長度／內容／語言覆聽；請在角色頁匯入乾淨{language}參考。詳見 {folder}/attempts.json')
