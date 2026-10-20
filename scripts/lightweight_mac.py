"""Make the signed desktop code small; dependency installers use Application Support."""
import hashlib,json,shutil,sys
from pathlib import Path

def prepare(resources,root):
    resources=Path(resources);root=Path(root)
    for name in ('runtimes','gpt-sovits','ollama'):
        path=resources/name
        if path.is_symlink():path.unlink()
        elif path.exists():shutil.rmtree(path)
    (resources/'runtimes').mkdir(parents=True)
    (resources/'BUNDLED-RUNTIMES.json').write_text('{}\n')
    for file in (root/'Resources').glob('*requirements.*'):
        if file.is_file():shutil.copy2(file,resources/file.name)
    (resources/'bin/uv').unlink(missing_ok=True)
    for name in ('python-installer.json','python-bootstrap.sh','python-bootstrap.ps1','runtime_installer.py','mac-runtime-catalog.json'):shutil.copy2(root/'Resources'/name,resources/name)
    sys.path.insert(0,str(root/'Resources'))
    import mac_runtime
    identities={name:dict(identity=mac_runtime.spec(name)['identity'],requirements=row['requirements']) for name,row in mac_runtime.catalog()['runtimes'].items()}
    (resources/'mac-runtime-identities.json').write_text(json.dumps(identities,indent=2)+'\n')
    (resources/'LIGHTWEIGHT-PACKAGE.json').write_text(json.dumps(dict(schemaVersion=1,
        platform='macos-arm64',runtimeStorage='Application Support/SamCantoSync',
        bundledRuntimes=False,bundledModelWeights=False,firstLaunchDeployment=True),indent=2)+'\n')
    notices=resources/'THIRD-PARTY-NOTICES.txt'
    if notices.is_file():
        notices.write_text(notices.read_text().replace(
            'Ollama and isolated standalone Python runtimes are bundled; dependency licenses remain in site-packages distribution metadata. Model downloads are app-managed.',
            'Python runtimes, optional Ollama, and model weights are downloaded on demand into Application Support/SamCantoSync. Runtime licenses are indexed there after installation.'))
    return identities
