import json,sys,tempfile,unittest,subprocess,wave,hashlib
from pathlib import Path
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import reference_quality as quality,engine_reference,dubbing

FFMPEG=Path(__file__).resolve().parents[1]/'dist/AniCanto.app/Contents/Resources/bin/ffmpeg'
def write(path,x,sr=24000):
    with wave.open(str(path),'wb') as f:f.setparams((1,2,sr,0,'NONE','not compressed'));f.writeframes((np.clip(x,-1,.999)*32768).astype('<i2').tobytes())
def run(args):subprocess.run([str(a) for a in args],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)

class ReferenceQualityTests(unittest.TestCase):
    def signal(self):
        t=np.arange(4*24000)/24000
        return .12*np.sin(2*np.pi*210*t)*(np.sin(2*np.pi*2*t)>-.2)
    def test_continuous_noise_and_padding_rank_below_clean_reference(self):
        x=self.signal();rng=np.random.default_rng(4)
        clean=quality.measure(x,24000);noisy=quality.measure(x+rng.normal(0,.035,len(x)),24000)
        padded=quality.measure(np.r_[x[:12000],np.zeros(84000)],24000)
        self.assertGreater(clean['score'],noisy['score']);self.assertIn('stationary-noise-risk',noisy['warnings'])
        self.assertGreater(clean['score'],padded['score']);self.assertIn('mostly-silence',padded['warnings'])
    def test_loud_tonal_voice_is_not_assumed_to_be_hiss(self):
        t=np.arange(3*24000)/24000;r=quality.measure(.4*np.sin(2*np.pi*210*t),24000)
        self.assertNotIn('stationary-noise-risk',r['warnings'])
    def test_quiet_voice_and_source_clipping_are_visible(self):
        self.assertIn('insufficient-speech',quality.measure(np.zeros(72000),24000)['warnings'])
        self.assertIn('source-clipping',quality.measure(np.ones(72000),24000)['warnings'])
    def test_clean_original_unchanged_and_no_background_generation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'ref.wav';write(p,self.signal());before=hashlib.sha256(p.read_bytes()).hexdigest()
            result,report=quality.clean(p,d,FFMPEG,run)
            self.assertEqual(result,p);self.assertFalse(report['applied']);self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),before)
    def test_filter_failure_retains_original(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'ref.wav';write(p,self.signal()+np.random.default_rng(4).normal(0,.035,96000))
            def fail(args):raise subprocess.CalledProcessError(1,args)
            result,report=quality.clean(p,d,FFMPEG,fail);self.assertEqual(result,p);self.assertFalse(report['applied'])
    def test_same_role_clean_alternate_selected_with_matching_prompt_and_engine_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);write(p/'noisy.wav',self.signal()+np.random.default_rng(4).normal(0,.035,96000));write(p/'clean.wav',self.signal())
            original=(p/'noisy.wav').read_bytes()
            profile=dict(id='one',reference=str(p/'noisy.wav'),promptText='最初',language='ja',referenceCandidates=[dict(reference=str(p/'clean.wav'),promptText='別の原文',language='ja',range=[10,14])])
            result=engine_reference.prepare(dict(storage=d,ttsBackend='gpt-sovits',ffmpeg=str(FFMPEG)),p,profile,run)
            report=json.loads(Path(result['referenceProvenance']).read_text())
            self.assertEqual(result['promptText'],'別の原文');self.assertTrue(report['selectedAlternate']);self.assertFalse(report['purityVerified'])
            self.assertEqual((p/'noisy.wav').read_bytes(),original);self.assertIn('/gpt-sovits/',result['reference'])
            self.assertTrue(result['referenceCandidates']);self.assertEqual(result['referenceCandidates'][0]['promptText'],'最初')
    def test_manual_engine_reference_cannot_borrow_automatic_japanese_candidates(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'manual.wav';write(p,self.signal())
            profile=dict(id='one',name='one',reference='original.wav',promptText='日文',referenceCandidates=[dict(reference='other.wav',promptText='別の原文')],engineReferences={'gpt-sovits:yue':dict(enabled=True,reference=str(p),promptText='廣東話')})
            result=dubbing.profile_for(dict(speakerId='one'),dict(voiceProfiles=[profile],ttsBackend='gpt-sovits',targetLanguage='yue'))
            self.assertEqual(result['referenceCandidates'],[]);self.assertEqual(result['promptText'],'廣東話')
    def test_background_evidence_changes_engine_selection_and_survives_alternate_retry(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);t=np.arange(96000)/24000;music=.15*np.sin(2*np.pi*440*t)
            noisy=music+self.signal()*.25
            write(p/'primary.wav',noisy);write(p/'clean.wav',self.signal())
            evidence=quality.measure(noisy,24000,music)
            profile=dict(reference=str(p/'primary.wav'),promptText='污染原句',language='ja',referenceQuality=evidence,
                         referenceCandidates=[dict(reference=str(p/'clean.wav'),promptText='乾淨原句',language='ja')])
            cfg=dict(storage=d,ttsBackend='gpt-sovits',ffmpeg=str(FFMPEG))
            result=engine_reference.prepare(cfg,p,profile,run)
            self.assertEqual(result['promptText'],'乾淨原句')
            self.assertTrue(result['referenceCandidates'])
            alternate=Path(result['referenceCandidates'][0]['reference']).with_suffix('.json')
            self.assertIn('shared-background-residual',json.loads(alternate.read_text())['sourceQuality']['warnings'])
    def test_imported_24_bit_reference_preserves_audio_and_conditions_successfully(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'studio.wav';x=self.signal();values=(x*8388608).astype(np.int32)
            raw=np.stack([values&255,(values>>8)&255,(values>>16)&255],axis=1).astype(np.uint8).tobytes()
            with wave.open(str(p),'wb') as f:f.setparams((1,3,24000,0,'NONE','not compressed'));f.writeframes(raw)
            decoded,sr=quality.read(p);np.testing.assert_allclose(decoded,x,atol=1/8388608)
            before=p.read_bytes()
            result=engine_reference.prepare(dict(storage=d,ttsBackend='gpt-sovits',ffmpeg=str(FFMPEG)),Path(d),dict(reference=str(p),promptText='参考原声',language='ja'),run)
            self.assertTrue(Path(result['reference']).exists());self.assertEqual(before,p.read_bytes())
    def test_imported_float_wav_uses_pcm_conversion_when_source_measurement_unavailable(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);write(p/'integer.wav',self.signal())
            run([FFMPEG,'-v','error','-y','-i',p/'integer.wav','-c:a','pcm_f32le',p/'float.wav'])
            result=engine_reference.prepare(dict(storage=d,ttsBackend='gpt-sovits',ffmpeg=str(FFMPEG)),p,dict(reference=str(p/'float.wav'),promptText='参考原声',language='ja'),run)
            self.assertTrue(Path(result['reference']).exists())

if __name__=='__main__':unittest.main()
