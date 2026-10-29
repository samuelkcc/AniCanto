"""Match a glossary name against the selected primary text in any stored language.

This checks written evidence. It does not select or splice original name audio.
"""
import re,unicodedata
FIELDS=('source','japanese','cantonese','mandarin','chinese','english')
def normalize(text):return re.sub(r'\s+','',unicodedata.normalize('NFKC',str(text))).casefold()
def aliases(term):
 values=[term.get(k) for k in FIELDS]
 extra=term.get('aliases',[])
 if isinstance(extra,dict):extra=list(extra.values())
 if isinstance(extra,(list,tuple)):
  for value in extra:values.extend(value if isinstance(value,list) else [value])
 return [normalize(v) for v in values if isinstance(v,str) and v.strip()]
def grounded(term,text):
 raw=unicodedata.normalize('NFKC',str(text)).casefold();compact=normalize(raw)
 for alias in aliases(term):
  if alias.isascii() and any(c.isalpha() for c in alias):
   pattern=r'(?<![a-z0-9])'+r'\s*'.join(re.escape(c) for c in alias)+r'(?![a-z0-9])'
   if re.search(pattern,raw):return True
  elif alias in compact:return True
 return False
