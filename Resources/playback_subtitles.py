"""Read-only movie subtitle tracks, independent of conversion and ASR clocks."""
import hashlib,json,subprocess
from pathlib import Path
TEXT={'subrip','srt','ass','ssa','webvtt','mov_text','text'}
REVISION='movie-subtitles-1'

def read(root,row,tools,choice='auto',output=False):
 source=Path((row.get('output') if output else row.get('video')) or '').resolve()
 if not source.is_file():raise ValueError('The selected media file is missing.')
 st=source.stat();identity=[REVISION,str(source),st.st_size,st.st_mtime_ns]
 directory=Path(root)/'cache/player-subtitles'/hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:24];directory.mkdir(parents=True,exist_ok=True)
 from atomic_files import write_json
 info_path=directory/'streams.json'
 if info_path.is_file():info=json.loads(info_path.read_text())
 else:
  p=subprocess.run([tools['ffprobe'],'-v','error','-show_format','-show_streams','-of','json',str(source)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=30)
  info=json.loads(p.stdout);write_json(info_path,info)
 tracks=[dict(id='embedded:'+str(s['index']),index=s['index'],title=s.get('tags',{}).get('title') or s.get('tags',{}).get('language') or str(s['index']),codec=s.get('codec_name'),supported=s.get('codec_name') in TEXT,default=bool(s.get('disposition',{}).get('default'))) for s in info.get('streams',[]) if s.get('codec_type')=='subtitle']
 external=Path(row['externalSubtitle']).resolve() if row.get('externalSubtitle') else None
 if external and external.is_file():tracks.append(dict(id='external',title=external.name,supported=True,default=True))
 result=dict(tracks=tracks,streams=info.get('streams',[]),cues=[],selected='off')
 if choice in ('list','off'):return result
 if choice=='auto':choice='external' if external and external.is_file() else next((x['id'] for x in tracks if x['supported'] and x['default']),next((x['id'] for x in tracks if x['supported']),'off'))
 if choice=='off':return result
 selected=next((x for x in tracks if x['id']==choice),None)
 if not selected or not selected['supported']:raise ValueError('This subtitle track is unavailable or uses image subtitles unsupported by this player.')
 if choice=='external':
  if external.stat().st_size>16*1024*1024:raise ValueError('The subtitle file exceeds 16 MB.')
  raw=external.read_bytes();key=hashlib.sha256(raw).hexdigest();input_file=external;stream='0:s:0'
 else:key=choice.split(':')[1];input_file=source;stream='0:'+str(selected['index'])
 cached=directory/('captions-'+key+'.json')
 if cached.is_file():cues=json.loads(cached.read_text())
 else:
  p=subprocess.run([tools['ffmpeg'],'-v','error','-nostdin','-i',str(input_file),'-map',stream,'-f','srt','pipe:1'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
  if p.returncode:raise ValueError('Could not read this subtitle track. Select another track or import a text subtitle file.')
  if len(p.stdout)>16*1024*1024:raise ValueError('The subtitle track exceeds 16 MB.')
  from worker import parse_srt
  cues=parse_srt(p.stdout.decode('utf-8-sig'));write_json(cached,cues)
 # External subtitles use source clocks. Translate only the playback clock
 # when viewing an exported excerpt; never alter the imported file or job.
 if output and choice=='external':
  review_path=Path(row.get('review') or Path(root)/'nonexistent')
  review=json.loads(review_path.read_text()) if review_path.is_file() else {}
  offset=float(review.get('config',{}).get('startOffset') or 0)
  cues=[dict(x,start=max(0,x['start']-offset),end=x['end']-offset) for x in cues if x['end']>offset]
 return dict(result,cues=cues,selected=choice)
