"""User-controlled spoken aliases, without rewriting the displayed script."""
import re

def rules(cfg):
    result={}
    for line in cfg.get('pronunciationText','').splitlines():
        if not line.strip():continue
        if '=' not in line:raise ValueError('讀音字典請每行輸入「原字 = 讀法」。')
        source,target=(s.strip() for s in line.split('=',1))
        if not source or not target or len(source)>100 or len(target)>100:raise ValueError('讀音字典原字／讀法不能留空或超過 100 字。')
        result[source]=target
    return result

def spoken(cfg, text):
    entries=rules(cfg)
    if not entries:return text
    # One pass, longest match first. Replacement text is never replaced again.
    patterns=[];lookup={}
    for index,(source,target) in enumerate(sorted(entries.items(),key=lambda x:-len(x[0]))):
        name='p'+str(index);lookup[name]=target
        left=r'(?<![A-Za-z0-9])' if source[0].isascii() and source[0].isalnum() else ''
        right=r'(?![A-Za-z0-9])' if source[-1].isascii() and source[-1].isalnum() else ''
        patterns.append(f'(?P<{name}>{left}{re.escape(source)}{right})')
    return re.sub('|'.join(patterns),lambda m:lookup[m.lastgroup],text,flags=re.IGNORECASE)
