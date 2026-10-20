"""Explicit bounded inference settings; no invented accent-removal controls."""
import math

def settings(cfg):
 out={}
 for key,default,low,high in [('gptTemperature',1,.6,1.2),('gptTopP',1,.6,1),('gptRepetitionPenalty',1.35,1,1.6),('cosyTemperature',.7,.3,1)]:
  value=float(cfg.get(key,default))
  if not math.isfinite(value) or not low<=value<=high:raise ValueError('試音參數超出範圍：'+key)
  out[key]=value
 value=int(cfg.get('gptTopK',15))
 if not 5<=value<=30:raise ValueError('GPT Top K 必須介乎 5–30。')
 out['gptTopK']=value
 style=cfg.get('cosyExpression','neutral')
 if style not in ('neutral','expressive','urgent','calm'):raise ValueError('情緒選項無效。')
 out['cosyExpression']=style
 return out

def instruction(style,language):
 if language=='en':
  return {'neutral':'','expressive':' Use warm, expressive acting, with meaningful emphasis and natural changes in intonation. Keep the same voice and say every word exactly.','urgent':' Use urgent, determined acting with clear emphasis and natural pauses. Keep the same voice and say every word exactly.','calm':' Use calm, gentle acting with natural pauses and subtle expression. Keep the same voice and say every word exactly.'}[style]
 return {'neutral':'','expressive':'用有层次的动画角色表演，自然的重音和语气起伏；保持原来的音色和地道香港粤语字音，完整说出台词，不增加文字。','urgent':'用紧张而坚定的情绪，语气有力量，重音鲜明，停顿自然；保持原来的音色和地道香港粤语字音，完整说出台词，不增加文字。','calm':'用平静温柔的表演，停顿自然，有细腻的情绪；保持原来的音色和地道香港粤语字音，完整说出台词，不增加文字。'}[style]
