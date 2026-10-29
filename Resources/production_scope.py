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
