import json,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import speakers,visual_speakers,visual_identity

class IdentityPlan(unittest.TestCase):
 def rows(self,durations):return [dict(start=i*10,end=i*10+d,mixed=False) for i,d in enumerate(durations)]
 def test_ambiguous_short_reply_does_not_create_character(self):
  vectors=np.array([[1.,0],[0,1],[.70710678,.70710678]])
  labels,evidence=speakers.stable_assignments(vectors,self.rows([4,4,2]),with_evidence=True)
  self.assertEqual(len(set(labels)),2);self.assertIn(labels[2],labels[:2]);self.assertEqual(evidence[2]['state'],'uncertain');self.assertEqual(evidence[2]['reason'],'tied-candidates')
 def test_noisy_long_outlier_does_not_establish_new_identity(self):
  rows=self.rows([4,4,4]);rows[2]['quality']={'score':20}
  labels,evidence=speakers.stable_assignments(np.eye(3),rows,with_evidence=True)
  self.assertEqual(len(set(labels)),2);self.assertEqual(evidence[2]['state'],'uncertain')
 def test_genuinely_distinct_clean_short_voice_remains_provisional(self):
  labels,evidence=speakers.stable_assignments(np.eye(3),self.rows([4,4,2]),with_evidence=True)
  self.assertEqual(labels,[0,1,2]);self.assertEqual(evidence[2]['state'],'provisional')
 def test_recurring_prototypes_merge_but_overlapping_groups_do_not(self):
  angles=np.deg2rad([-20,20,-40,40]);vectors=np.column_stack([np.cos(angles),np.sin(angles)]);rows=self.rows([4]*4)
  with patch.object(speakers,'cluster_embeddings',return_value=[0,0,1,1]):
   self.assertEqual(len(set(speakers.stable_assignments(vectors,rows))),1)
   rows[2].update(start=1,end=5)
   self.assertEqual(len(set(speakers.stable_assignments(vectors,rows))),2)
 def test_family_merge_does_not_chain_incompatible_endpoints(self):
  angles=np.deg2rad([0,40,80]);vectors=np.column_stack([np.cos(angles),np.sin(angles)])
  with patch.object(speakers,'cluster_embeddings',return_value=[0,1,2]):
   labels=speakers.stable_assignments(vectors,self.rows([4]*3));self.assertNotEqual(labels[0],labels[2])
 def test_empty_evidence_is_finite(self):self.assertEqual(speakers.stable_assignments(np.empty((0,2)),[],True),([],[]))
 def test_reference_transcription_occurs_after_visual_fusion_and_retains_raw_cache(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);job=root/'job';job.mkdir();(root/'speakers-ready.json').write_text('{}');speech=root/'speech';speech.mkdir();(speech/'model.bin').write_text('x');reference=job/'a.wav';reference.write_text('x')
   profiles=[dict(id='a',name='a',reference=str(reference),promptText=''),dict(id='b',name='b',reference=str(reference),promptText='')];events=[]
   def model_job(*args):
    (job/'speaker-analysis.json').write_text(json.dumps(dict(profiles=profiles,assignments=[dict(index=0,speakerId='a',speakerNote=''),dict(index=1,speakerId='b',speakerNote='')])))
   def fuse(cfg,job,cues,profiles,emit):
    events.append('fuse');cues[1]['speakerId']='a';return cues,profiles[:1]
   def transcribe(cfg,job,profiles,speech,emit):events.append('transcribe');self.assertEqual(len(profiles),1);profiles[0]['promptText']='speech'
   cfg=dict(storage=d,dialoguePath='source.wav',roleAnalysisMode='audiovisual');cues=[dict(start=0,end=3),dict(start=4,end=7)]
   with patch('dubbing.model_job',side_effect=model_job),patch('model_catalog.selected',return_value='stub'),patch('model_catalog.choice',return_value={}),patch('model_catalog.folder',return_value=speech),patch('visual_speakers.refine',side_effect=fuse),patch('speakers.transcribe_profiles',side_effect=transcribe):
    speakers.assign(cfg,job,cues,None,lambda *a:None)
   self.assertEqual(events,['fuse','transcribe']);self.assertEqual(len(json.loads((job/'auto-speakers.json').read_text())['profiles']),2)
   plan=json.loads((job/'character-plan.json').read_text());self.assertEqual(plan['finalVoiceGroups'],1);self.assertEqual(plan['identities'][0]['cueIndices'],[1,2])
 def test_merged_multi_range_reference_transcribes_matching_words(self):
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);(job/'japanese-analysis.json').write_text(json.dumps(dict(segments=[dict(words=[dict(word='a',start=0,end=1),dict(word='b',start=4,end=5),dict(word='unrelated',start=10,end=11)])])))
   profiles=[dict(name='a',reference='a.wav',referenceRanges=[[0,1]],referenceCandidates=[dict(reference='b.wav',ranges=[[0,1],[4,5]])])]
   with patch.dict(sys.modules,{'faster_whisper':types.SimpleNamespace(WhisperModel=lambda *a,**k: (_ for _ in ()).throw(AssertionError('no extra recognition')))}):speakers.transcribe_profiles({},job,profiles,job,lambda *a:None)
   self.assertEqual(profiles[0]['promptText'],'a');self.assertEqual(profiles[0]['referenceCandidates'][0]['promptText'],'ab')

