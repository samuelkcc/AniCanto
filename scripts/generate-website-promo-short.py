"""Record four new Shion lines with the installed Drama3 model.

Keep accepted recordings and application media unchanged. Save each bounded take.
"""
from pathlib import Path
import hashlib
import argparse
import json
import math
import os
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / '.build/website-promo-short-2026-10-28'
RATE = 44100


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    global WORK
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=WORK)
    parser.add_argument('--copy', type=Path, default=ROOT / 'scripts/website-promo-short-copy.json')
    args = parser.parse_args()
    WORK = args.work.resolve()
    WORK.mkdir(parents=True, exist_ok=True)
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
    (WORK / 'script-copy.json').write_text(json.dumps(copy, ensure_ascii=False, indent=2) + '\n')
    refs = json.loads((WORK / 'references.json').read_text())
    modelpath = Path.home() / 'Library/Application Support/SamCantoSync/models/voice-variants/drama3-35b-4bit'
    model = load_model(str(modelpath), strict=True)
    rows = []
    instructions = {
        'ja': '自然な日本語。参考と同じ紫音の声。友達に笑顔で話す、明るく親しみのある声。台詞だけ。',
        'yue': language_hint('yue', 'cantonese-strict') + '。少女帶笑意，自然親切。',
        'en': 'Natural English. Keep the same Shion voice as the reference. Warm friendly conversation. Read only the dialogue.',
        'zh': '普通话，保持参考声音，只读台词。',
    }
    for i, segment in enumerate(copy['segments']):
        lang, text = segment['language'], segment['text']
        out = WORK / f'{lang}.wav'
        trace = out.with_suffix('.json')
        if out.exists():
            row = json.loads(trace.read_text())
            assert row['text'] == text and row['audioSHA256'] == sha(out)
            rows.append(row)
            print('CACHED', lang, flush=True)
            continue
        ref = ROOT / refs[lang][0]
        reftext = refs[lang][1]
        refhash = sha(ref)
        audio, sr = sf.read(ref, dtype='float32')
        if len(refs[lang]) > 2:
            audio = audio[round(refs[lang][2] * sr):round(refs[lang][3] * sr)]
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        if sr != RATE:
            g = math.gcd(sr, RATE)
            audio = resample_poly(audio, RATE // g, sr // g).astype(np.float32)
        prompt = '[' + instructions[lang] + '] ' + text
        seed = 202610280400 + i * 37 + (20000 if lang == 'yue' else 30000 if lang == 'zh' and copy.get('theme') == 'anime-language-learning' else 10000 if lang == 'ja' and copy.get('theme') == 'anime-language-learning' else 0)
        mx.random.seed(seed)
        frames, chunks = {}, []
        began = time.monotonic()
        for result in model.generate(text=prompt, ref_audio=audio, ref_text=reftext, stream=True,
                                     first_chunk_frames=8, max_tokens=480, temperature=.7, top_p=.7, top_k=30):
            block = np.asarray(result.audio, dtype=np.float32).reshape(-1)
            if len(block):
                chunks.append(block)
            key = str(result.segment_idx)
            frames[key] = frames.get(key, 0) + int(result.token_count or 0)
        pcm = np.concatenate(chunks) if chunks else np.zeros(0, dtype='float32')
        draft = out.with_suffix('.draft.wav')
        sf.write(draft, pcm, RATE, subtype='PCM_24')
        row = dict(languageStandard='English, ASD-STE100 style.', language=lang, text=text, prompt=prompt,
                   seed=seed, speaker='Shion', reference=str(ref.relative_to(ROOT)), referenceText=reftext,
                   referenceSHA256=refhash, referenceUnchanged=refhash == sha(ref),
                   referenceBounds=refs[lang][2:], seconds=len(pcm) / RATE, frames=frames, maximumFrames=480,
                   sampling=dict(temperature=.7, top_p=.7, top_k=30),
                   model='Fish Audio Drama3 35B 4-bit MLX', modelConfigSHA256=sha(modelpath / 'config.json'),
                   generationSeconds=time.monotonic() - began, pitchChange=False, tempoChange=False)
        trace.write_text(json.dumps(row, ensure_ascii=False, indent=2) + '\n')
        if not len(pcm) or not np.isfinite(pcm).all() or np.sqrt(np.mean(pcm * pcm)) < .001:
            raise RuntimeError(f'Invalid signal: {lang}. Draft retained.')
        if len(frames) != 1 or max(frames.values()) >= 480 or not 3 <= len(pcm) / RATE <= 20:
            raise RuntimeError(f'Incomplete or excessive take: {lang}. Draft retained.')
        draft.replace(out)
        row.update(audio=str(out.relative_to(ROOT)), audioSHA256=sha(out))
        trace.write_text(json.dumps(row, ensure_ascii=False, indent=2) + '\n')
        rows.append(row)
        (WORK / 'takes.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')
        print('RECORDED', lang, round(row['seconds'], 3), flush=True)
        mx.clear_cache()
    (WORK / 'takes.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')
    print('DONE', len(rows), flush=True)


if __name__ == '__main__':
    main()
