"""Generate identical platform-neutral UI resources; never include model weights."""
import hashlib,json,shutil,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def prepare():
    target=ROOT/'studio/web/assets';target.mkdir(parents=True,exist_ok=True)
    guide_root=Path(os.environ.get('ANICANTO_GUIDE_ROOT') or ROOT/'docs')
    from validate_user_guide import validate
    validate(json.loads((guide_root/'APPLICATION-USER-GUIDE.json').read_bytes()))
    guide=(guide_root/'WORKFLOW-CONTROLS-GUIDE.json').read_bytes()
    (target/'workflow-controls-guide.json').write_bytes(guide)
    (target/'workflow-controls-guide.js').write_text('export const WORKFLOW_GUIDE='+guide.decode()+';\nexport const WORKFLOW_GUIDE_SHA='+json.dumps(hashlib.sha256(guide).hexdigest())+';\n')
    manual=(guide_root/'APPLICATION-USER-GUIDE.json').read_bytes()
    (target/'application-user-guide.json').write_bytes(manual)
    (target/'application-user-guide.js').write_text('export const APPLICATION_USER_GUIDE='+manual.decode()+';\nexport const APPLICATION_USER_GUIDE_SHA='+json.dumps(hashlib.sha256(manual).hexdigest())+';\n')
    for path in target.glob('welcome-*.png'):path.unlink()
    for path in (ROOT/'Resources/welcome-art').glob('welcome-*.png'):shutil.copy2(path,target/path.name)
    for path in (ROOT/'Resources').glob('pet-*.png'):shutil.copy2(path,target/path.name)
    shutil.copy2(ROOT/'Resources/fonts/NotoSansCJKtc-Regular.otf',target/'studio-cjk.otf')
    shutil.copy2(ROOT/'Resources/fonts/LICENSE',target/'font-LICENSE')
    shutil.copy2(ROOT/'Resources/fonts/NOTICE.txt',target/'font-NOTICE.txt')
    (target/'assistant-busy-atlas.png').unlink(missing_ok=True)
    (target/'assistant-rigs.js').write_text('export const ASSISTANT_RIGS='+ (ROOT/'Resources/assistant-rigs.json').read_text()+';\n')
    shutil.copy2(ROOT/'Resources/AniCanto-icon.png',target/'app-icon.png')
    shutil.copy2(ROOT/'LICENSE',target/'LICENSE')
    (target/'application-license.js').write_text('export const APPLICATION_LICENSE='+json.dumps((ROOT/'LICENSE').read_text())+';\n')
    terms=(ROOT/'Resources/USE-TERMS.json').read_bytes()
    (target/'use-terms.js').write_text('export const USE_TERMS='+json.dumps(dict(json.loads(terms),sha256=hashlib.sha256(terms).hexdigest()),ensure_ascii=False)+';\n')
    shutil.copy2(ROOT/'Resources/studio-interface.json',target/'studio-interface.json')
    (target/'app-version.js').write_text('export const APP_VERSION='+json.dumps(json.loads((ROOT/'VERSION.json').read_text())['version'])+';\n')
    (target/'version.json').write_text(json.dumps(dict(version=json.loads((ROOT/'VERSION.json').read_text())['version'],channel='Beta'))+'\n')
    import sys
    sys.path.insert(0,str(ROOT/'Resources'))
    from workflow_localization import catalog
    exact,patterns=catalog()
    (target/'workflow-localization.js').write_text('export const WORKFLOW='+json.dumps(dict(exact=exact,patterns=patterns),ensure_ascii=False)+';\n')
    from download_sources import inventory
    (target/'download-sources.js').write_text('export const DOWNLOAD_SOURCES='+json.dumps(inventory(),ensure_ascii=False)+';\n')
    web=target.parent
    files={str(p.relative_to(web)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(web.rglob('*')) if p.is_file() and p.name!='interface-manifest.json'}
    (target/'interface-manifest.json').write_text(json.dumps(dict(schemaVersion=1,files=files),sort_keys=True)+'\n')
    return target

if __name__=='__main__':print(prepare())
