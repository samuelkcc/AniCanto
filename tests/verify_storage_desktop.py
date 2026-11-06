"""Check packaged storage operations through the native allowlist with isolated data."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

binary=Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory(prefix='anicanto-storage-boundary-') as scratch:
    root=Path(scratch)
    env=dict(os.environ,SAM_CANTO_DATA=scratch,CANTOSYNC_STUDIO_DATA=scratch,CANTOSYNC_WINDOWS_DATA=scratch)
    def call(op,params=None):
        result=subprocess.run([str(binary),'--verify-desktop-operation'],
            input=json.dumps(dict(op=op,params=params or {}))+'\n',env=env,
            capture_output=True,text=True,timeout=30)
        packet=json.loads(result.stdout)
        assert result.returncode==0 and packet.get('ok'),(op,packet,result.stderr)
        return packet['result']
    call('state')
    (root/'jobs/fixture').mkdir(parents=True)
    saved=root/'jobs/fixture/request.json';saved.write_text('{"spent":2,"selectedTake":"first"}')
    recording=root/'jobs/fixture/take.wav';recording.write_bytes(b'keep selected recording')
    (root/'models').mkdir();weights=root/'models/model.bin';weights.write_bytes(b'keep model')
    frozen=hashlib.sha256(saved.read_bytes()).hexdigest()
    results=[]
    for mode in ('basic','expert'):
        call('configure',dict(mode=mode,settings={}))
        health=call('storage-health');assert health['modelsAndProjectsProtected'] and health['root']==str(root.resolve())
        result=call('repair-storage');assert result['removedFiles']==0 and result['projectsChanged'] is False
        temp=root/'cache/uv/cache.bin';temp.parent.mkdir(parents=True,exist_ok=True);temp.write_bytes(b'temporary bytes')
        plan=call('project-cache-plan');assert plan['count']>=1
        cleared=call('clear-project-cache',dict(token=plan['token'],orphanIDs=[],operationID='storage-'+mode))
        assert cleared['complete'] and not temp.exists()
        assert hashlib.sha256(saved.read_bytes()).hexdigest()==frozen
        assert recording.read_bytes()==b'keep selected recording' and weights.read_bytes()==b'keep model'
        results.append(dict(mode=mode,inspection=True,repair=True,cacheCleanup=True,frozenRequestAndAudioPreserved=True))
    owned=root/'jobs'/('c'*16);owned.mkdir()
    take=owned/'take.wav';take.write_bytes(b'explicitly disposable fixture')
    source=owned/'source.mkv';source.write_bytes(b'original fixture')
    sep=root/'separations'/('d'*20);sep.mkdir(parents=True)
    (sep/'vocals.wav').write_bytes(b'derived fixture')
    current=call('project-cache-plan')
    assert current['savedWorkCleanup']['canRemove'] and current['savedWorkCleanup']['count']>=2
    result=call('clear-project-cache',dict(token=current['token'],savedWorkToken=current['savedWorkCleanup']['token'],operationID='saved-work400'))
    assert result['complete'] and not take.exists() and not sep.exists()
    assert source.read_bytes()==b'original fixture' and recording.exists() and weights.exists()
    results.append(dict(savedWorkOptIn=True,separatedAudioCleared=True,unknownJobAndOriginalPreserved=True))
    print(json.dumps(dict(nativeBoundary=True,modes=results,realUserLibraryUsed=False),indent=2))
