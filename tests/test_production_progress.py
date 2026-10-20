import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Resources'))
import production_progress as p

class ProductionProgressTests(unittest.TestCase):
 def tearDown(self):p.reset()
 def test_child_progress_cannot_rewind_and_durations_survive_resume(self):
  with tempfile.TemporaryDirectory() as folder:
   clock=[0.];j=p.Journey(folder,clock=lambda:clock[0]);j.enter('prepare')
   clock[0]=10;j.enter('recognition');clock[0]=30;j.enter('roles')
   clock[0]=40;j.enter('translation');clock[0]=100;j.enter('voice')
   self.assertEqual(j.snapshot()['progress'],.5)
   clock[0]=120;j.enter('translation') # Inner retry cannot rewind.
   self.assertEqual(j.snapshot()['progress'],.5)
   j.save();self.assertEqual(j.rows[3]['seconds'],60)
   clock[0]=10000;r=p.Journey(folder,clock=lambda:clock[0]);r.prepared();r.enter('voice')
   clock[0]=10005;r.enter('repair');clock[0]=10010;r.enter('export');r.finish()
   self.assertEqual(r.snapshot()['progress'],1)
   self.assertEqual(r.rows[4]['seconds'],25) # 20 + 5, no paused gap.
   self.assertAlmostEqual(sum(row['seconds'] for row in r.rows),130)
 def test_partial_output_never_completes_export(self):
  with tempfile.TemporaryDirectory() as folder:
   j=p.Journey(folder);j.prepared();j.enter('voice');j.enter('repair');j.enter('export');j.finish(partial=True)
   self.assertEqual(j.rows[-1]['state'],'incomplete');self.assertLess(j.value,1);self.assertFalse(j.done)
 def test_published_output_is_complete_even_when_quality_needs_review(self):
  with tempfile.TemporaryDirectory() as folder:
   j=p.Journey(folder);j.enter('export');j.finish(partial=True,exported=True)
   self.assertEqual(j.value,1);self.assertTrue(j.done);self.assertEqual(j.rows[-1]['state'],'complete')
   self.assertEqual(j.snapshot()['qualityStatus'],'needs-review')
   j.enter('translation');j.advance('translation',.3);j.finish(partial=True)
   self.assertEqual(j.value,1);self.assertTrue(j.done);self.assertEqual(j.rows[-1]['state'],'complete')
 def test_primary_voice_counts_advance_within_phase_without_retry_rollback(self):
  with tempfile.TemporaryDirectory() as folder:
   j=p.Journey(folder);j.enter('voice');j.advance('voice',.5)
   self.assertAlmostEqual(j.value,.644)
   j.advance('voice',.1);self.assertAlmostEqual(j.value,.644)
   j.advance('voice',1);self.assertAlmostEqual(j.value,.788)
   j.enter('repair');j.advance('voice',1);self.assertEqual(j.value,.82)
   j.advance('repair',float('nan'));self.assertEqual(j.value,.82)
 def test_fast_skips_are_explicit_and_new_batch_is_independent(self):
  with tempfile.TemporaryDirectory() as folder:
   a=Path(folder)/'a';b=Path(folder)/'b';a.mkdir();b.mkdir()
   p.phase(a,'prepare');p.phase(a,'recognition');p.phase(a,'roles',skipped=True);p.phase(a,'translation')
   self.assertEqual(p.snapshot()['milestones'][2]['state'],'skipped')
   p.phase(a,'voice');p.phase(a,'repair',skipped=True);p.phase(a,'export');p.finish()
   p.phase(b,'prepare');self.assertEqual(p.snapshot()['progress'],0)
 def test_worker_replaces_all_child_fractions_with_authoritative_value(self):
  import worker,io,contextlib
  with tempfile.TemporaryDirectory() as folder:
   p.phase(folder,'translation');buf=io.StringIO()
   with contextlib.redirect_stdout(buf):
    worker.emit('模型','child 80%',.8);worker.emit('模型','retry 50%',.5)
   rows=[json.loads(r) for r in buf.getvalue().splitlines()]
   self.assertEqual([r['progress'] for r in rows],[.34,.34]);self.assertTrue(all('journey' in r for r in rows))
 def test_resume_keeps_high_water_mark_and_saved_take_migration(self):
  with tempfile.TemporaryDirectory() as folder:
   j=p.Journey(folder);j.enter('voice');j.enter('repair');j.save()
   r=p.Journey(folder);r.enter('prepare');r.enter('translation')
   self.assertEqual(r.value,.82);self.assertTrue(r.resumed)
   (Path(folder)/'production-progress.json').unlink()
   track=Path(folder)/'tracks/drama3';track.mkdir(parents=True);(track/'report.json').write_text('{}')
   old=p.Journey(folder);old.enter('translation');self.assertEqual(old.value,.5)
   self.assertEqual(old.rows[4]['state'],'saved')
 def test_cached_stage_is_reused_and_malformed_timing_cannot_stop_conversion(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'production-progress.json';path.write_text('{"progress":"bad","milestones":[{"id":"translation","seconds":"bad"}]}')
   j=p.Journey(folder);j.enter('recognition',cached=True);j.enter('translation')
   self.assertEqual(j.rows[1]['state'],'prepared');self.assertEqual(j.rows[3]['seconds'],0)
