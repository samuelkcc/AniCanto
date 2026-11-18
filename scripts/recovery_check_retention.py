"""Retire a completed, reproducible desktop recovery test workspace."""
import hashlib
import json
import shutil
from pathlib import Path
from generated_cache_retention import inventory, live_inputs, live_ancestors


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def validate(root, plan):
    root=root.resolve()
    rel=Path(plan['path'])
    if rel.is_absolute() or '..' in rel.parts or len(rel.parts)!=2 or rel.parts[0]!='.build':
        raise ValueError('Recovery check must be one scratch child.')
    path=root/rel
    if path.is_symlink() or not path.name.startswith('disaster-recovery-desktop-'):
        raise ValueError('Not a generated desktop recovery check.')
    receipt=json.loads((path/'receipt.json').read_text())
    for key in ('buildPassed','macProductVerifierPassed','windowsProductVerifierPassed'):
        if receipt.get(key) is not True:raise ValueError('Recovery check has not passed.')
    if receipt.get('ownerDataRead') is not False or receipt.get('ownerInstallationChanged') is not False:
        raise ValueError('The check is not isolated from owner data.')
    allowed={'materials','vendor','cargo-home','windows-payload','logs','receipt.json'}
    if any(p.name not in allowed for p in path.iterdir()):
        raise ValueError('Recovery check has an unexpected top-level input.')
    expected=receipt['assetHashes'];provided={}
    for row in plan['inputs']:
        input_path=(root/row['path']).resolve()
        if not input_path.is_relative_to(root) or input_path.is_relative_to(path) or not input_path.is_file():
            raise ValueError('Recovery input is missing or inside the removed check.')
        sha=digest(input_path)
        if expected.get(row['name'])!=sha or row['sha256']!=sha:
            raise ValueError('Recovery input checksum changed.')
        provided[row['name']]=sha
    if provided!=expected:raise ValueError('The complete checked release inputs must remain local.')
    materials=path/'materials';manifest=json.loads((materials/'SOURCE-MATERIALS.json').read_text())
    adapters={a['path']:a for a in receipt['buildRecipeAdapters']}
    for row in manifest['files']:
        p=materials/row['path'];sha=digest(p)
        if sha==row['sha256']:continue
        rel_app=Path(row['path']).relative_to('AniCanto').as_posix()
        adapter=adapters.get(rel_app)
        canonical=root/rel_app
        if (not adapter or adapter['originalSHA256']!=row['sha256'] or adapter['adaptedSHA256']!=sha
                or not canonical.is_file() or digest(canonical)!=sha):
            raise ValueError('A unique source change must be kept: '+row['path'])
    targets,_=live_inputs(root)
    if path.resolve() in live_ancestors(targets):raise ValueError('An active input uses the recovery check.')
    if inventory(path)!=plan['inventory']:raise ValueError('Recovery check changed after review.')
    proof=root/plan['proofCopy']
    if not proof.resolve().is_relative_to(root) or proof.resolve().is_relative_to(path):
        raise ValueError('The recovery proof must remain outside scratch.')
    return path,receipt,proof


def execute(root, plan_path, apply=False):
    plan=json.loads(plan_path.read_text());path,receipt,proof=validate(root,plan)
    before=shutil.disk_usage(root).free
    if apply:
        proof.parent.mkdir(parents=True,exist_ok=True)
        proof.write_text(json.dumps(dict(receipt,retiredScratchPath=plan['path'],localPinnedInputsPreserved=plan['inputs']),indent=2)+'\n')
        if json.loads(proof.read_text())['buildPassed'] is not True:raise ValueError('Proof copy failed.')
        shutil.rmtree(path)
    return dict(action='applied' if apply else 'dry-run',path=plan['path'],logicalBytes=plan['inventory']['logicalBytes'],
                sourceInputsPreserved=True,volumeFreeBeforeBytes=before,volumeFreeAfterBytes=shutil.disk_usage(root).free)
