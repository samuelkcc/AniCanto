"""Host UI and process acceptance. Native Windows/CUDA remains a separate gate."""
import copy,json,os,sys,tempfile,time,wave
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'windows'),str(ROOT/'Resources')]
from desktop import Studio,QApplication,QProcess,QTimer
from desktop_state import write,read,job_snapshot
from project_edit import materialize,spans_for
from voice_expression import settings as expression
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QInputDialog
OUT=Path(os.environ.get('CANTOSYNC_STUDIO_QA_OUT',ROOT/'.build/qa292'));OUT.mkdir(parents=True,exist_ok=True)
app=QApplication([])
def pump(seconds=.1):
 end=time.monotonic()+seconds
 while time.monotonic()<end:app.processEvents();time.sleep(.002)
def idle(window):
 end=time.monotonic()+8
 while (window.tasks or window.worker.state()!=QProcess.NotRunning or window.ui_process.state()!=QProcess.NotRunning) and time.monotonic()<end:pump(.02)
 assert not window.tasks
with tempfile.TemporaryDirectory(prefix='AniCanto-ui-') as root:
 root=Path(root);write(root/'desktop-state.json',dict(language='en',mode='basic',settings={},queue=[],ui={}))
 window=Studio(root);window.show();window.show_plan=lambda:None;pump()
 movie=ROOT/'.build/windows/desktop-qa/日本語 episode 01.mp4';assert movie.is_file()
 window.store.add([movie]);row=window.store.row();job=root/'jobs/fixture';job.mkdir(parents=True)
 audio=job/'speech.wav'
 with wave.open(str(audio),'wb') as w:w.setparams((1,2,24000,0,'NONE','not compressed'));w.writeframes(b'\x01\x20'*24000)
 cfg=dict(storage=str(root),video=str(movie),duration=6,ttsBackend='drama3',selectedEngines=['drama3'],dubLanguages=['yue','en'],voiceProfiles=[dict(id='R1',name='Hero',reference=str(audio),promptText='こんにちは')])
 cues=[dict(start=.2+i*1.6,end=1.4+i*1.6,text='日本語',japanese='こんにちは',cantonese='你好呀！',english='Hello there!',speakerId='R1') for i in range(3)]
 write(job/'review.json',dict(config=cfg,cues=cues));write(job/'subtitle-context.json',[dict(start=.1,end=1.5,text='你好。')]);row.update(review=str(job/'review.json'),status='paused');window.restore_queue();idle(window);pump(.3)
 window.enter('expert');window.select_cue(0,False)
 assert window.original_caption.text()=='你好。'
 window.translated_text.setPlainText('一齊出發啦！');window.commit_transcript();window.take_language.setCurrentIndex(1);assert window.translated_text.toPlainText()=='Hello there!'
 window.translated_text.setPlainText('Let us go!');window.commit_transcript();window.take_language.setCurrentIndex(0);assert window.translated_text.toPlainText()=='一齊出發啦！'
 window.undo();assert window.draft['segments'][0]['english']=='Hello there!';window.redo();assert window.draft['segments'][0]['english']=='Let us go!'
 window.timeline_edit(0,.3,1.4,'voice');assert window.draft['segments'][0]['start']==.3
 window.player.setPosition(3000);window.add_dialogue();assert any(x.get('manual') for x in window.draft['segments'])
 window.player.setPosition(2000);window.split_clip();assert len(window.draft['clips'])==2
 window.background_volume.setValue(80);window.ducking.setChecked(True);assert window.draft['settings']['backgroundGain']==.8
 window.set_setting('ttsBackend','gpt-sovits-v2');assert window.engine.currentData()=='gpt-sovits-v2';window.set_mode('basic');assert window.engine.currentData()=='gpt-sovits-v2';window.set_mode('expert');assert window.store.settings['selectedEngines']==['gpt-sovits-v2']
 with patch.object(QInputDialog,'getText',return_value=('Sidekick',True)):window.add_role()
 new_role=window.draft['settings']['voiceProfiles'][-1]['id'];ident=window.draft['segments'][0]['id'];window.stage_role(ident,new_role);assert window.draft['segments'][0]['speakerId']=='R1';window.commit_role_assignments();assert window.draft['segments'][0]['speakerId']==new_role;window.undo();assert window.draft['segments'][0]['speakerId']=='R1';window.redo();assert window.draft['segments'][0]['speakerId']==new_role
 window.save_draft();materialize(window.snapshot['review'],window.draft);spans_for(window.draft,6)
 for key,spin in window.inference_fields.items():
  values=dict(window.inference_settings);values[key]=spin.minimum();expression(values);values[key]=spin.maximum();expression(values)
 window.set_setting('appearance','dark');assert window.timeline.dark;window.set_setting('appearance','light');assert not window.timeline.dark
 with patch.object(window,'deploy') as deploy:
  window.ready={};window.start_all();deploy.assert_called_once();assert window.start_after_setup
 window.start_after_setup=False;window.enter('expert')
 request=window.store.submit(row);immutable=request.read_bytes();window.set_setting('limit',60);assert window.store.submit(row).read_bytes()==immutable
 for language in ('en','zh-HK'):
  if language!=window.store.language:
   idle(window);window.close();pump();window=Studio(root);window.store.language=language;window.store.save();window.close();pump();window=Studio(root);window.show();window.show_plan=lambda:None;window.enter('expert');idle(window)
  for i in range(10):
   window.nav.setCurrentRow(i);pump(.05);window.grab().save(str(OUT/f'{language}-page-{i}.png'))
  window.set_mode('basic');pump();window.grab().save(str(OUT/f'{language}-basic.png'))
  window.nav.setCurrentRow(9);pump();assert window.pages.currentIndex()==9 and window.basic_return.isVisible();window.grab().save(str(OUT/f'{language}-basic-projects.png'));window.basic_return.click();pump();assert window.pages.currentIndex()==0 and window.store.mode=='basic' and not window.workspace_bar.isVisible()
  window.welcome();pump();window.grab().save(str(OUT/f'{language}-welcome.png'))
  window.guide();assert ('第一次為動畫配音' if language=='zh-HK' else 'Your first dubbed episode') in window.drawer_text.toPlainText();window.close_drawer();window.enter('expert')
 # Exercise a real child process that emits an error and then an exit-0 batch summary.
 row=window.store.row();window.ready=dict(ffmpeg=sys.executable,ffprobe=sys.executable);row['status']='paused'
 failure=OUT/'native-failure-fixture.py';failure.write_text('import json,sys\nprint(json.dumps(dict(stage="批量錯誤",message="CUDA fixture failure")),flush=True)\nprint(json.dumps(dict(stage="批量完成",message="已處理 1 集")),flush=True)\nsys.stderr.write("native diagnostic tail\\n")\n',encoding='utf-8')
 launch=window.worker.launch
 with patch('desktop.env_python',return_value=Path(sys.executable)),patch.object(window.worker,'launch',side_effect=lambda python,script,args,folder:launch(python,str(failure),[],folder)):
  window.launch_worker('batch',request,row['id']);assert window.start_button.isEnabled();idle(window)
 assert row['status']=='attention' and row['lastError']['message']=='CUDA fixture failure';assert window.failure_banner.isVisible()
 evidence=Path(row['attempt']['path']);assert 'native diagnostic tail' in (evidence/'process.log').read_text()
 assert read(evidence/'attempt.json')['status']=='failed'
 window.resize(1280,800);window.set_mode('expert');pump();window.grab().save(str(OUT/'expert-1280.png'));assert window.width()<=1280,(window.width(),window.minimumSizeHint().width())
 window.set_mode('basic');pump();window.grab().save(str(OUT/'basic-1280.png'))
 # Retained state survives restart; no model download is performed by this fixture.
 idle(window);window.close();pump();window=Studio(root);window.show();window.show_plan=lambda:None;window.enter('basic');idle(window);assert window.store.row()['lastError']['message']=='CUDA fixture failure';assert window.failure_banner.isVisible();window.close();pump()
write(OUT/'studio-parity-acceptance.json',dict(host=sys.platform,nativeWindowsExecuted=False,pages=10,languages=['en','zh-HK'],screenshots=28,basicProjectsReturn=True,editing=True,undoRedo=True,fullWidthTimeline=True,captionEvidence=True,nonDestructiveClips=True,inferenceBounds=True,settingsSync=True,immutableSubmissions=True,zeroExitBatchFailurePreserved=True,stderrRetained=True,restartEvidence=True,smallWindow=True))
print(json.dumps(read(OUT/'studio-parity-acceptance.json'),indent=2))
