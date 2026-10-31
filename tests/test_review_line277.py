"""Regression tests for the 2026-10-31 proofreading fixes, desktop build 277.

D1  a saved draft that already carries a storage path must not fail a one-line retake.
D2  one recording is one report row, and an unused first take can be removed.
D3  every take row carries a creation time so the report can order takes.
D5  the frozen request records which source language was detected and how.
"""
import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'studio'),str(ROOT/'windows'),str(ROOT/'Resources')]
from backend import Studio
from desktop_state import job_snapshot,write,read,defaults,review_fingerprint
from review_take_removal import protection,remove

class ReviewLine277(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'SamCantoSync';self.root.mkdir()
  self.video=self.root/'episode.mp4';self.video.write_bytes(b'fixture source')
  self.helper=self.root/'native-helper';self.helper.write_text('fixture executable')
  self.app=Studio(self.root,ROOT/'Resources',platform='darwin',helper=self.helper)
  from use_terms import document
  self.app.dispatch('accept-use-terms',dict(accepted=True,sha256=document()['sha256'],language='en'))
 def tearDown(self):self.tmp.cleanup()
 def project(self):
  ident=self.app.dispatch('add',dict(paths=[str(self.video)]))['selected']
  folder=(self.root/'jobs/example').resolve();folder.mkdir(parents=True)
  cfg=dict(defaults(),video=str(self.video),duration=6,voiceProfiles=[])
  review=dict(config=cfg,cues=[dict(start=1.,end=3.,text='こんにちは',japanese='こんにちは',cantonese='你好呀。',english='Hello.',speakerId='R01')])
  write(folder/'review.json',review);row=self.app.row(ident);row.update(job=str(folder),review=str(folder/'review.json'));self.app.store.save()
  return ident,folder
 # D1: the old merge built dict(draft['settings'], storage=..., **tools()).
 def test_a_saved_draft_storage_path_cannot_break_a_one_line_render(self):
  ident,folder=self.project()
  take=folder/'takes/first.wav';take.parent.mkdir(parents=True);take.write_bytes(b'first take')
  draft=dict(review=str(folder/'review.json'),segments=[dict(id='seg-1',sources=[0],start=1.,end=3.,text='你好呀。',audioTake=str(take))],
             settings=dict(self.app.store.settings,storage=str(self.root/'stale-root')),
             baseFingerprint=review_fingerprint(read(folder/'review.json')))
  self.app.dispatch('save-draft',dict(id=ident,draft=draft))
  with patch.object(self.app,'task',return_value=dict(action='render-project')) as task:
   self.assertEqual(self.app.dispatch('render',dict(id=ident)),dict(action='render-project'))
  config=read(Path(task.call_args.args[1]))
  self.assertEqual(config['storage'],str(self.root.resolve()),'the draft storage must not survive the merge')
  # build276 shape: a tools mapping that already carries a storage path raised here.
  old_shape=lambda tools:dict(draft['settings'],storage=str(self.root),submission='x',**tools)
  with self.assertRaisesRegex(TypeError,"got multiple values for keyword argument 'storage'"):
   old_shape(dict(self.app.tools(),storage=str(self.root/'runtime')))
 def test_a_review_repair_draft_with_storage_starts_without_a_duplicate_keyword(self):
  ident,folder=self.project()
  row=self.app.row(ident);row.update(status='attention');self.app.store.save()
  submission=dict(id='e'*32,created=1.0,review=str(folder/'review.json'),segments=[],
                  settings=dict(self.app.store.settings,storage=str(self.root/'stale-root')))
  frozen=dict(job=str(folder),review=read(folder/'review.json'),root=str(folder),takes=[],history=[],
              recordingCandidates=[],reportRows=[],issues=[],resolvedIssues=[])
  with patch('backend.job_snapshot',return_value=frozen),patch('review_retry.submission',return_value=submission),patch.object(self.app,'task',return_value=dict(action='render-project')) as task:
   self.assertEqual(self.app.dispatch('retry-review',dict(id=ident,mode='pending')),dict(action='render-project'))
  config=read(Path(task.call_args.args[1]))
  self.assertEqual(config['storage'],str(self.root.resolve()))
  self.assertEqual(read(Path(config['submission']))['id'],'e'*32)
 # D2: the snapshot publishes the same protected list the removal guard uses.
 def test_the_snapshot_publishes_the_protection_list_for_the_report(self):
  ident,folder=self.project()
  used=folder/'takes/used.wav';used.parent.mkdir(parents=True);used.write_bytes(b'used take')
  spare=folder/'takes/spare.wav';spare.write_bytes(b'spare take')
  draft=dict(review=str(folder/'review.json'),segments=[dict(id='seg-1',sources=[0],start=1.,end=3.,text='你好呀。',audioTake=str(used))],settings={})
  draft['baseFingerprint']=review_fingerprint(read(folder/'review.json'))
  self.app.dispatch('save-draft',dict(id=ident,draft=draft))
  frozen=dict(job=str(folder),review=read(folder/'review.json'),root=str(folder),
              takes=[dict(index=1,language='yue',engine='drama3',audio=str(used))],
              history=[],recordingCandidates=[dict(index=1,language='yue',engine='drama3',path=str(spare),kind='first')],
              reportRows=[dict(index=1,language='yue',engine='drama3',selectedAudio=str(used),reportGroup='reportMissing')],
              issues=[],resolvedIssues=[])
  with patch('backend.job_snapshot',return_value=frozen):
   snapshot=self.app.dispatch('snapshot',dict(id=ident))
  published={row['path']:row['reason'] for row in snapshot['protectedTakes']}
  self.assertEqual(published,{str(used.resolve()):'current export'})
  self.assertNotIn(str(spare.resolve()),published)
 # D5: the detection record travels into the frozen request, not only the session.
 def test_the_frozen_request_records_the_detected_source_language(self):
  ident=self.project()[0]
  detection=dict(language='ja',detectedLanguage='ja',method='audio-stream-metadata',stream=1,
                 explicitOverride=False,confidence=0,confirmationSkipped=True)
  row=self.app.row(ident);row['sourcePreflight']=dict(language='ja',name='Japanese',supported=True,stream=1,
                                                     needsConfirmation=False,detection=detection)
  self.app.store.save()
  spec=self.app.dispatch('start',dict(id=ident))
  cfg=read(Path(spec['args'][-1]))
  self.assertEqual(cfg['sourceLanguage'],'ja','a Japanese source needs no second confirmation')
  self.assertEqual(cfg['sourceLanguageDetection'],detection)
  self.assertEqual(cfg['sourceAudioStream'],1)
 def test_a_source_without_a_detection_record_still_leaves_an_auditable_note(self):
  ident=self.project()[0]
  row=self.app.row(ident);row['sourcePreflight']=dict(language='en',name='English',supported=True,
                                                     needsConfirmation=False,method='audio-probe')
  self.app.store.save()
  cfg=read(Path(self.app.dispatch('start',dict(id=ident))['args'][-1]))
  self.assertEqual(cfg['sourceLanguageDetection'],dict(language='en',method='audio-probe',confirmationSkipped=True))

class ReviewSnapshotLine277(unittest.TestCase):
 """One job folder: job manifest and track manifest list the same first take."""
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  track=self.root/'tracks/drama';track.mkdir(parents=True)
  review=dict(config=dict(ttsBackend='drama3',targetLanguage='yue',dubLanguages=['yue'],selectedEngines=['drama3']),
              cues=[dict(start=1,end=2,cantonese='你好呀'),dict(start=4,end=5,cantonese='第二句')])
  write(self.root/'review.json',review);write(track/'review.json',dict(config=review['config'],cues=[]))
  self.first=track/'first.wav';self.first.write_bytes(b'first take')
  self.second=track/'second.wav';self.second.write_bytes(b'second take')
  # The job manifest and the track manifest both list the first recording.
  write(self.root/'audio-preview.json',dict(engine='drama3',language='yue',rows=[dict(index=1,audio=str(self.first))]))
  write(track/'audio-preview.json',dict(engine='drama3',language='yue',rows=[dict(index=1,audio=str(self.first)),dict(index=2,audio=str(self.second))]))
  history=track/'recording-history/take-1';history.mkdir(parents=True)
  failed=history/'audio.wav';failed.write_bytes(b'failed take')
  write(history/'take.json',dict(index=1,engine='drama3',language='yue',audio='audio.wav',reason='generation-failed'))
 def tearDown(self):self.tmp.cleanup()
 def snapshot(self):return job_snapshot(dict(job=str(self.root)))
 def take_rows(self,snapshot=None):
  rows=[x for x in (snapshot or self.snapshot())['takes'] if x.get('audio')]
  return rows
 def test_one_recording_is_one_take_row_across_manifests(self):
  rows=self.take_rows()
  paths=[row['audio'] for row in rows]
  self.assertEqual(sorted(paths),sorted({str(self.first.resolve()),str(self.second.resolve())}))
  candidates=[x['path'] for x in self.snapshot()['recordingCandidates']]
  self.assertEqual(len(candidates),len(set(candidates)),'no candidate path is listed twice')
  self.assertEqual([x for x in candidates if x.endswith('first.wav')],[str(self.first.resolve())])
 def test_every_take_row_carries_a_creation_time(self):
  for row in self.take_rows():
   self.assertIsInstance(row.get('created'),float)
 def test_a_history_row_uses_the_resolved_path_and_a_creation_time(self):
  archived=self.root/'tracks/drama/recording-history/take-1/audio.wav'
  history=self.snapshot()['history']
  self.assertEqual([x['path'] for x in history],[str(archived.resolve())])
  self.assertTrue(history[0]['created'])
 def test_an_unused_first_take_is_not_protected_and_can_be_removed(self):
  snapshot=self.snapshot()
  self.assertEqual(protection(snapshot,{}),{})
  record=remove(self.root,snapshot,{},0,'yue','drama3',str(self.first),True)
  self.assertEqual(record['index'],1);self.assertFalse(self.first.exists())
  self.assertNotIn(str(self.first.resolve()),[x['path'] for x in self.snapshot()['recordingCandidates']])
 def test_the_four_build275_links_still_protect_a_recording(self):
  first=str(self.first.resolve())
  base=self.snapshot()
  exported=dict(base,reportRows=[dict(index=1,language='yue',engine='drama3',selectedAudio=str(self.first))])
  completed=dict(base,takes=base['takes']+[dict(index=1,language='yue',engine='drama3',audio=str(self.first),versionStatus='complete')])
  for frozen in (exported,completed):
   self.assertEqual(sorted(protection(frozen,{})),[first])
   with self.assertRaisesRegex(ValueError,'current export or a saved choice'):
    remove(self.root,frozen,{},0,'yue','drama3',str(self.first),True)
  drafts=[dict(segments=[dict(sources=[0],audioTake=str(self.first))]),
          dict(segments=[dict(sources=[0],reviewDecisions={'yue:drama3':dict(audio=str(self.first))})])]
  for draft in drafts:
   self.assertEqual(sorted(protection(self.snapshot(),draft)),[first])
   with self.assertRaisesRegex(ValueError,'current export or a saved choice'):
    remove(self.root,self.snapshot(),draft,0,'yue','drama3',str(self.first),True)
  self.assertTrue(self.first.exists())

if __name__=='__main__':unittest.main()
