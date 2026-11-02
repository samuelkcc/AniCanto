"""Check the Mac product in dist/ before Samuel installs it.

A staged native-only bundle carries the Swift shell as the main executable and
shows the retired desktop interface. This check fails that bundle.
"""
import hashlib,json,os,plistlib,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    app=Path(os.environ.get('CANTOSYNC_VERIFY_APP',str(ROOT/'dist/AniCanto.app')))
    if not app.is_dir():raise SystemExit('Missing Mac product: '+str(app))
    release=json.loads((ROOT/'VERSION.json').read_text())
    contents=app/'Contents';resources=contents/'Resources'
    with (contents/'Info.plist').open('rb') as handle:info=plistlib.load(handle)
    version=info.get('CFBundleShortVersionString');build=str(info.get('CFBundleVersion'))
    if (version,build)!=(release['version'],str(release['build'])):
        raise SystemExit(f'Mac product identity {version}/{build} does not match VERSION.json {release["version"]}/{release["build"]}')
    if json.loads((resources/'VERSION.json').read_text())!=release:
        raise SystemExit('Bundled VERSION.json does not match the release VERSION.json')
    host=contents/'MacOS'/'AniCanto'
    worker=contents/'MacOS'/'AniCanto-worker'
    if not host.is_file():raise SystemExit('Missing executable: AniCanto')
    if not worker.is_file():raise SystemExit('Missing native worker: AniCanto-worker')
    # The shared UI host embeds the common interface manifest. The retired Swift
    # shell does not, so this byte test separates a correct product from a stage.
    manifest=(ROOT/'studio/web/assets/interface-manifest.json').read_bytes()
    host_bytes=host.read_bytes()
    if manifest not in host_bytes:
        raise SystemExit('Mac product does not embed the shared desktop interface; '
            'run scripts/build_shared_host.py --target native and scripts/package_shared_studio.py first.')
    if manifest in worker.read_bytes():
        raise SystemExit('AniCanto-worker carries the shared interface; the two executables are swapped.')
    if not (resources/'studio/backend.py').is_file():
        raise SystemExit('Missing shared desktop backend in the bundle.')
    staged=ROOT/'.build/shared-release'/release['version']/'AniCanto.app'
    if not staged.is_dir():
        raise SystemExit('Missing staged shared release. Package the shared desktop interface before delivery.')
    if hashlib.sha256(host_bytes).hexdigest()!=hashlib.sha256((staged/'Contents/MacOS'/'AniCanto').read_bytes()).hexdigest():
        raise SystemExit('dist/ does not match the staged shared release.')
    for source in sorted((ROOT/'Resources').glob('*.py')):
        if source.read_bytes()!=(resources/source.name).read_bytes():
            raise SystemExit('Stale Mac worker module: '+source.name)
    if (ROOT/'studio/backend.py').read_bytes()!=(resources/'studio/backend.py').read_bytes():
        raise SystemExit('Stale shared desktop backend.')
    subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(app)],check=True)
    with tempfile.TemporaryDirectory(prefix='anicanto-mac-verify-') as scratch:
        result=subprocess.run([str(worker),'--studio-validate-contract'],
            env=dict(os.environ,SAM_CANTO_DATA=scratch,CANTOSYNC_STUDIO_DATA=scratch,CANTOSYNC_WINDOWS_DATA=scratch),capture_output=True,text=True,timeout=60)
        if result.returncode:raise SystemExit('Native worker contract check failed: '+(result.stdout+result.stderr)[-1200:])
        probe=json.loads(result.stdout.strip().splitlines()[-1])
        if probe.get('languages')!=['yue','zh','en']:
            raise SystemExit('Native worker language plan does not match the release contract.')
    print(json.dumps(dict(version=version,build=build,sharedInterfaceHost=True,
        hostBytes=len(host_bytes),workerBytes=worker.stat().st_size,
        hostSha256=hashlib.sha256(host_bytes).hexdigest(),signatureValid=True,
        nativeContract=True,guiExecuted=False),indent=2))

if __name__=='__main__':main()
