"""Run retained-source translation boundaries without a model or user media."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Resources'))
import dub_languages
import hk_spoken_style
import normal_mode
import target_draft
import update_plan
from worker import atomic_json


class DubbingUpdate425(unittest.TestCase):
    def cue(self, **values):
        return dict(dict(start=0, end=2, text='泣きたい', japanese='泣きたい',
                         cantonese='我好想喊。', english='Stale draft.', mandarin='旧翻译。'), **values)

    def test_changed_language_clears_only_child_target_and_keeps_unknown_and_song(self):
        cues=[self.cue(), self.cue(text='[UNCONFIRMED_SOURCE]', japanese='[UNCONFIRMED_SOURCE]',
              sourcePolicyBlocked=True, noSpeech=False), self.cue(noSpeech=True,
              preserveOriginalSpeech=True, originalSpeechReason='opening-song')]
        original=copy.deepcopy(cues)
        cfg=dict(updateRecordingPlan=dict(revision=update_plan.REVISION, target=['zh','drama3'], translateFromOriginal=True))
        update_plan.prepare_cues(cfg,cues)
        self.assertEqual(original[0]['mandarin'],'旧翻译。')
        self.assertEqual(cues[0]['mandarin'],'')
        self.assertEqual(cues[0]['cantonese'],original[0]['cantonese'])
        self.assertEqual(cues[0]['japanese'],original[0]['japanese'])
        self.assertFalse(cues[1]['noSpeech']);self.assertTrue(cues[1]['preserveOriginalSpeech'])
        self.assertTrue(cues[2]['noSpeech']);self.assertEqual(cues[2]['originalSpeechReason'],'opening-song')
        self.assertEqual([(c['start'],c['end']) for c in cues],[(0,2)]*3)

    def test_same_language_keeps_verified_saved_words(self):
        cues=[self.cue()];before=copy.deepcopy(cues)
        cfg=dict(updateRecordingPlan=dict(revision=update_plan.REVISION,target=['yue','drama3'],translateFromOriginal=False))
        update_plan.prepare_cues(cfg,cues)
        self.assertEqual(cues,before)
        self.assertTrue(update_plan.source_language_changed(dict(config=dict(defaultDubLanguage='yue')),'en'))
        self.assertFalse(update_plan.source_language_changed(dict(config=dict(defaultDubLanguage='yue')),'yue'))

    def translate(self, folder, answers, cues):
        w=Mock();w.atomic_json=atomic_json;w.traditional_cantonese=lambda cfg,text:text
        w.ollama_chat.side_effect=[json.dumps(a,ensure_ascii=False) for a in answers]
        cfg=dict(productionMode='normal',model='fixture',port=1,sourceLanguage='ja',dubLanguages=['yue'],
                 targetDraftRevision=target_draft.REVISION)
        with patch.object(normal_mode,'glossary',return_value=[]), patch.object(normal_mode,'ensure_scripts'), \
             patch('caption_alignment.prepare'), patch('caption_alignment.batches',return_value=[(0,len(cues))]), \
             patch('caption_alignment.payload',side_effect=lambda rows,*args:rows), \
             patch('own_turn.guard',side_effect=lambda w,c,j,rows,i,l,t:t), \
             patch('source_proofread.review'), patch('caption_speech_guard.review'), patch('terminology.audit'), \
             patch('translation_brevity.review'):
            normal_mode.translate(w,cfg,folder,cues)
        return w

    def test_actual_translation_retry_receives_bad_draft_and_original(self):
        with tempfile.TemporaryDirectory() as d:
            cues=[self.cue(cantonese='')]
            w=self.translate(Path(d),[{'0':'我好想泣きたい。'},{'0':'我好想喊。'}],cues)
            second=json.loads(w.ollama_chat.call_args_list[1].args[2][1]['content'])['0']
            self.assertEqual(second['previousTargetDraft'],'我好想泣きたい。')
            self.assertEqual(second['japanese'],'泣きたい')
            self.assertEqual(cues[0]['cantonese'],'我好想喊。')
            self.assertEqual(w.ollama_chat.call_count,2)
            self.assertEqual(self.translate(Path(d),[],cues).ollama_chat.call_count,0)

    def test_exhausted_retry_does_not_reset_on_resume_or_mark_silence(self):
        with tempfile.TemporaryDirectory() as d:
            cues=[self.cue(cantonese='')]
            self.assertEqual(self.translate(Path(d),[{'0':'かな'},{'0':'かな'}],cues).ollama_chat.call_count,2)
            self.assertEqual(self.translate(Path(d),[],cues).ollama_chat.call_count,0)
            self.assertEqual(cues[0]['cantonese'],'');self.assertFalse(cues[0].get('noSpeech',False))
            self.assertIn('missing-cantonese',cues[0]['normalDefects'])

    def test_actual_mandarin_retry_uses_original_not_cantonese(self):
        with tempfile.TemporaryDirectory() as d:
            cues=[self.cue(mandarin='')]
            w=Mock();w.atomic_json=atomic_json
            w.ollama_chat.side_effect=['{"0":"かな"}','{"0":"我很想哭。"}']
            with patch('output_language.simplified',side_effect=lambda cfg,text:text), \
                 patch('own_turn.guard',side_effect=lambda w,c,j,rows,i,l,t:t):
                dub_languages.mandarin_script(w,dict(model='fixture',port=1,targetDraftRevision=target_draft.REVISION),Path(d),cues)
            row=json.loads(w.ollama_chat.call_args_list[1].args[2][1]['content'])['0']
            self.assertEqual(row['sourceSpeech'],'泣きたい')
            self.assertEqual(row['previousTargetDraft'],'かな')
            self.assertNotIn('我好想喊',json.dumps(row,ensure_ascii=False))
            self.assertEqual(cues[0]['mandarin'],'我很想哭。')

    def test_contextual_crying_examples_do_not_rewrite_quotes_or_shouting(self):
        cfg=dict(hongKongStyleRevision=hk_spoken_style.REVISION)
        self.assertIn('我好想喊。',[r['spoken'] for r in hk_spoken_style.retrieve(cfg,'我想哭。')])
        self.assertIn('佢大聲嗌救命。',[r['spoken'] for r in hk_spoken_style.retrieve(cfg,'cry for help',source_language='en')])
        self.assertEqual(hk_spoken_style.normalize(cfg,'電影「哭」好出名。'),'電影「哭」好出名。')
        legacy=dict(hongKongStyleRevision=hk_spoken_style.SOURCE_REVISION)
        self.assertFalse(any(r['id'].startswith('hk421') for r in hk_spoken_style.retrieve(legacy,'我想哭。')))

    def test_actual_reference_cache_reuses_same_source_and_rejects_changed_reference(self):
        import independent_voices
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'dialogue.wav';source.write_bytes(b'isolated source')
            reference=root/'reference.wav';reference.write_bytes(b'isolated reference')
            cfg=dict(storage=d,dialoguePath=str(source),productionMode='normal',sourceLanguage='ja')
            cues=[self.cue()];stat=source.stat()
            identity=[independent_voices.policy_revision(cfg),'normal',str(source),stat.st_size,
                      stat.st_mtime_ns,None,'',[(0,2,None,None,True,False)]]
            key=hashlib.sha256(json.dumps(identity).encode()).hexdigest()
            profile=dict(id='r',reference=str(reference),promptText='泣きたい',
                         referenceSHA256=hashlib.sha256(reference.read_bytes()).hexdigest())
            child=root/'child';child.mkdir()
            atomic_json(child/'independent-voices.json',dict(key=key,profiles=[profile],assignments=[dict(index=0,speakerId='r')]))
            with patch('dubbing.model_job',side_effect=RuntimeError('reference regeneration requested')) as generate:
                independent_voices.assign(cfg,child,cues,Mock())
                self.assertEqual(generate.call_count,0);self.assertEqual(cues[0]['speakerId'],'r')
                reference.write_bytes(b'changed reference')
                with self.assertRaisesRegex(RuntimeError,'regeneration requested'):
                    independent_voices.assign(cfg,child,cues,Mock())

    def test_changed_source_file_fails_before_translation(self):
        import primary_source
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'source.mp4';source.write_bytes(b'original')
            cfg=dict(sourcePolicyRevision=primary_source.REVISION,video=str(source),
                     sourceVideoSnapshot=dict(path=str(source),bytes=source.stat().st_size,mtimeNS=source.stat().st_mtime_ns))
            primary_source.verify(cfg)
            source.write_bytes(b'changed source')
            with self.assertRaisesRegex(ValueError,'changed'):primary_source.verify(cfg)


if __name__=='__main__':unittest.main()
