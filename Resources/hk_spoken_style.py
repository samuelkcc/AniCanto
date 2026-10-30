"""Shared contextual Cantonese examples for the first draft, not a retry loop."""
import json,re
from pathlib import Path
from functools import lru_cache
REVISION='hong-kong-contextual-260'
@lru_cache(maxsize=1)
def rules():return json.loads(Path(__file__).with_name('hk-spoken-style.json').read_text())
def enabled(cfg):return cfg.get('hongKongStyleRevision')==REVISION
def instruction(cfg,language='yue'):
 if language!='yue' or not enabled(cfg):return ''
 return ' HONG KONG CONTEXTUAL WORDING: '+json.dumps(rules(),ensure_ascii=False,separators=(',',':'))
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
