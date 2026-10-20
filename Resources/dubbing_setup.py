"""Install isolated, pinned local dubbing tools. Invoked only by explicit setup action."""
from runtime_installer import ensure_env, pip_command
import hashlib
import json
import os
os.environ['ORT_DISABLE_TELEMETRY'] = '1'
from pathlib import Path
import subprocess
import sys
import tarfile
import urllib.parse

REV = '48b1a0169a28582a8984402f82cf438d3bfa6aca'
SOURCE_SHA = '1c967e31777b2b88468af3e7481bcb770ac4d09dd854bdb9ee065d8c8c75fcb6'
HF_REV = '1cdb10a4f2b13b3e8103b873c4c70c9d54d92c85'
GSV_MODELS = {
 'chinese-hubert-base/config.json': 'c3e5060a1277e0f078cc6be9da4528a605dba6ece93018981fe2c820e5c7b103',
 'chinese-hubert-base/preprocessor_config.json': 'dcd684124d06722947939d41ea6ae58dbf10968c60a11a29f23ddc602c64a29b',
 'chinese-hubert-base/pytorch_model.bin': '24164f129c66499d1346e2aa55f183250c223161ec2770c0da3d3b08cf432d3c',
 'chinese-roberta-wwm-ext-large/config.json': '3d57de2fd7e80d0e5c8ff194f0bbb6baa10df7e43fc262a0cc71298a78b0a3e5',
 'chinese-roberta-wwm-ext-large/tokenizer.json': '173796956820ea27bd14f76bf28162607ff4254807e2948253eb5b46f5bb643b',
 'chinese-roberta-wwm-ext-large/pytorch_model.bin': 'e53a693acc59ace251d143d068096ae0d7b79e4b1b503fa84c9dcf576448c1d8',
 's1v3.ckpt': '87133414860ea14ff6620c483a3db5ed07b44be42e2c3fcdad65523a729a745a',
 'gsv-v4-pretrained/s2Gv4.pth': '906fe22f48c3e037a389df291d4d32a9414e15dbb8f9628643e83aaced109ea4',
 'gsv-v4-pretrained/vocoder.pth': '4d611913df7b12d49e8976c944558d2d096816365edfc6c35a9e85b67dd14ed9',
}


def emit(message):
 print(json.dumps({'stage':'部署配音','message':message},ensure_ascii=False),flush=True)


def call(args):
 subprocess.run([str(x) for x in args],check=True)


def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for block in iter(lambda:f.read(4*1024*1024),b''): h.update(block)
 return h.hexdigest()


from model_download import download


