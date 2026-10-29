"""Read four new website recordings through independent PCM-only ASR."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'mobile/DemoFilm'))
import audit_unified_demo as shared


def collect(work, design, languages, ids):
    script = work / 'script-copy.json'
    if not script.exists():
        script = ROOT / 'scripts/website-promo-short-copy.json'
    copy = json.loads(script.read_text())
    rows = json.loads((work / 'takes.json').read_text())
    return [dict(language=row['language'], id=i, audio=ROOT / row['audio'], expected=row['text'],
                 sourceJapanese=copy['segments'][0]['text'],
                 japaneseAudio=ROOT / 'mobile/DemoAssets/v19/audio/source-0.wav')
            for i, row in enumerate(rows) if row['language'] in languages]


if __name__ == '__main__':
    shared.DEFAULT_WORK = ROOT / '.build/website-promo-short-2026-10-28'
    shared.FULL_SCOPE = 'Four new Shion website advertising recordings'
    shared.FULL_COUNT = 4
    shared.collect_inputs = collect
    shared.main()
