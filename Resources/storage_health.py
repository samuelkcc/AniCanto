"""Inspect and repair app-owned directories without removing saved work."""
import os
import shutil
from pathlib import Path

DIRECTORIES = ('studio', 'jobs', 'models', 'cache', 'logs', 'exports', 'separations')
GROUPS = {
    'jobs': 'Projects and recordings', 'separations': 'Separated audio',
    'models': 'Downloaded models', 'cache': 'Temporary files',
    'exports': 'Finished exports', 'runtimes': 'Runtimes', 'runtime': 'Runtimes',
}


def inspect(root):
    root = Path(root).resolve()
    rows = []
    issues = []
    for name in DIRECTORIES:
        p = root / name
        if p.is_symlink():
            issues.append(dict(directory=name, reason='linked-directory', canRepair=False))
        elif p.exists() and not p.is_dir():
            issues.append(dict(directory=name, reason='not-a-directory', canRepair=False))
        elif not p.exists():
            issues.append(dict(directory=name, reason='missing-directory', canRepair=True))
    # Do not follow links into external media or count shared inodes twice.
    seen = set()
    for entry in sorted(root.iterdir()):
        if entry.is_symlink():
            rows.append(dict(name=entry.name, category=GROUPS.get(entry.name, 'Other app data'),
                             bytes=0, allocatedBytes=0, linked=True, files=0))
            continue
        logical = allocated = count = 0
        candidates = ((entry.parent, [], [entry.name]),) if entry.is_file() else os.walk(entry, followlinks=False)
        for base, dirs, names in candidates:
            dirs[:] = [n for n in dirs if not (Path(base) / n).is_symlink()]
            for name in names:
                p = Path(base) / name
                try:
                    st = p.lstat()
                    if p.is_symlink() or not p.is_file():
                        continue
                    count += 1
                    logical += st.st_size
                    key = (st.st_dev, st.st_ino)
                    if key not in seen:
                        allocated += getattr(st, 'st_blocks', (st.st_size + 511) // 512) * 512
                        seen.add(key)
                except OSError:
                    issues.append(dict(directory=entry.name, reason='unreadable-file', canRepair=False))
        rows.append(dict(name=entry.name, category=GROUPS.get(entry.name, 'Other app data'),
                         bytes=logical, allocatedBytes=allocated, linked=False, files=count))
    return dict(root=str(root),directories=rows,issues=issues,
                bytes=sum(x['bytes'] for x in rows),allocatedBytes=sum(x['allocatedBytes'] for x in rows),
                reclaimableEstimate=False, modelsAndProjectsProtected=True,
                availableBytes=shutil.disk_usage(root).free)


def repair(root):
    """Create missing folders only. Never replace files, links, or stored settings."""
    root = Path(root).resolve()
    created = []
    skipped = []
    for name in DIRECTORIES:
        p = root / name
        if p.is_symlink() or (p.exists() and not p.is_dir()):
            skipped.append(name)
            continue
        if not p.exists():
            p.mkdir(exist_ok=True)
            created.append(name)
    return dict(root=str(root),created=created,skipped=skipped,
                complete=not skipped,removedFiles=0,projectsChanged=False,modelsChanged=False)


def default_root(platform, home=None, local_app_data=None):
    """Use AniCanto for new data. Keep an existing legacy root available for migration."""
    home = Path(home or Path.home())
    parent = Path(local_app_data or os.environ.get('LOCALAPPDATA', str(home))) if platform == 'win32' else home / 'Library/Application Support'
    current = parent / 'AniCanto'
    legacy = parent / ('CantoSync-Windows' if platform == 'win32' else 'SamCantoSync')
    return current if current.exists() or not legacy.exists() else legacy
