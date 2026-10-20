import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import gsv_versions,multitrack,audio_format,voice_samples
from types import SimpleNamespace
class VersionsTests(unittest.TestCase):
 def test_six_active_tracks_keep_source_configuration(self):
  cfg=dict(selectedEngines=list(gsv_versions.VERSIONS)+['cosyvoice3'],dubLanguages=['yue','en']);old=copy.deepcopy(cfg)
  pairs=[e+':'+l for e in multitrack.selected(cfg) for l in cfg['dubLanguages']]
  self.assertEqual(len(set(pairs)),6);self.assertEqual(cfg,old)
 def test_v2_slot_uses_real_pro_plus_and_requires_speaker_encoder(self):
  self.assertEqual(gsv_versions.version(dict(ttsBackend='gpt-sovits-v2')),'v2ProPlus')
  files=gsv_versions.required('v2ProPlus');self.assertIn('v2Pro/s2Gv2ProPlus.pth',files);self.assertIn('sv/pretrained_eres2netv2w24s4ep4.ckpt',files)
  self.assertIn('s1v3.ckpt',files);self.assertNotIn('gsv-v2final-pretrained/s2G2333k.pth',files)
  self.assertEqual(gsv_versions.title('v2ProPlus'),'V2 Pro Plus')
 def test_native_rates_and_invalid_version(self):
  for e,v in gsv_versions.VERSIONS.items():self.assertEqual(audio_format.delivery_rate(dict(ttsBackend=e)),gsv_versions.RATES[v])
  with self.assertRaises(ValueError):gsv_versions.required('v1')
 def test_ab_same_engine_parameters_and_output_stay_independent(self):
  with tempfile.TemporaryDirectory() as d:
   folder=Path(d);cue=dict(editorID='line',speakerId='R06',cantonese='唔好放棄',start=1,end=3);old=copy.deepcopy(cue);calls=[]
   def generate(w,cfg,job,c):
    calls.append((cfg['ttsBackend'],cfg['gsvVersion'],cfg['gptTemperature'],cfg['audioRerunToken']))
    path=job/'take.wav';path.touch();(job/'report.json').write_text(json.dumps(dict(speechCheck={'heard':c['cantonese']})));return path,2
   w=SimpleNamespace(atomic_json=lambda p,j:Path(p).write_text(json.dumps(j)))
   cfg=dict(comparisonCandidates=[dict(engine='gpt-sovits-v2',parameters={'gptTemperature':.7}),dict(engine='gpt-sovits-v2',parameters={'gptTemperature':1.1})])
   with patch('audio_audition.generate',side_effect=generate):result=voice_samples.compare(w,cfg,folder,[cue],'line')
   self.assertEqual([c[:3] for c in calls],[('gpt-sovits-v2','v2ProPlus',.7),('gpt-sovits-v2','v2ProPlus',1.1)])
   self.assertNotEqual(calls[0][3],calls[1][3]);self.assertNotEqual(result['rows'][0]['audio'],result['rows'][1]['audio']);self.assertEqual(cue,old)
 def test_ab_english_fills_only_missing_script_before_synthesis(self):
  with tempfile.TemporaryDirectory() as d:
   folder=Path(d);cue=dict(editorID='line',speakerId='R06',cantonese='你好',start=1,end=3);calls=[]
   def translate(w,cfg,job,cues):cues[0]['english']='Hello there.'
   def generate(w,cfg,job,c):
    calls.append((cfg['targetLanguage'],c['cantonese']));p=job/'take.wav';p.touch();(job/'report.json').write_text(json.dumps(dict(speechCheck={'heard':c['cantonese']})));return p,1
   w=SimpleNamespace(atomic_json=lambda p,j:Path(p).write_text(json.dumps(j)))
   cfg=dict(targetLanguage='en',comparisonCandidates=[dict(engine='gpt-sovits'),dict(engine='cosyvoice3')])
   with patch('dub_languages.english_script',side_effect=translate),patch('audio_audition.generate',side_effect=generate):result=voice_samples.compare(w,cfg,folder,[cue],'line')
   self.assertEqual(calls,[('en','Hello there.')]*2);self.assertNotIn('english',cue);self.assertEqual(result['language'],'en')
