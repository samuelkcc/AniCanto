"""Build 245 contract: one standard mode, switches, source-matched script length.

Written in English to the ASD-STE100 style. Quoted Chinese and Japanese strings
are fixture data and stay literal.
"""
import sys, unittest
from pathlib import Path
ROOT=Path(__file__).parents[1]
sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows'),str(ROOT/'tests')]
import cantonese_style, delivery_policy, hong_kong_dialogue, source_mora, speech_timing, work_modes

STAMPED=dict(deliveryPolicyRevision=delivery_policy.REVISION,
    forcedDubbingRevision=delivery_policy.FORCED_TTS_REVISION,
    workModeRevision=work_modes.REVISION, workMode='performance')

def frozen(**over):
    """A new collapsed-mode job before the worker freezes it."""
    cfg=dict(workMode='balanced',workModeRevision=work_modes.REVISION,fullAIReview=False,
        aiAutoFix=False,automaticAlternateVoice=True,automaticSystemVoice=True,
        roleAnalysisMode='independent',productionMode='normal')
    cfg.update(over)
    return work_modes.configure(cfg)

class ModeCollapseTests(unittest.TestCase):
    def test_revision_two_offers_one_work_mode(self):
        self.assertEqual(work_modes.MODES,('performance',))
        cfg=frozen()
        self.assertEqual(work_modes.mode(cfg),'performance')
        self.assertEqual(cfg['workMode'],'performance')
        self.assertEqual(cfg['productionMode'],'fast')
        self.assertEqual(cfg['normalRepairPolicy'],'missing-only')
        self.assertFalse(cfg['automaticDurationRewrite'])
        self.assertEqual(cfg['maximumTimingRewritePasses'],0)
        self.assertEqual(cfg['maximumMissingRepairAttempts'],2)
        self.assertEqual(cfg['sourceMatchedScriptRevision'],source_mora.REVISION)

    def test_repair_switch_off_removes_voice_substitution(self):
        cfg=frozen(aiAutoFix=False)
        self.assertFalse(cfg['automaticAlternateVoice'])
        self.assertFalse(cfg['automaticSystemVoice'])
        self.assertFalse(work_modes.ai_repair(cfg))

    def test_repair_switch_on_lands_the_users_fallback_choices(self):
        cfg=frozen(aiAutoFix=True)
        self.assertTrue(cfg['automaticAlternateVoice'])
        self.assertTrue(cfg['automaticSystemVoice'])
        self.assertTrue(work_modes.ai_repair(cfg))
        kept=frozen(aiAutoFix=True,automaticAlternateVoice=False,automaticSystemVoice=False)
        self.assertFalse(kept['automaticAlternateVoice'])
        self.assertFalse(kept['automaticSystemVoice'])

    def test_full_ai_review_does_not_turn_on_repair(self):
        cfg=frozen(fullAIReview=True)
        self.assertEqual(cfg['productionMode'],'standard')
        self.assertFalse(cfg['aiAutoFix'])
        self.assertEqual(cfg['maximumTimingRewritePasses'],1)
        self.assertTrue(cfg['visualRoleAnalysisEnabled'])
        self.assertEqual(cfg['roleAnalysisMode'],'audiovisual')

    def test_revision_one_jobs_keep_the_old_three_modes(self):
        cfg=dict(workMode='quality',workModeRevision=work_modes.REVISION_1,fullAIReview=False,
            aiAutoFix=True,automaticAlternateVoice=True,automaticSystemVoice=True)
        work_modes.configure(cfg)
        self.assertEqual(cfg['workMode'],'quality')
        self.assertEqual(cfg['normalRepairPolicy'],'verified')
        self.assertTrue(cfg['automaticDurationRewrite'])
        self.assertEqual(cfg['maximumTimingRewritePasses'],2)
        self.assertTrue(work_modes.ai_repair(cfg))

