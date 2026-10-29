"""Prepare selected companion audio and shorten measured, near-silent internal gaps."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / '.build/website-companion-explainers-2026-10-28'
PUBLIC = ROOT / 'website/media/companions'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def measure_loudness(path):
    result = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(path), '-af',
        'loudnorm=I=-24:TP=-2:LRA=9:print_format=json', '-f', 'null', '-'],
        capture_output=True, text=True, check=True).stderr
    return json.JSONDecoder().raw_decode(result[result.rfind('{'):])[0]


def main():
    global WORK
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=WORK)
    parser.add_argument('--characters', help='Only these comma-separated character IDs.')
    parser.add_argument('--minimum-gap', type=float, default=1.2)
    parser.add_argument('--retained-gap', type=float, default=.55)
    parser.add_argument('--target-lufs', type=float, help='Use constant gain to match this level, with 2 dB true-peak headroom.')
    args = parser.parse_args()
    WORK = args.work.resolve()
    assert 0 < args.retained_gap < args.minimum_gap
    copy_file = WORK / 'script-copy.json' if args.characters else ROOT / 'scripts/website-companion-explainer-copy.json'
    copy = json.loads(copy_file.read_text())
    characters = args.characters.split(',') if args.characters else [c['id'] for c in copy['characters']]
    scripts = {(c['id'], locale): text for c in copy['characters'] for locale, text in c['dialogue'].items()}
    selected = {}
    for trace in sorted((WORK / 'raw').glob('*.json')):
        row = json.loads(trace.read_text())
        if row.get('state') == 'ready-for-readback' and not row.get('partial') and row['id'] in characters:
            selected[(row['id'], row['locale'])] = row
    assert len(selected) == len(characters) * 4, 'Do not publish an incomplete selection.'
    PUBLIC.mkdir(parents=True, exist_ok=True)
    edited = WORK / 'edited'
    edited.mkdir(exist_ok=True)
    receipts = []
    for key, row in selected.items():
        assert scripts[key] == row['text']
        source = ROOT / row['audio']
        assert sha(source) == row['audioSHA256']
        pcm, rate = sf.read(source, dtype='float32')
        detect = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(source), '-af',
            f'silencedetect=noise=-45dB:d={args.minimum_gap}', '-f', 'null', '-'], capture_output=True, text=True, check=True)
        starts = [float(x) for x in re.findall(r'silence_start: ([0-9.]+)', detect.stderr)]
        ends = [float(x) for x in re.findall(r'silence_end: ([0-9.]+)', detect.stderr)]
        assert len(starts) == len(ends), 'Unclosed quiet tail needs review.'
        cuts = []
        for start, end in zip(starts, ends):
            first = round((start + args.retained_gap * .45) * rate)
            last = round((end - args.retained_gap * .55) * rate)
            assert first > 0 and last < len(pcm)
            peak = float(np.max(np.abs(pcm[first:last])))
            assert peak < .001, 'Do not cut a gap that may contain quiet speech.'
            cuts.append(dict(firstSample=first, lastSample=last, removedSeconds=(last-first)/rate, peak=peak))
        parts, cursor = [], 0
        for cut in cuts:
            parts.append(pcm[cursor:cut['firstSample']])
            cursor = cut['lastSample']
        parts.append(pcm[cursor:])
        output = np.concatenate(parts)
        stem = row['id'] + '.' + row['locale']
        wav = edited / (stem + '.wav')
        sf.write(wav, output, rate, subtype='PCM_24')
        check, check_rate = sf.read(wav, dtype='float32')
        assert check_rate == rate and np.array_equal(check, output)
        mp3 = PUBLIC / (stem + '.mp3')
        gain, loudness, public_loudness = 0.0, None, None
        if args.target_lufs is not None:
            assert -35 <= args.target_lufs <= -14
            loudness = measure_loudness(wav)
            gain = round(min(args.target_lufs - float(loudness['input_i']), -2 - float(loudness['input_tp'])), 2)
        def encode(level):
            filters = ['-af', f'volume={level}dB'] if level else []
            subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(wav), *filters, '-c:a', 'libmp3lame', '-b:a', '128k',
                '-metadata', 'comment=Built with Fish Audio. AniCanto character explanation.', str(mp3)], check=True)
        encode(gain)
        if args.target_lufs is not None:
            public_loudness = measure_loudness(mp3)
            correction = args.target_lufs - float(public_loudness['input_i'])
            if abs(correction) > .15:
                # Calibrate the decoded MP3 once. Always encode from the preserved PCM.
                gain = round(gain + min(correction, -2 - float(public_loudness['input_tp'])), 2)
                encode(gain)
                public_loudness = measure_loudness(mp3)
        subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(mp3), '-f', 'null', '-'], check=True)
        receipts.append(dict(id=row['id'], locale=row['locale'], language=row['language'],
            source=str(source.relative_to(ROOT)), sourceSHA256=sha(source), selectedAttempt=row['attempt'],
            editedWAV=str(wav.relative_to(ROOT)), editedWAVSHA256=sha(wav), publicAudio=str(mp3.relative_to(ROOT)),
            publicSHA256=sha(mp3), seconds=len(output)/rate, cuts=cuts, retainedPCMExactlyPreserved=not bool(gain),
            retainedPCMExactlyPreservedBeforeGain=True, constantGainDB=gain, targetLUFS=args.target_lufs,
            sourceLoudness=loudness, publicLoudness=public_loudness,
            pitchChange=False, tempoChange=False, sourceUnchanged=sha(source)==row['audioSHA256']))
    receipt = dict(languageStandard='English, ASD-STE100 style.', recordings=receipts, count=len(receipts),
        lossyPublicEncoding='MP3, 128 kbit/s. No pitch or speed filter.', humanVoiceAcceptance='Not verified')
    (WORK / 'package-receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(dict(count=len(receipts), shortenedGaps=sum(len(r['cuts'])for r in receipts),
        totalSeconds=round(sum(r['seconds']for r in receipts),2))))


if __name__ == '__main__':
    main()
