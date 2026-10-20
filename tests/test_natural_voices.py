import sys,copy,tempfile,json,unittest
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import dubbing,natural_voices,gsv_reference

class NaturalVoicesTests(unittest.TestCase):
 def profile(self):return dict(id='role-one',name='Role one',reference='/missing-original.wav',promptText='ああ',language='ja')
 def test_target_language_reference_without_original_or_japanese_fallback(self):
  p=self.profile();before=copy.deepcopy(p)
  for language in ('yue','en'):
   cfg=dict(voiceStyleMode='natural',targetLanguage=language,ttsBackend='gpt-sovits',voiceProfiles=[p])
   result=dubbing.profile_for(dict(speakerId=p['id']),cfg)
   self.assertEqual(result['language'],language);self.assertEqual(result['id'],p['id']);self.assertTrue(Path(result['reference']).is_file());self.assertFalse(result['referenceCandidates'])
  self.assertEqual(p,before)
 def test_stable_range_casting_and_independent_per_language_overrides(self):
  p=self.profile();p['reference']=natural_voices.catalog()[0]['reference'];cfg=dict(targetLanguage='yue')
  with patch('natural_voices.pitch',return_value=110) as pitch:
   a=natural_voices.resolve(p,cfg);b=natural_voices.resolve(p,cfg)
   self.assertEqual(a['naturalReferenceId'],b['naturalReferenceId']);self.assertEqual(pitch.call_count,1)
  p['naturalVoices']=dict(yue='yue-soft',en='en-low')
  self.assertEqual(natural_voices.resolve(p,dict(targetLanguage='yue'))['naturalReferenceId'],'yue-soft')
  self.assertEqual(natural_voices.resolve(p,dict(targetLanguage='en'))['naturalReferenceId'],'en-low')
 def test_invalid_selection_fails_closed(self):
  p=dict(self.profile(),naturalVoices=dict(yue='en-low'))
  with self.assertRaises(ValueError):natural_voices.resolve(p,dict(targetLanguage='yue'))
 def test_manual_reference_must_use_target_language(self):
  row=next(r for r in natural_voices.catalog() if r['language']=='yue')
  p=self.profile();p['engineReferences']={'gpt-sovits:yue':dict(reference=row['reference'],promptText=row['promptText'],language='yue',enabled=True)}
  cfg=dict(voiceStyleMode='natural',targetLanguage='yue',ttsBackend='gpt-sovits',voiceProfiles=[p])
  self.assertEqual(dubbing.profile_for(dict(speakerId=p['id']),cfg)['naturalReferenceId'],'user-reference')
  p['engineReferences']['gpt-sovits:yue']['language']='ja'
  with self.assertRaises(ValueError):dubbing.profile_for(dict(speakerId=p['id']),cfg)
 def test_clone_mode_never_uses_natural_bank_implicitly(self):
  with patch('natural_voices.resolve',side_effect=AssertionError('no natural fallback')):
   with self.assertRaises(ValueError):dubbing.profile_for(dict(speakerId='role-one'),dict(voiceStyleMode='clone',voiceProfiles=[self.profile()]))
 def test_hallucinated_and_nonlexical_original_transcripts_rejected(self):
  self.assertFalse(gsv_reference.transcript_check('ああああああ','ご視聴ありがとうございました')[0])
  self.assertFalse(gsv_reference.transcript_check('故郷に戻れないのは悲しいもんな','ご視聴ありがとうございました')[0])
  self.assertTrue(gsv_reference.transcript_check('ご視聴ありがとうございました','ご視聴ありがとうございました。')[0])
  self.assertTrue(gsv_reference.transcript_check('故郷に戻れないのは悲しいもんな','故郷に戻れないのは悲しいもんな。')[0])
 def test_catalog_integrity_and_expected_languages(self):
  import hashlib,wave
  rows=natural_voices.catalog();self.assertEqual({r['language'] for r in rows},{'yue','en'})
  for r in rows:
   self.assertEqual(hashlib.sha256(Path(r['reference']).read_bytes()).hexdigest(),r['sha256'])
   with wave.open(r['reference']) as f:self.assertTrue(3<=f.getnframes()/f.getframerate()<=10.1)

if __name__=='__main__':unittest.main()
