"""Verify native CosyVoice controls at the actual adapter sampling boundary."""
import contextlib
import importlib.util
import math
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Resources'))
from voice_expression import native_cosy_temperature


class Scores:
    def __init__(self, values): self.values=tuple(values)
    def __truediv__(self, value): return Scores([x/value for x in self.values])
    def probabilities(self):
        values=[math.exp(x-max(self.values)) for x in self.values]
        return [x/sum(values) for x in values]


class Audio:
    def detach(self): return self
    def float(self): return self
    def cpu(self): return self
    def numpy(self): return self
    def reshape(self, *shape): return self


class SamplingTests(unittest.TestCase):
    def test_temperature_changes_distribution_and_preserves_sampling_arguments(self):
        seen=[]
        def original(scores,*args,**kwargs):
            seen.append((scores,args,kwargs));return scores.probabilities()
        llm=SimpleNamespace(sampling=original)
        model=SimpleNamespace(model=SimpleNamespace(llm=llm))
        scores=Scores([math.log(.7),math.log(.3)])
        with native_cosy_temperature(model,.5):
            cold=llm.sampling(scores,[1,2],25,top_p=.8)
        with native_cosy_temperature(model,1):
            base=llm.sampling(scores,[1,2],25,top_p=.8)
        self.assertGreater(cold[0],base[0])
        self.assertAlmostEqual(base[0],.7)
        self.assertIs(seen[-1][0],scores)
        self.assertEqual(seen[0][1:],(([1,2],25),{'top_p':.8}))
        self.assertIs(llm.sampling,original)

    def test_failure_restores_original_and_unsupported_controls_fail_before_inference(self):
        original=lambda *a: None
        llm=SimpleNamespace(sampling=original)
        model=SimpleNamespace(model=SimpleNamespace(llm=llm))
        with self.assertRaisesRegex(RuntimeError,'inference stopped'):
            with native_cosy_temperature(model,.7):raise RuntimeError('inference stopped')
        self.assertIs(llm.sampling,original)
        for value in [0,float('nan'),1.01]:
            with self.assertRaises(ValueError):
                with native_cosy_temperature(model,value):self.fail('Invalid temperature entered inference')
        with self.assertRaises(ValueError):
            with native_cosy_temperature(SimpleNamespace(),.7):self.fail('Missing backend entered inference')

    def test_both_actual_adapters_apply_controls_and_restore_after_early_close(self):
        for relative in ['Resources/cosy_native.py','windows/native_cosy.py']:
            with self.subTest(adapter=relative):
                spec=importlib.util.spec_from_file_location('sampling323_'+Path(relative).stem,ROOT/relative)
                module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
                calls=[];writes=[]
                def original(scores,*args,**kwargs):
                    calls.append(scores.probabilities());return 1
                llm=SimpleNamespace(sampling=original)
                class Model:
                    model=SimpleNamespace(llm=llm)
                    def inference_instruct2(self,text,instruction,path,**kwargs):
                        self.seen=(text,instruction,path,kwargs)
                        llm.sampling(Scores([math.log(.7),math.log(.3)]),[],25)
                        yield {'tts_speech':Audio()}
                        raise AssertionError('Early close must not request another chunk')
                model=Model();wrapper=module.NativeCosy(model);reference=object()
                fake_np=SimpleNamespace(asarray=lambda value,**kw:value,float32='float32')
                fake_sf=SimpleNamespace(write=lambda *args:writes.append(args))
                fake_torch=SimpleNamespace(inference_mode=contextlib.nullcontext)
                with patch.dict(sys.modules,{'numpy':fake_np,'soundfile':fake_sf,'torch':fake_torch}):
                    generator=wrapper.generate('你好',reference,'You are a helpful assistant. 请用广东话表达。',temperature=.5)
                    next(generator)
                    self.assertIsNot(llm.sampling,original)
                    generator.close()
                self.assertIs(llm.sampling,original)
                self.assertGreater(calls[0][0],.7)
                self.assertIs(writes[0][1],reference)
                self.assertEqual(model.seen[0],'你好')
                self.assertTrue(model.seen[1].endswith('<|endofprompt|>'))
                self.assertFalse(Path(model.seen[2]).exists())


if __name__=='__main__':unittest.main()
