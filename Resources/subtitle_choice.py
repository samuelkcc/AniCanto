"""Select authored captions by output language, or request an explicit user choice."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import subtitle_preference as preference
from source_modes import choice

AUTO_REVISION='automatic-caption-language-20261103'


def embedded_language(video, tools, stream):
    """Inspect bounded subtitle text without invoking a model or changing the source."""
    if not tools.get('ffmpeg'):return 'und'
    suffix='.ass' if stream.get('codec_name') in ('ass','ssa') else '.srt'
    with tempfile.TemporaryDirectory(prefix='anicanto-subtitle-language-') as scratch:
        output=Path(scratch)/('sample'+suffix)
        command=[str(tools['ffmpeg']),'-v','error','-nostdin','-i',str(video),
                 '-map','0:'+str(stream['index']),'-t','600','-fs','65536',
                 '-c:s','ass' if suffix=='.ass' else 'srt','-y',str(output)]
        try:
            subprocess.run(command,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=8,check=True)
            with output.open('rb') as handle:raw=handle.read(65536)
        except (OSError,subprocess.SubprocessError):return 'und'
    text=__import__('subtitle_versions').decode(raw)
    if suffix=='.ass':
        if 'zh' in __import__('subtitle_versions').languages(text):return 'zh'
        text='\n'.join(line.split(',',9)[-1] for line in text.splitlines() if line.lower().startswith('dialogue:'))
    return text_language(text)


def language(stream):
    family=preference.target_family(stream)
    if family in ('cantonese','traditional','simplified','chinese'):return 'zh'
    if family=='english':return 'en'
    tag=preference.canonical((stream.get('tags') or {}).get('language'))
    return {'jpn':'ja','ja':'ja','kor':'ko','ko':'ko'}.get(tag,'und')


def text_language(text):
    text=re.sub(r'<[^>]*>|\{[^}]*\}','',text)
    if re.search(r'[ぁ-ゖァ-ヺ]',text):return 'ja'
    if len(re.findall(r'[\u3400-\u9fff]',text))>=4:return 'zh'
    words=re.findall(r'[A-Za-z]+',text.lower())
    if len(words)>=8 and len(set(words)&{'the','a','an','you','your','i','we','is','are','not','have','this','that','with'})>=3:return 'en'
    return 'und'


def preflight(video, tools, settings, row, selected=None, selected_language=None):
    mode='auto' if settings.get('interfaceMode')=='basic' else choice(settings.get('sourceWorkflow','auto'))
    if mode=='speech-ocr':
        return dict(kind='subtitle',needsConfirmation=False,ignored=mode=='speech-ocr',options=[])
    video=Path(video);stat=video.stat()
    metadata=json.loads(subprocess.check_output([str(tools['ffprobe']),'-v','error','-show_streams','-of','json',str(video)],timeout=30))
    options=[];streams={};automatic=settings.get('autoApproveSourceLanguage') is True
    for stream in metadata.get('streams',[]):
        if preference.is_text_stream(stream):
            tags=stream.get('tags') or {}
            options.append(dict(key='embedded:'+str(stream['index']),stream=stream['index'],language=language(stream),title=tags.get('title') or tags.get('language') or 'Subtitle track '+str(stream['index']),family=preference.target_family(stream)))
            streams[stream['index']]=stream
    external=[]
    if row.get('externalSubtitle'):external=[Path(row['externalSubtitle'])]
    elif row.get('conversionSubtitleChoice','auto')=='auto':
        for suffix in preference.SUBTITLE_SUFFIXES:
            external.extend(p for p in video.parent.glob(video.stem+'*'+suffix) if p.stem==video.stem or p.stem.startswith(video.stem+'.'))
    for path in sorted(set(external)):
        if not path.is_file():raise ValueError('The imported subtitle file is missing.')
        if path.stat().st_size>16*1024*1024:raise ValueError('Subtitle file exceeds the supported size.')
        raw=path.read_bytes();text=__import__('subtitle_versions').decode(raw)
        if path.suffix.lower() in ('.ass','.ssa'):
            text='\n'.join(line.split(',',9)[-1] for line in text.splitlines() if line.lower().startswith('dialogue:'))
        else:text=re.sub(r'\d+:\d+:\d+[^\n]*|^\d+$','',text,flags=re.M)
        lang=text_language(text)
        editions=__import__('subtitle_versions').languages(__import__('subtitle_versions').decode(raw)) if path.suffix.lower() in ('.ass','.ssa') else []
        for edition in editions if len(editions)>1 else [lang]:
            options.append(dict(key='external:'+str(path)+('#lang:'+edition if len(editions)>1 else ''),path=str(path),language=edition,title=path.name+(' · '+edition if len(editions)>1 else ''),family='chinese' if edition=='zh' else 'english' if edition=='en' else 'unlabeled',sha256=hashlib.sha256(raw).hexdigest()))
    target=(settings.get('dubLanguages') or ['yue'])[0]
    identity=dict(video=str(video),size=stat.st_size,mtime=stat.st_mtime_ns,target=target,mode=mode)
    binding=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    saved=row.get('subtitleSelection') or {}
    explicit=row.get('conversionSubtitleChoice','auto')
    picked=next((x for x in options if x['key']==selected),None)
    confirmed=False
    if selected is not None:
        if picked is None or selected_language not in ('zh','en','ja','ko','other'):raise ValueError('Choose an available subtitle source and its language.')
        picked=dict(picked,language=selected_language);confirmed=True
    elif saved.get('binding')==binding:
        picked=next((dict(x,language=saved['language']) for x in options if x['key']==saved.get('key') and x.get('sha256')==saved.get('sourceSHA256')),None);confirmed=picked is not None
    elif explicit.startswith('embedded:'):
        picked=next((x for x in options if x['key']==explicit),None)
        if picked is None:raise ValueError('The selected subtitle track is missing.')
    if automatic and not confirmed:
        # Metadata leads. Read unknown text tracks only when the preferred language
        # is still missing. Stop after three samples to bound queue preparation.
        desired=['en','zh'] if target=='en' else ['zh']
        inspected=0
        for desired_language in desired:
            if any(x['language']==desired_language for x in options):break
            for option in options:
                if option['language']!='und' or 'stream' not in option or option.get('languageMethod'):continue
                if inspected>=3:break
                inspected+=1
                option['language']=embedded_language(video,tools,streams[option['stream']])
                option['languageMethod']='bounded-subtitle-text'
                if option['language']=='zh':option['family']='chinese'
                elif option['language']=='en':option['family']='english'
            if any(x['language']==desired_language for x in options):break
        if picked is not None:
            picked=next(x for x in options if x['key']==picked['key'])
    if picked is None:
        languages=['en','zh'] if target=='en' else ['zh']
        for desired in languages:
            pool=[x for x in options if x['language']==desired]
            if pool:
                picked=min(pool,key=lambda x:(0 if x.get('path')==row.get('externalSubtitle') else 1,preference.TARGET_ORDERS.get(target,()).index(x['family']) if x['family'] in preference.TARGET_ORDERS.get(target,()) else 9,x['key']));break
    desired={'en','zh'} if target=='en' else {'zh'}
    needs=not automatic and bool(options) and not confirmed and (picked is None or picked['language'] not in desired)
    result=dict(kind='subtitle',needsConfirmation=needs,options=options,targetLanguage=target,binding=binding,selected=picked,confirmed=confirmed,supported=True)
    if automatic:
        result['automaticSelection']=dict(revision=AUTO_REVISION,binding=binding,
            speechOnly=picked is None,selectedKey=picked['key'] if picked else None,
            reason='selected-authored-subtitles' if picked else 'no-reliable-target-subtitles')
    result['token']=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()
    return result


def apply_to_row(row, result):
    picked=result.get('selected')
    if result.get('needsConfirmation'):raise ValueError('Confirm the subtitle language before conversion.')
    if result.get('automaticSelection'):row['automaticSubtitleSelection']=result['automaticSelection']
    else:row.pop('automaticSubtitleSelection',None)
    if not picked:return
    row['subtitleSelection']=dict(binding=result['binding'],key=picked['key'],language=picked['language'],confirmed=result['confirmed'],sourceSHA256=picked.get('sha256'))
    row['conversionSubtitleChoice']=picked['key'] if 'stream' in picked else 'auto'
    if picked.get('path'):row['externalSubtitle']=picked['path']
    else:row.pop('externalSubtitle',None)
