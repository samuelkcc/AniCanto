"""Exercise the delivered PCM path, not just OP range selection."""
import math
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
import wave
from array import array

sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import source_evidence

ROOT=Path(__file__).parents[1]
FFMPEG=shutil.which('ffmpeg') or str(ROOT/'dist/AniCanto.app/Contents/Resources/bin/ffmpeg')

@unittest.skipUnless(Path(FFMPEG).is_file(),'FFmpeg unavailable')
class OpeningMixTests(unittest.TestCase):
    def test_repair_of_an_old_export_uses_dry_voice_and_is_idempotent(self):
        import hashlib
        def run(cmd):return subprocess.check_output([str(x) for x in cmd],stderr=subprocess.PIPE)
        with tempfile.TemporaryDirectory() as directory:
            job=Path(directory)
            for name,frequency in [('source',220),('cantonese',880)]:
                with wave.open(str(job/(name+'.wav')),'wb') as output:
                    output.setparams((1,2,48000,0,'NONE',''))
                    output.writeframes(array('h',(int(5000*math.sin(2*math.pi*frequency*i/48000)) for i in range(3*48000))).tobytes())
            native=job/'old.mp4'
            run([FFMPEG,'-v','error','-y','-f','lavfi','-i','color=s=64x64:r=10:d=3','-i',job/'source.wav','-c:v','libx264','-c:a','aac','-t','3',native])
            old=hashlib.sha256(native.read_bytes()).hexdigest()
            cfg=dict(video=str(native),ffmpeg=FFMPEG,duration=3,autoSkipOP=False,captionPolicy=dict(mode='original-chinese',revision=3),_captionPreserveRanges=[dict(start=0,end=1.5),dict(start=2.5,end=3)])
            (job/'review.json').write_text(json.dumps(dict(config=cfg,cues=[dict(start=.5,end=2.5,cantonese='完整句子',enabled=True)])))
            fixed=source_evidence.recover_caption_base(cfg,job,native,run,lambda *a:None)
            signature=(fixed.stat().st_mtime_ns,hashlib.sha256(fixed.read_bytes()).hexdigest())
            self.assertEqual(source_evidence.recover_caption_base(cfg,job,fixed,run,lambda *a:None),fixed)
            self.assertEqual(signature,(fixed.stat().st_mtime_ns,hashlib.sha256(fixed.read_bytes()).hexdigest()))
            self.assertEqual(hashlib.sha256(native.read_bytes()).hexdigest(),old)
            raw=run([FFMPEG,'-v','error','-ss','1','-i',fixed,'-t','0.25','-map','0:a:0','-ar','48000','-ac','1','-f','s16le','pipe:1'])
            samples=array('h',raw)
            def energy(frequency):
                return abs(sum(v*complex(math.cos(2*math.pi*frequency*i/48000),math.sin(2*math.pi*frequency*i/48000)) for i,v in enumerate(samples)))
            self.assertGreater(energy(880),50*max(1,energy(220)))

    def test_old_caption_display_gap_cannot_replace_the_start_of_a_completed_dub(self):
        with tempfile.TemporaryDirectory() as directory:
            job=Path(directory)
            for name,frequency in [('source',220),('dub',880)]:
                with wave.open(str(job/(name+'.wav')),'wb') as output:
                    output.setparams((1,2,48000,0,'NONE',''))
                    output.writeframes(array('h',(int(5000*math.sin(2*math.pi*frequency*i/48000)) for i in range(3*48000))).tobytes())
            cue=dict(start=.5,end=2.5,speechStart=.5,speechEnd=2.5,japanese='考えれば考えるほど',cantonese='諗得越多越懵',enabled=True)
            (job/'review.json').write_text(json.dumps(dict(cues=[cue])))
            cfg=dict(video=str(job/'source.wav'),ffmpeg=FFMPEG,duration=3,autoSkipOP=False,_captionPreserveRanges=[dict(start=0,end=1.5),dict(start=2.5,end=3)])
            original=json.dumps(cfg)
            w=SimpleNamespace(run=lambda cmd:subprocess.check_output([str(x) for x in cmd],stderr=subprocess.PIPE),emit=lambda *a:None)
            output=source_evidence.mix_caption_audio(w,cfg,job,job/'dub.wav')
            with wave.open(str(output)) as audio:
                channels=audio.getnchannels();audio.setpos(48000)
                samples=array('h',audio.readframes(12000))[::channels]
            def energy(frequency):
                return abs(sum(v*complex(math.cos(2*math.pi*frequency*i/48000),math.sin(2*math.pi*frequency*i/48000)) for i,v in enumerate(samples)))
            self.assertGreater(energy(880),100*max(1,energy(220)))
            self.assertEqual(json.dumps(cfg),original)

    def test_translated_opening_keeps_dub_instead_of_restoring_source_voice(self):
        def tone(path,frequency):
            with wave.open(str(path),'wb') as output:
                output.setparams((1,2,48000,0,'NONE',''))
                output.writeframes(array('h',(int(5000*math.sin(2*math.pi*frequency*i/48000)) for i in range(3*48000))).tobytes())
        def run(command):return subprocess.check_output([str(x) for x in command],stderr=subprocess.PIPE)
        w=SimpleNamespace(run=run,emit=lambda *args:None)
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);source=folder/'source.wav';dub=folder/'dub.wav'
            tone(source,220);tone(dub,880)
            for translate in (False,True):
                job=folder/str(translate);job.mkdir()
                cfg=dict(video=str(source),ffmpeg=FFMPEG,duration=3,autoSkipOP=True,translateOPED=translate,opRanges=[dict(start=0,end=2)])
                cues=[dict(start=.5,end=1.5,japanese='今から出発する',enabled=True)]
                source_evidence.apply_caption_policy(cfg,[dict(start=2,end=3,text='正文字幕')],cues)
                output=source_evidence.mix_caption_audio(w,cfg,job,dub)
                with wave.open(str(output)) as audio:
                    channels=audio.getnchannels();audio.setpos(24000)
                    samples=array('h',audio.readframes(24000))[::channels]
                def energy(frequency):
                    return abs(sum(v*complex(math.cos(2*math.pi*frequency*i/48000),math.sin(2*math.pi*frequency*i/48000)) for i,v in enumerate(samples)))
                wanted,unwanted=(880,220) if translate else (220,880)
                self.assertGreater(energy(wanted),100*max(1,energy(unwanted)))
                self.assertEqual(cues[0]['enabled'],translate)
