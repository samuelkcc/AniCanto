"""Public, deterministic expected-download inventory from the shipping manifests.

No user paths, credentials, live downloads or installed-file hashing. Inline
metadata is labelled separately from downloaded files. Never infer verification
of an installed file from a catalogue hash.
"""
import json
from pathlib import Path
from urllib.parse import quote,urlparse
ROOT=Path(__file__).resolve().parents[1]
def inventory(root=ROOT):
    rows=[]
    evidence={(r['repo'],r['revision']):r for r in json.loads((root/'licenses/model-evidence.json').read_text())['models']}
    def add(row,platform,origin,ident=None):
        if not row.get('files'):return
        repo=row.get('repo','');revision=row.get('revision','')
        files=[]
        for f in row['files']:
            inline='content' in f
            url=f.get('url') or (f'https://huggingface.co/{repo}/resolve/{revision}/{quote(f["path"],safe="/")}' if repo and revision and not repo.startswith('registry.ollama.ai/') and not inline else None)
            files.append(dict(path=f['path'],bytes=f.get('size'),sha256=f.get('sha') or f.get('sha256') or None,url=url,kind='generated' if inline else 'download'))
        record=evidence.get((repo,revision),{});base=record.get('baseModel') or []
        if isinstance(base,str):base=[base]
        publisher=repo.split('/')[0] if repo else urlparse(next((f['url'] for f in files if f['url']), '')).hostname or ''
        rows.append(dict(id=ident or row.get('id') or repo,title=row.get('title') or repo,platform=platform,origin=origin,repo=repo,revision=revision,publisher=publisher,baseModels=base,
            category=row.get('category') or 'support',engine=row.get('engine') or '',license=row.get('license') or '',availability='retired' if row.get('retired') else 'license-review' if row.get('licenseReviewRequired') else 'catalogue',files=files))
    for name,platform in [('Resources/model-options.json','Mac / Windows'),('windows/native-models.json','Windows')]:
        for row in json.loads((root/name).read_text()):
            actual='Mac' if name.startswith('Resources/') and (row.get('repo','').startswith('mlx-community/') or row.get('engine')=='mlx') else platform
            if row.get('engine')=='cosyvoice3' and name.startswith('windows/'):actual='Windows · NVIDIA'
            add(row,actual,name)
    # Supplementary tokenizers and compatibility manifests can carry files not
    # present in the selectable model list. Keep their exact pinned URL/hash.
    for name in ['Resources/asr-model.json','Resources/mlx-text-model.json','Resources/qwen-voice-model.json','Resources/cosy-models.json','windows/models.json']:
        if name=='Resources/cosy-models.json':continue  # Mac CosyVoice is not offered in this release.
        data=json.loads((root/name).read_text());parts={'model':data} if 'files' in data else data
        for key,row in parts.items():
            if not isinstance(row,dict):continue
            if row.get('files'):add(row,'Windows' if name.startswith('windows/') else 'Mac',name,name+':'+key)
            elif row.get('url'):
                add(dict(row,id=key,title=key,files=[dict(path=key+'.tar.gz',sha256=row.get('sha256'),url=row['url'])]),'Windows',name)
    for item in json.loads((root/'licenses/auxiliary-models.json').read_text())['components']:
        if item['repo'] not in ('Wespeaker/wespeaker-voxceleb-resnet34-LM','KimberleyJSN/melbandroformer'):continue
        path=item.get('installedFile') or 'MelBandRoformer.ckpt'
        add(dict(id=item['repo'],title=item['repo'],repo=item['repo'],revision=item['revision'],license=item['effectiveLicense'],files=[dict(path=path,sha=item['weightSHA256'])]),'Mac / Windows','licenses/auxiliary-models.json')
    # Same files can appear in an old compatibility manifest and a selector.
    # Retain selector policy and merge only genuinely identical inventories.
    policies={(r['repo'],r['revision']):r for r in rows if r['origin'].endswith('model-options.json')}
    for row in rows:
        policy=policies.get((row['repo'],row['revision']))
        if policy and policy is not row:
            row['availability']=policy['availability'];row['license']=policy['license']
    merged={}
    for row in rows:
        # About describes selectable downloads, not every historical catalogue
        # entry. Keep full licence evidence separately in the notice archive.
        if row['availability']!='catalogue':continue
        # Qwen TTS has no selectable engine in the shipping release. Its
        # historical pinned files remain in the separate legal archive.
        if row['engine']=='qwen-tts' or '/Qwen3-TTS-' in row['repo'] or row['origin']=='Resources/qwen-voice-model.json':continue
        if row['category']=='text' or row['engine'] in ('mlx-text','ollama'):
            import re
            if not re.search(r'qwen3[.]5-(?:9b|35b)(?:-|:|$)',row['id'],re.I) and not re.search(r'qwen3[.]5:(?:9b|35b)$',row['id'],re.I):continue
        key=(row['repo'],row['revision'],tuple((f['path'],f['sha256'],f['url'],f['kind']) for f in row['files']))
        if key in merged:
            merged[key]['origins'].append(row['origin']);merged[key]['ids'].append(row['id']);continue
        row['origins']=[row.pop('origin')];row['ids']=[row['id']];merged[key]=row
    return dict(schemaVersion=1,hashAlgorithm='SHA-256',verification='expected-only',models=list(merged.values()))
if __name__=='__main__':print(json.dumps(inventory(),ensure_ascii=False,indent=2))
