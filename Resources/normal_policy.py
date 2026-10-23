"""Normal production retains audible takes; expensive review is explicit."""
import json
from pathlib import Path


def finish_requested(cfg):
    control=cfg.get('_trackControl') or {}
    if not control.get('folder') or not control.get('token'):return False
    try:row=json.loads((Path(control['folder'])/'finish-with-current.json').read_text())
    except (OSError,ValueError):return False
    return row.get('token')==control['token']


def missing_only(cfg):
    return cfg.get('productionMode')=='normal' and cfg.get('normalRepairPolicy','missing-only')=='missing-only'


def retain(cfg):return missing_only(cfg) or finish_requested(cfg)
