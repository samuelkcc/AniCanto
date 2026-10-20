"""Windows-to-shared settings contract; migrate only known historical values.

Submitted requests remain immutable. Their invocation projections may normalize
an old Windows value before the shared worker validates and freezes the plan.
"""
import copy,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
SHARED=HERE/'shared' if (HERE/'shared').is_dir() else HERE.parent/'Resources'
if str(SHARED) not in sys.path:sys.path.insert(0,str(SHARED))
from translation_source import COMBINED,AUDIO_ONLY,configure as configure_source

def migrate(settings):
    result=copy.deepcopy(settings)
    if result.get('translationSource')=='combined':result['translationSource']=COMBINED
    return result

def validated(settings):
    result=migrate(settings)
    result.setdefault('translationSource',COMBINED)
    return configure_source(result)
