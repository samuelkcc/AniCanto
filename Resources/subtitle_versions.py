"""Keep one authored language edition and its display clocks in multilingual ASS files."""
import re



def decode(raw):
    if raw.startswith((b'\xff\xfe',b'\xfe\xff')):return raw.decode('utf-16')
    return raw.decode('utf-8-sig')


def detected(text):
    text=re.sub(r'\{[^}]*\}|<[^>]*>','',text)
    if re.search(r'[ぁ-ゖァ-ヺ]',text):return 'ja'
    if re.search(r'[\u3400-\u9fff]',text):return 'zh'
    words=set(re.findall(r'[a-z]+',text.lower()))
    if len(words & {'the','a','i','you','we','is','are','not','this','that','my','your'})>=2:return 'en'
    return 'und'


def ass_rows(raw):
    rows=[];fields=['layer','start','end','style','name','marginl','marginr','marginv','effect','text']
    events=False
    def stamp(value):
        h,m,s=value.strip().split(':');return int(h)*3600+int(m)*60+float(s)
    for line in raw.splitlines():
        if line.startswith('['):events=line.strip().lower()=='[events]'
        if not events:continue
        if line.lower().startswith('format:'):fields=[x.strip().lower() for x in line.split(':',1)[1].split(',')]
        if not line.lower().startswith('dialogue:'):continue
        values=line.split(':',1)[1].lstrip().split(',',len(fields)-1)
        if len(values)!=len(fields):continue
        row=dict(zip(fields,values));text=re.sub(r'\{[^}]*\}','',row.get('text','')).replace('\\N','\n').replace('\\n','\n').strip()
        if not text:continue
        style=row.get('style','').lower();tokens=set(re.split(r'[^a-z]+',style))
        lang='zh' if tokens&{'zh','chs','cht','cn','tc','sc','chinese'} or any(x in style for x in ['繁體','简体','簡體','中文']) else 'ja' if tokens&{'jp','ja','jpn','japanese'} or '日文' in style else 'en' if tokens&{'en','eng','english'} or '英文' in style else detected(text)
        start,end=stamp(row['start']),stamp(row['end'])
        if end>start>=0:rows.append(dict(start=start,end=end,text=text,language=lang))
    return rows


def languages(raw):
    return sorted({x['language'] for x in ass_rows(raw)}-{'und'})


def selected_srt(raw, language):
    rows=ass_rows(raw);known={r['language'] for r in rows}-{'und'}
    if len(known)<2:return None
    chosen=[r for r in rows if r['language']==language or r['language']=='und' and not any(other['language']!='und' and min(r['end'],other['end'])>max(r['start'],other['start']) for other in rows)]
    if not chosen:raise ValueError('The selected authored subtitle language is unavailable.')
    def stamp(value):
        ms=round(value*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
        return f'{h:02}:{m:02}:{s:02},{ms:03}'
    return '\n\n'.join(f"{i+1}\n{stamp(r['start'])} --> {stamp(r['end'])}\n{r['text']}" for i,r in enumerate(chosen))+'\n'
