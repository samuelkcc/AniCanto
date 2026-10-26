"""Exercise the packaged native allowlist and editing RPC with isolated media."""
import json,os,sys,tempfile,subprocess,hashlib,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];binary=Path(sys.argv[1]).resolve();sys.path.insert(0,str(ROOT/'tests'))
from test_playback_subtitles import PlaybackSubtitlesTests as Fixture
Fixture.setUpClass()
try:
 with tempfile.TemporaryDirectory(prefix='anicanto-tools77-native-') as d:
  root=Path(d);env=dict(os.environ,CANTOSYNC_STUDIO_DATA=d,PYTHONDONTWRITEBYTECODE='1')
  def call(op,expect=True,**params):
   p=subprocess.run([str(binary),'--verify-desktop-operation'],input=json.dumps(dict(op=op,params=params))+'\n',text=True,capture_output=True,env=env,timeout=45)
   data=json.loads(p.stdout)
   if expect:assert data['ok'],(op,data,p.stderr);return data['result']
   assert not data['ok'],(op,data);return data
  state=call('add',paths=[str(Fixture.source)]);ident=state['selected'];call('set-external-subtitle',id=ident,path=str(Fixture.zh));raw=Fixture.zh.read_bytes()
  preview=call('subtitle-alignment-preview',id=ident,alignment=dict(mode='offset',offset=.2));assert preview['offset']==.2
  call('set-subtitle-alignment',expect=False,id=ident,alignment=dict(offset=.2),token='stale')
  call('set-subtitle-alignment',id=ident,alignment=dict(mode='offset',offset=.2),token=preview['token']);aligned=call('media-subtitles',id=ident,choice='external');assert Fixture.zh.read_bytes()==raw
  assert abs(aligned['cues'][0]['start']-preview['sample'][0]['start'])<.001
  folder=root/'jobs/fixture';folder.mkdir(parents=True)
  wav=folder/'japanese-original.wav';ffmpeg=binary.parent.parent/'Resources/bin/ffmpeg'
  subprocess.run([str(ffmpeg),'-v','error','-i',str(Fixture.source),'-map','0:a:0','-ac','1',str(wav)],check=True)
  shutil.copy2(wav,folder/'voice.wav')
  review=dict(config=dict(video=str(Fixture.source),storage=d,duration=4,selectedEngines=['drama3'],dubLanguages=['yue'],ttsBackend='drama3'),cues=[dict(start=.2,end=1.6,japanese='こんにちは',text='こんにちは',cantonese='你好',speakerId='R01',enabled=True)])
  (folder/'review.json').write_text(json.dumps(review));(folder/'timing.json').write_text(json.dumps([dict(index=1,start=.2,end=1.6,audio=str(folder/'voice.wav'))]));(folder/'audio-preview.json').write_text(json.dumps(dict(engine='drama3',language='yue')))
  (folder/'japanese-analysis.json').write_text(json.dumps(dict(segments=[dict(words=[dict(start=.2,end=.5,word='こん',probability=.9),dict(start=1.1,end=1.6,word='にちは',probability=.9)])])))
  statefile=root/'studio/desktop-state.json';state=json.loads(statefile.read_text());state['queue'][0].update(status='complete',review=str(folder/'review.json'),job=str(folder));statefile.write_text(json.dumps(state))
  snapshot=call('snapshot',id=ident);draft=snapshot['draft'];assert snapshot['coverage']['tracks'][0]['recordings']==1
  waves=call('audio-waveforms',id=ident,index=0,engine='drama3',language='yue');assert {x['label'] for x in waves['rows']}=={'original','generated'};assert all(x['peaks'] for x in waves['rows'])
  params=dict(id=ident,draft=draft,operation='all',engine='drama3',language='yue',replaced=[''],segment=draft['segments'][0]['id'])
  before=(folder/'review.json').read_bytes();impact=call('recording-impact',**params);assert impact['dialogueCount']==1;assert (folder/'review.json').read_bytes()==before
  call('update-recording-plan',expect=False,**params,impactToken='stale');updated=call('update-recording-plan',**params,impactToken=impact['token']);assert updated['settings']['audioRerunToken'];assert (folder/'review.json').read_bytes()==before
  suggestions=call('boundary-proposals',id=ident,draft=draft);assert suggestions['proposals'];split=call('apply-boundary',id=ident,draft=draft,proposalIndex=0,token=suggestions['token'],parts=dict(original=dict(left='こん',right='にちは'),text=dict(left='你',right='好')));assert len(split['draft']['segments'])==2;assert (folder/'voice.wav').is_file()
  removed=call('remove-videos',ids=[ident]);assert not removed['state']['queue'];assert (folder/'voice.wav').is_file();restored=call('restore-videos',batch=removed['batch']);assert restored['state']['queue'][0]['id']==ident
  result=dict(packagedNative=True,subtitlePreviewAndApply=True,stalePreviewRejected=True,waveforms=True,coverage=True,regenerationImpactGuard=True,wordBoundaryDraftOnly=True,metadataRemovalAndRestore=True,modelInference=False,sourceModified=False)
  if os.environ.get('ANICANTO_TEST_REPORT'):Path(os.environ['ANICANTO_TEST_REPORT']).write_text(json.dumps(result,indent=2))
  print(json.dumps(result))
finally:Fixture.tearDownClass()
