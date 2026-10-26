"""Available ONNX providers with first-inference numerical validation and fallback.

A requested provider is not proof that graph nodes run there. Retain real node
provider counts from the first profile and never overwrite a source/model.
"""
import hashlib,json,os,sys,tempfile,time
from pathlib import Path

class CheckedSession:
 def __init__(self,path,options=None,root=None,stage='onnx'):
  import onnxruntime as ort
  self.ort=ort;self.path=str(path);self.root=root;self.stage=stage;self.cpu=None;self.checked=False;self.profile=None
  available=ort.get_available_providers();provider='CoreMLExecutionProvider' if sys.platform=='darwin' and 'CoreMLExecutionProvider' in available else 'CUDAExecutionProvider' if 'CUDAExecutionProvider' in available else 'DmlExecutionProvider' if 'DmlExecutionProvider' in available else None
  self.provider=provider;self.reason=None
  # Reproduced non-finite embeddings with both ALL and CPUAndGPU. Keep the
  # pinned WeSpeaker/ORT combination on CPU until a new provider is validated.
  if provider=='CoreMLExecutionProvider' and ort.__version__=='1.30.0':
   with Path(path).open('rb') as file:digest=hashlib.file_digest(file,'sha256').hexdigest()
   if digest=='7bb2f06e9df17cdf1ef14ee8a15ab08ed28e8d0ef5054ee135741560df2ec068':
    self.reason='Pinned WeSpeaker/CoreML runtime returned non-finite embeddings in validation; CPU retained';provider=None;self.provider=None
  options=options or ort.SessionOptions()
  if provider:
   folder=Path(root)/'cache/onnx-profiles' if root else Path(tempfile.gettempdir())/'anicanto-onnx-profiles';folder.mkdir(parents=True,exist_ok=True)
   options.enable_profiling=True;options.profile_file_prefix=str(folder/stage)
  if provider=='DmlExecutionProvider':options.enable_mem_pattern=False;options.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
  candidates=[('CoreMLExecutionProvider',dict(MLComputeUnits='ALL',ModelFormat='MLProgram',RequireStaticInputShapes='0')),'CPUExecutionProvider'] if provider=='CoreMLExecutionProvider' else ([provider,'CPUExecutionProvider'] if provider else ['CPUExecutionProvider'])
  try:self.session=ort.InferenceSession(self.path,sess_options=options,providers=candidates)
  except Exception as error:
   self.reason=str(error)[:500];self.provider=None;self.session=ort.InferenceSession(self.path,providers=['CPUExecutionProvider'])
  self.save(dict(state='configured',backend=provider or 'CPUExecutionProvider',requestedProvider=provider,sessionProviders=self.session.get_providers(),reason=self.reason,modelInferencePassed=False))
 def save(self,value):
  from compute_policy import record
  record(self.root,self.stage,value)
 def __getattr__(self,name):return getattr(self.session,name)
 def run(self,names,inputs,*args,**kwargs):
  import numpy as np
  start=time.monotonic()
  try:result=self.session.run(names,inputs,*args,**kwargs)
  except Exception as error:
   if not self.provider:raise
   self.reason=str(error)[:500];self.provider=None;self.session=self.ort.InferenceSession(self.path,providers=['CPUExecutionProvider']);result=self.session.run(names,inputs,*args,**kwargs)
  seconds=time.monotonic()-start
  if self.checked:return result
  self.checked=True;counts={};matched=None
  if self.provider:
   self.profile=self.session.end_profiling()
   for item in json.loads(Path(self.profile).read_text()):
    provider=item.get('args',{}).get('provider')
    if provider:counts[provider]=counts.get(provider,0)+1
   self.cpu=self.ort.InferenceSession(self.path,providers=['CPUExecutionProvider']);expected=self.cpu.run(names,inputs,*args,**kwargs)
   matched=len(result)==len(expected) and all(a.shape==b.shape and np.isfinite(a).all() and np.allclose(a,b,rtol=.02,atol=.002) for a,b in zip(result,expected))
   if not matched:
    self.session=self.cpu;self.provider=None;result=expected;self.reason='First inference differs from CPU reference beyond the numerical tolerance'
   self.cpu=None
  self.save(dict(state='inference-passed',backend=self.provider or 'CPUExecutionProvider',requestedProvider=self.provider or 'CPUExecutionProvider',sessionProviders=self.session.get_providers(),nodeProviders=counts,firstInferenceSeconds=round(seconds,4),numericalReferenceMatched=matched,reason=self.reason,modelInferencePassed=True,profile=self.profile))
  return result


def session(path,options=None,root=None,stage='onnx'):return CheckedSession(path,options,root,stage)
