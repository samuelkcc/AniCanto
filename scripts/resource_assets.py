"""Remove retired visual experiments from cloned app bundles before signing."""
from pathlib import Path
import shutil
RETIRED_PATTERNS=('scene-*.png','theme-*-poses.png','theme-characters.png','studio-character.png','workspace-guide.png','assistant-busy-atlas.png','assistant-busy-provenance.json','companion-*.png','guide-*.png')
def prune(resources):
    root=Path(resources)
    for pattern in RETIRED_PATTERNS:
        for path in root.glob(pattern):
            if path.is_file():path.unlink()
    old=root/'ui-art'
    if old.is_dir():shutil.rmtree(old)

    # The shared desktop uses its own browser-compatible preview. The legacy
    # VLC player is not invoked by this host; exclude that unused binary stack.
    for folder in ('vlc','Licenses/VLC'):
        path=root/folder
        if path.is_dir():shutil.rmtree(path)
    metadata=root/'BUNDLED-COMPONENTS.json'
    if metadata.is_file():
        import json
        old=json.loads(metadata.read_text());clean={}
        for target,source in old.items():
            key=target.split('/Contents/')[-1]
            if isinstance(source,str) and not source.startswith('homebrew/'):
                parts=Path(source).resolve().parts
                if 'Cellar' in parts:
                    at=parts.index('Cellar');source='/'.join(('homebrew',)+parts[at+1:at+3]+(Path(source).name,))
                else:source=Path(source).name
            clean[key]=source
        metadata.write_text(json.dumps(clean,indent=2)+'\n')
