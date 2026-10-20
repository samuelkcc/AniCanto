"""Pinned NLTK data with exact contents and retained upstream terms.

No floating nltk.download index and no implicit model/data downloads at setup.
"""
import hashlib,json,os,shutil,uuid,zipfile
from pathlib import Path


def manifest():
    base=Path(__file__).resolve().parent
    if not (base/'licenses/text-data.json').is_file():base=base.parent
    return base,json.loads((base/'licenses/text-data.json').read_text())


def verified_files(folder,files):
    for row in files:
        path=folder/row['path']
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(folder.resolve()):return False
        if hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:return False
    return True


def install_nltk(root,download=None):
    if download is None:
        from model_download import download
    base,data=manifest();root=Path(root);receipts=[]
    for row in data['packages']:
        docs=[]
        for doc in row['documents']:
            path=base/doc['path']
            if not path.resolve().is_relative_to((base/'licenses').resolve()):raise ValueError('Unsafe text-data notice path')
            raw=path.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=doc['sha256']:raise ValueError('Text-data licence evidence integrity failed')
            docs.append((path.name,raw))
        parent=root/'models/nltk'/row['subdir'];target=parent/row['id'];parent.mkdir(parents=True,exist_ok=True)
        if not verified_files(target,row['files']):
            archive=root/'downloads/text-data'/(row['id']+'-'+row['revision'][:12]+'.zip')
            download(row['url'],archive,row['archiveSHA256'],row['archiveBytes'])
            if hashlib.sha256(archive.read_bytes()).hexdigest()!=row['archiveSHA256']:raise ValueError('Text-data archive integrity failed')
            stage=parent/('.'+row['id']+'-'+uuid.uuid4().hex);stage.mkdir()
            old=parent/('.'+row['id']+'-previous-'+uuid.uuid4().hex)
            try:
                expected={row['id']+'/'+f['path'] for f in row['files']}
                with zipfile.ZipFile(archive) as z:
                    entries=[e for e in z.infolist() if not e.is_dir()]
                    if len(entries)!=len(expected) or {e.filename for e in entries}!=expected:raise ValueError('Unexpected text-data archive contents')
                    for entry in entries:
                        rel=Path(entry.filename).relative_to(row['id'])
                        if '..' in rel.parts or rel.is_absolute():raise ValueError('Unsafe text-data member')
                        output=stage/rel;output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(z.read(entry))
                if not verified_files(stage,row['files']):raise ValueError('Text-data extraction integrity failed')
                if target.is_symlink():raise ValueError('Text-data destination must not be a symlink')
                if target.exists():os.rename(target,old)
                try:os.rename(stage,target)
                except BaseException:
                    if old.exists():os.rename(old,target)
                    raise
                if old.exists():shutil.rmtree(old)
            finally:
                if stage.exists():shutil.rmtree(stage)
        notice=target/'AniCanto-LICENSES';notice.mkdir(exist_ok=True)
        for name,raw in docs:(notice/name).write_bytes(raw)
        (notice/'provenance.json').write_text(json.dumps(row,indent=2)+'\n')
        receipts.append(dict(id=row['id'],revision=row['revision'],archiveSHA256=row['archiveSHA256']))
    return receipts
