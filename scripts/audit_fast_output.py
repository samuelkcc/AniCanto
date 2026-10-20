#!/usr/bin/env python3
"""Read-only audit of a completed export. Never loads an AI model or changes a job.

Decoder completion and file existence do not establish audible speech. Measure
the delivered isolated takes and report tempo separately from content/identity.
"""
import argparse
import array
import hashlib
import html
import json
import math
from pathlib import Path
import subprocess
import wave


def read(path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return default


def signal(path):
    try:
        with wave.open(str(path)) as audio:
            if audio.getsampwidth() != 2:
                return dict(status='unsupported-pcm')
            samples = array.array('h', audio.readframes(audio.getnframes()))
            peak = max((abs(x) for x in samples), default=0)
            rms = math.sqrt(sum(x*x for x in samples)/max(1, len(samples)))
            return dict(status='near-silent' if peak <= 32 else 'signal-present',
                        peakDB=round(20*math.log10(max(1, peak)/32768), 2),
                        rmsDB=round(20*math.log10(max(.001, rms)/32768), 2),
                        seconds=audio.getnframes()/audio.getframerate())
    except (OSError, EOFError, wave.Error):
        return dict(status='unreadable')


def audit(job, output=None):
    job = Path(job).resolve()
    report = read(job/'report.json', {})
    review = read(job/'review.json', {})
    cfg = review.get('config', {})
    output = Path(output or report.get('exportedOutput') or report['output'])
    tracks = report.get('tracks') or [dict(engine=cfg.get('ttsBackend'), language=cfg.get('targetLanguage', 'yue'), report=str(job/'report.json'))]
    result = dict(job=str(job), output=str(output), outputExists=output.is_file(),
                  processingSeconds=report.get('processingSeconds'),
                  milestones=report.get('milestones', []), productionMode=cfg.get('productionMode'),
                  contentReviewed=False, voiceIdentityReviewed=False, tracks=[])
    for track in tracks:
        folder = Path(track['report']).parent
        cues = read(folder/'review.json', review).get('cues', [])
        timing = {r['index']: r for r in read(folder/'timing.json', [])}
        rows = []
        for n, cue in enumerate(cues):
            if not cue.get('enabled', True):
                continue
            index = cue.get('reviewIndex', n)+1
            delivery = timing.get(index, {})
            field = 'english' if track.get('language') == 'en' and 'english' in cue else 'cantonese'
            row = dict(index=index, start=cue['start'], end=cue['end'],
                       japanese=cue.get('japanese') or cue.get('text', ''),
                       caption=cue.get('subtitleHint', ''), script=cue.get(field, ''),
                       captionSpeechRescue=bool(cue.get('captionSpeechRescue')),
                       rate=delivery.get('rate', 1), rawSeconds=delivery.get('seconds'),
                       renderedSeconds=delivery.get('renderedSeconds', 0),
                       signal=signal(delivery.get('renderedAudio', '')),
                       deadlineViolation=bool(delivery.get('renderedEnd', 0) > cue.get('speechEnd', cue['end'])+.001))
            row['missingScript'] = not row['script'].strip()
            row['missingAudio'] = row['missingScript'] or delivery.get('skipped', False) or row['signal']['status'] != 'signal-present'
            rows.append(row)
        generations = [read(p, {}) for p in folder.glob('*.generation.json')]
        profiles = report.get('voiceProfiles', review.get('config', {}).get('voiceProfiles', []))
        result['tracks'].append(dict(engine=track.get('engine'), language=track.get('language'),
            total=len(rows), missingScripts=[r['index'] for r in rows if r['missingScript']],
            missingOrNearSilentAudio=[r['index'] for r in rows if r['missingAudio']],
            compressionCounts={str(k): sum(r['rate'] > k for r in rows) for k in (1.5, 2, 3, 4)},
            deadlineViolations=[r['index'] for r in rows if r['deadlineViolation']],
            completedDecoders=sum(g.get('status') == 'completed' for g in generations),
            decoderRetries=sum(len(g.get('recoveryAttempts', [])) for g in generations),
            sourceReferenceCount=sum(p.get('identityStatus') == 'independent' for p in profiles),
            shortSourceReferenceCount=sum(p.get('shortReference', False) for p in profiles), rows=rows))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('job', type=Path)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--decode', action='store_true')
    parser.add_argument('--samples', action='store_true')
    args = parser.parse_args()
    destination = args.destination.resolve()
    job = args.job.resolve()
    if destination == job or job in destination.parents:
        parser.error('The audit destination must be outside the original job.')
    destination.mkdir(parents=True, exist_ok=True)
    before = hashlib.sha256((job/'review.json').read_bytes()).hexdigest()
    result = audit(job)
    cfg = read(job/'review.json')['config']
    ffmpeg, ffprobe = cfg['ffmpeg'], cfg['ffprobe']
    command = lambda cmd, **kw: subprocess.run([str(x) for x in cmd], check=True, capture_output=True, **kw)
    metadata = json.loads(command([ffprobe, '-v', 'error', '-show_streams', '-show_format', '-of', 'json', result['output']]).stdout)
    result['container'] = dict(duration=float(metadata['format']['duration']), bytes=int(metadata['format']['size']),
        streams=[dict(index=s['index'], type=s['codec_type'], codec=s.get('codec_name'),
                      language=s.get('tags', {}).get('language'), title=s.get('tags', {}).get('title')) for s in metadata['streams']])
    if args.decode:
        checked = subprocess.run([ffmpeg, '-v', 'error', '-xerror', '-i', result['output'], '-map', '0:v', '-map', '0:a', '-f', 'null', '-'], capture_output=True)
        result['fullDecode'] = dict(passed=checked.returncode == 0, errors=checked.stderr.decode(errors='replace')[-5000:])
    samples = []
    if args.samples:
        rows = result['tracks'][0]['rows']
        selected = set(result['tracks'][0]['missingOrNearSilentAudio'])
        selected.update(r['index'] for r in sorted(rows, key=lambda r: r['rate'], reverse=True)[:6])
        selected.add(1)
        for row in rows:
            if row['index'] not in selected:
                continue
            start, duration = max(0, row['start']-.15), max(1, row['end']-row['start']+.3)
            pair = dict(row)
            for name, track in [('dub', '0:a:0'), ('original', '0:a:1')]:
                target = destination/f"{row['index']:03d}-{name}.m4a"
                command([ffmpeg, '-v', 'error', '-y', '-ss', start, '-i', result['output'], '-t', duration,
                         '-map', track, '-vn', '-c:a', 'aac', '-b:a', '128k', target])
                pair[name] = target.name
            samples.append(pair)
    result['reviewUnchanged'] = before == hashlib.sha256((job/'review.json').read_bytes()).hexdigest()
    (destination/'audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    e = html.escape
    cards = ''.join(f"<article><h3>#{r['index']} · {r['start']:.2f}–{r['end']:.2f}s · {r['rate']:.2f}×</h3>"
                    f"<p>日文：{e(r['japanese'])}<br>原字幕：{e(r['caption'])}<br>配音稿：{e(r['script'])}</p>"
                    f"<label>成品廣東話音軌 <audio controls preload='none' src='{r['dub']}'></audio></label>"
                    f"<label>成品日文原聲音軌 <audio controls preload='none' src='{r['original']}'></audio></label></article>" for r in samples)
    (destination/'index.html').write_text("<!doctype html><meta charset='utf-8'><title>EP08 output audit</title>"
        "<style>body{font:16px system-ui;max-width:1080px;margin:40px auto;background:#f5f6f8;color:#222}"
        "article{background:white;border:1px solid #ddd;border-radius:12px;padding:20px;margin:16px 0}"
        "label{display:inline-flex;flex-direction:column;gap:8px;margin-right:30px}p{line-height:1.8}</style>"
        "<h1>EP08 高速模式成品核對</h1><p>原成品及工作資料保持原狀。以下係風險抽樣，唔代表逐句語意、聲線或語言已通過覆核。"
        "片段取自成品兩條音軌；廣東話音軌包含背景聲，隔離人聲嘅近靜音證據見 audit.json。</p>"+cards)
    print(json.dumps({k: v for k, v in result.items() if k != 'tracks'}, ensure_ascii=False))
    for track in result['tracks']:
        print(json.dumps({k: v for k, v in track.items() if k != 'rows'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
