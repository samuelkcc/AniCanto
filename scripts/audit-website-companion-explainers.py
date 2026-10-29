"""Read all website companion recordings through independent PCM-only ASR."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'mobile/DemoFilm'))
import audit_unified_demo as shared


def collect(work, design, languages, ids):
    copy = json.loads((work / 'script-copy.json').read_text())
    index = {row['id']: i for i, row in enumerate(copy['characters'])}
    selected = {}
    for path in sorted((work / 'raw').glob('*.json')):
        row = json.loads(path.read_text())
        if row.get('audio') and not row.get('partial'):
            selected[(row['id'], row['language'])] = row
    inputs = []
    for (name, lang), row in selected.items():
        i = index[name]
        if lang not in languages or (ids is not None and i not in ids):
            continue
        japanese = selected[(name, 'ja')]
        inputs.append(dict(language=lang, id=i, audio=ROOT / row['audio'], expected=row['text'],
            sourceJapanese=copy['characters'][i]['dialogue']['ja'], japaneseAudio=ROOT / japanese['audio']))
    return inputs


if __name__ == '__main__':
    shared.DEFAULT_WORK = ROOT / '.build/website-companion-explainers-2026-10-28'
    shared.FULL_SCOPE = 'Nine website companion explanations in four languages'
    shared.FULL_COUNT = 36
    shared.collect_inputs = collect
    shared.main()
