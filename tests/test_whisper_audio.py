"""Regression for the Windows av.open(metadata_errors=...) production failure."""
import sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import soundfile as sf
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'Resources'))
from whisper_audio import load

class WhisperAudioTests(unittest.TestCase):
    def test_real_pcm_resampling_retains_duration_and_tone_for_each_reference_rate(self):
        with tempfile.TemporaryDirectory() as d:
            for rate in (16000,24000,32000,44100,48000):
                path=Path(d)/f'{rate}.wav';t=np.arange(rate)/rate;mono=.2*np.sin(t*440*2*np.pi);sf.write(path,np.column_stack([mono,mono]),rate)
                audio=load(path);self.assertEqual(audio.dtype,np.float32);self.assertEqual(audio.shape,(16000,));self.assertTrue(audio.flags.c_contiguous)
                self.assertAlmostEqual(np.argmax(abs(np.fft.rfft(audio))),440,delta=1);self.assertGreater(np.max(audio),.19)
    def test_empty_and_invalid_audio_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'empty.wav';sf.write(p,np.zeros(0),16000)
            with self.assertRaisesRegex(ValueError,'empty'):load(p)
    def test_reference_fallback_whisper_receives_pcm_never_av_open_path(self):
        import speakers
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'original-ja.wav';sf.write(p,.2*np.sin(np.arange(48000)*.08),48000)
            seen=[]
            def transcribe(audio,**kw):
                # faster-whisper only enters PyAV when its input is not a waveform.
                if not isinstance(audio,np.ndarray):raise TypeError("open() got an unexpected keyword argument 'metadata_errors'")
                seen.append(audio);return iter([SimpleNamespace(text='こんにちは。')]),None
            model=SimpleNamespace(transcribe=transcribe)
            with patch.dict(sys.modules,{'faster_whisper':SimpleNamespace(WhisperModel=lambda *a,**kw:model)}):
                profile=dict(id='line-199',name='第 199 句原聲',reference=str(p),referenceRanges=[],referenceCandidates=[])
                speakers.transcribe_profiles(dict(independentVoiceMapping=True),root,[profile],root,lambda *a:None)
            self.assertEqual(profile['promptText'],'こんにちは。');self.assertEqual(seen[0].shape,(16000,))