class PhotoMemory(unittest.TestCase):
 def test_frames_extract_once_and_comparison_contains_real_reference(self):
  from PIL import Image
  with tempfile.TemporaryDirectory() as d:
   job=Path(d);cfg=dict(key='test-key',ffmpeg='stub',video='stub',offset=10);cues=[dict(start=1,end=4)];calls=[]
   def frame(args,**kwargs):calls.append(args);Image.new('RGB',(256,144),'blue').save(args[-1])
   with patch('visual_identity.subprocess.run',side_effect=frame):
    shots=visual_identity.prepare_storyboards(cfg,job,cues,[0]);visual_identity.prepare_storyboards(cfg,job,cues,[0])
   self.assertEqual(len(calls),4);self.assertAlmostEqual(float(calls[0][5]),11.45)
   portrait=job/'reference.jpg';Image.new('RGB',(60,80),'red').save(portrait);target=job/'comparison.jpg'
   visual_identity.comparison_sheet([dict(visualId='v1',photos=[str(portrait)])],shots,[0],target)
   with Image.open(target) as image:
    self.assertEqual(image.size,(1024,296));self.assertGreater(image.getpixel((64,60))[0],200);self.assertGreater(image.getpixel((200,160))[2],150)
 def test_hands_and_reaction_crowds_never_enter_photo_memory(self):
  with tempfile.TemporaryDirectory() as d,patch('visual_identity.subprocess.run') as run:
   for row in [dict(headVisible=False,multipleSpeakers=False),dict(headVisible=True,multipleSpeakers=True)]:
    row.update(index=0,visualId='v1',continuousShot=True,confidence=.99,characterBox=[.2,.1,.4,.5])
    gallery=visual_identity.photo_atlas(dict(key='test'),Path(d),[dict(start=0,end=3)],[row],[dict(id='v1',appearance='red helmet')]);self.assertEqual(gallery,[])
   run.assert_not_called()
 def test_changed_evidence_key_cannot_reuse_a_stale_photo(self):
  from PIL import Image
  with tempfile.TemporaryDirectory() as d,patch('visual_identity.subprocess.run') as run:
   def crop(args,**kwargs):Image.new('RGB',(60,80),'red').save(args[-1])
   run.side_effect=crop;row=dict(index=0,visualId='v1',headVisible=True,continuousShot=True,multipleSpeakers=False,confidence=.99,characterBox=[.2,.1,.4,.5]);cues=[dict(start=0,end=3)];roster=[dict(id='v1')]
   first=visual_identity.photo_atlas(dict(key='old',ffmpeg='stub',video='stub'),Path(d),cues,[row],roster)
   second=visual_identity.photo_atlas(dict(key='new',ffmpeg='stub',video='stub'),Path(d),cues,[row],roster)
   self.assertNotEqual(first[0]['photos'],second[0]['photos']);self.assertEqual(run.call_count,2)

if __name__=='__main__':unittest.main()
