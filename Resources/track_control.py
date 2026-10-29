"""Token-scoped cooperative skip: finish the current take, preserve final files."""
import json
from pathlib import Path

class UserSkipped(RuntimeError):pass

def requested(control):
    if not control:return False
    try:return json.loads((Path(control['folder'])/'skip-generation.json').read_text()).get('token')==control['token']
    except (OSError,ValueError,KeyError):return False

def check(cfg):
    __import__('repair_limits').check(cfg)
    if requested(cfg.get('_trackControl')):raise UserSkipped('使用者跳過本音軌餘下生成；已完成錄音保留。')
