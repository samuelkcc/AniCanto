"""Fetch only the pinned pip wheel needed to build a public-source checkout."""
import hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def prepare():
    row=json.loads((ROOT/'Resources/python-installer.json').read_text())['pip']
    target=ROOT/'Resources'/row['file'];target.parent.mkdir(parents=True,exist_ok=True)
    def valid(path):return path.is_file() and path.stat().st_size==row['size'] and hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
    if not valid(target):
        part=target.with_suffix('.partial')
        subprocess.run(['curl','--fail','--location','--retry','3','--output',str(part),row['url']],check=True)
        if not valid(part):part.unlink(missing_ok=True);raise ValueError('Pinned pip wheel checksum mismatch')
        part.replace(target)
    return target
if __name__=='__main__':print(prepare())
