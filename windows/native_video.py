"""Real encoder probes and a finite software fallback; track maps stay untouched."""
from functools import lru_cache

def command_for(command,name):
 from gpu import encoder_options
 out=[];i=0
 while i<len(command):
  if command[i] in ('-preset','-crf'):i+=2;continue
  out.append(name if command[i]=='libx264' else command[i]);i+=1
 return out[:-1]+encoder_options(name)+out[-1:]

def encode(run,command,cfg,emit):
 if 'libx264' not in command or cfg.get('videoAcceleration')=='software':return run(command)
 from gpu import adapters,encoder_candidates
 for name in encoder_candidates(adapters(),cfg.get('videoAcceleration','auto')):
  if name=='libx264':return run(command)
  try:
   run([cfg['ffmpeg'],'-v','error','-f','lavfi','-i','color=size=128x128:rate=1','-frames:v','1','-c:v',name,'-f','null','-'])
   emit('Video encoder',name+' hardware probe passed; preserving audio/subtitle maps.')
   return run(command_for(command,name))
  except RuntimeError as error:emit('Video encoder',name+' unavailable; completed recordings retained. '+str(error)[-200:])
 return run(command)
