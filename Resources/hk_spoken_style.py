"""Shared contextual Cantonese examples for the first draft, not a retry loop."""
import json,re
from pathlib import Path
from functools import lru_cache
LEGACY_REVISION='hong-kong-contextual-260'
REVISION='hong-kong-contextual-377'
@lru_cache(maxsize=1)
def rules():return json.loads(Path(__file__).with_name('hk-spoken-style.json').read_text())
def enabled(cfg):return cfg.get('hongKongStyleRevision') in (REVISION,LEGACY_REVISION)
def instruction(cfg,language='yue'):
 if language!='yue' or not enabled(cfg):return ''
 return ' HONG KONG CONTEXTUAL WORDING: '+json.dumps(rules(),ensure_ascii=False,separators=(',',':'))+(' Each row may include spokenStyleExamples. Use only that row’s matched examples for Cantonese grammar, never their names or facts. Preserve every clause, relationship, negation, condition and question. Do not perform word substitution or add particles mechanically.' if cfg.get('hongKongStyleRevision')==REVISION else '')
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


@lru_cache(maxsize=1)
def style_memory():
 return json.loads(Path(__file__).with_name('hk-spoken-retrieval-377.json').read_text())

@lru_cache(maxsize=1)
def traditional_lookup():
 try:
  from opencc import OpenCC
  return OpenCC('s2t')
 except ImportError:return None

def retrieve(cfg,source,language='yue'):
 """Return at most three matching first-party examples. Source text stays unchanged."""
 if language!='yue' or cfg.get('hongKongStyleRevision')!=REVISION:return []
 import unicodedata
 converter=traditional_lookup()
 def key(text):
  value=unicodedata.normalize('NFKC',text).lower()
  return converter.convert(value) if converter else value
 source=key(str(source));matched=[]
 for index,row in enumerate(style_memory()['entries']):
  scores=[sum(len(key(term)) for term in group) for group in row['matchesAny'] if group and all(key(term) in source for term in group)]
  if scores:matched.append((max(scores),index,row))
 matched.sort(key=lambda row:(-row[0],row[1]))
 return [dict(id=row['id'],written=row['written'],spoken=row['spoken'],usage=row.get('usage','')) for _,_,row in matched[:3]]
