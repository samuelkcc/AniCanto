"""Pinned runtime selection from original AniCanto metadata; no upstream code."""
import json,math,re
from pathlib import Path
POLICY=json.loads(Path(__file__).with_name('hardware-runtimes.json').read_text())

def nvidia(name='',capability=None,driver=None,preferred=None):
 name=re.sub(r'\s+',' ',name.upper()).strip()
 try:driver_major=int(str(driver).split('.')[0])
 except (TypeError,ValueError):driver_major=0
 profiles=[]
 for p in POLICY['nvidia']:
  if driver_major<p.get('minimumDriverMajor',0):continue
  fits=p['minimumCC']<=capability<=p['maximumCC'] if isinstance(capability,(int,float)) and math.isfinite(capability) else any(hint in name for hint in p['nameHints'])
  if fits:profiles.append(p)
 if preferred:profiles.sort(key=lambda p:p['torchIndex']!=preferred)
 return dict(profiles[0]) if profiles else dict(id='cpu',torchIndex='cpu',cuda=None,reason='GPU architecture is not covered by the pinned runtime profiles.')


def amd_supported(name):
 name=re.sub(r'\s+',' ',name.upper()).removesuffix(' GRAPHICS')
 return any(re.search(r'\b'+re.escape(model)+r'$',name) for model in POLICY['amd']['models'])
