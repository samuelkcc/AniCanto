"""Future-job settings scope. Existing submitted requests remain immutable."""
import copy
GLOBAL_ONLY={'appearance','animeTheme','randomAnimeTheme','themeSession','controlDensity',
             'deploymentModels','speechAcceleration','independentAsrBackend'}
def individual(row):return bool(row) and row.get('useGlobalSettings',True) is False
def snapshot(settings):return {k:copy.deepcopy(v) for k,v in settings.items() if k not in GLOBAL_ONLY}
def effective(settings,row):
 result=copy.deepcopy(settings)
 if individual(row):result.update(snapshot(row.get('productionSettings',{})))
 return result


def reset_parameters(language='en'):
 from desktop_state import defaults
 from voice_parameters import SPECS,defaults as voice_defaults
 preserve={'animeTheme','randomAnimeTheme','selectedEngines','ttsBackend','defaultAudioEngine',
           'dubLanguages','includeOriginal','subtitleOutput','burnOutputCaptions','subtitleModes','subtitleSelection','subtitleSource','batchAutoSubtitles',
           'sourceWorkflow','defaultSubtitleWorkflow','defaultOCRWorkflow','translationSource',
           'speechAcceleration','independentAsrBackend','startOffset','limit'}
 patch={k:v for k,v in defaults(language).items() if k not in preserve}
 for engine in SPECS:patch.update(voice_defaults(engine))
 patch.update(backgroundGain=.8,backgroundDucking=False,cosyExpression='neutral')
 return patch
