"""Add optional tracks without replacing a verified movie on failure."""
from collections import Counter
import json
import math
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from export_picture import verify
from track_control import UserSkipped


REVISION = 'verified-desktop-packages-1'


def enabled(config):
    return config.get('exportPackageRevision') == REVISION


def _probe(config, run, path):
    return json.loads(run([config['ffprobe'], '-v', 'error', '-show_streams',
                           '-show_format', '-of', 'json', path]))


def package(config, run, emit, movie, destination, duration, source_streams, captions, metadata,
            *, required=False, burned=False):
    """Use one attempt per original track and one attempt per optional package."""
    from caption_tracks import labels
    movie = Path(movie)
    current = movie
    warnings = []
    accepted_originals = []
    embedded = []

    def warn(kind, error, **extra):
        if required:
            raise error
        warnings.append(dict(kind=kind, detail=str(error)[:1000], **extra))
        emit('輸出提示', '部分附加音軌或字幕未能封裝，已保留驗證通過的影片。')

    with TemporaryDirectory(prefix='export-packages-', dir=movie.parent) as scratch:
        folder = Path(scratch)
        for original in source_streams:
            index = original['index']
            track = folder / f'original-{index}.m4a'
            try:
                run([config['ffmpeg'], '-v', 'error', '-xerror', '-y',
                     '-ss', str(config.get('startOffset', 0)), '-i', config['video'],
                     '-map', f'0:{index}', '-t', str(config['duration']),
                     '-c:a', 'aac', '-b:a', '192k', track])
                stream = _probe(config, run, track)['streams'][0]
                if stream.get('codec_type') != 'audio' or not str(stream.get('nb_frames', '')).isdigit() or int(stream['nb_frames']) == 0:
                    raise ValueError('The original audio stream has no frames.')
                accepted_originals.append((original, track))
            except UserSkipped:
                raise
            except (OSError, RuntimeError, ValueError, IndexError) as error:
                warn('original-audio-stream', error, sourceStream=index)

        def adopt(extra, maps, codecs, audio, subtitle):
            nonlocal current
            candidate = folder / 'candidate.mp4'
            run([config['ffmpeg'], '-v', 'error', '-xerror', '-y', '-i', current,
                 *extra, '-map', '0', *maps, '-c', 'copy', *codecs,
                 '-t', str(duration), '-movflags', '+faststart', candidate])
            result = _probe(config, run, candidate)
            picture = verify(result['streams'], duration)
            actual_duration = float(result['format']['duration'])
            if not math.isfinite(actual_duration) or abs(actual_duration - duration) > .5:
                raise ValueError('The optional package changed the movie duration.')
            counts = [sum(s.get('codec_type') == kind for s in result['streams'])
                      for kind in ('audio', 'subtitle')]
            if counts != [audio, subtitle]:
                raise ValueError('The optional package has a missing track.')
            result['pictureRange'] = picture
            candidate.replace(destination)
            current = destination
            return result

        base_audio = sum(s.get('codec_type') == 'audio' for s in metadata['streams'])
        if accepted_originals:
            from source_language import iso_code
            selected_index = config.get('sourceAudioStream')
            if selected_index is None:
                selected_index = source_streams[0]['index']
            inputs, maps = [], []
            titles = [stream.get('tags', {}).get('title') or stream.get('tags', {}).get('handler_name')
                      or f'Original {position}' for position, (stream, _) in enumerate(accepted_originals, 1)]
            title_counts = Counter(title.casefold() for title in titles)
            for position, ((stream, file), title) in enumerate(zip(accepted_originals, titles), 1):
                inputs.extend(['-i', file])
                out = base_audio + position - 1
                tags = stream.get('tags', {})
                lang = tags.get('language', 'und')
                lang = lang if isinstance(lang, str) and re.fullmatch('[a-zA-Z]{3}', lang) else 'und'
                if lang.lower() == 'und' and stream['index'] == selected_index:
                    lang = iso_code(config.get('sourceLanguage', 'ja'))
                if title_counts[title.casefold()] > 1:
                    title = f'{title} ({position})'
                maps.extend(['-map', f'{position}:a:0', f'-disposition:a:{out}', '0',
                             f'-metadata:s:a:{out}', 'language=' + lang,
                             f'-metadata:s:a:{out}', 'handler_name=' + title])
            try:
                metadata = adopt(inputs, maps, [], base_audio + len(accepted_originals), 0)
            except UserSkipped:
                raise
            except (OSError, RuntimeError, ValueError) as error:
                warn('original-audio-package', error)
                accepted_originals.clear()

        if captions:
            inputs, maps = [], []
            for index, track in enumerate(captions):
                lang, title = labels(track)
                inputs.extend(['-i', track['path']])
                maps.extend(['-map', f'{index + 1}:s:0', f'-metadata:s:s:{index}',
                             'language=' + lang, f'-metadata:s:s:{index}', 'handler_name=' + title,
                             f'-disposition:s:{index}', 'default' if index == 0 and (track['mode'] == 'original' or not burned) else '0'])
            try:
                metadata = adopt(inputs, maps, ['-c:s', 'mov_text'],
                                 base_audio + len(accepted_originals), len(captions))
                embedded = captions
            except UserSkipped:
                raise
            except (OSError, RuntimeError, ValueError) as error:
                warn('embedded-subtitle-package', error)
    return current, metadata, [stream['index'] for stream, _ in accepted_originals], embedded, warnings
