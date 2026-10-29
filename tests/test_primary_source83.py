import copy,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows'),str(ROOT/'studio'),str(ROOT/'tests')]
import primary_source as p
from atomic_files import write_json
class PrimarySourceTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.job=Path(self.tmp.name);self.requests=[]
  self.cfg=dict(sourcePolicyRevision=p.REVISION,translationSource='audio-and-subtitles',subtitleSource='external',subtitle='authored.srt',model='test',port=1,sourceLanguage='ja',dubLanguages=['yue'],subtitleModes=['yue'])
  self.w=SimpleNamespace(atomic_json=write_json,emit=lambda *a,**k:None,traditional_cantonese=lambda cfg,s:s,ollama_chat=self.chat)
 def chat(self,*args,**kwargs):
  self.requests.append(args[2]);return json.dumps({'0':[dict(captionID='caption_1',quote='小茜')],'1':[dict(captionID='caption_1',quote='我只用右手打倒佢')]},ensure_ascii=False)
 def cue(self,a=0,b=2,source='昨日は雨でした'):
  return dict(start=a,end=b,speechStart=a,speechEnd=b,japanese=source,text=source,enabled=True,cantonese='')
 def captions(self,rows):write_json(self.job/'subtitle-context.json',rows)
 def test_authored_caption_is_primary_and_raw_transcript_clocks_survive(self):
  self.captions([dict(start=0,end=2,text='慢慢去約會吧')]);c=self.cue();original=copy.deepcopy(c);p.prepare(self.w,self.cfg,self.job,[c]);self.assertEqual(p.content(c),'慢慢去約會吧');self.assertEqual(c['japanese'],original['japanese']);self.assertFalse(c['captionEvidenceOnly']);self.assertEqual((c['start'],c['end']),(0,2));self.assertEqual(self.requests,[])
 def test_ownership_exact_quotes_no_duplicate_or_lost_clause(self):
  self.captions([dict(start=0,end=4,text='小茜 我只用右手打倒佢')]);cues=[self.cue(0,1),self.cue(1,4)];p.prepare(self.w,self.cfg,self.job,cues);self.assertEqual([p.content(c) for c in cues],['小茜','我只用右手打倒佢']);self.assertEqual(len(self.requests),1);self.assertEqual([c['japanese'] for c in cues],['昨日は雨でした']*2)
  before=len(self.requests);p.prepare(self.w,self.cfg,self.job,cues);self.assertEqual(len(self.requests),before,'resume must reuse ownership without another request')
 def test_ownership_rejects_omissions_duplicates_neighbour_and_foreign_ids(self):
  records={'c':dict(text='我只用右手打倒佢')};owners={'c':['0','1']};good={'0':[dict(captionID='c',quote='我只用右手')],'1':[dict(captionID='c',quote='打倒佢')]};self.assertTrue(p.allocate(good,['0','1'],records,owners))
  for bad in [dict(good,**{'1':[]}),dict(good,**{'1':good['0']}),dict(good,**{'1':[dict(captionID='c',quote='左手')]}),{'9':good['0'],'1':good['1']}]:
   with self.assertRaises(ValueError):p.allocate(bad,['0','1'],records,owners)
 def test_lexical_blank_and_out_of_order_allocations_are_rejected(self):
  records={'c':dict(text='小茜，我只用右手打倒佢')};owners={'c':['0','1']}
  with self.assertRaisesRegex(ValueError,'lexical'):p.allocate({'0':[dict(captionID='c',quote=records['c']['text'])],'1':[]},['0','1'],records,owners,['0','1'])
  with self.assertRaisesRegex(ValueError,'order'):p.allocate({'0':[dict(captionID='c',quote='我只用右手打倒佢')],'1':[dict(captionID='c',quote='小茜，')]},['0','1'],records,owners,['0','1'])
 def test_bad_allocation_is_bounded_reported_and_never_bad_asr_fallback(self):
  self.captions([dict(start=0,end=4,text='小茜 我只用右手打倒佢')]);self.w.ollama_chat=lambda *a,**k:'{}';cues=[self.cue(0,1),self.cue(1,4)];p.prepare(self.w,self.cfg,self.job,cues);self.assertTrue(all(c['sourcePolicyBlocked'] and c['preserveOriginalSpeech'] for c in cues));report=json.loads((self.job/'source-policy.json').read_text());self.assertEqual(report['unresolved'],[1,2]);self.assertEqual(p.content(cues[0]),'')
  ledger=json.loads((self.job/'primary-allocation.json').read_text());self.assertEqual(next(iter(ledger.values()))['attempts'],2)
 def test_no_subtitles_uses_asr_and_gap_is_reported_without_inventing_clock(self):
  self.captions([dict(start=10,end=12,text='無語音時鐘字幕')]);c=self.cue();p.prepare(self.w,self.cfg,self.job,[c]);self.assertEqual(p.content(c),c['japanese']);self.assertEqual(c['primarySource']['kind'],'asr');self.assertEqual(c['primarySource']['language'],'ja');self.assertEqual(len(json.loads((self.job/'source-policy.json').read_text())['subtitleClockGaps']),1)
 def test_ocr_remains_a_comparison_and_does_not_overwrite_transcript(self):
  c=self.cue();c.update(subtitleHint='今天下雨',ocrEvidence=[dict(start=0,end=2,text='今天下雨')]);p.prepare(self.w,dict(self.cfg,ocr=True,translationSource='audio-and-ocr'),self.job,[c]);self.assertEqual(c['primarySource']['kind'],'ocr-and-speech');self.assertEqual(p.content(c),c['japanese']);self.assertIn('OCR_AND_SPEECH',p.rules(self.cfg))
 def test_normal_translation_and_names_receive_primary_not_wrong_asr(self):
  import normal_mode
  self.captions([dict(start=0,end=2,text='慢慢去約會吧')]);c=self.cue();p.prepare(self.w,self.cfg,self.job,[c]);self.requests=[]
  def chat(*a,**kw):
   self.requests.append(a[2]);return '{"0":"慢慢去拍拖啦。"}'
  self.w.ollama_chat=chat
  with patch.object(normal_mode,'glossary',return_value=[]):normal_mode.translate(self.w,self.cfg,self.job,[c])
  raw=json.dumps(self.requests,ensure_ascii=False);self.assertIn('慢慢去約會吧',raw);self.assertNotIn('昨日は雨でした',raw);self.assertEqual(c['cantonese'],'慢慢去拍拖啦。');self.assertEqual(c['japanese'],'昨日は雨でした')
 def test_recovery_keeps_authored_captions_not_ocr_auxiliary(self):
  from script_gap_recovery import evidence
  import caption_alignment,worker,translation_source
  self.captions([dict(start=0,end=2,text='不要離開')]);c=self.cue();p.prepare(self.w,self.cfg,self.job,[c])
  with patch.object(worker,'atomic_json',write_json):caption_alignment.prepare(self.cfg,self.job,[c])
  self.assertFalse(translation_source.audio_primary(self.cfg,c));e=evidence(c);self.assertEqual(e['ownedMeaning'],'不要離開');self.assertTrue(e['captions']);self.assertEqual(e['japanese'],'不要離開')
 def test_english_and_mandarin_use_the_same_authored_primary(self):
  import normal_mode,dub_languages
  self.captions([dict(start=0,end=3,text='慢慢去約會吧')]);c=self.cue(0,3);p.prepare(self.w,self.cfg,self.job,[c]);requests=[]
  def english(*a,**k):requests.append(a[2]);return '{"0":"Enjoy your date."}'
  self.w.ollama_chat=english
  with patch.object(normal_mode,'glossary',return_value=[]):normal_mode.translate(self.w,dict(self.cfg,dubLanguages=['en'],subtitleModes=['english']),self.job,[c])
  self.assertEqual(c['english'],'Enjoy your date.');self.assertNotIn('昨日は雨でした',json.dumps(requests,ensure_ascii=False))
  requests.clear()
  def mandarin(*a,**k):requests.append(a[2]);return '{"0":"慢慢去约会吧。"}'
  self.w.ollama_chat=mandarin;dub_languages.mandarin_script(self.w,self.cfg,self.job,[c]);self.assertEqual(c['mandarin'],'慢慢去约会吧。');self.assertNotIn('昨日は雨でした',json.dumps(requests,ensure_ascii=False))
 def test_new_caption_alignment_does_not_disable_speech_outside_subtitle(self):
  from source_evidence import apply_caption_policy
  c=self.cue(5,7);cfg=dict(self.cfg,duration=10);result=apply_caption_policy(cfg,[dict(id='c',start=0,end=2,text='字幕')],[c]);self.assertTrue(c['enabled']);self.assertEqual(result['excluded'],[])
 def test_semantic_source_and_render_merge_preserve_the_primary_text(self):
  from script_preflight import source
  self.captions([dict(start=0,end=2,text='我只用右手打倒佢')]);c=self.cue();c.update(japaneseAlt='同情破り',japaneseRecheck='錯誤ASR');p.prepare(self.w,self.cfg,self.job,[c]);proof=source(c);self.assertEqual(proof['japanese'],'我只用右手打倒佢');self.assertEqual(proof['independent_japanese'],'');self.assertEqual(proof['isolated_japanese'],'');self.assertNotIn('同情',json.dumps(proof,ensure_ascii=False))
 def test_intentionally_preserved_opening_does_not_report_false_subtitle_gap(self):
  self.captions([dict(start=10,end=12,text='保留片頭歌詞')]);c=self.cue();p.prepare(self.w,dict(self.cfg,duration=12,startOffset=0,opRanges=[dict(start=10,end=12,kind='OP')]),self.job,[c]);self.assertEqual(json.loads((self.job/'source-policy.json').read_text())['subtitleClockGaps'],[])
 def test_legacy_jobs_keep_original_policy(self):
  c=self.cue();before=copy.deepcopy(c);p.prepare(self.w,{},self.job,[c]);self.assertEqual(c,before)
 def test_language_is_primary_text_language(self):
  self.assertEqual(p.language('不要走'),'zh');self.assertEqual(p.language('待って'),'ja');self.assertEqual(p.language('Do not leave'),'en')

