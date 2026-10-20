import io
import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Resources'))
import cosy
import cosy_native
import model_catalog
import voice_models


class OfficialCosyTests(unittest.TestCase):
    def test_platform_catalogues_share_official_hashes(self):
        model=model_catalog.choice('cosy-native-0.5b')
        voice=voice_models.choice('cosyvoice3')
        self.assertEqual(model['repo'],voice['repo'])
        self.assertEqual(model['files'],voice['files'])
        self.assertEqual(model['bytes'],sum(row['size'] for row in model['files']))
        self.assertEqual(model['platform'],'darwin')
        self.assertEqual(cosy.selected_variant('cosy-0.5b-4bit'),'cosy-native-0.5b')

    def test_safe_source_extraction_and_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);archive=base/'source.tar.gz';target=base/'source'
            with tarfile.open(archive,'w:gz') as tar:
                data=b'Apache-2.0';entry=tarfile.TarInfo('repo/LICENSE');entry.size=len(data)
                tar.addfile(entry,io.BytesIO(data))
            cosy._extract_source({'revision':'a'*40},archive,target)
            self.assertEqual((target/'LICENSE').read_bytes(),b'Apache-2.0')
            self.assertEqual((target/'.source-complete').read_text(),'a'*40)
            bad=base/'bad.tar.gz'
            with tarfile.open(bad,'w:gz') as tar:
                entry=tarfile.TarInfo('repo/../escape');entry.size=1
                tar.addfile(entry,io.BytesIO(b'x'))
            with self.assertRaises(ValueError):cosy._extract_source({'revision':'b'*40},bad,target)
            self.assertFalse((base/'escape').exists())

    def test_native_wrapper_passes_reference_and_official_instruction(self):
        seen={}
        class Model:
            def inference_instruct2(self,text,instruction,path,**kwargs):
                seen.update(text=text,instruction=instruction,path=path,kwargs=kwargs)
                import numpy as np
                return [dict(tts_speech=SimpleNamespace(detach=lambda:SimpleNamespace(float=lambda:SimpleNamespace(cpu=lambda:SimpleNamespace(numpy=lambda:np.ones((1,2400)))))))]
        import numpy as np
        wrapper=cosy_native.NativeCosy(Model())
        with patch('soundfile.write'):
            chunks=list(wrapper.generate('你好',np.zeros(24000),'講廣東話'))
        self.assertEqual(len(chunks[0].audio),2400)
        self.assertEqual(seen['text'],'你好')
        self.assertTrue(seen['instruction'].endswith('<|endofprompt|>'))
        self.assertFalse(Path(seen['path']).exists())


if __name__=='__main__':unittest.main()
