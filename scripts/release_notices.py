"""Install the reviewed evidence, without model weights or private audit files."""
import json,shutil,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def install(resources):
    resources=Path(resources)
    application=resources/'Licenses';application.mkdir(parents=True,exist_ok=True)
    for legacy in ('CantoSync-GPL-3.0.txt','CantoSync-MIT.txt','AniCanto-GPL-3.0.txt'):
        (application/legacy).unlink(missing_ok=True)
    shutil.copy2(ROOT/'LICENSE',application/'AniCanto-MIT.txt')
    shutil.copy2(ROOT/'LICENSE',resources/'LICENSE')
    (resources/'fonts').mkdir(exist_ok=True)
    shutil.copy2(ROOT/'Resources/fonts/NOTICE.txt',resources/'fonts/NOTICE.txt')
    shutil.copy2(ROOT/'Resources/app-icon.svg',resources/'app-icon.svg')
    # Refresh only this generated evidence tree; macOS may treat Licenses and
    # licenses as the same directory, so preserve other native/application notices.
    shutil.rmtree(resources/'licenses/python-installer',ignore_errors=True)
    shutil.rmtree(resources/'licenses/models',ignore_errors=True)
    shutil.copytree(ROOT/'licenses',resources/'licenses',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.pyo'))
    # Exclude retired tool evidence from new artifacts; historical evidence stays in source.
    shutil.rmtree(resources/'licenses/tools/uv-dependencies',ignore_errors=True)
    for name in ('uv-MIT.txt','uv-APACHE.txt','uv-notice-supplements.json'):(resources/'licenses/tools'/name).unlink(missing_ok=True)
    shutil.rmtree(resources/'licenses/tools/uv',ignore_errors=True)
    shutil.rmtree(resources/'Licenses/uv',ignore_errors=True)
    for name in ('uv','uv-dependencies'):shutil.rmtree(resources/'Licenses/tools'/name,ignore_errors=True)
    (resources/'Licenses/tools/uv-notice-supplements.json').unlink(missing_ok=True)
    notices=resources/'THIRD-PARTY-NOTICES.txt'
    if notices.is_file():
        lines=[line for line in notices.read_text().splitlines() if not line.startswith('uv 0.') ]
        if not any(line.startswith('Private CPython and pip:') for line in lines):lines+=['Private CPython and pip: pinned upstream distributions; see licenses/python-installer.']
        notices.write_text('\n'.join(lines)+'\n')
    shutil.copy2(ROOT/'Resources/python-installer.json',resources/'python-installer.json')
    shutil.copy2(ROOT/'Resources/USE-TERMS.json',resources/'USE-TERMS.json')
    # A cloned prior release must not retain retired human samples/evidence.
    shutil.rmtree(resources/'natural-voices',ignore_errors=True)
    shutil.copytree(ROOT/'Resources/natural-voices',resources/'natural-voices')
    # Cloned prior app stages may still contain an unused noncommercial wheel.
    for pattern in ('diffq*.whl','distance-*.whl'):
        for path in (resources/'wheels').glob(pattern):path.unlink()
    shutil.copy2(ROOT/'NOTICE.txt',resources/'NOTICE.txt')
    shutil.copy2(ROOT/'Resources/MODEL-NOTICES.txt',resources/'MODEL-NOTICES.txt')
    return records(resources)

def records(resources):
    resources=Path(resources);rows=[]
    for record in json.loads((resources/'licenses/model-evidence.json').read_text())['models']:
        if record.get('status') in ('retired','blocked-missing-license'):continue
        rows.append(dict(name=record['repo']+' (optional model)',version=record['revision'],
            license=record['effectiveLicense'],origin='Pinned model declaration; '+record['status'],
            files=[doc['path'] for doc in record['documents']]))
    for record in json.loads((resources/'licenses/python-wheels.json').read_text()):
        if record.get('bundled') is False:continue
        directory=resources/'licenses/python-wheels'/(record['name']+'-'+record['version'])
        rows.append(dict(name=record['name'],version=record['version'],license=record.get('license') or 'See supplied notice',origin='Bundled wheel',files=[str(p.relative_to(resources)) for p in directory.rglob('*') if p.is_file()]))
    installer=json.loads((resources/'python-installer.json').read_text())
    for platform,row in installer['platforms'].items():
        rows.append(dict(name='Private CPython ('+platform+')',version=row['version'],license='Python-2.0, CNRI-Python and component-specific notices',origin='Pinned standalone Python archive; downloaded on demand',files=[d['path'] for d in row['notices']]))
    row=installer['pip']
    rows.append(dict(name='pip and vendored dependencies',version=row['version'],license='MIT and component-specific notices',origin='Bundled verified installer wheel; standard pip',files=[d['path'] for d in row['notices']]))
    ffmpeg_notice=resources/'licenses/ffmpeg/notice-evidence.json'
    if ffmpeg_notice.is_file():
        evidence=json.loads(ffmpeg_notice.read_text())
        rows.append(dict(name='FFmpeg and dependency notices (Windows download)',version='n8.1.3-18-g46d899d7a0',license='GPL-3.0-or-later; dependency-specific terms preserved',origin='Exact downloaded native binary and pinned dependency sources',files=['licenses/ffmpeg/windows-GPL-3.0.txt','licenses/ffmpeg/REBUILDING.md','licenses/ffmpeg/notice-evidence.json']+[d['path'] for row in evidence['sources'] for d in row['documents']]))
    rows.append(dict(name='Reference recordings',version='3',license='CC0-1.0; generators Apache-2.0 and MIT',origin='Original synthetic English mixtures and Cantonese generation; no human reference clips',files=['natural-voices/NOTICE.txt','licenses/common/CC0-1.0.txt','licenses/common/Kokoro-Apache-2.0.txt','licenses/common/GPT-SoVITS-MIT.txt','natural-voices/catalog.json','natural-voices/cantonese-generation.json','natural-voices/english-generation.json']))
    rows.append(dict(name='AniCanto original brand icon',version='2026-10-18',license='MIT',origin='Original SCKC vector artwork',files=['licenses/BRANDING-NOTICE.txt']))
    rows.append(dict(name='Shared interface icon geometry',version='Feather 4.29.2; AniCanto adaptations',license='MIT',origin='Upstream geometry acknowledgement',files=['licenses/INTERFACE-NOTICE.txt','licenses/common/Feather-MIT.txt']))
    auxiliary=resources/'licenses/auxiliary-models.json'
    if auxiliary.is_file():
        for record in json.loads(auxiliary.read_text())['components']:
            rows.append(dict(name=record['repo']+' (auxiliary model evidence)',version=record['revision'],license=record['effectiveLicense'],origin=record['status'],files=['licenses/auxiliary-models.json']+[doc['path'] for doc in record['documents']]))
    ocr=resources/'licenses/ocr-models.json'
    if ocr.is_file():
        row=json.loads(ocr.read_text())
        rows.append(dict(name='RapidOCR model weights (Windows)',version=row['version'],license=row['license'],origin=row['status'],files=['licenses/ocr-models.json']+[d['path'] for d in row['documents']]))
    text_data=resources/'licenses/text-data.json'
    if text_data.is_file():
        for record in json.loads(text_data.read_text())['packages']:
            rows.append(dict(name='NLTK data: '+record['id'],version=record['revision'],license=record['license'],origin='Pinned data archive; terms retained separately from the NLTK code',files=['licenses/text-data.json']+[doc['path'] for doc in record['documents']]))
    dictionaries=resources/'licenses/text-data/pyopenjtalk-evidence.json'
    if dictionaries.is_file():
        for record in json.loads(dictionaries.read_text()):
            rows.append(dict(name='Open JTalk dictionary and bundled Mei voice ('+record['platform']+')',version=record['version'],license='BSD-3-Clause dictionary; CC-BY-3.0 Mei voice; MIT adapter',origin='Exact published wheel; voice is unused by AniCanto',files=['licenses/text-data/pyopenjtalk-evidence.json']+[doc['path'] for doc in record['documents']]))
    cuda=resources/'licenses/tools/drama-full-cuda'
    if cuda.is_dir():
        rows.append(dict(name='Complete Drama 3 NVIDIA CUDA runtime (optional Windows download)',version='v0.9.2-drama3-base-small',license='Apache-2.0, MIT, component notices; NVIDIA CUDA and Microsoft runtime terms',origin='Pinned binary archives and exact source evidence; downloaded on demand',files=[str(p.relative_to(resources)) for p in cuda.rglob('*') if p.is_file() and p.suffix!='.html']))
    return rows
