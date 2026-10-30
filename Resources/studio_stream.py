"""Read bounded HLS segments from the source. Keep no video cache on disk.

The native host owns this process and its FFmpeg children. The service binds
only loopback, accepts one random capability path, and permits no file queries.
"""
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json,math,os,re,secrets,signal,subprocess,sys,threading,time

SEGMENT=6
MAX_BYTES=48*1024*1024
MAX_SEGMENTS=4
MAX_SEGMENT_BYTES=16*1024*1024

class Media:
    def __init__(self,config):
        self.source=config['source'];self.duration=float(config['duration'])
        if not math.isfinite(self.duration) or not 0<self.duration<86400:raise ValueError('Invalid movie duration.')
        self.ffmpeg=config['ffmpeg'];self.audio=config.get('audioStream')
        if self.audio is not None and (type(self.audio) is not int or self.audio<0):raise ValueError('Invalid audio stream.')
        self.count=math.ceil(self.duration/SEGMENT);self.token=secrets.token_urlsafe(32)
        self.lock=threading.Lock();self.cache=OrderedDict();self.last=time.monotonic()
    def playlist(self):
        rows=['#EXTM3U','#EXT-X-VERSION:3','#EXT-X-TARGETDURATION:6','#EXT-X-MEDIA-SEQUENCE:0','#EXT-X-PLAYLIST-TYPE:VOD','#EXT-X-INDEPENDENT-SEGMENTS']
        for n in range(self.count):
            if n:rows.append('#EXT-X-DISCONTINUITY')
            rows.extend([f'#EXTINF:{min(SEGMENT,self.duration-n*SEGMENT):.6f},',f'{n}.ts'])
        return ('\n'.join(rows+['#EXT-X-ENDLIST'])+'\n').encode()
    def command(self,n):
        start=n*SEGMENT;length=min(SEGMENT,self.duration-start)
        args=[self.ffmpeg,'-v','error','-nostdin','-threads','2','-ss',str(start),'-i',self.source,'-t',str(length),'-map','0:v:0']
        if self.audio is not None:args+=['-map',f'0:{self.audio}']
        else:args+=['-an']
        args+=['-vf',"scale=w='min(1280,iw)':h=-2,setsar=1",'-c:v','libx264','-preset','ultrafast','-crf','23','-tune','zerolatency','-threads','2','-filter_threads','1','-pix_fmt','yuv420p','-flags','+cgop','-g','48','-sc_threshold','0']
        if self.audio is not None:args+=['-c:a','aac','-b:a','160k','-ac','2']
        return args+['-sn','-dn','-output_ts_offset',str(start),'-muxdelay','0','-mpegts_flags','+resend_headers','-f','mpegts','pipe:1']
    def segment(self,n):
        if not 0<=n<self.count:raise ValueError('Invalid segment.')
        # One decoder per service. Concurrent duplicate requests share the result.
        with self.lock:
            if n in self.cache:
                self.cache.move_to_end(n);return self.cache[n]
            process=subprocess.Popen(self.command(n),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            errors=bytearray()
            def drain():
                for block in iter(lambda:process.stderr.read(4096),b''):
                    errors.extend(block);del errors[:-8192]
            reader=threading.Thread(target=drain,daemon=True);reader.start()
            expired=threading.Event()
            def deadline():expired.set();process.kill()
            timer=threading.Timer(25,deadline);timer.start();blocks=[];size=0
            try:
                for block in iter(lambda:process.stdout.read(65536),b''):
                    size+=len(block)
                    if size>MAX_SEGMENT_BYTES:raise ValueError('Source segment exceeded the memory limit.')
                    blocks.append(block)
                code=process.wait();reader.join(timeout=1)
                if expired.is_set():raise subprocess.TimeoutExpired(self.ffmpeg,25)
                if code:raise subprocess.CalledProcessError(code,self.ffmpeg,stderr=bytes(errors))
                output=b''.join(blocks)
                if not output:raise ValueError('Empty source segment.')
            finally:
                timer.cancel()
                if process.poll() is None:process.kill();process.wait()
                process.stdout.close();reader.join(timeout=1);process.stderr.close()
            self.cache[n]=output
            while len(self.cache)>MAX_SEGMENTS or sum(map(len,self.cache.values()))>MAX_BYTES:self.cache.popitem(last=False)
            return output

class Server(ThreadingHTTPServer):
    daemon_threads=True
    allow_reuse_address=False
    def __init__(self,media):
        self.media=media;super().__init__(('127.0.0.1',0),Handler)

class Handler(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def log_message(self,*args):pass
    def do_HEAD(self):self.serve(True)
    def do_GET(self):self.serve(False)
    def serve(self,head):
        media=self.server.media;prefix='/'+media.token+'/'
        if self.headers.get('Host')!=f'127.0.0.1:{self.server.server_port}' or not self.path.startswith(prefix):
            self.send_error(404);return
        name=self.path[len(prefix):];media.last=time.monotonic()
        try:
            if name=='index.m3u8':data=media.playlist();mime='application/vnd.apple.mpegurl'
            elif name=='status':data=b'{"ready":true}';mime='application/json'
            elif re.fullmatch(r'\d{1,5}\.ts',name):data=media.segment(int(name[:-3]));mime='video/mp2t'
            else:self.send_error(404);return
            self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.send_header('Access-Control-Allow-Origin','*');self.send_header('X-Content-Type-Options','nosniff');self.end_headers()
            if not head:self.wfile.write(data)
        except (subprocess.SubprocessError,OSError,ValueError):
            try:self.send_error(503,'Source playback segment unavailable')
            except (BrokenPipeError,ConnectionResetError):pass

def main():
    config=json.loads(sys.stdin.readline());owner=int(config['owner']);media=Media(config);server=Server(media)
    print(json.dumps(dict(url=f'http://127.0.0.1:{server.server_port}/{media.token}/index.m3u8',streamID=media.token)),flush=True)
    def watch():
        while True:
            time.sleep(2)
            try:os.kill(owner,0)
            except OSError:os.killpg(os.getpgrp(),signal.SIGTERM);os._exit(0)
            if time.monotonic()-media.last>600:os.killpg(os.getpgrp(),signal.SIGTERM);os._exit(0)
    threading.Thread(target=watch,daemon=True).start();server.serve_forever(poll_interval=.5)
if __name__=='__main__':main()
