"""Build a short website film from four newly recorded Shion performances."""
from pathlib import Path
import importlib.util
import argparse
import json
import math
import subprocess
import time

import numpy as np
import soundfile as sf
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / '.build/website-promo-short-2026-10-28'
PUBLIC = ROOT / 'website/media'
RATE, FPS = 44100, 24
spec = importlib.util.spec_from_file_location('website_film_art', ROOT / 'scripts/build-website-promo.py')
art = importlib.util.module_from_spec(spec)
spec.loader.exec_module(art)


def main():
    global WORK
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=WORK)
    args = parser.parse_args()
    WORK = args.work.resolve()
    script = WORK / 'script-copy.json'
    if not script.exists():
        script = ROOT / 'scripts/website-promo-short-copy.json'
    copy = json.loads(script.read_text())
    if copy.get('theme') == 'anime-language-learning':
        art.ACTOR = ROOT / 'website/assets/web-shion-studio-v2.png'
        art.INTRO_TITLE = ['從喜歡的動畫，', '學懂一句廣東話。']
        art.OUTRO_TITLE = ['每天一句，', '從興趣開始。']
        art.INTRO_SUBTITLE = 'ANIME. CANTONESE. YOUR OWN PACE.'
        art.INTRO_NOTE = '聽聲音，認識粵語文字。'
        art.TITLES = {
            'ja': ('JAPANESE / 日本語', ['好きなアニメで、', '広東語を学ぼう。'], 'ja', '從喜歡的故事開始。', 'YOUR INTEREST. YOUR FIRST WORD.'),
            'yue': ('CANTONESE / 香港廣東話', ['聽一句對白，', '認識粵語用字。'], 'zh', '逐句翻譯、重聽，慢慢學。', 'LISTEN. READ. LEARN.'),
            'en': ('ENGLISH / 英語', ['Understand a line.', 'Learn a little more.'], 'bold', 'English & Mandarin, side by side.', 'LEARNING AT YOUR PACE'),
            'zh': ('MANDARIN / 普通話', ['每天一句，', '学懂粤语声音与文字。'], 'zh', '讓喜歡的動畫，陪你學習。', 'A LITTLE CANTONESE, EVERY DAY.'),
        }
    rows = json.loads((WORK / 'takes.json').read_text())
    takes = {row['language']: row for row in rows}
    edits_path = WORK / 'audio-edits.json'
    edits = json.loads(edits_path.read_text())['edits'] if edits_path.exists() else {}
    offset, timeline, clips = 2.0, [], []
    for segment in copy['segments']:
        path = ROOT / takes[segment['language']]['audio']
        assert art.sha(path) == takes[segment['language']]['audioSHA256']
        edit = edits.get(segment['language'])
        if edit:
            assert art.sha(path) == edit['sourceSHA256']
            path = ROOT / edit['audio']
            assert art.sha(path) == edit['audioSHA256']
        pcm, rate = sf.read(path, dtype='float32')
        assert rate == RATE and pcm.ndim == 1
        # Keep the selected PCM samples. Add silence between language scenes.
        length = math.ceil((len(pcm) / RATE + .8) * FPS) / FPS
        row = dict(segment, start=offset, voiceEnd=offset + len(pcm) / RATE, end=offset + length)
        timeline.append(row)
        clips.append(pcm)
        offset += length
    duration = math.ceil(offset + 4)
    assert duration < 180
    mix = np.zeros((duration * RATE, 2), dtype=np.float32)
    for row, pcm in zip(timeline, clips):
        start = round(row['start'] * RATE)
        mix[start:start + len(pcm)] = pcm[:, None]
        assert np.array_equal(mix[start:start + len(pcm), 0], pcm)
    mix.tofile(WORK / 'audio.f32')
    for locale in ['zh-HK', 'zh-Hans', 'en', 'ja']:
        blocks = ['WEBVTT', '']
        for i, row in enumerate(timeline, 1):
            text = row['text']
            same = {'zh-HK': 'yue', 'zh-Hans': 'zh', 'en': 'en', 'ja': 'ja'}[locale] == row['language']
            if not same:
                text += '\n' + row['translations'][locale]
            blocks += [str(i), f'{art.stamp(row["start"])} --> {art.stamp(row["voiceEnd"] + .25)}', text, '']
        (PUBLIC / f'shion-promo.{locale}.vtt').write_text('\n'.join(blocks))
    art.save(WORK / 'timeline.json', dict(languageStandard='English, ASD-STE100 style.',
                                        duration=duration, scenes=timeline))
    background = art.make_background()
    actor = Image.open(art.ACTOR).convert('RGBA')
    boundaries = [2.0] + [row['end'] for row in timeline]

    def picture(seconds):
        if seconds < 2:
            state = ('ja', seconds, 0, True, False)
        elif seconds >= offset:
            state = ('zh', seconds - offset, 3, False, True)
        else:
            index = next(i for i, row in enumerate(timeline) if row['start'] <= seconds < row['end'])
            row = timeline[index]
            state = (row['language'], seconds - row['start'], index, False, False)
        distance = min(abs(seconds - boundary) for boundary in boundaries)
        opacity = min(art.ease(seconds / .6), art.ease(distance / .45))
        return art.render_frame(seconds, background, actor, mix, scene=state, text_opacity=opacity)

    picture(.8).save(PUBLIC / 'shion-promo-poster.jpg', quality=94)
    for i, row in enumerate(timeline):
        picture(row['start'] + 2).save(WORK / f'scene-{i}.jpg', quality=94)
    target = PUBLIC / 'shion-promo.mp4'
    pending = WORK / 'shion-promo.pending.mp4'
    began = time.monotonic()
    with (WORK / 'render.log').open('w') as log:
        process = subprocess.Popen(['ffmpeg', '-y', '-v', 'warning', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
            '-s', '1280x720', '-r', str(FPS), '-i', 'pipe:0', '-f', 'f32le', '-ar', str(RATE), '-ac', '2',
            '-i', str(WORK / 'audio.f32'), '-c:v', 'libx264', '-preset', 'fast', '-crf', '20', '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-b:a', '192k', '-metadata:s:a:0', 'language=mul',
            '-metadata', 'comment=New Shion advertising dialogue. Built with Fish Audio.',
            '-movflags', '+faststart', '-t', str(duration), str(pending)], stdin=subprocess.PIPE, stderr=log)
        for n in range(duration * FPS):
            process.stdin.write(picture(n / FPS).tobytes())
            if n % (FPS * 10) == 0:
                print('RENDER_SECONDS', n // FPS, flush=True)
        process.stdin.close()
        assert process.wait() == 0, 'Read render.log'
    subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(pending), '-f', 'null', '-'], check=True)
    pending.replace(target)
    art.save(WORK / 'render-receipt.json', dict(languageStandard='English, ASD-STE100 style.',
        duration=duration, width=1280, height=720, fps=FPS, frames=duration * FPS,
        newVoiceSynthesis=True, referenceVoices='Accepted Shion, one matching reference per language.',
        picture='Left-facing microphone Shion. No facial features or app screens.',
        audioPitchChange=False, audioTempoChange=False, completeNewTakesRetained=not bool(edits),
        completeSourceRecordingsPreserved=True, editorialAudioEdits=edits,
        movieSHA256=art.sha(target), bytes=target.stat().st_size, subtitleCuesPerLocale=4,
        applicationMediaChanged=False, renderSeconds=time.monotonic() - began,
        humanVoiceAcceptance='Not verified'))
    print('MOVIE_READY', duration, str(target), flush=True)


if __name__ == '__main__':
    main()
