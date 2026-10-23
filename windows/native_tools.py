"""Native equivalents of the platform media helpers, invoked without a shell."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;SHARED=HERE/'shared' if (HERE/'shared').is_dir() else HERE.parent/'Resources';sys.path.insert(0,str(SHARED))

def classifier_windows(samples,rate=16000):
 """Integer sample clocks avoid floating-point crumbs at the final hop.

 Kaldi's 25 ms analysis window requires 400 samples at 16 kHz. A residual
 sub-window fragment cannot yield meaningful features and is not a new event.
 Keep all substantial final windows with their exact source duration.
 """
 if rate<=0:raise ValueError('Invalid classification sample rate')
 hop=round(2.5*rate);window=round(5*rate);minimum=max(2,round(.025*rate))
 for start in range(0,len(samples),hop):
  clip=samples[start:start+window]
  if len(clip)<minimum:continue
  yield start/rate,min(hop,len(samples)-start)/rate,clip

def classifier(root):
 from transformers import AutoFeatureExtractor,AutoModelForAudioClassification
 folder=Path(root)/'models/audio-classifier'
 return AutoFeatureExtractor.from_pretrained(str(folder),local_files_only=True),AutoModelForAudioClassification.from_pretrained(str(folder),local_files_only=True).eval()
def classify(path):
 import numpy as np
 import soundfile as sf
 import torch
 from gpu import data_root
 from scipy.signal import resample_poly
 import math
 audio,sr=sf.read(path,dtype='float32',always_2d=True);audio=audio.mean(axis=1)
 if sr!=16000:
  g=math.gcd(sr,16000);audio=resample_poly(audio,16000//g,sr//g)
 if not np.isfinite(audio).all():raise ValueError('Audio classification input contains invalid samples')
 windows=iter(classifier_windows(audio));first=next(windows,None)
 if first is None:return []
 import itertools
 processor,model=classifier(data_root());rows=[]
 labels={int(k):str(v).lower() for k,v in model.config.id2label.items()}
 groups={'music':['music'],'singing':['singing'],'choir_singing':['choir'],'rapping':['rapping'],'speech':['speech','conversation','narration','monologue'],'laughter':['laughter','giggle','snicker'],'baby_laughter':['baby laughter'],'belly_laugh':['belly laugh'],'crying_sobbing':['crying','sobbing'],'sigh':['sigh'],'breathing':['breathing'],'gasp':['gasp'],'screaming':['screaming','scream'],'shout':['shout','shouting'],'yell':['yell','yelling']}
 torch.set_num_threads(4)
 for start,span,clip in itertools.chain((first,),windows):
  inputs=processor(clip,sampling_rate=16000,return_tensors='pt')
  with torch.inference_mode():scores=torch.sigmoid(model(**inputs).logits[0]).tolist()
  row=dict(start=round(float(start),3),duration=round(span,3))
  for key,words in groups.items():row[key]=max((scores[i] for i,label in labels.items() if any(w in label for w in words)),default=0)
  rows.append(row)
 return rows

def ocr(folder):
 import rapidocr_onnxruntime
 from rapidocr_onnxruntime import RapidOCR
 from ocr_licenses import install as preserve_ocr_terms
 from gpu import data_root
 preserve_ocr_terms(data_root(),Path(rapidocr_onnxruntime.__file__).parent)
 from PIL import Image
 import hashlib,time,os
 from atomic_files import write_json
 folder=Path(folder)
 paths=sorted(p for p in folder.iterdir() if p.suffix.lower() in ('.jpg','.jpeg','.png'))
 started=time.monotonic();rows=[];cache={};inferences=0
 def progress(completed):
  write_json(folder/'ocr-progress.json',dict(completed=completed,total=len(paths),
      seconds=round(time.monotonic()-started,3),inferences=inferences,
      reused=completed-inferences,backend='ONNX CPU',engine='RapidOCR 1.4.4'),indent=2)
 progress(0)
 # Three small ONNX sessions must not each monopolise every CPU thread.
 engine=RapidOCR(intra_op_num_threads=min(4,os.cpu_count() or 1),inter_op_num_threads=1)
 progress(0)
 for index,path in enumerate(paths):
  # Exact image-byte duplicates reuse OCR without guessing text similarity.
  digest=hashlib.sha256(path.read_bytes()).hexdigest()
  if digest in cache:
   rows.append(dict(index=index,**cache[digest]));progress(index+1);continue
  found,_=engine(str(path));inferences+=1
  accepted=[r for r in (found or []) if float(r[2])>=.5]
  with Image.open(path) as image:width,height=image.size
  boxes=[]
  for polygon,text,confidence in accepted:
   xs=[float(p[0]) for p in polygon];ys=[float(p[1]) for p in polygon]
   boxes.append(dict(text=str(text),confidence=float(confidence),x=max(0,min(xs)/width),
                     y=max(0,min(ys)/height),width=(max(xs)-min(xs))/width,height=(max(ys)-min(ys))/height))
  boxes.sort(key=lambda b:(round((b['y']+b['height']/2)*20),b['x']))
  result=dict(text=' '.join(b['text'] for b in boxes),boxes=boxes)
  rows.append(dict(index=index,**result));cache[digest]=result
  if len(cache)>256:cache.pop(next(iter(cache)))
  progress(index+1)
 return rows

def subtitles(path):
 from PIL import Image,ImageDraw,ImageFont
 cfg=json.loads(Path(path).read_text(encoding='utf-8'));folder=Path(cfg['folder']);folder.mkdir(parents=True,exist_ok=True)
 w,h=cfg['width'],cfg['height'];size=max(14,round(h*cfg.get('fontSize',.043)))
 font=ImageFont.truetype(str(SHARED/'fonts/NotoSansCJKtc-Regular.otf'),size)
 for i,event in enumerate(cfg['captions']):
  image=Image.new('RGBA',(w,h));draw=ImageDraw.Draw(image);lines=[];line=''
  for char in event.get('text',''):
   if char=='\n' or draw.textlength(line+char,font=font)>w*.87:
    lines.append(line);line='' if char=='\n' else char
   else:line+=char
  if line:lines.append(line)
  if lines:
   gap=round(size*1.3);top=max(0,h-round(h*cfg.get('bottom',.045))-gap*len(lines)-size*.2)
   for n,line in enumerate(lines):
    length=draw.textlength(line,font=font);x=(w-length)/2;y=top+n*gap
    draw.rounded_rectangle((max(0,x-size*.25),y-size*.05,min(w,x+length+size*.25),y+gap),radius=size*.16,fill=(0,0,0,180))
    draw.text((x,y),line,font=font,fill='white',stroke_width=max(1,size//32),stroke_fill='black')
  image.save(folder/f'{i:05d}.png')

def main(args):
 flag=args[0]
 if flag in ('--traditional-text','--simplified-text'):
  from opencc import OpenCC
  sys.stdout.write(OpenCC('t2s' if flag=='--simplified-text' else 's2twp').convert(sys.stdin.read()));return
 if flag=='--render-subtitles':subtitles(args[1]);return
 if flag=='--ocr':result=ocr(args[1])
 elif flag in ('--classify-opening','--classify-performance'):result=classify(args[1])
 else:raise ValueError('Unknown native helper action: '+flag)
 print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main(sys.argv[1:])
