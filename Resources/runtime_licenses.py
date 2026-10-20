"""Inventory external Mac runtime notices without importing model packages."""
from email.parser import Parser
import hashlib,json
from pathlib import Path

def update(root):
    root=Path(root);grouped={}
    for runtime in root.glob('*runtime'):
        if not runtime.is_dir():continue
        for info in runtime.glob('lib/python*/site-packages/*.dist-info'):
            try:meta=Parser().parsestr((info/'METADATA').read_text(encoding='utf-8'))
            except OSError:continue
            name=meta.get('Name',info.stem);version=meta.get('Version','');license=meta.get('License-Expression') or meta.get('License') or 'See distribution notice'
            if len(license)>100:license='See distribution notice'
            row=grouped.setdefault((name.lower(),version,license),dict(name=name,version=version,license=license,origin='Application Support',origins=[],files=[],fileRoot='applicationSupport',noticeSources={}))
            row['origins'].append(runtime.name);hashes={}
            for old in row['files']:hashes[hashlib.sha256((root/old).read_bytes()).hexdigest()]=old
            candidates=list(info.rglob('*'))
            if name.lower().replace('_','-')=='pyopenjtalk-plus':
                candidates += list((info.parent/'pyopenjtalk/dictionary').glob('COPYING')) + list((info.parent/'pyopenjtalk/htsvoice').glob('LICENSE*'))
            for path in candidates:
                if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()) or not path.is_file() or path.stat().st_size>5_000_000:continue
                if not (any(word in path.name.lower() for word in ('license','licence','copying','notice','copyright')) or 'licenses' in path.parts):continue
                digest=hashlib.sha256(path.read_bytes()).hexdigest();relative=str(path.relative_to(root));primary=hashes.get(digest)
                if primary is None:primary=relative;row['files'].append(primary);hashes[digest]=primary
                row['noticeSources'].setdefault(primary,[]).append(relative)
    rows=sorted(grouped.values(),key=lambda r:(r['name'].lower(),r['version']))
    for row in rows:row['origin']=' · '.join(row['origins'])
    path=root/'runtime-license-inventory.json';temp=path.with_suffix('.tmp');temp.write_text(json.dumps(rows,ensure_ascii=False,indent=2));temp.replace(path)
    return rows
