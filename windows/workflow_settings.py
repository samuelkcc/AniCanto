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
    __import__('basic_flow').validate(result)
    modes=__import__('work_modes')
    # Revision 2 has no speed choice. The stored value stays 'performance' so the
    # frozen performance gates keep working while the selector is hidden.
    if modes.collapsed(result):result['workMode']='performance'
    elif result.get('workMode','balanced') not in ('performance','balanced','quality'):raise ValueError('Unknown work mode.')
    if not isinstance(result.get('fullAIReview',False),bool):raise ValueError('Full AI review must be on or off.')
    if not isinstance(result.get('aiAutoFix',False),bool):raise ValueError('AI repair must be on or off.')
    if not isinstance(result.get('limitSpeechDuration',False),bool):raise ValueError('Speech duration control must be on or off.')
    result.setdefault('translationSource',COMBINED)
    __import__('source_workflow').validate(result)
    return configure_source(result)
