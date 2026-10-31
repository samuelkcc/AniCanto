"""Recorded voice reference for each desktop recording, build 278."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Resources'))
import review_workbench as w

def snapshot(takes):
    cue=dict(start=0,end=2,speechStart=0,speechEnd=2,cantonese='你好',speakerId='R01')
    profile=dict(id='R01',reference='/job/line-references/754159a965aa103b350d/reference.wav',promptText='こんにちは',language='ja')
    return dict(review=dict(cues=[cue],config=dict(voiceProfiles=[profile])),
      draft=dict(settings=dict(voiceProfiles=[profile]),segments=[dict(id='s1',sources=[0],start=0,end=2,text='你好',speakerId='R01',take=42)]),
      reportRows=[dict(index=1,language='yue',engine='drama3',reportGroup='reportAvailable',selectedAudio='/job/takes/first.wav',recordingSHA256='h1')],
      issues=[],resolvedIssues=[],takes=takes)

def take(audio,reference,sha,seed,created):
    provenance=dict(speakerId='R01',reference=w.reference_signature(dict(id='R01',reference=REFERENCE,promptText='こんにちは',language='ja')))
    if reference:provenance['recordedReference']=reference
    if sha:provenance['recordedReferenceSHA256']=sha
    if seed is not None:provenance['recordedSeed']=seed
    return dict(index=1,language='yue',engine='drama3',audio=audio,created=created,recordingProvenance=provenance)

REFERENCE='/job/line-references/754159a965aa103b350d/reference.wav'

class VoiceReferenceTests(unittest.TestCase):
 def test_a_retake_on_the_same_reference_reads_as_the_same_voice(self):
  first=take('/job/takes/first.wav',REFERENCE,'a009bdde',42,100)
  retake=take('/job/takes/new.wav',REFERENCE,'a009bdde',42,200)
  states=w.voice_references(snapshot([first,retake]))
  self.assertEqual(states['/job/takes/first.wav']['state'],'first')
  self.assertEqual(states['/job/takes/new.wav']['state'],'same')
  self.assertEqual(states['/job/takes/new.wav']['seed'],42)
  self.assertEqual(states['/job/takes/new.wav']['reference'],'reference.wav')
 def test_a_retake_on_another_reference_is_reported(self):
  first=take('/job/takes/first.wav',REFERENCE,'a009bdde',42,100)
  retake=take('/job/takes/new.wav','/job/line-references/other/reference.wav','ff00ff00',42,200)
  states=w.voice_references(snapshot([first,retake]))
  self.assertEqual(states['/job/takes/first.wav']['state'],'first')
  self.assertEqual(states['/job/takes/new.wav']['state'],'different')
 def test_a_recording_without_an_engine_record_is_unknown_and_not_guessed(self):
  legacy=dict(index=1,language='yue',engine='drama3',audio='/job/takes/legacy.wav',created=5)
  self.assertEqual(w.voice_references(snapshot([legacy]))['/job/takes/legacy.wav']['state'],'unknown')
 def test_the_report_is_per_line_and_never_adds_a_regeneration_target(self):
  one=take('/job/takes/one.wav',REFERENCE,'a009bdde',42,100)
  two=dict(take('/job/takes/two-line.wav',REFERENCE,'a009bdde',42,120),index=2)
  other=take('/job/takes/other-engine.wav','/job/voices/scene.wav','bbbb',42,130);other['engine']='voxcpm2'
  snap=snapshot([one,two,other]);states=w.voice_references(snap)
  self.assertEqual(states['/job/takes/two-line.wav']['line'],'2:yue:drama3')
  self.assertEqual(states['/job/takes/other-engine.wav']['state'],'first')
  # A different recorded reference is a listening note. It never selects the line
  # for automatic regeneration, so a bulk conversion keeps its saved recordings.
  drifted=dict(take('/job/takes/new.wav','/job/line-references/other/reference.wav','ff00ff00',42,200))
  self.assertEqual(w.voice_references(snapshot([one,drifted]))['/job/takes/new.wav']['state'],'different')
  self.assertEqual(w.stale_recordings(snapshot([one,drifted])),[])
 def test_project_publishes_the_reference_report(self):
  import tempfile
  with tempfile.TemporaryDirectory() as d:
   snap=w.project(d,snapshot([take('/job/takes/first.wav',REFERENCE,'a009bdde',42,100)]))
   self.assertEqual(snap['voiceReferences']['/job/takes/first.wav']['state'],'first')

if __name__=='__main__':unittest.main()
