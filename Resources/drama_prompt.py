"""Preflight the exact pinned MLX splitter without loading a neural model."""
import importlib.util,json,re
from functools import lru_cache
from pathlib import Path
REVISION='drama-spoken-chunks-255'
@lru_cache(maxsize=1)
def splitter():
 path=Path(__file__).parent/'tts-vendor/drama3/mlx_audio/tts/models/fish_drama3/chunking.py'
 spec=importlib.util.spec_from_file_location('_anicanto_drama_chunks',path)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 return module

def spoken(text):
 # Preserve the words inside paired tags. Bracketed cues are delivery controls.
 value=re.sub(r'\[[^\[\]]*\]','',text)
 value=re.sub(r'<[^>]+>','',value)
 return any(ch.isalnum() for ch in value)

def plan(text,hint=''):
 m=splitter();prefix='['+hint+'] ' if hint else ''
 limit=m.CHUNK_BYTES-len(prefix.encode('utf-8'))
 if limit<32:raise ValueError('Drama3 delivery instruction leaves no safe space for dialogue.')
 bodies=m.split_text(text,limit=limit)
 if not bodies:raise ValueError('Drama3 needs spoken target dialogue.')
 result=[]
 for body in bodies:
  prompt=prefix+body;actual=m.split_text(prompt)
  if not spoken(body) or any(not spoken(chunk) for chunk in actual):
   raise ValueError('Drama3 instruction-only synthesis chunk was blocked before inference.')
  if len(actual)!=1 or len(prompt.encode('utf-8'))>m.CHUNK_BYTES:
   raise ValueError('Drama3 prompt exceeds the verified spoken-chunk boundary.')
  result.append(dict(text=body,prompt=prompt))
 return result

def defects(trace):
 if not isinstance(trace,dict) or trace.get('backend')!='mlx':return []
 result=[]
 for part in trace.get('parts',[]):
  prompts=part.get('synthesisChunks') or [part.get('promptedText','')]
  for prompt in prompts:
   for chunk in splitter().split_text(prompt):
    if chunk.strip() and not spoken(chunk):result.append(dict(kind='generation-input',chunk=chunk,qualityCertified=False))
 return result

def file_defects(path):
 try:return defects(json.loads(Path(path).read_text()))
 except (OSError,ValueError,TypeError):return []
