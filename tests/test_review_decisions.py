"""Track-specific recovery evidence and explicit user fallback boundaries."""
import copy,json,sys,tempfile,unittest,wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'Resources'))
import review_report,review_choices
class ReviewDecisionTests(unittest.TestCase):
 def save(self,p,value):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value))
 def fixture(self,root):
  video=root/'original.mkv';video.write_bytes(b'original test fixture')
  review=dict(config=dict(video=str(video),duration=6,selectedEngines=['drama3','gpt-sovits'],dubLanguages=['yue','en']),meta=dict(streams=[dict(codec_type='audio')]),cues=[dict(index=1,start=0,end=2,cantonese='完整台詞',english='Complete words'),dict(index=2,start=4,end=6,cantonese='下一句')])
  draft=dict(segments=[dict(sources=[0],start=0,end=2,text='完整台詞',english='Complete words')]);return review,draft
 def test_empty_report_during_processing_is_never_a_quality_pass(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);review,_=self.fixture(r);result=review_report.project(r,review,dict(status='running'))
   self.assertTrue(result['reviewState']['processing']);self.assertFalse(result['reviewState']['qualityChecked'])
   result=review_report.project(r,review,dict(status='attention',lastError=dict(message='Missing output')));self.assertEqual(result['reviewState']['projectProblem'],'Missing output')
 def test_track_coverage_and_recovery_are_projected_without_obsolete_folders(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);review,_=self.fixture(r);child=r/'tracks/current';child.mkdir(parents=True)
   self.save(r/'track-progress.json',dict(tracks=[dict(folder=str(child))]));self.save(child/'review.json',dict(config=dict(ttsBackend='drama3',targetLanguage='en')))
   self.save(r/'dialogue-delivery-audit.json',dict(tracks=[dict(engine='drama3',language='en',rows=[dict(index=1,available=False)])]))
   self.save(child/'automatic-recovery.json',dict(rows={'1':dict(index=1,attempts=[dict(status='generating')])}))
   self.save(r/'tracks/obsolete/segment-issues.json',[dict(index=2,kind='obsolete')]);result=review_report.project(r,review,dict(status='running'))
   self.assertEqual(len(result['issues']),1);self.assertEqual(result['issues'][0]['language'],'en');self.assertEqual(result['issues'][0]['status'],'repairing');self.assertEqual(result['issues'][0]['text'],'Complete words')
 def test_original_audio_choice_is_explicit_and_scoped_to_one_track(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);review,draft=self.fixture(r);review_choices.select(r,review,draft,{},0,'drama3','yue','original')
   cue=dict(cantonese='完整台詞',editorDecisions=copy.deepcopy(draft['segments'][0]['reviewDecisions']));cfg=dict(editorRender=True,_editorSourceRoot=str(r))
   self.assertTrue(review_choices.apply([cue],cfg,'drama3','yue')[0]['preserveOriginalSpeech']);self.assertNotIn('preserveOriginalSpeech',review_choices.apply([cue],cfg,'gpt-sovits','yue')[0]);self.assertFalse(draft['segments'][0]['reviewDecisions']['yue:drama3']['qualityCertified'])
 def test_defect_recording_requires_confirmation_and_immutable_project_copy(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);review,draft=self.fixture(r);p=r/'takes/one.wav';p.parent.mkdir()
   with wave.open(str(p),'wb') as f:f.setparams((1,2,16000,16000,'NONE','not compressed'));f.writeframes(b'\0\0'*16000)
   snap=dict(takes=[dict(index=1,engine='drama3',language='yue',audio=str(p),text='完整台詞')])
   with self.assertRaisesRegex(ValueError,'Confirm'):review_choices.select(r,review,draft,snap,0,'drama3','yue','recording',str(p))
   review_choices.select(r,review,draft,snap,0,'drama3','yue','recording',str(p),True);choice=draft['segments'][0]['reviewDecisions']['yue:drama3'];accepted=Path(choice['audio']);self.assertNotEqual(accepted,p);self.assertEqual(accepted.read_bytes(),p.read_bytes());accepted.write_bytes(b'changed')
   cue=dict(cantonese='完整台詞',editorDecisions=draft['segments'][0]['reviewDecisions'])
   with self.assertRaisesRegex(ValueError,'changed'):review_choices.apply([cue],dict(editorRender=True,_editorSourceRoot=str(r)),'drama3','yue')
 def test_rejected_attempt_can_be_accepted_and_reexported(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);review,draft=self.fixture(r);p=r/'normal-repairs/rejected.wav';p.parent.mkdir()
   with wave.open(str(p),'wb') as f:f.setparams((1,2,16000,0,'NONE','not compressed'));f.writeframes(b'\x10\x00'*24000)
   snap=dict(issues=[dict(index=1,engine='drama3',language='yue',attempts=[dict(audition=dict(path=str(p)))])])
   review_choices.select(r,review,draft,snap,0,'drama3','yue','recording',str(p),True)
   cue=dict(cantonese='完整台詞',editorDecisions=draft['segments'][0]['reviewDecisions'])
   self.assertEqual(review_choices.apply([cue],dict(editorRender=True,_editorSourceRoot=str(r)),'drama3','yue')[0]['manualReviewChoice'],'accepted-defect-recording')
 def test_changed_words_and_split_lines_cannot_reuse_an_old_acceptance(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);review,draft=self.fixture(r);draft['segments'][0]['sources']=[0,1]
   with self.assertRaisesRegex(ValueError,'split or merged'):review_choices.select(r,review,draft,{},0,'drama3','yue','original')
   cue=dict(cantonese='changed',editorDecisions={'yue:drama3':dict(action='original',acceptedByUser=True,text='old')})
   with self.assertRaisesRegex(ValueError,'script'):review_choices.apply([cue],dict(editorRender=True,_editorSourceRoot=str(r)),'drama3','yue')
 def test_detailed_evidence_exposes_measured_lengths_and_three_scoped_audio_sources(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);review,_=self.fixture(r);review['cues'][0].update(japanese='原文',speakerId='own')
   for name in ('japanese-original.wav','dialogue.wav','candidate.wav'):
    with wave.open(str(r/name),'wb') as audio:audio.setparams((1,2,24000,0,'NONE','not compressed'));audio.writeframes(b'\x01\x00'*72000)
   review['config'].update(ttsBackend='drama3',targetLanguage='yue',dialoguePath=str(r/'dialogue.wav'),voiceProfiles=[dict(id='own',reference=str(r/'dialogue.wav'),language='ja')]);self.save(r/'review.json',review)
   self.save(r/'natural-placement.json',dict(rows=[dict(index=1,start=0,deadline=2,seconds=3.,fit=False)]))
   self.save(r/'automatic-recovery.json',dict(rows={'key':dict(index=1,selectedVerified=True,selectedAudio=str(r/'candidate.wav'),attempts=[dict(action='retry-clauses',status='adopted',candidateAudio=str(r/'candidate.wav'),check=dict(heard='完整台詞',decision='cantonese'))])}))
   result=review_report.project(r,review,dict(status='attention'));issue=result['issues'][0]
   self.assertEqual(issue['diagnostic']['sourceText'],'原文');self.assertEqual(issue['diagnostic']['overrunSeconds'],1.)
   self.assertEqual(set(issue['auditions']),{'original','separated','generated'});self.assertEqual(issue['auditions']['original']['end'],2)
   self.assertEqual(issue['attempts'][0]['audition']['path'],str((r/'candidate.wav').resolve()))
   self.assertEqual(result['reviewState']['repaired'],0,'Language proof cannot clear an unresolved timing failure')
 def test_audio_outside_the_project_is_not_exposed_as_an_audition(self):
  from review_diagnostics import enrich
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);job=root/'job';job.mkdir();external=root/'other.wav';external.write_bytes(b'outside')
   issue=dict(index=1,language='yue',evidence=[])
   enrich(issue,dict(start=0,end=1),dict(dialoguePath=str(external)),job,director=dict(selectedAudio=str(external)))
   self.assertEqual(issue['auditions'],{})
 def test_shared_separation_cache_uses_the_same_source_window_and_current_script(self):
  with tempfile.TemporaryDirectory() as d:
   storage=Path(d);root=storage/'jobs/project';root.mkdir(parents=True);stem=storage/'separations/pinned/dialogue.wav';stem.parent.mkdir(parents=True)
   video=storage/'source.mkv';video.write_bytes(b'video');stat=video.stat()
   self.save(stem.parent/'complete.json',[str(video.resolve()),stat.st_size,stat.st_mtime_ns,0,6,'test',None])
   for p in (root/'japanese-original.wav',stem,root/'reference.wav'):
    with wave.open(str(p),'wb') as f:f.setparams((1,2,16000,0,'NONE','not compressed'));f.writeframes(b'\0\0'*96000)
   review=dict(config=dict(storage=str(storage),video=str(video),duration=6,ttsBackend='drama3',dialoguePath=str(stem),voiceProfiles=[dict(id='own',reference=str(root/'reference.wav'))]),cues=[dict(start=2,end=4,cantonese='舊稿')])
   child=root/'tracks/current';self.save(root/'track-progress.json',dict(tracks=[dict(folder=str(child))]));self.save(child/'review.json',dict(config=review['config'],cues=[dict(start=2,end=4,cantonese='本次錄音稿',speakerId='own')]))
   self.save(child/'segment-issues.json',[dict(index=1,kind='timing-overrun')])
   issue=review_report.project(root,review,dict(status='attention'))['issues'][0]
   self.assertEqual(issue['text'],'本次錄音稿');self.assertEqual(issue['diagnostic']['translatedText'],issue['text'])
   self.assertEqual(issue['auditions']['original']['start'],2);self.assertEqual(issue['auditions']['original']['end'],4)
   self.assertEqual(issue['auditions']['separated'],dict(path=str(stem.resolve()),start=2,end=4))
   # A stale cache for another source/offset cannot masquerade as this stem.
   review['config']['startOffset']=1
   from review_diagnostics import enrich
   x=dict(index=1,evidence=[]);enrich(x,review['cues'][0],review['config'],root)
   self.assertNotIn('separated',x['auditions'])
 def test_short_reference_is_never_labelled_full_separated_audio(self):
  from review_diagnostics import enrich
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=root/'short-reference.wav'
   with wave.open(str(p),'wb') as f:f.setparams((1,2,16000,0,'NONE','not compressed'));f.writeframes(b'\0\0'*8000)
   issue=dict(index=1,evidence=[]);enrich(issue,dict(start=20,end=22,speakerId='own'),dict(voiceProfiles=[dict(id='own',reference=str(p))]),root)
   self.assertNotIn('separated',issue['auditions']);self.assertEqual(issue['diagnostic']['referenceSeconds'],.5)
 def test_float_stem_duration_is_measured_without_decoding_the_episode(self):
  import struct
  from review_diagnostics import duration
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'float.wav';pcm=b'\0'*16000*4
   fmt=struct.pack('<HHIIHH',3,1,16000,64000,4,32);body=b'WAVEfmt '+struct.pack('<I',16)+fmt+b'data'+struct.pack('<I',len(pcm))+pcm
   p.write_bytes(b'RIFF'+struct.pack('<I',len(body))+body);self.assertEqual(duration(p),1)
 def test_transcript_matches_selected_recording_not_the_latest_failed_candidate(self):
  from review_diagnostics import enrich
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   for name in ('chosen.wav','rejected.wav'):
    with wave.open(str(root/name),'wb') as f:f.setparams((1,2,16000,0,'NONE','not compressed'));f.writeframes(b'\0\0'*16000)
   chosen=str(root/'chosen.wav');rejected=str(root/'rejected.wav');issue=dict(index=1,evidence=[])
   director=dict(selectedAudio=chosen,attempts=[dict(candidateAudio=chosen,status='adopted',check=dict(heard='完整廣東話',decision='cantonese')),dict(candidateAudio=rejected,status='not-verified',check=dict(heard='日本語',decision='japanese'))])
   enrich(issue,dict(start=0,end=2,cantonese='完整廣東話'),{},root,director=director)
   self.assertEqual(issue['auditions']['generated']['path'],str(Path(chosen).resolve()));self.assertEqual(issue['diagnostic']['heard'],'完整廣東話');self.assertEqual(issue['diagnostic']['detectedLanguage'],'cantonese')
   self.assertEqual(issue['auditions']['lastFailed']['path'],str(Path(rejected).resolve()))
   self.assertEqual(issue['diagnostic']['lastFailedHeard'],'日本語')
   self.assertEqual(issue['diagnostic']['lastFailedDetectedLanguage'],'japanese')
 def test_rejected_model_recording_is_retrievable_from_retry_archive(self):
  import recording_history
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);review,_=self.fixture(root)
   review['config'].update(ttsBackend='drama3',targetLanguage='yue')
   retry=root/'normal-repairs'/'retry-a';retry.mkdir(parents=True)
   source=retry/'failed.wav'
   with wave.open(str(source),'wb') as f:f.setparams((1,2,16000,0,'NONE','not compressed'));f.writeframes(b'\0\0'*16000)
   archive=recording_history.preserve(retry,'drama3','yue',dict(reviewIndex=0,text='完整台詞'),source,'Japanese language check',review['cues'][0],dict(speechCheck=dict(heard='日本語',decision='japanese')))
   source.unlink()  # The immutable copy must remain audible after retry cleanup.
   self.save(root/'segment-issues.json',[dict(index=1,kind='verification-unresolved')])
   issue=review_report.project(root,review,dict(status='attention'))['issues'][0]
   self.assertEqual(issue['auditions']['lastFailed']['path'],str((archive/'audio.wav').resolve()))
   self.assertEqual(issue['diagnostic']['lastFailedHeard'],'日本語')
   self.assertEqual(issue['attempts'][-1]['reason'],'Japanese language check')
if __name__=='__main__':unittest.main()
