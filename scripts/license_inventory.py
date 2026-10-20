"""Inventory the exact bundle's distribution metadata and on-disk notices."""
import json,email,hashlib
from pathlib import Path

def generate(resources):
    resources=Path(resources);records=[]
    if (resources/'core-dependencies.json').is_file():
        records.extend(json.loads((resources/'core-dependencies.json').read_text()))
    for runtime in sorted((resources/'runtimes').glob('*')):
        for dist in sorted(runtime.glob('lib/python*/site-packages/*.dist-info')):
            meta=dist/'METADATA'
            if not meta.exists():continue
            info=email.message_from_string(meta.read_text(errors='replace'))
            license=info.get('License-Expression') or info.get('License') or ''
            if not license or len(license)>100:
                license='; '.join(x.split(' :: ')[-1] for x in info.get_all('Classifier',[]) if x.startswith('License ::')) or 'See bundled notice / 未標示 SPDX'
            files=[str(p.relative_to(resources)) for p in dist.rglob('*') if p.is_file() and (any(x in p.name.lower() for x in ['license','licence','copying','notice','copyright']) or 'licenses' in p.parts) and p.stat().st_size<5000000]
            records.append(dict(name=info.get('Name',dist.name),version=info.get('Version',''),license=license,origin=runtime.name,files=files))
    for folder in sorted((resources/'Licenses').iterdir()):
        if not folder.is_dir() or folder.name=="anicanto-core":continue
        files=[str(p.relative_to(resources)) for p in folder.rglob('*') if p.is_file() and p.stat().st_size<5000000]
        records.append(dict(name=folder.name,version='Bundled native component',license='See bundled licence / 詳見內附授權',origin='Native libraries and fonts',files=files))
    vendor=resources/'tts-vendor'
    if vendor.exists():
        provenance=json.loads((vendor/'provenance.json').read_text())
        for title,folder in [('VoxCPM2','voxcpm2'),('WenetSpeech-Yue','wsyue')]:
            files=[str(p.relative_to(resources)) for p in (vendor/folder).glob('LICENSE*')]
            records.append(dict(name=title,version=provenance[title]['revision'],license='Apache-2.0; Matcha MIT (see notices)',origin=provenance[title]['repo'],files=files))
        if (vendor/'drama3/SOURCE.json').is_file():
            drama=json.loads((vendor/'drama3/SOURCE.json').read_text())
            records.append(dict(name='Fish Drama 3 MLX adapter',version=drama['revision'],license='MIT',origin=drama['repo'],files=['tts-vendor/drama3/LICENSE','tts-vendor/drama3/SOURCE.json']))
        if (vendor/'drama3-small/SOURCE.json').is_file():
            records.append(dict(name='Drama3-small native adapter',version='9277495a + pinned small-model patch',license='Apache-2.0; Fish Audio Community License',origin='https://huggingface.co/pentacoxian-dev/drama3-small-GGUF',files=['tts-vendor/drama3-small/audio.cpp-LICENSE','tts-vendor/drama3-small/LICENSE','tts-vendor/drama3-small/NOTICE','tts-vendor/drama3-small/SOURCE.json']))
    # One component/version/licence row across runtimes. Preserve every origin
    # and distinct notice; identical bytes may share a displayed document.
    grouped={}
    for row in records:
        key=(row['name'].lower(),row['version'],row['license'])
        merged=grouped.setdefault(key,dict(row,origins=[],files=[],noticeSources={}))
        if row['origin'] not in merged['origins']:merged['origins'].append(row['origin'])
        for name in row['files']:
            file=resources/name
            if not file.is_file():continue
            digest=hashlib.sha256(file.read_bytes()).hexdigest()
            primary=next((p for p in merged['files'] if hashlib.sha256((resources/p).read_bytes()).hexdigest()==digest),None)
            if primary is None:merged['files'].append(name);primary=name
            merged['noticeSources'].setdefault(primary,[]).append(name)
    records=list(grouped.values())
    for row in records:
        row['origin']=' · '.join(row['origins'])
    records.sort(key=lambda r:(r['name'].lower(),r['version'],r['origin']))
    (resources/'license-inventory.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
    return records
if __name__=='__main__':
    import sys
    print(len(generate(sys.argv[1])))
