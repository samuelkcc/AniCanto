"""Refresh film artwork. Copy the accepted compressed audio without encoding it."""
from pathlib import Path
import importlib.util
import hashlib
import json
import subprocess
import time

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / '.build/website-visual-refresh-2026-10-29'
PUBLIC = ROOT / 'website/media'
SOURCE = WORK / 'before-shion-promo.mp4'
ACCEPTED_SHA = 'c23f20e9a1fd6816046764d56b498d6dd84e4dbfdf03d5abf64403910e74b809'


def audio_bytes(path, decoded=False):
    output = ['-c:a', 'pcm_f32le', '-f', 'f32le'] if decoded else ['-c:a', 'copy', '-f', 'adts']
    return subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-map', '0:a:0', *output, 'pipe:1'])


def main():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == ACCEPTED_SHA
    spec = importlib.util.spec_from_file_location('website_art', ROOT / 'scripts/build-website-promo.py')
    art = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(art)
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
    timeline = json.loads((ROOT / '.build/website-promo-learning-2026-10-28/timeline.json').read_text())
    rows, duration = timeline['scenes'], timeline['duration']
    assert duration == 34
    mix = np.fromfile(ROOT / '.build/website-cantonese-pronunciation-2026-10-29/opening-fixed-audio.f32', dtype=np.float32).reshape(-1, 2)
    assert len(mix) == duration * art.RATE
    background = art.make_background()
    actor = Image.open(ROOT / 'website/assets/web-shion-film-v3.png').convert('RGBA')
    boundaries = [2.0] + [row['end'] for row in rows]

    def picture(seconds):
        if seconds < 2:
            state = ('ja', seconds, 0, True, False)
        elif seconds >= rows[-1]['end']:
            state = ('zh', seconds - rows[-1]['end'], 3, False, True)
        else:
            index = next(i for i, row in enumerate(rows) if row['start'] <= seconds < row['end'])
            row = rows[index]
            state = (row['language'], seconds - row['start'], index, False, False)
        distance = min(abs(seconds - edge) for edge in boundaries)
        opacity = min(art.ease(seconds / .6), art.ease(distance / .45))
        return art.render_frame(seconds, background, actor, mix, scene=state, text_opacity=opacity)

    picture(.8).save(PUBLIC / 'shion-promo-poster.jpg', quality=94)
    for label, second in [('opening', .8), ('japanese', 4), ('cantonese', 11), ('english', 19), ('mandarin', 26), ('closing', 32)]:
        picture(second).save(WORK / f'{label}.jpg', quality=94)
    pending = WORK / 'visual-refresh.pending.mp4'
    began = time.monotonic()
    with (WORK / 'render.log').open('w') as log:
        process = subprocess.Popen(['ffmpeg', '-y', '-v', 'warning', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
            '-s', '1280x720', '-r', str(art.FPS), '-i', 'pipe:0', '-i', str(SOURCE),
            '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'libx264', '-preset', 'fast', '-crf', '20',
            '-pix_fmt', 'yuv420p', '-c:a', 'copy', '-map_metadata', '1',
            '-metadata', 'comment=Demo voices: AniCanto Desktop / Drama3. Built with Fish Audio.',
            '-movflags', '+faststart', '-t', str(duration), str(pending)], stdin=subprocess.PIPE, stderr=log)
        for n in range(duration * art.FPS):
            process.stdin.write(picture(n / art.FPS).tobytes())
            if n % (10 * art.FPS) == 0:
                print('RENDER_SECONDS', n // art.FPS, flush=True)
        process.stdin.close()
        assert process.wait() == 0, 'Read render.log'
    subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(pending), '-f', 'null', '-'], check=True)
    before, after = audio_bytes(SOURCE), audio_bytes(pending)
    assert before == after, 'Compressed audio changed'
    assert audio_bytes(SOURCE, True) == audio_bytes(pending, True), 'Decoded audio changed'
    pending.replace(PUBLIC / 'shion-promo.mp4')
    art.save(WORK / 'render-receipt.json', dict(languageStandard='English, ASD-STE100 style.',
        duration=duration, width=1280, height=720, fps=art.FPS, frames=duration * art.FPS,
        sourceMovieSHA256=ACCEPTED_SHA, movieSHA256=art.sha(PUBLIC / 'shion-promo.mp4'),
        compressedAudioEqual=True, decodedAudioEqual=True,
        audioADTS_SHA256=hashlib.sha256(after).hexdigest(),
        audioRegenerated=False, subtitleFilesChanged=False,
        renderSeconds=round(time.monotonic() - began, 2)))
    print('MOVIE_READY', duration, flush=True)


if __name__ == '__main__':
    main()
