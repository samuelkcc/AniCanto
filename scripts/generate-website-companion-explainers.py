"""Record 36 website explanations with each companion's existing voice references."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import os
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / '.build/website-companion-explainers-2026-10-28'
RATE = 44100


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    global WORK
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=WORK)
    parser.add_argument('--copy', type=Path, default=ROOT / 'scripts/website-companion-explainer-copy.json')
    parser.add_argument('--references', type=Path)
    parser.add_argument('--directions', type=Path)
    parser.add_argument('--languages', default='ja,yue,en,zh')
    parser.add_argument('--only', help='One character:language pair, for a reviewed second attempt.')
    parser.add_argument('--attempt', type=int, choices=[1, 2], default=1)
    parser.add_argument('--continuation', action='store_true', help='Record the reviewed missing Kohaku Japanese clause only.')
    args = parser.parse_args()
    WORK = args.work.resolve()
    WORK.mkdir(parents=True, exist_ok=True)
    raw = WORK / 'raw'
    raw.mkdir(exist_ok=True)
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1',
                      HF_HOME=str(WORK / 'offline-cache'))
    sys.path.insert(0, str(ROOT / 'Resources'))
    import numpy as np
    import soundfile as sf
    import mlx.core as mx
    from scipy.signal import resample_poly
    from drama3 import vendor_modules, language_hint
    vendor_modules()
    from mlx_audio.tts.models.fish_drama3 import drama3 as vendor
    from mlx_audio.tts.models.fish_drama3.chunking import split_text
    vendor.split_text = lambda text: split_text(text, limit=2048)
    from mlx_audio.tts.utils import load_model
    copy = json.loads(args.copy.read_text())
    reference_overrides = json.loads(args.references.read_text()) if args.references else {}
    directions = json.loads(args.directions.read_text()) if args.directions else {}
    selected_languages = args.languages.split(',')
    assert len(set(selected_languages)) == len(selected_languages) and all(x in ['ja', 'yue', 'en', 'zh'] for x in selected_languages)
    save(WORK / 'script-copy.json', copy)
    langs = {'ja': 'ja', 'zh-HK': 'yue', 'en': 'en', 'zh-Hans': 'zh'}
    refs = {lang: json.loads((ROOT / f'.build/demo-unified-v10-2026-10-24/{lang}-scenes.json').read_text()) for lang in langs.values()}
    shion_refs = json.loads((ROOT / '.build/website-promo-learning-2026-10-28/references.json').read_text())
    modelpath = Path.home() / 'Library/Application Support/SamCantoSync/models/voice-variants/drama3-35b-4bit'
    model = load_model(str(modelpath), strict=True)
    instructions = {
        'ja': '自然な日本語。参考と同じ人物の声で、親しみのある会話。台詞だけ。',
        'yue': language_hint('yue', 'cantonese-strict') + '。保持參考角色聲線，自然親切，只讀對白。',
        'en': 'Natural English. Keep the exact character voice from the reference. Friendly conversation. Read only the dialogue.',
        'zh': '自然普通话，保持参考角色声线，亲切对话，只读台词。',
    }
    for index, char in enumerate(copy['characters']):
        for ordinal, (locale, lang) in enumerate(langs.items()):
            key = char['id'] + ':' + lang
            if lang not in selected_languages:
                continue
            if args.only and key not in args.only.split(',') and char['id'] not in args.only.split(','):
                continue
            if args.continuation:
                assert key == 'kohaku:ja'
            out = raw / (f'{char["id"]}-{lang}-continuation.wav' if args.continuation else f'{char["id"]}-{lang}-take-{args.attempt}.wav')
            trace = out.with_suffix('.json')
            text = char['dialogue'][locale]
            if args.continuation:
                text = '自然な言い回しや語調にも目を向けてみてね。'
            if out.exists():
                row = json.loads(trace.read_text())
                assert row['text'] == text and row['audioSHA256'] == sha(out)
                print('CACHED', key, flush=True)
                continue
            if trace.exists():
                print('EXISTING_ATTEMPT', key, 'Review before a second attempt.', flush=True)
                continue
            reference = next(row for row in refs[lang] if row['speaker'] == char['speaker'])
            selected = shion_refs[lang] if char['id'] == 'shion' else [reference['audio'], reference['text']]
            selected = reference_overrides.get(key, selected)
            ref, reftext = ROOT / selected[0], selected[1]
            digest = sha(ref)
            audio, sr = sf.read(ref, dtype='float32')
            if len(selected) > 2:
                audio = audio[round(selected[2] * sr):round(selected[3] * sr)]
            if audio.ndim > 1:
                audio = audio.mean(axis=1)
            if sr != RATE:
                divisor = math.gcd(sr, RATE)
                audio = resample_poly(audio, RATE // divisor, sr // divisor).astype(np.float32)
            seed = 202610281000 + index * 101 + ordinal * 19 + (args.attempt - 1) * 10000 + (5000 if args.continuation else 0)
            maximum_frames = 256 if args.continuation else 640
            direction = directions.get(char['id'], {})
            instruction = instructions[lang] + ' ' + direction.get(lang, '')
            emotion = '[' + direction['emotion'] + '] ' if direction.get('emotion') else ''
            prompt = '[' + instruction.strip() + '] ' + emotion + text
            mx.random.seed(seed)
            row = dict(languageStandard='English, ASD-STE100 style.', id=char['id'], speaker=char['speaker'],
                locale=locale, language=lang, text=text, prompt=prompt, seed=seed, attempt=args.attempt,
                reference=str(ref.relative_to(ROOT)), referenceText=reftext, referenceSHA256=digest,
                referenceBounds=selected[2:], performanceDirection=direction, maximumFrames=maximum_frames, partial=args.continuation, pitchChange=False, tempoChange=False)
            began = time.monotonic()
            try:
                frames, chunks = {}, []
                for result in model.generate(text=prompt, ref_audio=audio, ref_text=reftext, stream=True,
                        first_chunk_frames=8, max_tokens=maximum_frames, temperature=.7, top_p=.7, top_k=30):
                    block = np.asarray(result.audio, dtype=np.float32).reshape(-1)
                    if len(block):
                        chunks.append(block)
                    part = str(result.segment_idx)
                    frames[part] = frames.get(part, 0) + int(result.token_count or 0)
                pcm = np.concatenate(chunks) if chunks else np.zeros(0, dtype='float32')
                sf.write(out, pcm, RATE, subtype='PCM_24')
                row.update(audio=str(out.relative_to(ROOT)), audioSHA256=sha(out), seconds=len(pcm) / RATE,
                    frames=frames, generationSeconds=time.monotonic() - began, referenceUnchanged=digest == sha(ref))
                row['validSignal'] = bool(len(pcm) and np.isfinite(pcm).all() and np.sqrt(np.mean(pcm * pcm)) >= .001)
                row['boundedComplete'] = bool(len(frames) == 1 and max(frames.values()) < maximum_frames and 2 <= row['seconds'] <= 30)
                row['state'] = 'ready-for-readback' if row['validSignal'] and row['boundedComplete'] else 'review-required'
                print('RECORDED', key, round(row['seconds'], 3), row['state'], flush=True)
            except Exception as error:
                row.update(state='generation-error', error=str(error), generationSeconds=time.monotonic() - began)
                print('ERROR', key, str(error), flush=True)
            save(trace, row)
            mx.clear_cache()
    rows = [json.loads(path.read_text()) for path in sorted(raw.glob('*.json'))]
    save(WORK / 'takes.json', rows)
    print('BATCH_END', len(rows), flush=True)


if __name__ == '__main__':
    main()
