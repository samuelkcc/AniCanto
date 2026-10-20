"""Pinned GPT versions; distinct engine IDs keep audio channels and caches separate."""
from pathlib import Path
VERSIONS={'gpt-sovits-v2':'v2ProPlus','gpt-sovits-v3':'v3','gpt-sovits':'v4'}
RATES={'v2ProPlus':32000,'v2':32000,'v3':24000,'v4':48000}
FILES={
 'v2ProPlus':{'s1v3.ckpt':(155284856, '87133414860ea14ff6620c483a3db5ed07b44be42e2c3fcdad65523a729a745a'),'v2Pro/s2Gv2ProPlus.pth':(200125741, 'd42a22bbbf65fb2bbdd45ad6a66841156977db45c7aabe0a6992ff378d9c7d3b'),'sv/pretrained_eres2netv2w24s4ep4.ckpt':(107528697, '4f5a0bf73c61eb41b174e1bb54e7ee3c83233892be8e0af1f187024e8e581a35')},
 'v2':{'gsv-v2final-pretrained/s1bert25hz-5kh-longer-epoch=12-step=369668.ckpt':(155315150,'732f94e63b148066e24c7f9d2637f3374083e637635f07fbdb695dee20ddbe1f'),
       'gsv-v2final-pretrained/s2G2333k.pth':(106035259,'924fdccaa3c574bf139c25c9759aa1ed3b3f99e19a7c529ee996c2bc17663695')},
 'v3':{'s1v3.ckpt':(155284856,'87133414860ea14ff6620c483a3db5ed07b44be42e2c3fcdad65523a729a745a'),
       's2Gv3.pth':(769035145,'f33abb1920076d988e1711d5f41b5c9c6d7f92575b4acf0ad4fae6a4ebf0cf19'),
       'models--nvidia--bigvgan_v2_24khz_100band_256x/config.json':(1402,'d77e2c96583ca2296ac112a56ec7cc6bd5da4bf7681ceff18448bedc4fcf6512'),
       'models--nvidia--bigvgan_v2_24khz_100band_256x/bigvgan_generator.pt':(450088331,'6f9c5715550c9d0f11159ceb8935638da5aeb19e27d1e63677632df095e376f5')},
 'v4':{'s1v3.ckpt':(155284856,'87133414860ea14ff6620c483a3db5ed07b44be42e2c3fcdad65523a729a745a'),
       'gsv-v4-pretrained/s2Gv4.pth':(769025545,'906fe22f48c3e037a389df291d4d32a9414e15dbb8f9628643e83aaced109ea4'),
       'gsv-v4-pretrained/vocoder.pth':(57781109,'4d611913df7b12d49e8976c944558d2d096816365edfc6c35a9e85b67dd14ed9')}}
BIGVGAN_REV='c329ede9e9bbc100ddf5c91e2330a61921262370'
def version(cfg):
 engine=cfg.get('ttsBackend','gpt-sovits')
 if engine not in VERSIONS:raise ValueError('Unknown GPT engine.')
 return VERSIONS[engine]
def required(v):
 if v not in FILES:raise ValueError('GPT 只支援 V2 Pro Plus、V3、V4（舊 V2 僅供歷史相容）。')
 return FILES[v]
def complete(source,v):
 return all((source/'GPT_SoVITS/pretrained_models'/name).is_file() and (source/'GPT_SoVITS/pretrained_models'/name).stat().st_size==size for name,(size,sha) in required(v).items())

def title(v):
 return "V2 Pro Plus" if v=="v2ProPlus" else v.upper()
