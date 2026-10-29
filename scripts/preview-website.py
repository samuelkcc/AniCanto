"""Serve the isolated website with byte ranges for browser video seeking."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse
import re
import shutil

ROOT = Path(__file__).resolve().parents[1] / 'website'

class WebsiteHandler(SimpleHTTPRequestHandler):
    def send_head(self):
        self.byte_range = None
        path = Path(self.translate_path(self.path))
        if path.is_dir() or not self.headers.get('Range'):
            return super().send_head()
        try:
            stream = path.open('rb')
        except OSError:
            self.send_error(404)
            return None
        length = path.stat().st_size
        match = re.fullmatch(r'bytes=(\d*)-(\d*)', self.headers['Range'].strip())
        if not match or not any(match.groups()) or length == 0:
            stream.close()
            self.send_error(416)
            return None
        left, right = match.groups()
        if left:
            start, end = int(left), min(int(right) if right else length - 1, length - 1)
        else:
            start, end = max(0, length - int(right)), length - 1
        if start > end or start >= length:
            stream.close()
            self.send_response(416)
            self.send_header('Content-Range', f'bytes */{length}')
            self.end_headers()
            return None
        self.byte_range = (start, end)
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(str(path)))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Range', f'bytes {start}-{end}/{length}')
        self.send_header('Content-Length', str(end - start + 1))
        self.send_header('Last-Modified', self.date_time_string(path.stat().st_mtime))
        self.end_headers()
        stream.seek(start)
        return stream

    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        super().end_headers()

    def copyfile(self, source, outputfile):
        if self.byte_range is None:
            shutil.copyfileobj(source, outputfile)
            return
        remaining = self.byte_range[1] - self.byte_range[0] + 1
        while remaining:
            data = source.read(min(256 * 1024, remaining))
            if not data:
                break
            outputfile.write(data)
            remaining -= len(data)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=4179)
    args = parser.parse_args()
    handler = partial(WebsiteHandler, directory=str(ROOT))
    with ThreadingHTTPServer(('127.0.0.1', args.port), handler) as server:
        print(f'Local preview: http://127.0.0.1:{args.port}/', flush=True)
        server.serve_forever()