def install(root, kind, variant=None):
 from runtime_paths import python_for,packages_ready
 if kind=='asr':
  from asr_verify import install
  install(Path(root),variant)
  return
 if kind=='qwen':
  from qwen_voice import install
  install(Path(root),variant)
  return
 if kind=='cosy':
  from cosy import install
  install(Path(root),variant)
  return
 if kind in ('voxcpm2','wsyue','drama3'):
  from local_tts import install as local_install
  local_install(Path(root),kind,variant)
  return
 if kind=='speakers':
  root=Path(root)
  if not python_for(root,'separator-runtime').exists(): install(str(root),'separator')
  emit('下載聲紋模型（約 27 MB），用原聲自動配對角色。')
  call([python_for(root,'separator-runtime'),Path(__file__).with_name('dubbing_runner.py'),'prepare-speakers',root])
  return
 root=Path(root)
 version=variant or 'v4'
 if kind=='gsv':
  from gsv_versions import required
  required(version)
 (root/(f'gsv-{version}-ready.json' if kind=='gsv' else 'separator-ready.json')).unlink(missing_ok=True)
 env=root/('gsv-runtime' if kind=='gsv' else 'separator-runtime')
 python=python_for(root,env.name)
 if not python.exists(): ensure_env(root, env, run=lambda args,**kw: call(args))
 if kind=='gsv':
  emit('安裝 GPT-SoVITS 專用依賴；唔會更改語音辨識環境。')
  if not packages_ready(root,env.name):call(pip_command(python, root, 'install', '--only-binary', ':all:', '--no-deps', '--find-links', Path(__file__).with_name('wheels'), '-r', Path(__file__).with_name('gsv-requirements.lock')))
  archive=root/'downloads'/f'gpt-sovits-{REV}.tar.gz'
  emit('下載及校驗 GPT-SoVITS 官方程式。')
  bundled=Path(__file__).resolve().parent/'gpt-sovits'/REV
  source=root/'gpt-sovits'/REV
  if not (source/'.source-complete').exists() and (bundled/'.source-complete').exists():
   import shutil
   shutil.copytree(bundled,source,dirs_exist_ok=True)
  if source!=bundled:download(f'https://codeload.github.com/RVC-Boss/GPT-SoVITS/tar.gz/{REV}',archive,SOURCE_SHA)
  if not (source/'.source-complete').exists():
   source.mkdir(parents=True,exist_ok=True)
   with tarfile.open(archive) as tf:
    for m in tf.getmembers():
     parts=Path(m.name).parts[1:]
     if not parts: continue
     if m.issym() or m.islnk() or '..' in parts: raise ValueError('無效程式封裝')
     m.name=str(Path(*parts)); tf.extract(m,source,filter='data')
   (source/'.source-complete').write_text(REV)
  from gsv_versions import required,BIGVGAN_REV
  models={name:digest for name,digest in GSV_MODELS.items() if name.startswith(('chinese-hubert-base/','chinese-roberta-wwm-ext-large/'))}
  models.update({name:row[1] for name,row in required(version).items()})
  for i,(name,digest) in enumerate(models.items()):
   packaged=bundled/'GPT_SoVITS/pretrained_models'/name
   dest=source/'GPT_SoVITS/pretrained_models'/name
   if not dest.exists() and packaged.is_file() and (not digest or sha(packaged)==digest):
    import shutil
    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(packaged,dest)
   emit(f'下載 GPT-SoVITS {version.upper()} 模型 {i+1}/{len(models)}：{name}')
   url=f'https://huggingface.co/lj1995/GPT-SoVITS/resolve/{HF_REV}/{urllib.parse.quote(name)}'
   if name.startswith('models--nvidia--'):
    url=f'https://huggingface.co/nvidia/bigvgan_v2_24khz_100band_256x/resolve/{BIGVGAN_REV}/{name.split("/")[-1]}'
   download(url,dest,digest)
  emit('準備日語字典同語音文字元件，之後推理離線執行。')
  call([python,Path(__file__).with_name('dubbing_runner.py'),'prepare-gsv',str(root),version])
  marker=json.dumps({'revision':REV,'version':version,'python':str(python)})
  (root/f'gsv-{version}-ready.json').write_text(marker)
  if version=='v4' or not (root/'gsv-ready.json').exists():(root/'gsv-ready.json').write_text(marker)
  from model_ownership import mark_available
  mark_available(root,dict(id=version))
 else:
  emit('安裝背景分離專用依賴。')
  if not packages_ready(root,env.name):call(pip_command(python, root, 'install', '--only-binary', ':all:', '--no-deps', '--find-links', Path(__file__).with_name('wheels'), '-r', Path(__file__).with_name('separator-requirements.lock')))
  call([python,Path(__file__).with_name('dubbing_runner.py'),'prepare-separator',str(root)])
  (root/'separator-ready.json').write_text(json.dumps({'version':'0.30.2','model':'Kimberley Jensen Mel-Band RoFormer'}))
 emit('部署完成。模型留喺本機；可以開始試聽。')


if __name__=='__main__':
 if sys.platform != 'win32': os.setpgrp()
 try: install(*sys.argv[1:])
 except Exception as e:
  print(json.dumps({'stage':'錯誤','message':str(e)},ensure_ascii=False),flush=True);sys.exit(1)
