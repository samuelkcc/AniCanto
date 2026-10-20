import copy,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import role_reanalysis as roles,project_edit


class RoleReanalysisTests(unittest.TestCase):
    def fixture(self,folder):
        reference=folder/'reference.wav';reference.write_bytes(b'original voice')
        p=dict(id='auto-old-1',name='自動角色 1',reference=str(reference),promptText='source')
        cues=[dict(editorID=str(i),editorSources=[i],start=i*4,end=i*4+3,text='原文',japanese='原文',cantonese='已保存台詞',english='Approved English',speakerId=p['id'],identityEvidence=dict(state='acoustic-anchor')) for i in range(3)]
        source=dict(config=dict(voiceProfiles=[p]),cues=copy.deepcopy(cues))
        cfg=dict(reanalyzeRoles=True,storage=str(folder),port=0,voiceProfiles=[p],visualModel=roles.MODEL)
        w=SimpleNamespace(emit=Mock(),run=Mock(),atomic_json=lambda p,d:Path(p).write_text(json.dumps(d)),ollama_chat=Mock())
        return p,cues,source,cfg,w

    def test_frozen_reference_path_with_same_bytes_is_not_manual(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);p,cues,source,cfg,w=self.fixture(folder)
            frozen=folder/'hash.wav';frozen.write_bytes(b'original voice');p['reference']=str(frozen)
            # Source review owns a separate immutable copy, as JSON normally does.
            source['config']['voiceProfiles']=copy.deepcopy(source['config']['voiceProfiles'])
            source['config']['voiceProfiles'][0]['reference']=str(folder/'reference.wav')
            self.assertEqual(roles.protected_indices(cues,[p],source),set())
            frozen.write_bytes(b'manual voice')
            self.assertEqual(roles.protected_indices(cues,[p],source),{0,1,2})

    def test_manual_assignment_custom_reference_and_disabled_cue_are_protected(self):
        with tempfile.TemporaryDirectory() as d:
            p,cues,source,cfg,w=self.fixture(Path(d))
            cues[0]['speakerId']='manual-role';cues[1]['enabled']=False
            self.assertEqual(roles.protected_indices(cues,[p],source),{0,1})
            p['engineReferences']={'cosyvoice3:yue':{'enabled':True,'reference':'custom'}}
            self.assertEqual(roles.protected_indices(cues,[p],source),{0,1,2})

    def test_new_version_only_and_changed_roles_invalidate_old_adopted_take(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);p,cues,source,cfg,w=self.fixture(folder)
            cues[2]['speakerId']='manual-role';cues[0]['editorAudio']='old.wav'
            cfg['voiceProfiles'].append(dict(id='manual-role',name='manual',reference=p['reference'],promptText='source'))
            before=copy.deepcopy(cues);source_before=copy.deepcopy(source)
            def assign(config,job,rows,run,emit):
                self.assertFalse(rows[2]['enabled']);self.assertEqual(config['visualModel'],roles.MODEL);self.assertTrue(config['requireVisualModel'])
                for c in rows:c['speakerId']='auto-new-1'
                config['voiceProfiles']=[dict(p,id='auto-new-1')];config['roleAnalysisResult']={'actual':'audiovisual'}
                return rows
            with patch('dubbing.separate',return_value=('background','dialogue')),patch('speakers.assign',side_effect=assign),patch.object(roles,'adjudicate',return_value=[]):
                out=roles.prepare(w,cfg,folder,cues,source)
            self.assertEqual(source,source_before);self.assertEqual(out[2],before[2]);self.assertNotIn('editorAudio',out[0])
            for a,b in zip(before,out):
                for key in ('start','end','cantonese','english','text','editorSources'):self.assertEqual(a[key],b[key])
            self.assertEqual({p['id'] for p in cfg['voiceProfiles']},{'auto-new-1','manual-role'})
            summary=json.loads((folder/'role-reanalysis.json').read_text());self.assertEqual(summary['changedIndices'],[1,2]);self.assertEqual(summary['protectedSegments'],1)

    def test_visual_failure_continues_with_acoustic_plan_and_reports_partial_analysis(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);p,cues,source,cfg,w=self.fixture(folder);before=copy.deepcopy(cues)
            def assign(config,*args):config['roleAnalysisResult']={'actual':'audio','reason':'missing model'};return args[1]
            with patch('dubbing.separate',return_value=('background','dialogue')),patch('speakers.assign',side_effect=assign):
                roles.prepare(w,cfg,folder,cues,source)
            self.assertEqual(cues,before)
            summary=json.loads((folder/'role-reanalysis.json').read_text());self.assertEqual(summary['status'],'partial');self.assertEqual(summary['analysisErrors'],['missing model'])

    def test_different_model_is_rejected_and_all_manual_cast_does_not_fake_inference(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);p,cues,source,cfg,w=self.fixture(folder);cfg['roleDecisionModel']='small'
            with self.assertRaises(ValueError):roles.prepare(w,cfg,folder,cues,source)
            cfg['roleDecisionModel']=roles.MODEL
            for c in cues:c['manual']=True
            with patch('speakers.assign',side_effect=AssertionError('manual cast must remain unchanged')):
                roles.prepare(w,cfg,folder,cues,source)
            w.ollama_chat.assert_not_called()

    def test_candidate_requires_repeated_visual_voice_and_no_overlap(self):
        cues=[dict(start=i*4,end=i*4+3,speakerId='anchor',visualEvidence=dict(visualId='v1',speaking=True,mouthChanged=True,continuousShot=True,multipleSpeakers=False,portraitInspected=True,confidence=.99),identityEvidence=dict(state='acoustic-anchor')) for i in range(3)]
        cues[2].update(speakerId='uncertain',identityEvidence=dict(state='uncertain'))
        matrix={i:np.array([1.,0]) for i in range(3)}
        rows=roles.evidence_requests(cues,[],matrix,set());self.assertEqual(rows['cue:2']['allowed'],['keep','anchor'])
        matrix[2]=np.array([0.,1]);self.assertEqual(roles.evidence_requests(cues,[],matrix,set())['cue:2']['allowed'],['keep'])
        matrix[2]=np.array([1.,0]);cues[2]['start']=1
        self.assertEqual(roles.evidence_requests(cues,[],matrix,set())['cue:2']['allowed'],['keep'])
        cues[2]['start']=8;cues[2]['visualEvidence']['mouthChanged']=False
        self.assertEqual(roles.evidence_requests(cues,[],matrix,set())['cue:2']['allowed'],['keep'])

    def test_model_decides_bounded_candidate_with_strict35b_and_invalid_choice_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);p,cues,source,cfg,w=self.fixture(folder)
            np.savez(folder/'speaker-embeddings.npz',indices=[0,1,2],vectors=np.ones((3,2)))
            rows={'cue:0':dict(kind='assignment',index=0,allowed=['keep','auto-other'],current=p['id'])}
            w.ollama_chat.return_value=json.dumps({'cue:0':dict(choice='auto-other',reason='重複畫面及聲紋支持')})
            with patch.object(roles,'evidence_requests',return_value=rows):roles.adjudicate(w,cfg,folder,cues,[p],set())
            self.assertEqual(cues[0]['speakerId'],'auto-other');self.assertTrue(w.ollama_chat.call_args.kwargs['strict_model']);self.assertEqual(w.ollama_chat.call_args.args[1],roles.MODEL)
            rows['cue:0']['current']='new fingerprint';w.ollama_chat.return_value=json.dumps({'cue:0':dict(choice='/arbitrary/file',reason='invented')})
            with patch.object(roles,'evidence_requests',return_value=rows):ds=roles.adjudicate(w,cfg,folder,cues,[p],set())
            self.assertTrue(ds[0]['invalid']);self.assertEqual(cues[0]['speakerId'],'auto-other')

    def test_model_failure_preserves_assignment_and_continues_without_claiming_repair(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);p,cues,source,cfg,w=self.fixture(folder)
            np.savez(folder/'speaker-embeddings.npz',indices=[0],vectors=np.ones((1,2)))
            w.ollama_chat.side_effect=RuntimeError('model unavailable')
            with patch.object(roles,'evidence_requests',return_value={'cue:0':dict(kind='assignment',index=0,allowed=['keep'])}):
                decisions=roles.adjudicate(w,cfg,folder,cues,[p],set())
            self.assertTrue(decisions[0]['analysisFailed']);self.assertEqual(decisions[0]['choice'],'keep');self.assertEqual(w.ollama_chat.call_count,1)

    def test_export_enters_role_analysis_before_tts_and_original_review_is_immutable(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p,cues,source,cfg,w=self.fixture(root)
            video=root/'source.mkv';video.write_bytes(b'source');source['config'].update(duration=12,video=str(video),ttsBackend='voxcpm2',storage=d)
            review=root/'review.json';review.write_text(json.dumps(source));original=review.read_bytes()
            draft=dict(id='version-new',review=str(review),segments=[dict(id=str(i),sources=[i],start=c['start'],end=c['end'],text=c['cantonese'],original=c['text'],speakerId=p['id']) for i,c in enumerate(cues)],settings=dict(reanalyzeRoles=True))
            submission=root/'submission.json';submission.write_text(json.dumps(draft))
            w.render_review=Mock(side_effect=AssertionError('no TTS after analysis failure'))
            with patch.object(roles,'prepare',side_effect=ValueError('Qwen not available')) as prepare,self.assertRaisesRegex(ValueError,'Qwen not available'):
                project_edit.render(w,dict(submission=str(submission)))
            prepare.assert_called_once();w.render_review.assert_not_called();self.assertEqual(review.read_bytes(),original)
            self.assertEqual(json.loads((root/'versions/version-new/version.json').read_text())['status'],'failed')

    def test_recovered_automatic_roles_are_compared_to_current_plan_not_stale_editor_base(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p,cues,source,cfg,w=self.fixture(root)
            video=root/'source.mkv';video.write_bytes(b'source');source['config'].update(duration=12,video=str(video),ttsBackend='voxcpm2',storage=d)
            (root/'review.json').write_text(json.dumps(source));base=copy.deepcopy(source);base['config']['voiceProfiles']=[]
            for c in base['cues']:c.pop('speakerId')
            (root/'editor-base.json').write_text(json.dumps(base))
            draft=dict(id='recovered-analysis',review=str(root/'review.json'),segments=[dict(id=str(i),sources=[i],start=c['start'],end=c['end'],text=c['cantonese'],original=c['text'],speakerId=p['id']) for i,c in enumerate(cues)],settings=dict(reanalyzeRoles=True,voiceProfiles=[p]))
            submission=root/'submission.json';submission.write_text(json.dumps(draft))
            def check(worker,config,folder,rows,identity):
                self.assertEqual(roles.protected_indices(rows,config['voiceProfiles'],identity),set())
                raise ValueError('checked current identity plan')
            with patch.object(roles,'prepare',side_effect=check),self.assertRaisesRegex(ValueError,'checked current'):
                project_edit.render(w,dict(submission=str(submission)))

    def test_sequential_model_decisions_cannot_create_overlapping_same_role(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);p,cues,source,cfg,w=self.fixture(folder)
            cues[1].update(start=1,end=4)
            np.savez(folder/'speaker-embeddings.npz',indices=[0,1],vectors=np.ones((2,2)))
            rows={f'cue:{i}':dict(kind='assignment',index=i,current=c['speakerId'],allowed=['keep','target']) for i,c in enumerate(cues[:2])}
            w.ollama_chat.return_value=json.dumps({key:dict(choice='target',reason='候選證據') for key in rows})
            with patch.object(roles,'evidence_requests',return_value=rows):ds=roles.adjudicate(w,cfg,folder,cues,[p],set())
            self.assertEqual(cues[0]['speakerId'],'target');self.assertEqual(cues[1]['speakerId'],p['id']);self.assertEqual(ds[1]['veto'],'overlapping-resulting-role')

    def test_reference_selection_is_bounded_to_clean_same_role_recordings(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);p,cues,source,cfg,w=self.fixture(folder)
            alternate=folder/'alternate.wav';alternate.write_bytes(b'clean same role')
            p['referenceCandidates']=[dict(reference=str(alternate),promptText='clean source transcript',range=[0,4],quality=dict(score=90))]
            p['mixedReference']=True;p['referenceQuality']={'score':30}
            np.savez(folder/'speaker-embeddings.npz',indices=[0,1,2],vectors=np.ones((3,2)))
            w.ollama_chat.return_value=json.dumps({'ref:'+p['id']:dict(choice='1',reason='較清晰同角色原聲')})
            roles.adjudicate(w,cfg,folder,cues,[p],set())
            self.assertEqual(p['reference'],str(alternate));self.assertEqual(p['promptText'],'clean source transcript');self.assertFalse(p['mixedReference'])

    def test_malformed_batch_retries_individual_items_and_preserves_each_success(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);p,cues,source,cfg,w=self.fixture(folder)
            np.savez(folder/'speaker-embeddings.npz',indices=[0,1],vectors=np.ones((2,2)))
            rows={f'cue:{i}':dict(kind='assignment',index=i,current=p['id'],allowed=['keep']) for i in range(2)}
            w.ollama_chat.side_effect=[RuntimeError('HTTP 422 invalid JSON'),json.dumps({'cue:0':dict(choice='keep',reason='證據不足')}),RuntimeError('HTTP 422 invalid JSON')]
            with patch.object(roles,'evidence_requests',return_value=rows):ds=roles.adjudicate(w,cfg,folder,cues,[p],set())
            self.assertEqual(w.ollama_chat.call_count,3);self.assertFalse(ds[0].get('analysisFailed'));self.assertTrue(ds[1]['analysisFailed'])
            self.assertEqual(len(json.loads((folder/'role-decisions.json').read_text())),2)
            with patch.object(roles,'evidence_requests',return_value=rows):roles.adjudicate(w,cfg,folder,cues,[p],set())
            self.assertEqual(w.ollama_chat.call_count,3,'Resume must not regenerate cached successful or conservative keep decisions')
            self.assertTrue(all(c.kwargs['constrained_json'] for c in w.ollama_chat.call_args_list))

    def test_compact_payload_shares_cast_and_omits_box_coordinates(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);p,cues,source,cfg,w=self.fixture(folder)
            np.savez(folder/'speaker-embeddings.npz',indices=[0],vectors=np.ones((1,2)))
            rows={'cue:0':dict(kind='assignment',index=0,current=p['id'],allowed=['keep'],cast=[{'id':'a'}],visual=dict(visualId='v1',characters=['large raw head boxes'],mouthChanged=False))}
            w.ollama_chat.return_value=json.dumps({'cue:0':dict(choice='keep',reason='證據不足')})
            with patch.object(roles,'evidence_requests',return_value=rows):roles.adjudicate(w,cfg,folder,cues,[p],set())
            payload=json.loads(w.ollama_chat.call_args.args[2][1]['content']);self.assertEqual(payload['cast'],[{'id':'a'}]);self.assertNotIn('cast',payload['items']['cue:0']);self.assertNotIn('characters',payload['items']['cue:0']['visual'])

if __name__=='__main__':unittest.main()
