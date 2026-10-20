"""Resumable pinned downloads with bounded retries and UI transfer telemetry."""
import collections
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import time
import sys


def emit_transfer(path, received, total, speed, attempt, state):
    eta = (total - received) / speed if total and speed > 0 else None
    transfer = dict(file=path.name, bytesReceived=received, totalBytes=total,
                    bytesPerSecond=speed, etaSeconds=max(0, eta) if eta is not None else None,
                    attempt=attempt, state=state)
    print(json.dumps(dict(stage='下載模型', message=path.name,
                          progress=min(1, received / total) if total else None,
                          download=transfer), ensure_ascii=False), flush=True)


def header_total(headers, offset):
    """Use the final redirect response, never an intermediate redirect body length."""
    responses = re.split(r'(?=HTTP/\S+ \d{3})', headers)
    final = responses[-1] if responses else ''
    match = re.search(r'content-range:\s*bytes\s+(?:\d+-\d+|\*)/(\d+)', final, re.I)
    if match:
        return int(match[1])
    match = re.search(r'content-length:\s*(\d+)', final, re.I)
    status = re.match(r'HTTP/\S+ (\d{3})', final)
    if match and status and int(status[1]) in (200, 206):
        return int(match[1]) + (offset if int(status[1]) == 206 else 0)
    return None


def sha(path,progress=None):
    h = hashlib.sha256()
    received=0;last=0;total=path.stat().st_size
    with path.open('rb') as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(block)
            received+=len(block);now=time.monotonic()
            if progress and (now-last>=.5 or received==total):progress(received,total);last=now
    return h.hexdigest()


def download(url, path, digest='', expected_size=None):
    if sys.platform=='win32':
        from downloads import download as native_download
        return native_download(url,path,digest,expected_size)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    def verified(candidate):
        if not candidate.is_file() or (expected_size and candidate.stat().st_size!=expected_size):return False
        emit_transfer(path,0,candidate.stat().st_size,0,1,'verifying')
        return not digest or sha(candidate,lambda n,total:emit_transfer(path,n,total,0,1,'verifying'))==digest
    if verified(path):
        emit_transfer(path,path.stat().st_size,path.stat().st_size,0,1,'reused');return
    part = path.with_name(path.name + '.partial')
    if digest and expected_size and part.is_file() and part.stat().st_size>=expected_size:
        if verified(part):
            part.replace(path);emit_transfer(path,expected_size,expected_size,0,1,'complete');return
        part.replace(part.with_name(part.name+f'.invalid-{time.time_ns()}'))
    total = expected_size
    for attempt in range(1, 6):
        offset = part.stat().st_size if part.exists() else 0
        emit_transfer(path, offset, total, 0, attempt, 'connecting')
        with tempfile.TemporaryFile() as errors, tempfile.NamedTemporaryFile() as headers:
            # HTTP/1.1 avoids the observed CDN HTTP/2 CANCEL. Retry manually so
            # each new request resumes the latest bytes and gets a fresh redirect.
            args = ['/usr/bin/curl', '--http1.1', '--fail', '--location', '--silent', '--show-error',
                    '--connect-timeout', '30', '--max-time', '7200', '--speed-time', '45',
                    '--speed-limit', '1024', '--continue-at', '-', '--dump-header', headers.name,
                    '--output', str(part), url]
            process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=errors)
            samples = collections.deque([(time.monotonic(), offset)])
            try:
                while process.poll() is None:
                    time.sleep(1)
                    now = time.monotonic()
                    received = part.stat().st_size if part.exists() else offset
                    samples.append((now, received))
                    while len(samples) > 2 and now - samples[0][0] > 8:
                        samples.popleft()
                    speed = max(0, received - samples[0][1]) / max(0.001, now - samples[0][0])
                    total = expected_size or header_total(Path(headers.name).read_text(errors='replace'), offset)
                    emit_transfer(path, received, total, speed, attempt, 'transferring' if speed else 'waiting')
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait()
            errors.seek(0)
            detail = errors.read().decode(errors='replace')[-1200:]
            code = process.returncode
        received = part.stat().st_size if part.exists() else 0
        # A previous request may have finished before interruption; still verify.
        if code == 0 or (code == 22 and total and received == total and digest and sha(part) == digest):
            break
        transient = code in (5, 6, 7, 18, 28, 35, 52, 55, 56, 92) or (code == 22 and re.search(r'\b(408|429|5\d\d)\b', detail))
        if not transient or attempt == 5:
            emit_transfer(path, received, total, 0, attempt, 'failed')
            reason = detail.strip().splitlines()[-1] if detail.strip() else f'curl exit {code}'
            raise RuntimeError(f'模型下載未完成：{path.name}；{reason}。已保留下載內容，按「校驗／修復」或重新下載即可續傳。')
        emit_transfer(path, received, total, 0, attempt, 'retrying')
        time.sleep(min(16, 2 ** (attempt - 1)))
    emit_transfer(path, received, total, 0, attempt, 'verifying')
    if not part.is_file() or (expected_size and received != expected_size) or (digest and sha(part,lambda n,total:emit_transfer(path,n,total,0,attempt,'verifying')) != digest):
        # Never load corrupt weights. Keep the rejected bytes for diagnosis.
        if part.is_file():part.replace(part.with_name(part.name + f'.invalid-{time.time_ns()}'))
        raise ValueError('模型大小或 SHA-256 校驗失敗，未載入模型。請重新部署。')
    part.replace(path)
    emit_transfer(path, received, total or received, 0, attempt, 'complete')
