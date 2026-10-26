"""Packaged movie subtitle endpoint, isolated library, no conversion tasks."""
import hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];binary=Path(sys.argv[1]).resolve();sys.path.insert(0,str(ROOT/'tests'))
from test_playback_subtitles import PlaybackSubtitlesTests as Fixture
Fixture.setUpClass()
try:
 with tempfile.TemporaryDirectory(prefix='anicanto-movie-native-') as d:
  root=Path(d);env=dict(os.environ,CANTOSYNC_STUDIO_DATA=d)
  def call(op,**params):
   p=subprocess.run([str(binary),'--verify-desktop-operation'],input=json.dumps(dict(op=op,params=params))+'\n',text=True,capture_output=True,env=env,timeout=40)
   result=json.loads(p.stdout);assert result['ok'],(op,result,p.stderr);return result['result']
  ident=call('add',paths=[str(Fixture.source)])['selected'];statefile=root/'studio/desktop-state.json';before=statefile.read_bytes()
  listing=call('media-subtitles',id=ident,choice='list');assert len(listing['tracks'])==2
  auto=call('media-subtitles',id=ident,choice='auto');assert auto['cues'][0]['text']=='原裝中文字幕'
  en=call('media-subtitles',id=ident,choice=listing['tracks'][1]['id']);assert en['cues'][0]['text']=='Original English'
  assert call('media-subtitles',id=ident,choice='off')['cues']==[];assert statefile.read_bytes()==before
  original=Fixture.zh.read_bytes();call('set-external-subtitle',id=ident,path=str(Fixture.zh));before=statefile.read_bytes()
  external=call('media-subtitles',id=ident,choice='auto');assert external['selected']=='external' and len(external['cues'])==2;assert statefile.read_bytes()==before
  assert Fixture.zh.read_bytes()==original;assert not (root/'jobs').exists()
  report=dict(packagedNativePlayer=True,allEmbeddedChoices=True,external=True,off=True,readonlyPlaybackChoices=True,noASROrConversion=True,sourceModified=False)
  if os.environ.get('ANICANTO_TEST_REPORT'):Path(os.environ['ANICANTO_TEST_REPORT']).write_text(json.dumps(report,indent=2))
  print(json.dumps(report))
finally:Fixture.tearDownClass()
