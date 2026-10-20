import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import numpy as np
import visual_speakers as visual

class VisualRoles(unittest.TestCase):
    def fixture(self):
        cues=[dict(start=i*4,end=i*4+3,speakerId='a' if i<2 else 'b') for i in range(4)]
        profiles=[dict(id='a',reference='a.wav'),dict(id='b',reference='b.wav')]
        rows=[dict(index=i,visualId='v1',speaking=True,mouthChanged=True,multipleSpeakers=False,continuousShot=True,headVisible=True,confidence=.99) for i in range(4)]
        vectors=np.array([[1.,0],[1.,0],[.6,.8],[.6,.8]])
        return cues,profiles,rows,vectors
    def fuse(self,mutate=None):
        c,p,r,v=self.fixture()
        if mutate:mutate(c,r,v)
        profiles,changed=visual.fuse(c,p,r,v,range(4));return c,profiles,changed
    def test_two_corroborated_visual_turns_and_compatible_voices_merge(self):
        c,p,changed=self.fuse();self.assertEqual(changed,[3,4]);self.assertEqual([x['id'] for x in p],['a']);self.assertEqual(c[2]['acousticSpeakerId'],'b')
    def test_single_visual_turn_is_not_enough(self):
        c,p,changed=self.fuse(lambda c,r,v:r.pop());self.assertEqual(changed,[])
    def test_open_static_mouth_is_not_speech_evidence(self):
        c,p,changed=self.fuse(lambda c,r,v:r[2].update(mouthChanged=False));self.assertEqual(changed,[])
    def test_mixed_voices_are_not_merged(self):
        c,p,changed=self.fuse(lambda c,r,v:c[2].update(mixedVoices=True));self.assertEqual(changed,[])
    def test_visual_only_similarity_cannot_override_unrelated_voice(self):
        c,p,r,v=self.fixture();v[2:]=[0,1];self.assertEqual(visual.fuse(c,p,r,v,range(4))[1],[])
    def test_two_simultaneous_roles_cannot_be_merged(self):
        c,p,changed=self.fuse(lambda c,r,v:c[2].update(start=1,end=4));self.assertEqual(changed,[])
    def test_contradictory_visual_identity_keeps_audio(self):
        c,p,changed=self.fuse(lambda c,r,v:r[3].update(visualId='v2'));self.assertEqual(changed,[])
    def test_low_confidence_keeps_audio(self):
        c,p,changed=self.fuse(lambda c,r,v:r[3].update(confidence=.94));self.assertEqual(changed,[])
    def test_offscreen_unknown_keeps_audio(self):
        c,p,changed=self.fuse(lambda c,r,v:r[3].update(visualId='unknown',speaking=False));self.assertEqual(changed,[])
    def test_reaction_shot_cut_keeps_audio(self):
        c,p,changed=self.fuse(lambda c,r,v:r[3].update(continuousShot=False));self.assertEqual(changed,[])
    def test_brief_uncertain_turn_requires_acoustic_support(self):
        c,p,r,v=self.fixture();c[2].update(end=c[2]['start']+.5,speakerNote='短句');r.pop();profiles,changed=visual.fuse(c,p,r,v,range(4));self.assertEqual(changed,[3]);self.assertEqual(c[3]['speakerId'],'b')
    def test_audio_mode_never_loads_visual_model(self):
        c,p,_,_=self.fixture()
        with patch.object(visual,'model_id',side_effect=AssertionError('must not load')):
            self.assertEqual(visual.refine({'roleAnalysisMode':'audio'},'.',c,p,lambda *a:None),(c,p))
    def test_masked_portrait_retains_full_frame_without_claiming_speaker_merge(self):
        c,p,r,v=self.fixture()
        for row in r:row.update(speaking=False,mouthChanged=False,headVisible=True,characterBox=[.2,.1,.4,.5])
        self.assertEqual(visual.fuse(c,p,r,v,range(4))[1],[])
        def extract(args,**kwargs):Path(args[-1]).write_bytes(b'isolated-image-fixture')
        with tempfile.TemporaryDirectory() as d,patch.object(visual.subprocess,'run',side_effect=extract) as run:
            visual.attach_avatars({'ffmpeg':'ffmpeg','video':'source.mkv','startOffset':10},d,c,p,{'roster':[{'id':'v1','appearance':'Red masked helmet'}],'rows':r})
            self.assertAlmostEqual(p[0]['avatarTime'],1.86)
            self.assertTrue(Path(p[0]['sourceFrame']).exists())
            self.assertEqual(len(p[0]['portraits']),2)
            self.assertAlmostEqual(float(run.call_args_list[0].args[0][5]),11.86)
    def test_hands_torso_or_missing_head_confirmation_never_create_portrait(self):
        for head in (False,None):
            c,p,r,v=self.fixture()
            for row in r:
                row['characterBox']=[.2,.1,.4,.5]
                if head is None:row.pop('headVisible')
                else:row['headVisible']=head
            with tempfile.TemporaryDirectory() as d,patch.object(visual.subprocess,'run') as run:
                visual.attach_avatars({'ffmpeg':'ffmpeg','video':'source.mkv'},d,c,p,{'roster':[{'id':'v1','appearance':'Red helmet'}],'rows':r})
                self.assertFalse(run.called);self.assertTrue(all('avatar' not in profile for profile in p))
    def test_conflicting_unconfirmed_portraits_are_not_assigned(self):
        c,p,r,v=self.fixture()
        for row in r:row.update(speaking=False,mouthChanged=False,headVisible=True,characterBox=[.2,.1,.4,.5])
        r[1]['visualId']='v2'
        with tempfile.TemporaryDirectory() as d,patch.object(visual.subprocess,'run'):
            visual.attach_avatars({'ffmpeg':'ffmpeg','video':'source.mkv'},d,c,p,{'roster':[{'id':'v1','appearance':'Red helmet'},{'id':'v2','appearance':'Blue helmet'}],'rows':r})
            self.assertNotIn('avatar',p[0])
    def test_three_independently_observed_fragments_can_establish_visual_anchor(self):
        c,p,r,v=self.fixture();c=c[:3];r=r[:3];v=v[:3]
        for i in range(3):c[i]['speakerId']=str(i)
        p=[dict(id=str(i),reference=str(i)+'.wav',shortReference=i==0,referenceQuality={'score':i*20}) for i in range(3)]
        result,changed=visual.fuse(c,p,r,v,range(3))
        self.assertEqual(changed,[2,3]);self.assertEqual(len(result),1);self.assertEqual(result[0]['reference'],'2.wav')
    def test_global_anchor_rejects_incompatible_third_fragment(self):
        c,p,r,v=self.fixture();c=c[:3];r=r[:3];v=v[:3];v[2]=[0,1]
        for i in range(3):c[i]['speakerId']=str(i)
        p=[dict(id=str(i)) for i in range(3)]
        self.assertEqual(visual.fuse(c,p,r,v,range(3))[1],[])
    def test_missing_model_continues_with_auditable_reason(self):
        c,p,_,_=self.fixture();events=[]
        with tempfile.TemporaryDirectory() as d,patch.object(visual,'model_id',side_effect=ValueError('missing model')):
            actual=visual.refine({'roleAnalysisMode':'audiovisual'},d,c,p,lambda *a:events.append(a))
            self.assertEqual(actual,(c,p));summary=json.loads(Path(d,'visual-role-summary.json').read_text());self.assertEqual(summary['actual'],'audio');self.assertEqual(summary['reason'],'missing model');self.assertTrue(events)

if __name__=='__main__':unittest.main()