class SourceMatchedScriptTests(unittest.TestCase):
    cfg=dict(STAMPED,sourceMatchedScriptRevision=source_mora.REVISION)
    def test_morae_count_kana_and_kanji(self):
        self.assertEqual(source_mora.morae('ありがとう'),5.)
        self.assertEqual(source_mora.morae('おはようございます'),9.)
        self.assertAlmostEqual(source_mora.morae('学校'),source_mora.KANJI_MORA*2)
    def test_mora_target_sets_the_script_length_when_the_window_is_long(self):
        target=source_mora.target_characters(self.cfg,
            dict(japanese='おはようございます',speechStart=10.,speechEnd=20.))
        self.assertEqual(target,int(round(9*source_mora.MORA_TO_CHARACTERS)))
    def test_the_speech_window_caps_a_short_line(self):
        target=source_mora.target_characters(self.cfg,
            dict(japanese='おはようございます',speechStart=10.,speechEnd=11.4))
        self.assertEqual(target,int(1.4*source_mora.CHARACTERS_PER_SECOND))
    def test_a_cue_without_japanese_gets_no_target(self):
        self.assertIsNone(source_mora.target_characters(self.cfg,dict(text='你好',start=0,end=5)))
    def test_the_take_deadline_stops_at_its_own_caption_end_not_past_the_next_line(self):
        # Common case: caption and source speech end together, so the witnessed
        # speech deadline still closes the window.
        same=[dict(start=0.,end=4.,speechStart=0.,speechEnd=4.),
              dict(start=10.,end=20.,speechStart=10.,speechEnd=14.)]
        self.assertAlmostEqual(speech_timing.natural_window(same[0],same,60.,dict(self.cfg))[1],
                               4.+source_mora.END_GRACE_SECONDS)
        # A caption longer than the witnessed speech span may be filled to its own
        # end, which keeps the Chinese subtitle window from staying silent.
        cues=[dict(start=0.,end=10.,speechStart=0.,speechEnd=4.),
              dict(start=10.,end=20.,speechStart=10.,speechEnd=14.)]
        start,end=speech_timing.natural_window(cues[0],cues,60.,dict(self.cfg))
        self.assertEqual(start,0.)
        self.assertAlmostEqual(end,10.)
        # The next line always closes the window first.
        cues[1].update(start=6.,end=8.,speechStart=6.,speechEnd=8.)
        self.assertAlmostEqual(speech_timing.natural_window(cues[0],cues,60.,dict(self.cfg))[1],6.)
    def test_older_jobs_keep_the_full_gap_after_the_line(self):
        cues=[dict(start=0.,end=10.,speechStart=0.,speechEnd=4.),
              dict(start=10.,end=20.,speechStart=10.,speechEnd=14.)]
        self.assertAlmostEqual(speech_timing.natural_window(cues[0],cues,60.,{})[1],10.)
        self.assertAlmostEqual(speech_timing.natural_window(cues[0],cues,60.,
            dict(self.cfg,sourceSpeechEndCap=False))[1],10.)

class SpokenRegisterTests(unittest.TestCase):
    def test_written_forms_become_hong_kong_spoken_forms(self):
        self.assertEqual(cantonese_style.rewrite('我們為什麼不知道？'),'我哋點解唔知？')
        self.assertEqual(cantonese_style.rewrite('這個非常謝，沒有感覺'),'呢個好謝，冇覺得')
    def test_the_two_register_passes_carry_new_revisions(self):
        self.assertEqual(cantonese_style.REVISION,'hk-register-3-spoken-particles')
        self.assertEqual(hong_kong_dialogue.REVISION,'hong-kong-cantonese-2-spoken-register')
    def test_the_drafting_prompt_asks_for_acted_spoken_dialogue(self):
        cfg=dict(STAMPED,sourceMatchedScriptRevision=source_mora.REVISION)
        prompt=delivery_policy.instruction(cfg)
        self.assertIn('mora',prompt)
        self.assertIn('actor',prompt)
        self.assertNotEqual(prompt,delivery_policy.PROMPT)
        self.assertEqual(delivery_policy.instruction(dict(STAMPED)),delivery_policy.PROMPT)

if __name__=='__main__':unittest.main()
