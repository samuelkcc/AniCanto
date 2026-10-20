"""Exercise the packaged native RPC boundary using isolated application data.

No model downloads, user-library edits or speech inference. This intentionally
uses the same operation allowlist as Tauri, not direct Python-only dispatch.
"""
import json,os,subprocess,sys,tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
binary=Path(sys.argv[1]).resolve()
python=Path(os.environ['CANTOSYNC_STUDIO_PYTHON'])
with tempfile.TemporaryDirectory(prefix='anicanto-native-rpc-') as folder:
    env=dict(os.environ,CANTOSYNC_STUDIO_DATA=folder,CANTOSYNC_STUDIO_PYTHON=str(python))
    def call(op,params=None,success=True):
        result=subprocess.run([str(binary),'--verify-desktop-operation'],input=json.dumps(dict(op=op,params=params or {}))+'\n',text=True,capture_output=True,env=env,timeout=30)
        data=json.loads(result.stdout)
        assert data['ok'] is success,(op,data,result.stderr)
        assert (result.returncode==0) is success,(op,result.returncode)
        return data.get('result') if success else data['error']
    document=call('use-terms');assert document['accepted'] is False
    for language in ('en','zh-HK'):
        state=call('configure',dict(language=language,settings={}))
        assert state['language']==language
        assert 'Unsupported' not in call('accept-use-terms',dict(accepted=True,sha256=document['sha256'],language=language))
        assert call('state')['useTermsAccepted'] is True
        assert call('use-terms')['accepted'] is True
        call('revoke-use-terms');assert call('state')['useTermsAccepted'] is False
    error=call('accept-use-terms',dict(accepted=True,sha256='stale'),success=False)
    assert 'Unsupported' not in error and 'accept' in error
    assert 'Unsupported desktop operation' not in call('source-language',success=False)
    assert 'Unsupported desktop operation' not in call('review-resolution',success=False)
    assert 'Unsupported desktop operation' in call('execute-shell',success=False)
    ffmpeg=Path(os.environ.get('ANICANTO_TEST_FFMPEG',str(ROOT/'dist/AniCanto.app/Contents/Resources/bin/ffmpeg')))
    movie=Path(folder)/'language-fixture.mkv'
    subprocess.run([str(ffmpeg),'-v','error','-y','-f','lavfi','-i','color=s=64x64:r=10:d=1','-f','lavfi','-i','sine=frequency=440:duration=1','-f','lavfi','-i','sine=frequency=880:duration=1','-map','0:v','-map','1:a','-map','2:a','-c:v','libx264','-c:a','aac','-metadata:s:a:0','language=jpn','-metadata:s:a:1','language=eng','-disposition:a:0','0','-disposition:a:1','default',str(movie)],check=True)
    added=call('add',dict(paths=[str(movie)]))
    other=Path(folder)/'queue-fixture.mkv';other.write_bytes(movie.read_bytes())
    more=call('add',dict(paths=[str(other)]));second=more['queue'][-1]['id']
    moved=call('move-video',dict(id=second,beforeID=added['selected']))
    assert [r['id'] for r in moved['queue']]==[second,added['selected']]
    assert moved['selected']==added['selected']
    call('move-video',dict(id=second,beforeID=None))
    assert 'list changed' in call('move-video',dict(id=second,beforeID='stale'),success=False)
    # Simulate a host crash: metadata says running, but this exclusive native
    # host owns no worker. Recovery must preserve its frozen request and work.
    state_path=Path(folder)/'studio/desktop-state.json'
    saved=json.loads(state_path.read_text());saved['queue'][0].update(status='running',request='retained-frozen-request',job='retained-work')
    state_path.write_text(json.dumps(saved))
    recovered=call('state')['queue'][0]
    assert recovered['status']=='paused' and recovered['request']=='retained-frozen-request' and recovered['job']=='retained-work'
    sys.path.insert(0,str(ROOT/'Resources'))
    from model_catalog import catalog,folder as model_folder
    model=next(r for r in catalog() if r['id']=='v4')
    base=model_folder(Path(folder),model);file=base/next(f['path'] for f in model['files'] if f['path']=='gsv-v4-pretrained/s2Gv4.pth');file.parent.mkdir(parents=True);file.write_bytes(b'private fixture')
    v2=next(r for r in catalog() if r['id']=='v2ProPlus')
    shared_path=next(f['path'] for f in model['files'] if f['path'] in {x['path'] for x in v2['files']})
    common=base/shared_path;common.parent.mkdir(parents=True,exist_ok=True);common.write_bytes(b'shared fixture')
    removal=call('model-removal-plan',dict(id='v4'));assert removal['canRemove'] is True and removal['sharedBytesRetained']==14
    call('remove-model',dict(id='v4'));assert not file.exists() and common.exists()
    assert 'v4' not in {r['id'] for r in call('models')}
    assert 'v2ProPlus' in {r['id'] for r in call('models')}
    final=call('remove-model',dict(id='v2ProPlus'));assert final['freedBytes']==14 and not common.exists()
    assert 'v2ProPlus' not in {r['id'] for r in call('models')}
    language=call('source-language',dict(id=added['selected']))
    assert language['language']=='en' and language['stream']==2
    assert language['supported'] is True and language['needsConfirmation'] is True
    assert call('state')['queue'][0]['sourceLanguage']=='en'
    assert not (Path(folder)/'use-terms-acceptance.json').exists()
print(json.dumps(dict(nativeDesktopBoundary=True,queueMovesPersist=True,sharedVariantRemoval=True,staleRecovery=True,termsReadAcceptRevoke=True,sourceLanguageNativeBoundary=True,nonJapaneseRequiresConfirmation=True,languages=['en','zh-HK'],staleConsentRejected=True,unknownOperationsRejected=True,userLibraryChanged=False)))
