"""Shared contextual Cantonese examples for the first draft, not a retry loop."""
import json,re
from pathlib import Path
from functools import lru_cache
LEGACY_REVISION='hong-kong-contextual-260'
EXPANDED_REVISION='hong-kong-contextual-377'
SOURCE_REVISION='hong-kong-contextual-415'
REVISION='hong-kong-contextual-425'
@lru_cache(maxsize=1)
def rules():return json.loads(Path(__file__).with_name('hk-spoken-style.json').read_text())
def enabled(cfg):return cfg.get('hongKongStyleRevision') in (REVISION,SOURCE_REVISION,EXPANDED_REVISION,LEGACY_REVISION)
def instruction(cfg,language='yue'):
 if language!='yue' or not enabled(cfg):return ''
 return ' HONG KONG CONTEXTUAL WORDING: '+json.dumps(rules(),ensure_ascii=False,separators=(',',':'))+(' Each row may include spokenStyleExamples. Use only that row’s matched examples for Cantonese grammar, never their names or facts. Preserve every clause, relationship, negation, condition and question. Do not perform word substitution or add particles mechanically.' if cfg.get('hongKongStyleRevision') in (REVISION,SOURCE_REVISION,EXPANDED_REVISION) else '')
def normalize(cfg,text):
 if not enabled(cfg):return text
 # Only complete, unambiguous fixed speech phrases. Ambiguous 搞不好 is
 # resolved by the existing first-draft model, never by a global replacement.
 spans=[m.span() for m in re.finditer(r'「[^」]*」|『[^』]*』|“[^”]*”|"[^"]*"',text)]
 for term in cfg.get('termRules',[]):
  for field in ('source','yue'):
   name=term.get(field,'')
   if name:spans.extend(m.span() for m in re.finditer(re.escape(name),text))
 replacements=[]
 for source,target in rules()['safePhraseRewrites'].items():
  for match in re.finditer(re.escape(source),text):
   if not any(match.start()<b and match.end()>a for a,b in spans):replacements.append((match.start(),match.end(),target))
 for a,b,target in sorted(replacements,reverse=True):text=text[:a]+target+text[b:]
 return text


@lru_cache(maxsize=2)
def style_memory(revision=EXPANDED_REVISION):
 name='hk-spoken-source-425.json' if revision==REVISION else 'hk-spoken-source-415.json' if revision==SOURCE_REVISION else 'hk-spoken-retrieval-377.json'
 return json.loads(Path(__file__).with_name(name).read_text())

@lru_cache(maxsize=1)
def traditional_lookup():
 try:
  from opencc import OpenCC
  return OpenCC('s2t')
 except ImportError:return None

def retrieve(cfg,source,language='yue',source_language=None):
 """Return at most three primary-source examples. Preserve frozen legacy selection."""
 revision=cfg.get('hongKongStyleRevision')
 if language!='yue' or revision not in (REVISION,SOURCE_REVISION,EXPANDED_REVISION):return []
 import unicodedata
 converter=traditional_lookup()
 def key(text):
  value=unicodedata.normalize('NFKC',text).lower()
  return converter.convert(value) if converter else value
 source=key(str(source));matched=[]
 for index,row in enumerate(style_memory(revision)['entries']):
  scores=[sum(len(key(term)) for term in group) for group in row['matchesAny'] if group and all(key(term) in source for term in group)]
  if revision in (REVISION,SOURCE_REVISION):
   for trigger in row.get('sourceTriggers',{}).get(source_language,[]):
    token=key(trigger)
    if (re.search(r'\b'+re.escape(token)+r'\b',source) if source_language=='en' else token in source):scores.append(len(token))
  if scores:matched.append((max(scores),index,row))
 matched.sort(key=lambda row:(-row[0],row[1]));selected=[];seen=set()
 for _,_,row in matched:
  identity=(key(row['written']),key(row['spoken']))
  if revision in (REVISION,SOURCE_REVISION) and identity in seen:continue
  seen.add(identity);selected.append(dict(id=row['id'],written=row['written'],spoken=row['spoken'],usage=row.get('usage','')))
  if len(selected)==3:break
 return selected
