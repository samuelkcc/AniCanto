import copy,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'Resources'),str(ROOT/'windows')]
import primary_source as p
import performance_review
from atomic_files import write_json
class OwnershipBoundaryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.job=Path(self.tmp.name);self.calls=0
  self.cfg=dict(sourcePolicyRevision=p.REVISION,sourceAllocationRevision=p.ALLOCATION_REVISION,translationSource='audio-and-subtitles',subtitle='s.srt',model='test',port=0,sourceLanguage='ja')
  def chat(*a,**k):self.calls+=1;return '{}'
  self.w=SimpleNamespace(atomic_json=write_json,emit=lambda *a,**k:None,ollama_chat=chat)
 def cue(self,a,b,text='日本語'):
  return dict(start=a,end=b,speechStart=a,speechEnd=b,japanese=text,text=text,enabled=True)
 def test_display_tail_does_not_chain_three_distinct_captions(self):
  cs=[self.cue(1392.13,1394.05),self.cue(1394.05,1396.91),self.cue(1396.91,1398.81)]
  captions=[dict(start=1392.14,end=1394.26,text='甚平与娜美在城堡内到处奔走'),dict(start=1394.39,end=1397.06,text='另外为了传达隐藏在婚礼中的阴谋'),dict(start=1397.14,end=1398.85,text='路飞拼命奔向香吉身边')]
  original=copy.deepcopy(cs);write_json(self.job/'subtitle-context.json',captions);p.prepare(self.w,self.cfg,self.job,cs)
  self.assertEqual([p.content(c) for c in cs],[r['text'] for r in captions]);self.assertEqual(self.calls,0);self.assertFalse(any(c.get('sourcePolicyBlocked') for c in cs));self.assertEqual([(c['start'],c['end'],c['japanese']) for c in cs],[(c['start'],c['end'],c['japanese']) for c in original])
 def test_real_shared_name_call_is_not_lost_by_overlap_filter(self):
  r=dict(start=0,end=4,text='小茜，我只用右手打倒佢');cs=[self.cue(0,.45,'あかね'),self.cue(.45,4)]
  self.assertEqual(p.speech_owners(r,cs),['0','1'])
 def test_failed_model_keeps_full_authored_caption_once_and_warns(self):
  cs=[self.cue(0,.5,'あかね'),self.cue(.5,4)];text='小茜，我只用右手打倒佢';write_json(self.job/'subtitle-context.json',[dict(start=0,end=4,text=text)]);before=copy.deepcopy(cs)
  p.prepare(self.w,self.cfg,self.job,cs);self.assertEqual(self.calls,2);self.assertEqual([p.content(c) for c in cs],['',text]);self.assertEqual(cs[0]['originalSpeechReason'],'subtitle-continuation');self.assertTrue(all(c['sourceAllocationReview'] for c in cs));self.assertFalse(cs[1].get('sourcePolicyBlocked'));self.assertTrue(cs[0]['preserveOriginalSpeech']);self.assertEqual([(c['start'],c['end']) for c in cs],[(c['start'],c['end']) for c in before])
  report=json.loads((self.job/'source-policy.json').read_text());self.assertEqual(report['fallbackTurns'],[1,2]);p.prepare(self.w,self.cfg,self.job,cs);self.assertEqual(self.calls,2,'bounded decisions must survive resume');self.assertEqual([p.content(c) for c in cs],['',text])
 def test_frozen_83_request_keeps_old_allocation_policy(self):
  cfg=dict(self.cfg);cfg.pop('sourceAllocationRevision');cs=[self.cue(0,.5),self.cue(.5,4)];write_json(self.job/'subtitle-context.json',[dict(start=0,end=4,text='完整字幕')]);p.prepare(self.w,cfg,self.job,cs);self.assertTrue(all(c.get('sourcePolicyBlocked') for c in cs));self.assertEqual(self.calls,2)
 def test_mislabeled_id_can_only_rebind_a_unique_exact_allowed_quote(self):
  records={'a':dict(text='小茜'),'b':dict(text='我只用右手打倒佢')};owners={'a':['0'],'b':['1']};answer={'0':[dict(captionID='a',quote='小茜')],'1':[dict(captionID='a',quote='我只用右手打倒佢')]}
  fixed=p.allocate(answer,['0','1'],records,owners,rebind=True);self.assertEqual(fixed['1']['ids'],['b']);self.assertEqual(fixed['1']['text'],records['b']['text'])
  with self.assertRaises(ValueError):p.allocate(answer,['0','1'],records,owners)
  answer['1'][0]['quote']='我只用左手打倒佢'
  with self.assertRaises(ValueError):p.allocate(answer,['0','1'],records,owners,rebind=True)
 def test_punctuation_only_contact_is_not_speech_overlap(self):
  self.assertEqual(p.speech_owners(dict(start=2,end=4),[self.cue(0,2),self.cue(2,4)]),['1'])
class PollProjectionTests(unittest.TestCase):
 def test_large_performance_report_reads_review_once_per_folder(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'japanese-original.wav').write_bytes(b'audio');events=[dict(start=i,end=i+.2,label='laugh') for i in range(1200)]
   write_json(root/'nonverbal-report.json',dict(reviewEvents=events,events=[],originalSoundRanges=[]));write_json(root/'review.json',dict(config={}))
   original=performance_review.read;reads=[]
   def read(path,default):reads.append(Path(path).name);return original(path,default)
   with patch.object(performance_review,'read',read):result=performance_review.project(root,[root],{})
   self.assertEqual(reads.count('review.json'),1);self.assertEqual(result['remainingNotes'],1000);self.assertEqual(result['notes'][0]['auditions']['original']['end'],.2);self.assertEqual(result['notes'][1]['auditions']['original']['start'],1)
 def test_uncertain_caption_is_a_per_line_review_issue(self):
  import review_report
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);review=dict(config=dict(ttsBackend='drama3',dubLanguages=['yue']),cues=[dict(start=2,end=4,japanese='日本語',cantonese='',sourcePolicyBlocked=True)])
   value=review_report.project(root,review,dict(status='complete'))
   self.assertTrue(any(i['index']==1 and any(e.get('file')=='source-policy.json' for e in i['evidence']) for i in value['issues']))
if __name__=='__main__':unittest.main()
