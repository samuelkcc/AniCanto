"""Host Qt acceptance fixture; not a claim of native Windows/GPU execution."""
import hashlib,json,os,sys,time,subprocess
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'windows'),str(ROOT/'Resources')]
from desktop import QApplication,Studio,QProcess,QTimer,NativeProcess
from desktop_state import write,read

out=ROOT/'.build/windows/desktop-qa';out.mkdir(parents=True,exist_ok=True)
data=out/'data';data.mkdir(exist_ok=True)
for name in ['desktop-state.json']:(data/name).unlink(missing_ok=True)
app=QApplication([]);window=Studio(data);window.show()
def pump(seconds=.2):
 end=time.monotonic()+seconds
 while time.monotonic()<end:app.processEvents();time.sleep(.002)

import imageio_ffmpeg
movie=out/'日本語 episode 01.mp4'
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-y','-f','lavfi','-i','testsrc2=size=640x360:rate=24','-f','lavfi','-i','sine=frequency=220:sample_rate=48000','-t','6','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',str(movie)],check=True)
window.store.add([movie,out/'日本語 episode 02.mp4'])
row=window.store.queue[0];job=data/'jobs/fixture';job.mkdir(parents=True,exist_ok=True)
cues=[dict(start=i*.05,end=i*.05+.045,text=f'日本語 {i}',japanese=f'日本語 {i}',cantonese=f'一齊出發啦，{i}！',english=f'Let us go, {i}!',speakerId='r1') for i in range(100)]
review=job/'review.json';write(review,dict(config=dict(storage=str(data),video=row['video'],duration=6,ttsBackend='drama3',dubLanguages=['yue','en'],voiceProfiles=[dict(id='r1',name='Actor',reference='sample.wav',promptText='こんにちは')]),cues=cues))
row['review']=str(review);row['status']='paused';window.store.selected=row['id'];window.store.save();window.restore_queue();pump(.8)
assert window.draft and len(window.draft['segments'])==100
assert window.player.duration()>=5900,window.player.errorString()
assert window.store.settings['dubLanguages']==['yue','en']
request=window.store.submit(row);before=request.read_bytes();row['status']='paused'
window.enter('expert');pump();assert window.pages.count()==10
assert window.take_engine.currentData()=='drama3'
window.select_cue(50);assert window.cue_index==50
window.cue_table.item(50,3).setText('唔好停呀！');assert window.draft['segments'][50]['text']=='唔好停呀！'
window.store.settings['selectedEngines']=['cosyvoice3'];window.store.settings['ttsBackend']='cosyvoice3';window.sync_controls()
window.set_mode('basic');assert window.engine.currentData()=='cosyvoice3'
assert window.store.submit(row).read_bytes()==before
window.store.settings['selectedEngines']=['drama3'];window.store.settings['ttsBackend']='drama3';window.sync_controls()
window.resize(1550,990);pump();window.grab().save(str(out/'basic.png'))
window.set_mode('expert');pump();window.grab().save(str(out/'expert.png'))
window.guide();assert 'Your first dubbed episode' in window.drawer_text.toPlainText()
assert '第一次' not in window.drawer_text.toPlainText();window.close_drawer()
window.about();pump(.8);assert 'MIT' in window.drawer_text.toPlainText();window.close_drawer()
for i in range(10):
 window.nav.setCurrentRow(i);pump(.03)
window.nav.setCurrentRow(0);window.set_mode('basic')
heartbeat=[];last=[time.monotonic()]
timer=QTimer();timer.setInterval(10)
def beat():
 now=time.monotonic();heartbeat.append(now-last[0]);last[0]=now
timer.timeout.connect(beat);timer.start()
window.player.play();pump(.15)
for i in range(100):window.seek((i%50)/10);pump(.002)
window.player.pause()
started=time.monotonic()
with patch('desktop.read',side_effect=AssertionError('Playback performed disk JSON I/O')):
 for i in range(2000):window.playhead((i%200)*1000)
cost=time.monotonic()-started;pump(.3);timer.stop()
assert cost<1.5,cost
source=out/'emit-fixture.py'
source.write_text('import os,time,json\ns=json.dumps(dict(stage="翻譯",message="香港廣東話",journey=dict(progress=.51,milestones=[])),ensure_ascii=False).encode()+b"\\n"\nfor b in s: os.write(1,bytes([b])); time.sleep(.0001)\n',encoding='utf-8')
process=NativeProcess(window);events=[];process.event.connect(events.append);process.launch(sys.executable,str(source),[],data)
deadline=time.monotonic()+5
while process.state()!=QProcess.NotRunning and time.monotonic()<deadline:pump(.03)
assert len(events)==1 and events[0]['message']=='香港廣東話',events
window.running=row['id'];window.run_action='render-project';window.run_started=time.monotonic();window.edit_job=None;window.edit_output=None
row['output']=str(out/'completed.mp4');window.work_event(dict(stage='試音完成',output='audition.wav',job=str(job/'versions/a')))
assert row['output']==str(out/'completed.mp4');assert row['review']==str(review)
window.running=None;window.save_draft();pump();window.close();pump()
receipt=dict(host=sys.platform,nativeWindowsExecuted=False,pages=10,basicExpertShareSettings=True,
 immutableResume=True,japaneseUnicodeEventStreaming=True,auditionDoesNotOverwriteMovie=True,
 playbackJSONReads=0,playheadCallbacks=2000,playheadSeconds=round(cost,4),
 maxHeartbeatSeconds=round(max(heartbeat),4),englishGuide=True,aboutMIT=True,realMediaLoaded=True,rapidNativeSeeks=100)
write(out/'receipt.json',receipt);print(json.dumps(receipt,indent=2))
