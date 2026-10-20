"""Verify native-frequency retention, not subjective voice clarity."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave
import numpy as np
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
from audio_format import delivery_rate
import delivery,dubbing


class BandwidthTests(unittest.TestCase):
    def test_gpt_preserves_native_32k_band_in_48k_carrier(self):
        self.assertEqual(delivery_rate(dict(ttsBackend='gpt-sovits')),48000)
        self.assertEqual(delivery_rate(dict(ttsBackend='cosyvoice3')),24000)
        with self.assertRaises(ValueError):delivery_rate(dict(audioSampleRate=22050))

    @unittest.skipUnless(shutil.which('ffmpeg'),'FFmpeg required for frequency-preservation test')
    def test_trim_fit_and_full_track_keep_14khz_native_detail(self):
        ff=shutil.which('ffmpeg')
        run=lambda args:subprocess.check_output([str(a) for a in args],stderr=subprocess.DEVNULL)
        with tempfile.TemporaryDirectory() as name:
            folder=Path(name);source=folder/'native32.wav';sr=32000;t=np.arange(sr)/sr
            samples=.12*np.sin(2*np.pi*300*t)+.04*np.sin(2*np.pi*14000*t)
            with wave.open(str(source),'wb') as f:f.setparams((1,2,sr,0,'NONE','not compressed'));f.writeframes((samples*32767).astype('<i2').tobytes())
            cfg=dict(ffmpeg=ff,ttsBackend='gpt-sovits',duration=2,autoFit=False)
            prepared=delivery.prepare_audio(cfg,folder,[source],run)[0]
            with wave.open(str(prepared)) as f:self.assertEqual(f.getframerate(),48000)
            cue=dict(start=.25,end=1.25,text='source',cantonese='完整原文')
            report=[dict(index=1,seconds=1,slot=1)]
            audio,_=dubbing.render_complete_preview(cfg,folder,[cue],[prepared],report,run,lambda *a:None)
            with wave.open(str(audio)) as f:
                self.assertEqual(f.getframerate(),48000);pcm=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').astype(float)/32768
            interval=pcm[round(.25*48000):round(1.25*48000)]
            def amplitude(x,sr,freq):return abs(np.dot(x,np.exp(-2j*np.pi*freq*np.arange(len(x))/sr)))*2/len(x)
            self.assertGreater(amplitude(interval,48000,14000),.03)
            self.assertAlmostEqual(report[0]['renderedStart'],.25)
            self.assertAlmostEqual(report[0]['renderedSeconds'],1,places=2)
            legacy=delivery.prepare_audio(dict(cfg,audioSampleRate=24000),folder,[source],run)[0]
            self.assertNotEqual(prepared,legacy)
            with wave.open(str(legacy)) as f:old=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').astype(float)/32768
            self.assertLess(np.sqrt(np.mean(old**2)),np.sqrt(np.mean(interval**2)))


if __name__=='__main__':unittest.main()

class ReferenceBandwidthTests(unittest.TestCase):
    def test_role_reference_keeps_native_source_bandwidth_and_ranges(self):
        from source_reference import write
        import soundfile as sf
        sr=44100;t=np.arange(sr*5)/sr;source=.12*np.sin(2*np.pi*300*t)+.04*np.sin(2*np.pi*14000*t)
        with tempfile.TemporaryDirectory() as name:
            path=Path(name)/'reference.wav';write(path,source,sr,[[1,4.5]])
            data,rate=sf.read(path);self.assertEqual(rate,sr);self.assertEqual(len(data),round(3.5*sr))
            amplitude=abs(np.dot(data,np.exp(-2j*np.pi*14000*np.arange(len(data))/rate)))*2/len(data)
            self.assertGreater(amplitude,.035)
    def test_gpt_conditioning_preserves_reference_14khz_at_native_32k(self):
        import engine_reference, soundfile as sf
        sr=44100;t=np.arange(round(sr*3.5))/sr;source=.12*np.sin(2*np.pi*300*t)+.04*np.sin(2*np.pi*14000*t)
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);path=root/'original.wav';sf.write(path,source,sr,subtype='PCM_16')
            profile=dict(id='role',reference=str(path),promptText='日本語',language='ja')
            cfg=dict(storage=name,ffmpeg=shutil.which('ffmpeg'),ttsBackend='gpt-sovits')
            run=lambda args:subprocess.check_output([str(x) for x in args],stderr=subprocess.DEVNULL)
            prepared=engine_reference.prepare(cfg,root,profile,run)
            data,rate=sf.read(prepared['reference']);self.assertEqual(rate,32000)
            amplitude=abs(np.dot(data,np.exp(-2j*np.pi*14000*np.arange(len(data))/rate)))*2/len(data)
            self.assertGreater(amplitude,.025)
            self.assertEqual(json.loads(Path(prepared['referenceProvenance']).read_text())['referenceSampleRate'],32000)
