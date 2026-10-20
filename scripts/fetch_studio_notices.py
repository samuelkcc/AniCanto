"""Recover notices omitted from published crates, at their recorded VCS commit.

Run once when updating Cargo.lock; builds only consume these checked-in files.
No model weights or mutable branch URLs are involved.
"""
import hashlib,json,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
metadata=json.loads((ROOT/'.build/shared-studio-qa/cargo-metadata.json').read_text())
cache={}
for package in metadata['packages']:
    if not package.get('source'):continue
    folder=Path(package['manifest_path']).parent
    if any(p.is_file() and p.name.upper().startswith(('LICENSE','LICENCE','COPYING','NOTICE','UNLICENSE')) for p in folder.iterdir()):continue
    vcs=json.loads((folder/'.cargo_vcs_info.json').read_text());revision=vcs['git']['sha1']
    repository=package['repository'].removesuffix('.git').removesuffix('/')
    owner_repo='/'.join(repository.split('/')[-2:])
    if (owner_repo,revision) not in cache:
        req=urllib.request.Request(f'https://api.github.com/repos/{owner_repo}/git/trees/{revision}',headers={'User-Agent':'AniCanto-build'})
        with urllib.request.urlopen(req,timeout=30) as response:tree=json.load(response)
        notices=[r for r in tree['tree'] if r['type']=='blob' and r['path'].upper().startswith(('LICENSE','LICENCE','COPYING','NOTICE','UNLICENSE'))]
        if not notices and package.get('license')=='MPL-2.0':
            url='https://www.mozilla.org/media/MPL/2.0/index.txt'
            with urllib.request.urlopen(url,timeout=30) as response:data=response.read()
            if b'Mozilla Public License' not in data[:150]:raise RuntimeError('Unexpected MPL text')
            cache[owner_repo,revision]=[('LICENSE-MPL-2.0',url,data)]
        elif not notices:raise RuntimeError('No repository-root notices at '+repository+' / '+revision)
        rows=[]
        for notice in notices:
            url=f'https://raw.githubusercontent.com/{owner_repo}/{revision}/{notice["path"]}'
            with urllib.request.urlopen(url,timeout=30) as response:data=response.read()
            rows.append((notice['path'],url,data))
        if rows:cache[owner_repo,revision]=rows
    target=ROOT/'studio/notices'/(package['name']+'-'+package['version']);target.mkdir(parents=True,exist_ok=True)
    sources=[]
    for name,url,data in cache[owner_repo,revision]:
        (target/name).write_bytes(data);sources.append(dict(file=name,url=url,sha256=hashlib.sha256(data).hexdigest()))
    (target/'SOURCE.json').write_text(json.dumps(dict(crate=package['name'],version=package['version'],revision=revision,sources=sources),indent=2)+'\n')
    print(package['name'],revision)
