"""Independent local transcription for one narrowly identified ASR spelling gap."""
from whisper_audio import load as whisper_pcm
import hashlib,json,subprocess,sys
from pathlib import Path

REVISION='whisper-no-prompt-1'

def transcribe(w,cfg,folder,audio,auto_language=False):
    return transcribe_batch(w,cfg,[(folder,audio)],auto_language)[0]


def transcribe_batch(w,cfg,items,auto_language=False):
    """One model load for all uncached independent witnesses in this pass."""
    from model_catalog import resolve
    from runtime_paths import python_for
    model=cfg.get('referenceSpeechModel') or 'whisper-large-v3'
    path=resolve(cfg['storage'],model)
    if not Path(path).is_dir():return [None]*len(items)
    results=[None]*len(items);pending=[]
    for index,(folder,audio) in enumerate(items):
        key=hashlib.sha256(Path(audio).read_bytes()+str(path).encode()+REVISION.encode()+str(auto_language).encode()).hexdigest()
        cache=Path(folder)/'secondary-speech.json'
        try:saved=json.loads(cache.read_text())
        except (OSError,ValueError):saved={}
        if saved.get('key')==key:results[index]=saved
        else:pending.append(dict(index=index,key=key,audio=str(audio),cache=str(cache)))
    if not pending:return results
    request=Path(items[0][0])/'secondary-speech-request.json'
    w.atomic_json(request,dict(items=[dict(audio=r['audio']) for r in pending],model=str(path),language=None if auto_language else 'zh'))
    from execution_timing import measure
    with measure(request.parent,'independent-asr-batch',items=len(pending),model=str(path),modelProcesses=1):
        response=json.loads(w.run([python_for(cfg['storage'],'runtime'),Path(__file__).resolve(),request]))
    if len(response)!=len(pending):raise ValueError('Independent speech batch is incomplete; original recordings retained.')
    for row,result in zip(pending,response):
        if cfg.get('executable'):
            result['heard']=subprocess.check_output([cfg['executable'],'--traditional-text'],input=result['heard'].encode()).decode()
        result.update(key=row['key'],method=REVISION,languageMode='automatic' if auto_language else 'zh',conditioning='No expected text, prompt or vocabulary supplied')
        w.atomic_json(row['cache'],result);results[row['index']]=result
    return results

if __name__=='__main__':
    import os,contextlib
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    from faster_whisper import WhisperModel
    request=json.loads(Path(sys.argv[1]).read_text())
    with contextlib.redirect_stdout(sys.stderr):
        model=WhisperModel(request['model'],device='cpu',compute_type='int8',local_files_only=True,cpu_threads=8)
        results=[]
        for item in request.get('items',[request]):
            segments,info=model.transcribe(whisper_pcm(item['audio']),language=request.get('language','zh'),beam_size=5,vad_filter=False,condition_on_previous_text=False)
            results.append(dict(heard=''.join(s.text for s in segments),language=info.language))
    print(json.dumps(results if 'items' in request else results[0],ensure_ascii=False))
