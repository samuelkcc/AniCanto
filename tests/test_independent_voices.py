import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
import numpy as np
import soundfile as sf
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import independent_voices,speakers,delivery,processing_time

class IndependentVoiceTests(unittest.TestCase):
    def fixture(self,folder):
        sr=44100;t=np.arange(sr*6)/sr
        audio=np.where(t<2,.15*np.sin(2*np.pi*180*t),.15*np.sin(2*np.pi*490*t)).astype('float32')
        path=folder/'dialogue.wav';sf.write(path,audio,sr,subtype='FLOAT')
        cues=[dict(start=0,end=.6,speechStart=.1,speechEnd=.5,text='一',japanese='一',cantonese='第一句'),dict(start=3,end=4,text='二',japanese='二',cantonese='第二句'),dict(start=4,end=5,text='disabled',enabled=False)]
        return dict(storage=str(folder),job=str(folder),audio=str(path),dialoguePath=str(path),cues=cues,roleAnalysisMode='independent',continueOnError=True),cues,sr

    def test_each_line_gets_own_voice_and_only_silence_padding(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);cfg,cues,sr=self.fixture(folder);before=copy.deepcopy(cues)
            independent_voices.prepare(cfg,Mock())
            result=json.loads((folder/'independent-voices.json').read_text());profiles=result['profiles']
            self.assertEqual(len(profiles),2);self.assertNotEqual(profiles[0]['id'],profiles[1]['id']);self.assertNotEqual(profiles[0]['reference'],profiles[1]['reference'])
            raw,_=sf.read(cfg['audio'],dtype='float32')
            for profile in profiles:
                audio,rate=sf.read(profile['reference'],dtype='float32');self.assertEqual(rate,sr);self.assertAlmostEqual(len(audio)/sr,3.1,places=3)
                a,b=profile['referenceRanges'][0];n=round((b-a)*sr)
                np.testing.assert_allclose(audio[:n],raw[round(a*sr):round(b*sr)],atol=1/32768)
                self.assertTrue(np.all(audio[n:]==0));self.assertTrue(profile['shortReference']);self.assertEqual(profile['identityStatus'],'independent')
                self.assertFalse(profile['referenceCandidates']);self.assertNotIn('avatar',profile)
            self.assertEqual(cues,before);self.assertFalse(result['speakerGrouped']);self.assertFalse(result['visualAnalysis'])

    def test_identical_source_intervals_are_still_independent(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);cfg,cues,_=self.fixture(folder);cfg['cues']=[cues[0],dict(cues[0])]
            independent_voices.prepare(cfg,Mock());profiles=json.loads((folder/'independent-voices.json').read_text())['profiles']
            self.assertNotEqual(profiles[0]['id'],profiles[1]['id']);self.assertNotEqual(profiles[0]['reference'],profiles[1]['reference'])

    def test_bad_source_interval_is_reported_without_borrowing_other_voice(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);cfg,cues,_=self.fixture(folder);cues[0].update(speechStart=99,speechEnd=100)
            independent_voices.prepare(cfg,Mock());profiles=json.loads((folder/'independent-voices.json').read_text())['profiles']
            self.assertEqual(profiles[0]['reference'],'');self.assertIn('referenceIssue',profiles[0]);self.assertTrue(Path(profiles[1]['reference']).exists())

    def test_assign_bypasses_speaker_model_and_vision_and_reuses_reference_cache(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);cfg,cues,_=self.fixture(folder);original=copy.deepcopy(cues)
            def child(cfg,action,request,emit):
                self.assertEqual(action,'independent-voices');independent_voices.prepare(request,Mock())
            def transcript(cfg,job,profiles,path,emit):
                for p in profiles:p['promptText']='exact own-source Japanese'
            with patch('dubbing.model_job',side_effect=child) as job,patch('speakers.transcribe_profiles',side_effect=transcript),patch('model_catalog.selected',return_value='whisper-small'),patch('visual_speakers.refine',side_effect=AssertionError('vision must not run')),patch('speakers.analyze',side_effect=AssertionError('speaker model must not run')):
                actual=speakers.assign(cfg,folder,cues,Mock(),Mock())
                self.assertTrue(cfg['independentVoiceMapping']);self.assertFalse((folder/'character-plan.json').exists())
                self.assertNotEqual(actual[0]['speakerId'],actual[1]['speakerId'])
                for before,after in zip(original,actual):
                    for key in ('start','end','text'):self.assertEqual(before[key],after[key])
                speakers.assign(cfg,folder,cues,Mock(),Mock());self.assertEqual(job.call_count,1)
                self.assertTrue(cfg['roleAnalysisResult']['cacheReused'])
                (folder/'japanese-analysis.json').write_text(json.dumps(dict(segments=[])))
                speakers.assign(cfg,folder,cues,Mock(),Mock());self.assertEqual(job.call_count,2)

    def test_independent_mode_never_loads_group_consistency_embeddings(self):
        with patch('voicecheck.embeddings',side_effect=AssertionError('no group embeddings')):
            paths=['one.wav'];self.assertIs(delivery.stabilize_voices(dict(roleAnalysisMode='independent'),'.',[],paths,Mock(),Mock(),Mock()),paths)
        self.assertEqual(processing_time.category('逐句聲音配對'),'roles')

if __name__=='__main__':unittest.main()
