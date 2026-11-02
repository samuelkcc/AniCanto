"""Replace one reviewed data-root prefix, then remove its compatibility alias.

Use an idle library. Keep a complete metadata rollback archive outside the library.
Model, media and recording bytes are never candidates.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import subprocess
import tempfile
import zipfile


def replacement(raw, old, new):
    return raw.replace(old.encode(), new.encode())


def update_database(path, old, new):
    connection = sqlite3.connect(path)
    counts = []
    try:
        connection.execute('BEGIN IMMEDIATE')
        for (table,) in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
            quoted_table = '"' + table.replace('"', '""') + '"'
            for column in connection.execute('PRAGMA table_info(' + quoted_table + ')').fetchall():
                quoted_column = '"' + column[1].replace('"', '""') + '"'
                cursor = connection.execute('UPDATE ' + quoted_table + ' SET ' + quoted_column +
                    '=replace(' + quoted_column + ',?,?) WHERE typeof(' + quoted_column +
                    ")='text' AND instr(" + quoted_column + ',?)>0', (old, new, old))
                if cursor.rowcount:
                    counts.append(dict(table=table, column=column[1], rows=cursor.rowcount))
        if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Database integrity check failed.')
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()
    return counts


def atomic_bytes(path, raw, mode, times):
    handle, name = tempfile.mkstemp(prefix='.anicanto-path-', dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(handle, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(stat.S_IMODE(mode))
        os.utime(temporary, ns=times)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def copy_database(source, target):
    with sqlite3.connect('file:' + str(source) + '?mode=ro', uri=True) as reader:
        with sqlite3.connect(target) as writer:
            reader.backup(writer)


def migrate(plan, evidence, apply=False):
    root = Path(plan['newRoot']).resolve()
    legacy = Path(plan['oldRoot'])
    if not legacy.is_symlink() or legacy.resolve() != root:
        raise ValueError('The reviewed legacy path must be an alias to AniCanto.')
    if root.parent != legacy.parent.resolve() or root.name != 'AniCanto':
        raise ValueError('Only the same-parent AniCanto transition is supported.')
    if evidence.resolve().is_relative_to(root):
        raise ValueError('Keep rollback evidence outside the data directory.')
    evidence.mkdir(parents=True, exist_ok=True)
    old, new = str(legacy), str(root)
    rows = []
    for row in plan['files']:
        relative = Path(row['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Invalid relative path.')
        path = root / relative
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError('A reviewed file changed into a link.')
        raw = path.read_bytes()
        if b'\0' in raw or old.encode() not in raw:
            raise ValueError('A reviewed text file changed.')
        changed = replacement(raw, old, new)
        if path.suffix == '.json':
            # Keep natural speech verbatim. Only stored filesystem references move.
            protected={'text','japanese','originalJapanese','cantonese','mandarin','english','translation','script','promptText'}
            def check_speech(value, key=''):
                if isinstance(value,dict):
                    for name,child in value.items():check_speech(child,name)
                elif isinstance(value,list):
                    for child in value:check_speech(child,key)
                elif key in protected and isinstance(value,str) and old in value:
                    raise ValueError('A speech field contains the old path; review it separately.')
            check_speech(json.loads(raw))
            json.loads(changed)
        info = path.stat()
        rows.append(dict(path=path, relative=row['path'], mode=info.st_mode,
                         times=(info.st_atime_ns, info.st_mtime_ns),
                         sha=hashlib.sha256(raw).hexdigest()))
    for row in plan['symlinks']:
        path = root / row['path']
        if path.is_absolute() and not path.parent.resolve().is_relative_to(root):
            raise ValueError('A link parent escapes the library.')
        if not path.is_symlink() or os.readlink(path) != row['target']:
            raise ValueError('A reviewed runtime link changed.')
        target = row['target'].replace(old, new)
        if Path(row['target']).exists() and not Path(target).exists():
            raise ValueError('The new runtime link target is missing.')
    result = dict(textFiles=len(rows), links=len(plan['symlinks']), aliasRemoved=False,
                  mediaAndModelsChanged=False, nonPathValuesChanged=False)
    if not apply:
        return result
    rollback = evidence / 'path-migration-rollback.zip'
    database_before = evidence / 'projects-before.sqlite3'
    database_after = evidence / 'projects-after.sqlite3'
    if rollback.exists() or database_before.exists() or database_after.exists():
        raise ValueError('Use a new evidence directory; never overwrite rollback files.')
    marker=root/'data-root-relocation.json'
    if marker.exists():raise ValueError('A data-root relocation receipt already exists.')
    database = root / 'projects.sqlite3'
    copy_database(database, database_before)
    copy_database(database_before, database_after)
    result['databaseColumns'] = update_database(database_after, old, new)
    # Persist all rollback bytes before the first library mutation.
    with zipfile.ZipFile(rollback, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for row in rows:
            raw = row['path'].read_bytes()
            if hashlib.sha256(raw).hexdigest() != row['sha']:
                raise ValueError('The library changed during staging.')
            archive.writestr(row['relative'], raw)
        archive.writestr('migration-files.json', json.dumps([
            dict(path=x['relative'],mode=x['mode'],times=x['times']) for x in rows]))
    changed_rows = []
    changed_links = []
    try:
        with zipfile.ZipFile(rollback) as archive:
            for row in rows:
                raw = archive.read(row['relative'])
                if hashlib.sha256(row['path'].read_bytes()).hexdigest() != row['sha']:
                    raise ValueError('The library changed before writing.')
                atomic_bytes(row['path'], replacement(raw, old, new), row['mode'], row['times'])
                changed_rows.append(row)
            for row in plan['symlinks']:
                path = root / row['path']
                temporary = path.with_name(path.name + '.anicanto-path-link')
                if temporary.exists() or temporary.is_symlink():
                    raise ValueError('A temporary link path is occupied.')
                temporary.symlink_to(row['target'].replace(old, new))
                os.replace(temporary, path)
                changed_links.append(row)
            copy_database(database_after, database)
            marker.write_text(json.dumps(dict(schemaVersion=1,complete=True,oldRoot=old,newRoot=new),indent=2)+'\n')
            # Remove only the alias, then prove runtime startup without it.
            legacy.unlink()
            for folder in ['runtime','text-runtime','asr-runtime','separator-runtime','cosy-runtime','gsv-runtime']:
                python = root / folder / 'bin/python3'
                probe = subprocess.run([str(python), '-I', '-c',
                    'import json,sys; print(json.dumps(dict(prefix=sys.prefix,version=sys.version_info[:2])))'],
                    capture_output=True, text=True, timeout=30, check=True)
                prefix = json.loads(probe.stdout)['prefix']
                if str(root / folder) != prefix:
                    raise ValueError('A runtime uses the wrong environment.')
            for row in rows:
                expected = replacement(archive.read(row['relative']), old, new)
                if row['path'].read_bytes() != expected:
                    raise ValueError('The written path substitution does not match.')
        result.update(aliasRemoved=True, runtimeStartupPassed=6,
                      rollbackArchive=str(rollback), databaseBackup=str(database_before))
    except BaseException:
        marker.unlink(missing_ok=True)
        if not legacy.exists() and not legacy.is_symlink():
            legacy.symlink_to(root)
        with zipfile.ZipFile(rollback) as archive:
            for row in changed_rows:
                atomic_bytes(row['path'], archive.read(row['relative']), row['mode'], row['times'])
        for row in changed_links:
            path=root/row['path'];path.unlink();path.symlink_to(row['target'])
        copy_database(database_before, database)
        raise
    (evidence / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    # The native host owns the same lock. Never migrate an active library.
    import fcntl
    plan=json.loads(args.plan.read_text())
    with (Path(plan['newRoot'])/'studio/instance.lock').open('rb') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state=json.loads((Path(plan['newRoot'])/'studio/desktop-state.json').read_text())
        if any(row.get('status') == 'running' for row in state.get('queue', [])):
            raise ValueError('Pause all jobs before path migration.')
        print(json.dumps(migrate(plan,args.evidence,args.apply),indent=2))
