"""Release engine policy; does not delete models or rewrite submitted jobs."""
import json
from pathlib import Path
import sys

COSY_MESSAGE='CosyVoice 3 is available only on Windows with an NVIDIA GPU and a working CUDA runtime. Choose another compatible voice engine.'

def require(engine,root=None,platform=None,backend=None):
    if engine!='cosyvoice3':return
    if (platform or sys.platform)!='win32':raise ValueError(COSY_MESSAGE)
    if backend is not None:
        if backend not in ('cuda','nvidia'):raise ValueError(COSY_MESSAGE)
        return
    # Before setup a physical adapter permits planning, not a claim of inference.
    from gpu import adapters,vendor
    if not any(vendor(row)=='nvidia' for row in adapters()):raise ValueError(COSY_MESSAGE)
