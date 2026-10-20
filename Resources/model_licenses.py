"""Preserve pinned model-card/license evidence beside downloaded model files."""
import hashlib,json,shutil
from pathlib import Path

def install_auxiliary_notices(repo,target):
    """Keep exact auxiliary-weight evidence, without claiming unresolved rights."""
    base=Path(__file__).parent
    if not (base/'licenses/auxiliary-models.json').is_file():base=base.parent
    records=json.loads((base/'licenses/auxiliary-models.json').read_text())['components']
    record=next((r for r in records if r['repo']==repo),None)
    if record is None:raise ValueError('Auxiliary model provenance is missing.')
    # Read and verify everything before creating any sidecar.
    verified=[]
    for doc in record['documents']:
        source=base/doc['path']
        if not source.resolve().is_relative_to((base/'licenses').resolve()):raise ValueError('Unsafe auxiliary notice path.')
        raw=source.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=doc['sha256']:raise ValueError('Auxiliary notice integrity check failed.')
        verified.append((source.name,raw))
    dest=Path(target)/'AniCanto-LICENSES'/repo.replace('/','--');dest.mkdir(parents=True,exist_ok=True)
    for name,raw in verified:(dest/name).write_bytes(raw)
    (dest/'provenance.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    (dest/'NOTICE.txt').write_text('\n'.join(filter(None,[repo,record.get('attribution'),
        'Declared weight licence: '+record['effectiveLicense'],record.get('licenseURL'),
        'Review status: '+record['status'],'Weight evidence is separate from the adapter code licence.']))+'\n')
    return dest

def install_notices(row,target):
    if row.get('licenseReviewRequired'):
        raise ValueError('This model conversion has no confirmed license; choose a reviewed model variant.')
    base=Path(__file__).parent
    index=base/'licenses/model-evidence.json'
    if not index.is_file():
        # Development sources keep the same reviewed inventory at repository root.
        base=base.parent;index=base/'licenses/model-evidence.json'
    records=json.loads(index.read_text())['models']
    evidence=next((r for r in records if r['repo']==row.get('repo') and r['revision']==row.get('revision')),None)
    if evidence is None or evidence.get('status')=='blocked-missing-license':
        raise ValueError('Pinned model-license evidence is missing; repair the app or choose a reviewed variant.')
    dest=Path(target)/'AniCanto-LICENSES';dest.mkdir(parents=True,exist_ok=True)
    for doc in evidence['documents']:
        source=base/doc['path']
        if not source.resolve().is_relative_to((base/'licenses').resolve()) or hashlib.sha256(source.read_bytes()).hexdigest()!=doc['sha256']:
            raise ValueError('Model license document integrity check failed.')
        shutil.copy2(source,dest/source.name)
    common={'Apache-2.0':'Apache-2.0.txt','MIT':'GPT-SoVITS-MIT.txt','BSD-3-Clause':'AST-BSD-3-Clause.txt'}.get(evidence.get('effectiveLicense'))
    if common and not any(p.name.upper().startswith('LICENSE') for p in dest.iterdir()):
        # MIT and BSD attribution is component-specific, never a generic invented holder.
        if evidence.get('effectiveLicense')=='MIT' and row.get('repo')!='lj1995/GPT-SoVITS':common=None
        if common:shutil.copy2(base/'licenses/common'/common,dest/common)
    (dest/'provenance.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
