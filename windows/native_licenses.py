"""Read installed distribution notices without importing any AI runtime."""
from email.parser import Parser
import hashlib
from pathlib import Path

def inventory(root):
    grouped={}
    for runtime in sorted((Path(root)/'runtimes').glob('*')):
        for info in sorted((runtime/'Lib/site-packages').glob('*.dist-info')):
            try:metadata=Parser().parsestr((info/'METADATA').read_text(encoding='utf-8',errors='replace'))
            except OSError:continue
            name=metadata.get('Name',info.stem);version=metadata.get('Version','')
            key=(name.lower().replace('_','-'),version)
            row=grouped.setdefault(key,dict(name=name,version=version,license=metadata.get('License-Expression') or metadata.get('License') or 'See distribution notices',runtimes=[],notices=[]))
            if len(row['license'])>100:row['license']='See distribution notices'
            if runtime.name not in row['runtimes']:row['runtimes'].append(runtime.name)
            candidates=[p for p in info.rglob('*') if p.is_file() and (p.name.upper().startswith(('LICENSE','LICENCE','COPYING','NOTICE','AUTHORS')) or 'licenses' in p.parts)]
            if name.lower().replace('_','-')=='pyopenjtalk-plus':
                candidates += list((info.parent/'pyopenjtalk/dictionary').glob('COPYING')) + list((info.parent/'pyopenjtalk/htsvoice').glob('LICENSE*'))
            for path in candidates:
                if not path.resolve().is_relative_to(Path(root).resolve()) or path.stat().st_size>5_000_000:continue
                raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
                if not any(n['sha256']==digest for n in row['notices']):row['notices'].append(dict(name=path.name,sha256=digest,text=raw.decode('utf-8',errors='replace')))
    for base in sorted((Path(root)/'tools').glob('drama-full-cuda*/notices')):
        row=dict(name='Complete Drama 3 CUDA installed runtime',version=base.parent.name,license='Apache-2.0; dependency-specific NVIDIA / Microsoft terms',runtimes=[base.parent.name],notices=[])
        for path in sorted(base.rglob('*')):
            if path.is_file() and path.suffix in ('.txt','.md') and path.stat().st_size<5_000_000 and path.resolve().is_relative_to(Path(root).resolve()):
                raw=path.read_bytes();row['notices'].append(dict(name=str(path.relative_to(base)),sha256=hashlib.sha256(raw).hexdigest(),text=raw.decode('utf-8',errors='replace')))
        grouped[(row['name'],row['version'])]=row
    return list(grouped.values())
