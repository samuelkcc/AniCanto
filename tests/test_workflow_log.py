import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'Resources')]
import workflow_log as log
class WorkflowLogTests(unittest.TestCase):
 def test_journal_has_order_time_and_duplicate_suppression(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);path=root/'attempts/row/run';row=dict(attempt=dict(path=str(path)))
   with patch('workflow_log.time.time',return_value=1000):
    log.record(root,row,dict(stage='準備',message='Load model'))
    log.record(root,row,dict(stage='準備',message='Load model'))
    log.record(root,row,dict(stage='辨識',message='Read dialogue'))
   entries=[json.loads(s) for s in (path/'workflow.jsonl').read_text().splitlines()]
   self.assertEqual([e['sequence'] for e in entries],[1,2]);self.assertEqual(entries[0]['at'],1000)
   text=log.summary(root,row);self.assertIn('001 | 1970-01-01 00:16:40 UTC | 準備 | Load model',text);self.assertIn('002 |',text)
 def test_legacy_log_and_missing_attempt_do_not_invent_time(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);path=root/'attempts/row/run';path.mkdir(parents=True)
   (path/'process.log').write_text('raw trace\n'+json.dumps(dict(stage='ASR',message='259 seconds'))+'\n')
   text=log.summary(root,dict(attempt=dict(path=str(path))),'zh-HK');self.assertIn('時間未記錄',text);self.assertIn('259 seconds',text)
   self.assertEqual(log.summary(root,dict(stage='ASR',message='Now')),'001 | time not recorded | ASR | Now')
 def test_external_attempt_is_not_read_or_written(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);row=dict(attempt=dict(path=str(root/'external')))
   log.record(root,row,dict(stage='X',message='Y'));self.assertFalse((root/'external').exists())
 def test_language_switch_affects_new_entries_only_and_preserves_raw_details(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);path=root/'attempts/row/run';row=dict(attempt=dict(path=str(path)))
   source=dict(stage='日語原聲',message='已辨識 180.4 / 1420.2 秒日語。')
   original=dict(source)
   log.record(root,row,source,'zh-HK');log.record(root,row,source,'en')
   rows=[json.loads(line) for line in (path/'workflow.jsonl').read_text().splitlines()]
   self.assertEqual(len(rows),2);self.assertEqual(rows[0]['message'],source['message'])
   self.assertEqual(rows[1]['stage'],'Japanese speech');self.assertEqual(rows[1]['message'],'Transcribed 180.4 / 1420.2 seconds of Japanese speech.')
   self.assertEqual(rows[1]['originalMessage'],source['message']);self.assertEqual(source,original)
   text=log.summary(root,row,'en');self.assertIn(source['message'],text);self.assertIn(rows[1]['message'],text)
 def test_unknown_diagnostic_is_labelled_without_guessing_or_discarding_evidence(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);path=root/'attempts/row/run';row=dict(attempt=dict(path=str(path)))
   log.record(root,row,dict(stage='未登記階段',message='未登記模型錯誤 abc-42'),'en')
   entry=json.loads((path/'workflow.jsonl').read_text())
   self.assertFalse(entry['localized']);self.assertEqual(entry['originalMessage'],'未登記模型錯誤 abc-42')
   self.assertIn('Detailed process log',entry['message'])
 def test_new_natural_speed_stages_are_readable_in_english(self):
  from workflow_localization import present
  for stage,message in [('自然語速編排','已微調 12 句配音起點（每句最多 0.5 秒）；保留完整錄音、自然語速同原本字幕時間。'),('精簡重配','只重配 17 句偏長台詞（1/2），保持自然語速同本句原聲參考。')]:
   result=present(stage,message,'en')
   self.assertTrue(result['localized']);self.assertNotIn('Worker diagnostic',result['message'])
 def test_preference_language_does_not_change_production_choices(self):
  sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'studio'),str(Path(__file__).resolve().parents[1]/'windows')]
  from backend import Studio
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);app=Studio(root,Path(__file__).resolve().parents[1]/'Resources',helper=root/'helper')
   before=dict(app.store.settings)
   state=app.dispatch('configure',dict(language='zh-HK',settings={},preserveProductionSettings=True))
   self.assertEqual(state['language'],'zh-HK')
   for key in ['dubLanguages','includeOriginal','subtitleModes','ttsBackend']:
    self.assertEqual(app.store.settings[key],before[key])
if __name__=='__main__':unittest.main()
