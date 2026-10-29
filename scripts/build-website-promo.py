"""Build the website film from approved Shion audio and silhouette artwork.

The script does not run a speech model. It does not change application media.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import subprocess
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / '.build/website-promo-2026-10-28'
PUBLIC = ROOT / 'website/media'
SOURCE = ROOT / 'mobile/DemoAssets/v19/desktop.mp4'
ACTOR = ROOT / 'website/assets/silhouette-shion-mic.png'
WIDTH, HEIGHT, FPS, RATE, DURATION = 1280, 720, 24, 44100, 90
ORDER = ['ja', 'yue', 'en', 'zh']
STREAMS = {'ja': 3, 'yue': 0, 'en': 1, 'zh': 2}
FONTS = {
    'en': '/System/Library/Fonts/Supplemental/Arial.ttf',
    'bold': '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
    'zh': '/System/Library/Fonts/STHeiti Medium.ttc',
    'ja': '/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc',
}
FONT_CACHE = {}
INTRO_TITLE = ['你的動畫，', '另一種聲音。']
OUTRO_TITLE = ['下一幕，', '換你開口。']
INTRO_SUBTITLE = 'ONE STORY. FOUR LANGUAGES.'
INTRO_NOTE = '一段故事，四種語言。'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def font(kind, size):
    key = kind, size
    if key not in FONT_CACHE:
        FONT_CACHE[key] = ImageFont.truetype(FONTS[kind], size)
    return FONT_CACHE[key]


def ease(value):
    x = max(0, min(1, value))
    return x * x * (3 - 2 * x)


def stamp(seconds, separator='.'):
    ms = round(seconds * 1000)
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f'{h:02}:{m:02}:{s:02}{separator}{ms:03}'


def prepare_audio():
    before = sha(SOURCE)
    mix = np.zeros((DURATION * RATE, 2), dtype=np.float32)
    clips, receipts = {}, []
    for index, language in enumerate(ORDER):
        raw = subprocess.check_output([
            'ffmpeg', '-v', 'error', '-i', str(SOURCE), '-map', f'0:a:{STREAMS[language]}',
            '-t', '20', '-c:a', 'pcm_f32le', '-f', 'f32le', 'pipe:1',
        ])
        audio = np.frombuffer(raw, dtype='<f4').reshape(-1, 2)
        assert audio.shape == (RATE * 20, 2)
        assert np.isfinite(audio).all()
        start = 3 + index * 20
        mix[start * RATE:(start + 20) * RATE] = audio
        assert np.array_equal(mix[start * RATE:(start + 20) * RATE], audio)
        clips[language] = audio
        receipts.append(dict(language=language, speaker='Shion', sourceStart=0, sourceEnd=20,
                             filmStart=start, filmEnd=start + 20,
                             decodedPCM_SHA256=hashlib.sha256(raw).hexdigest(),
                             insertedPCMIsIdentical=True, pitchChange=False, tempoChange=False,
                             synthesis=False, equalisation=False, normalisation=False))
    mix.astype('<f4').tofile(WORK / 'audio.f32')
    save(WORK / 'voice-preservation.json', dict(
        languageStandard='English, ASD-STE100 style.', source=str(SOURCE.relative_to(ROOT)),
        sourceSHA256=before, sourceSHA256After=sha(SOURCE), sourceUnchanged=before == sha(SOURCE),
        duration=DURATION, sampleRate=RATE, channels=2, clips=receipts,
        scope='Decoded approved audio enters the new timeline unchanged. Final AAC encoding is lossy.',
        newVoiceSynthesis=False, applicationMediaChanged=False))
    return mix


def prepare_captions():
    plan = json.loads((ROOT / '.build/demo-candidate-v19-2026-10-25/restoration.json').read_text())
    translations = json.loads((ROOT / '.build/demo-candidate-v19-2026-10-25/translations.json').read_text())
    story = json.loads((ROOT / 'mobile/Design/DemoFilm/v15/storyboard.json').read_text())
    rows = []
    for index, spoken in enumerate(ORDER):
        offset = 3 + index * 20
        for cue in plan['cues'][:3]:
            i = cue['id']
            tr = translations[i]
            original = story['lines'][i]['ja'] if spoken == 'ja' else tr['zh_Hans' if spoken == 'zh' else spoken]
            rows.append(dict(start=offset + cue['start'], end=offset + cue['end'] + .35,
                             spokenLanguage=spoken, speaker='Shion', original=original,
                             translations={'zh-HK': tr['zh_Hant'], 'zh-Hans': tr['zh_Hans'],
                                           'en': tr['en'], 'ja': story['lines'][i]['ja']}))
    save(WORK / 'caption-timeline.json', dict(languageStandard='English, ASD-STE100 style.', cues=rows))
    for language in ['zh-HK', 'zh-Hans', 'en', 'ja']:
        blocks = ['WEBVTT', '']
        srt = []
        for i, row in enumerate(rows):
            same_language = ((language == 'ja' and row['spokenLanguage'] == 'ja')
                             or (language == 'en' and row['spokenLanguage'] == 'en')
                             or (language == 'zh-HK' and row['spokenLanguage'] == 'yue')
                             or (language == 'zh-Hans' and row['spokenLanguage'] == 'zh'))
            text = row['original']
            if not same_language and row['translations'][language] != text:
                text += '\n' + row['translations'][language]
            blocks.extend([str(i + 1), f'{stamp(row["start"])} --> {stamp(row["end"])}', text, ''])
            srt.extend([str(i + 1), f'{stamp(row["start"], ",")} --> {stamp(row["end"], ",")}', text, ''])
        (PUBLIC / f'shion-promo.{language}.vtt').write_text('\n'.join(blocks))
        (WORK / f'shion-promo.{language}.srt').write_text('\n'.join(srt))
    return rows


def make_background():
    yy, xx = np.mgrid[0:HEIGHT, 0:WIDTH]
    glow = np.clip(1 - np.sqrt(((xx - 960) / 950) ** 2 + ((yy - 260) / 670) ** 2), 0, 1)
    array = np.zeros((HEIGHT, WIDTH, 3), dtype=np.float32) + [14, 10, 25]
    array += glow[..., None] * [34, 18, 53]
    image = Image.fromarray(np.uint8(array)).convert('RGBA')
    draw = ImageDraw.Draw(image)
    for x in range(-HEIGHT, WIDTH, 52):
        draw.line((x, HEIGHT, x + HEIGHT, 0), fill=(29, 21, 42, 255), width=1)
    return image


TITLES = {
    'ja': ('JAPANESE / 日本語', ['物語は、', '声で近づく。'], 'ja', '先聽見，原來的心動。', 'ORIGINAL FEELING'),
    'yue': ('CANTONESE / 香港廣東話', ['熟悉的話，', '熟悉的感覺。'], 'zh', '同一個故事，另一種親切。', 'A LITTLE CLOSER TO HOME'),
    'en': ('ENGLISH / 英語', ['The same story.', 'Another voice.'], 'bold', 'One voice. Another way to connect.', 'MAKE THE WORDS YOURS'),
    'zh': ('MANDARIN / 普通話', ['换一种语言，', '听见另一种心动。'], 'zh', '故事的溫度，可以跨越語言。', 'FOUR LANGUAGES. ONE SHION.'),
}


def text(draw, xy, value, kind, size, fill, width=None):
    while width and size > 15 and draw.textlength(value, font=font(kind, size)) > width:
        size -= 1
    draw.text(xy, value, font=font(kind, size), fill=fill, stroke_width=0)


def render_frame(seconds, background, actor, mix, scene=None, text_opacity=None):
    frame = background.copy()
    draw = ImageDraw.Draw(frame)
    if seconds < 3:
        language, local, index = 'ja', seconds, 0
    elif seconds < 83:
        index = min(3, int((seconds - 3) // 20))
        language, local = ORDER[index], (seconds - 3) % 20
    else:
        language, local, index = 'yue', seconds - 83, 3
    closing = seconds >= 83
    opening = seconds < 3
    if scene is not None:
        language, local, index, opening, closing = scene
    fade = ease(local / .7)
    accent = (213, 192, 255, 255) if index < 2 else (187, 224, 209, 255)
    # The animated lines and rings are new vector composition.
    radius = 270 + 14 * math.sin(seconds * .22)
    for add in [0, 22, 45]:
        draw.ellipse((970 - radius - add, 318 - radius - add, 970 + radius + add, 318 + radius + add),
                     outline=(51, 35, 73, 255), width=1)
    text(draw, (53, 31), 'AniCanto', 'bold', 31, (244, 239, 249, 255))
    text(draw, (55, 77), 'A LOCAL AI DUBBING STORY', 'en', 10, (160, 145, 184, 255))
    draw.line((54, 109, WIDTH - 54, 109), fill=(47, 33, 63, 255))
    text(draw, (1010, 39), '紫音 / SHION', 'zh', 17, accent)
    text(draw, (1029, 70), 'THE STUDIO COMPANION', 'en', 8, (160, 145, 184, 255))
    # The source artwork has no facial features.
    actor_height = round(650 * (1 + .018 * math.sin(seconds * .62)))
    art = actor.resize((round(actor.width * actor_height / actor.height), actor_height), Image.Resampling.BICUBIC)
    x = 776 if text_opacity is not None else 776 + round((1 - fade) * 50)
    y = 118 + round(2.0 * math.sin(seconds * .8))
    frame.alpha_composite(art, (x, y))
    title_layer = Image.new('RGBA', frame.size) if text_opacity is not None else None
    draw = ImageDraw.Draw(title_layer if title_layer is not None else frame)
    if opening:
        text(draw, (56, 173), INTRO_TITLE[0], 'zh', 61, (245, 239, 248, 255), 700)
        text(draw, (56, 263), INTRO_TITLE[1], 'zh', 61, accent, 700)
        text(draw, (60, 374), INTRO_SUBTITLE, 'bold', 20, (190, 222, 210, 255), 700)
        text(draw, (60, 426), INTRO_NOTE, 'zh', 22, (190, 178, 204, 255))
    elif closing:
        text(draw, (56, 165), OUTRO_TITLE[0], 'zh', 64, (245, 239, 248, 255))
        text(draw, (56, 260), OUTRO_TITLE[1], 'zh', 64, accent)
        text(draw, (60, 370), 'YOUR STORY. ANOTHER VOICE.', 'bold', 19, (190, 222, 210, 255))
        text(draw, (60, 424), 'anicanto.com', 'bold', 34, (245, 239, 248, 255))
        text(draw, (61, 487), 'macOS / Windows Beta', 'en', 17, (190, 178, 204, 255))
        text(draw, (61, 517), 'iPad / iPhone — Coming soon', 'en', 17, (190, 178, 204, 255))
    else:
        label, title, kind, subline, note = TITLES[language]
        text(draw, (58, 150), f'0{index + 1} / {label}', 'zh', 15, accent)
        entry = 0 if text_opacity is not None else round((1 - fade) * 22)
        for line_index, line in enumerate(title):
            text(draw, (56 + entry, 212 + line_index * 91), line, kind, 62, (244, 239, 248, 255), 700)
        text(draw, (60, 419), subline, 'en' if language == 'en' else 'zh', 21, accent, 700)
        text(draw, (60, 467), note, 'en', 10, (164, 148, 188, 255))
        # The bars use the retained audio envelope.
        n = round(seconds * RATE)
        audio = mix[n:min(len(mix), n + RATE // 24)]
        level = float(np.sqrt(np.mean(audio * audio))) if len(audio) else 0
        strength = min(1, level / .08)
        for bar in range(57):
            wave = abs(math.sin(bar * 1.23 + seconds * 2.2) * math.cos(bar * .27 - seconds))
            height = 3 + strength * (10 + wave * 42)
            bx = 60 + bar * 9
            draw.rounded_rectangle((bx, 536 - height / 2, bx + 3, 536 + height / 2), radius=1, fill=accent)
    if title_layer is not None:
        opacity = max(0, min(1, text_opacity))
        title_layer.putalpha(title_layer.getchannel('A').point(lambda alpha: round(alpha * opacity)))
        frame.alpha_composite(title_layer)
    # The caption area stays clear for the matching browser subtitle track.
    overlay = Image.new('RGBA', frame.size)
    od = ImageDraw.Draw(overlay)
    od.rectangle((0, 578, WIDTH, HEIGHT), fill=(13, 9, 23, 235))
    od.line((54, 578, WIDTH - 54, 578), fill=(160, 126, 206, 75))
    frame.alpha_composite(overlay)
    draw = ImageDraw.Draw(frame)
    for i, badge in enumerate(['JA', 'YUE', 'EN', 'ZH']):
        bx = 60 + i * 64
        color = accent if i == index else (92, 77, 113, 255)
        draw.rectangle((bx, 689, bx + 42, 691), fill=color)
        text(draw, (bx, 667), badge, 'en', 10, color)
    text(draw, (892, 677), 'Built with Fish Audio', 'en', 12, (164, 148, 188, 255))
    text(draw, (60, 622), 'Same Shion. Four languages. / 同一位紫音，四種語言。', 'zh', 16,
         (190, 178, 204, 255)) if opening or closing else None
    return frame.convert('RGB')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stills', action='store_true')
    args = parser.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    mix = prepare_audio()
    cues = prepare_captions()
    background = make_background()
    actor = Image.open(ACTOR).convert('RGBA')
    for t in [.8, 9, 29, 49, 69, 86]:
        render_frame(t, background, actor, mix).save(WORK / f'frame-{t:04.1f}.jpg', quality=94)
    render_frame(.8, background, actor, mix).save(PUBLIC / 'shion-promo-poster.jpg', quality=94)
    if args.stills:
        print('STILLS_READY', flush=True)
        return
    destination = PUBLIC / 'shion-promo.mp4'
    log = (WORK / 'ffmpeg-render.log').open('w')
    command = ['ffmpeg', '-y', '-v', 'warning', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
               '-s', f'{WIDTH}x{HEIGHT}', '-r', str(FPS), '-i', 'pipe:0',
               '-f', 'f32le', '-ar', str(RATE), '-ac', '2', '-i', str(WORK / 'audio.f32'),
               '-c:v', 'libx264', '-preset', 'fast', '-crf', '20', '-pix_fmt', 'yuv420p',
               '-c:a', 'aac', '-b:a', '192k', '-metadata:s:a:0', 'language=mul',
               '-movflags', '+faststart', '-t', str(DURATION), str(destination)]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=log)
    began = time.monotonic()
    try:
        for frame in range(DURATION * FPS):
            picture = render_frame(frame / FPS, background, actor, mix)
            process.stdin.write(picture.tobytes())
            if frame % (FPS * 10) == 0:
                print('RENDER_SECONDS', frame // FPS, flush=True)
        process.stdin.close()
        if process.wait() != 0:
            raise RuntimeError('The video encoder failed. Read ffmpeg-render.log.')
    finally:
        log.close()
    save(WORK / 'render-receipt.json', dict(languageStandard='English, ASD-STE100 style.',
        duration=DURATION, width=WIDTH, height=HEIGHT, fps=FPS, frames=DURATION * FPS,
        actor='Shion', silhouetteOnly=True, spokenLanguages=ORDER,
        sourceSHA256=sha(SOURCE), artworkSHA256=sha(ACTOR), movieSHA256=sha(destination),
        bytes=destination.stat().st_size, captionCues=len(cues), renderSeconds=time.monotonic() - began,
        newVoiceSynthesis=False, appScreens=False, applicationMediaChanged=False,
        humanAcceptance='Not verified'))
    print('MOVIE_READY', destination, flush=True)


if __name__ == '__main__':
    main()