class SubmissionTests(unittest.TestCase):
 def setUp(self):
  import test_shared_studio as shared
  self.f=shared.SharedStudioTests('test_basic_submit_uses_automatic_captions_and_preserves_japanese_and_background');self.f.setUp();self.addCleanup(self.f.tearDown);self.app=self.f.app
 def test_new_request_versioned_old_paused_request_not_migrated(self):
  from desktop_state import read,write
  ident=self.f.add();row=self.app.row(ident);first=self.app.store.submit(row);cfg=read(first,{});self.assertEqual(cfg['sourcePolicyRevision'],p.REVISION)
  cfg.pop('sourcePolicyRevision');write(first,cfg);row['status']='paused';self.assertEqual(self.app.store.submit(row),first);self.assertNotIn('sourcePolicyRevision',read(first,{}))
 def test_explicit_source_choice_freezes_into_submission_and_guards_paused(self):
  from desktop_state import read
  ident=self.f.add();self.app.dispatch('set-subtitle-source',dict(id=ident,choice='audio-only'));cfg=read(self.app.store.submit(self.app.row(ident)),{});self.assertEqual(cfg['translationSource'],'audio-only');self.assertFalse(cfg['ocr']);self.assertFalse(cfg['batchAutoSubtitles'])
  self.app.row(ident)['status']='paused'
  with self.assertRaisesRegex(ValueError,'Finish'):self.app.dispatch('set-subtitle-source',dict(id=ident,choice='auto'))
 def test_auto_sidecar_is_frozen_and_source_video_changes_are_rejected(self):
  from desktop_state import read
  ident=self.f.add();video=self.f.video;subtitle=video.with_suffix('.srt');subtitle.write_text('1\n00:00:00,000 --> 00:00:01,000\n字幕\n')
  cfg=read(self.app.store.submit(self.app.row(ident)),{});self.assertTrue(cfg['batchExplicitSubtitle']);self.assertFalse(cfg['batchAutoSubtitles']);self.assertIn('subtitleSnapshot',cfg);self.assertNotEqual(cfg['subtitle'],str(subtitle));p.verify(dict(cfg,video=str(video)))
  video.write_bytes(b'changed source')
  with self.assertRaisesRegex(ValueError,'changed'):p.verify(dict(cfg,video=str(video)))
 def test_explicit_auto_source_cannot_inherit_old_global_audio_or_ocr_mode(self):
  from desktop_state import read
  ident=self.f.add();self.app.store.settings.update(translationSource='audio-and-ocr',ocr=True);self.app.dispatch('set-subtitle-source',dict(id=ident,choice='auto'));cfg=read(self.app.store.submit(self.app.row(ident)),{});self.assertEqual(cfg['translationSource'],'audio-and-subtitles');self.assertFalse(cfg['ocr']);self.assertTrue(cfg['batchAutoSubtitles'])
 def test_ocr_is_expert_only(self):
  ident=self.f.add();self.app.store.mode='basic'
  with self.assertRaisesRegex(ValueError,'Expert'):self.app.dispatch('set-subtitle-source',dict(id=ident,choice='ocr'))
  self.app.store.mode='expert';self.app.dispatch('set-subtitle-source',dict(id=ident,choice='ocr'));self.assertEqual(self.app.row(ident)['conversionSubtitleChoice'],'ocr')
if __name__=='__main__':unittest.main()
