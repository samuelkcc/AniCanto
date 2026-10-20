"""Studio interactions; views edit drafts and never rewrite submitted requests."""
import copy,json,os,time,uuid
from pathlib import Path
from PySide6.QtCore import Qt,QTimer,QProcess,QUrl
from PySide6.QtGui import QPixmap
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import *
from desktop_state import ENGINES,write,read,find_take
from studio_icons import icon
from studio_layout import M
from workflow_settings import validated
class StudioEditing:
    def checkpoint_edit(self):
        if self.loading or not self.draft:return
        self.undo_stack.append(copy.deepcopy(self.draft));self.undo_stack=self.undo_stack[-50:];self.redo_stack=[];self.update_edit_buttons()
    def update_edit_buttons(self):
        if hasattr(self,'undo_button'):self.undo_button.setEnabled(bool(self.undo_stack));self.redo_button.setEnabled(bool(self.redo_stack));self.save_button.setEnabled(self.draft is not None)
        if hasattr(self,'dirty_label'):self.dirty_label.setText(self.t('Draft changed','草稿已修改') if self.dirty else '')
    def undo(self):
        if self.draft and self.undo_stack:self.redo_stack.append(copy.deepcopy(self.draft));self.draft=self.undo_stack.pop();self.dirty=True;self.populate_editor();self.update_edit_buttons()
    def redo(self):
        if self.draft and self.redo_stack:self.undo_stack.append(copy.deepcopy(self.draft));self.draft=self.redo_stack.pop();self.dirty=True;self.populate_editor();self.update_edit_buttons()
    def set_setting(self,key,value,project=False):
        if self.loading:return
        if project and self.draft:
            self.checkpoint_edit();self.draft['settings'][key]=value;self.dirty=True
        else:
            if key=='translationSource':value=validated(dict(translationSource=value))['translationSource']
            self.store.settings[key]=value
            if key=='visualRoleAnalysisEnabled':self.store.settings['roleAnalysisMode']='audiovisual' if value else 'audio'
            if key=='roleAnalysisMode' and value!='audiovisual':self.store.settings['visualRoleAnalysisEnabled']=False
            if key=='ttsBackend':self.store.settings.update(selectedEngines=[value],defaultAudioEngine=value)
            if self.draft:
                self.draft['settings'][key]=copy.deepcopy(value);self.dirty=True
                if key in ('visualRoleAnalysisEnabled','roleAnalysisMode'):
                    for name in ('visualRoleAnalysisEnabled','roleAnalysisMode'):self.draft['settings'][name]=self.store.settings[name]
                if key=='ttsBackend':
                    for name in ('selectedEngines','defaultAudioEngine'):self.draft['settings'][name]=copy.deepcopy(self.store.settings[name])
            self.store.save()
        if key in ('ttsBackend','productionMode','includeOriginal','translateOPED','startOffset','limit','subtitleSource','translationSource'):self.sync_controls()
        if key in ('appearance','controlDensity','animeTheme','showStudioCompanion','companionMotion','desktopPetRoaming'):self.apply_preferences()
        self.sync_generic();self.update_edit_buttons()
    def set_inference(self,key,value):
        if self.loading:return
        self.inference_settings[key]=value
    def commit_transcript(self):
        index=getattr(self,'transcript_index',-1)
        if self.loading or not self.draft or not 0<=index<len(self.draft['segments']):return
        row=self.draft['segments'][index];key='english' if getattr(self,'transcript_language','yue')=='en' else 'text';values={key:self.translated_text.toPlainText(),'original':self.source_text.toPlainText(),'captionText':self.caption_override.text()}
        if any(row.get(k,'')!=v for k,v in values.items()):self.checkpoint_edit();row.update(values);row.pop('audioTake',None);self.dirty=True;self.refresh_timeline();self.update_edit_buttons()
    def select_cue(self,index,seek=True):
        self.commit_transcript();self.backend_select_cue(index,seek)
        if not self.draft or not 0<=index<len(self.draft['segments']):return
        self.transcript_index=index;self.transcript_language=self.take_language.currentData();row=self.draft['segments'][index];self.loading=True
        self.source_text.setPlainText(row.get('original',''));self.preview_language.setCurrentIndex(max(0,self.preview_language.findData(self.transcript_language)));self.translated_text.setPlainText(row.get('english','') if self.transcript_language=='en' else row.get('text',''));self.caption_override.setText(row.get('captionText',''))
        self.original_caption.setText(self.original_subtitle_at(row['start']));self.line_title.setText(self.t('Line ','第 ')+str(index+1)+(' 段對白' if self.store.language=='zh-HK' else '')+'\n'+self.timecode(row['start'])+' – '+self.timecode(row['end']))
        self.cue_role.clear();self.cue_role.addItem(self.t('Unassigned','未指定'),'')
        for profile in self.draft['settings'].get('voiceProfiles',[]):self.cue_role.addItem(profile.get('name',profile['id']),profile['id'])
        self.cue_role.setCurrentIndex(max(0,self.cue_role.findData(row.get('speakerId',''))))
        for key,widget in self.segment_fields.items():widget.setValue(row.get(key,1 if key=='rate' else 42 if key=='take' else row['start'] if key=='captionStart' else row['end'] if key=='captionEnd' else 0))
        self.loading=False
    def original_subtitle_at(self,seconds):
        for row in self.snapshot.get('originalCaptions',[]):
            if row.get('start',0)<=seconds<row.get('end',0):return row.get('text','')
        return self.t('No original subtitle at this position','本時段冇原裝字幕')
    def timecode(self,value):
        value=max(0,float(value or 0));return f'{int(value)//3600:02}:{int(value)//60%60:02}:{value%60:04.1f}'
    def populate_editor(self):
        self.transcript_index=-1
        self.backend_populate_editor();self.refresh_role_cards();self.refresh_timeline();self.update_edit_buttons();self.sync_generic()
    def edit_cue(self,item):
        if not self.loading:self.checkpoint_edit()
        self.backend_edit_cue(item)
        if not self.loading and self.draft and self.cue_index>=0:self.transcript_index=-1;self.select_cue(self.cue_index,False)
        self.refresh_timeline();self.update_edit_buttons()
    def change_segment(self,key,value):
        if self.loading or not self.draft or self.cue_index<0:return
        row=self.draft['segments'][self.cue_index]
        if row.get(key)==value:return
        self.checkpoint_edit();self.backend_change_segment(key,value)
        if key in ('start','end','text','english','speakerId'):row.pop('audioTake',None)
        self.refresh_timeline();self.update_edit_buttons()
    def save_draft(self):
        self.commit_transcript();self.backend_save_draft();self.update_edit_buttons()
    def select_queue(self,index):
        old=self.store.selected
        self.backend_select_queue(index)
        if old!=self.store.selected:self.role_changes={};self.undo_stack=[];self.redo_stack=[];self.transcript_index=-1;self.update_edit_buttons()
        row=self.store.row()
        if row and hasattr(self,'workspace_file'):
            self.workspace_file.setText(Path(row['video']).name);self.footer_file.setText(Path(row['video']).name)
            self.browser_info.setText(self.t('Video information','影片資訊')+'\n'+Path(row['video']).name+'\n'+str(Path(row['video']).parent)+'\n'+self.t('Total processing: ','累計處理：')+self.timecode(row.get('processingSeconds',0)))
            self.failure_banner.setVisible(bool(row.get('lastError')))
            if row.get('lastError'):self.show_failure(row)
    def restore_queue(self):
        self.backend_restore_queue()
        if not hasattr(self,'queue_filter'):return
        self.filter_queue()
        if self.store.mode=='basic':
            for index,row in enumerate(self.store.queue):
                item=self.queue_list.item(index);box=QFrame();box.setObjectName('shelfCard');v=QVBoxLayout(box);v.setContentsMargins(12,12,12,12);line=QHBoxLayout();line.addWidget(self.label(f'{index+1:02}',f'{index+1:02}',True));line.addStretch();line.addWidget(self.label(self.status_name(row['status']),self.status_name(row['status']),True));b=QToolButton();b.setIcon(icon('close'));b.setAutoRaise(True);b.clicked.connect(lambda checked=False,i=index:self.remove_shelf_video(i));line.addWidget(b);v.addLayout(line);name=self.label(Path(row['video']).name,Path(row['video']).name);name.setMaximumHeight(66);v.addWidget(name);v.addWidget(self.label(self.t('Total processing: ','累計處理：')+self.timecode(row.get('processingSeconds',0)),self.t('Total processing: ','累計處理：')+self.timecode(row.get('processingSeconds',0)),True));item.setSizeHint(box.sizeHint());self.queue_list.setItemWidget(item,box)
        self.batch_button.setText(self.t('Start all waiting','開始全部待處理')+' ('+str(sum(r['status'] in ('waiting','paused','attention') for r in self.store.queue))+')')
    def remove_shelf_video(self,index):self.queue_list.setCurrentRow(index);self.remove_video()
    def refresh_take(self,*unused):
        self.backend_refresh_take(*unused)
        if hasattr(self,'adopt_button'):self.adopt_button.setEnabled(bool(find_take(self.snapshot,self.cue_index,self.take_engine.currentData(),self.take_language.currentData())))
        if not hasattr(self,'take_rows'):return
        chosen=self.take_engine.currentData();language=self.take_language.currentData();requested=self.store.settings['selectedEngines']
        if self.draft:requested=self.draft['settings'].get('selectedEngines',requested)
        for key,(frame,label,b) in self.take_rows.items():
            take=find_take(self.snapshot,self.cue_index,key,language);frame.setVisible(key in requested or take is not None);b.setEnabled(bool(take));label.setText(dict(ENGINES)[key]+'\n'+(self.t('Available','可試聽') if take else self.t('Waiting for recording','等待生成')))
        if self.draft and self.cue_index>=0:
            row=self.draft['segments'][self.cue_index];self.basic_script.setText(row.get('text',''));self.basic_audition.setText(dict(ENGINES).get(chosen,chosen)+' · '+self.t('Cantonese','廣東話'));self.basic_english.setVisible('en' in self.store.settings.get('dubLanguages',[]));self.basic_english.setEnabled(find_take(self.snapshot,self.cue_index,chosen,'en') is not None)
        self.refresh_timeline()
    def play_engine(self,key):self.take_engine.setCurrentIndex(self.take_engine.findData(key));self.play_take()
    def play_language(self,language):self.take_language.setCurrentIndex(self.take_language.findData(language));self.play_take()
    def refresh_timeline(self):
        if not hasattr(self,'timeline'):return
        self.timeline.cues=self.draft.get('segments',[]) if self.draft else self.snapshot.get('review',{}).get('cues',[]);self.timeline.takes=self.snapshot.get('takes',[]);self.timeline.engine=self.take_engine.currentData() if hasattr(self,'take_engine') else self.store.settings['ttsBackend'];self.timeline.engines=self.store.settings['selectedEngines'];self.timeline.language=self.take_language.currentData();self.timeline.languages=self.store.settings['dubLanguages'];self.timeline.labels=dict(video=self.t('Video','影片'),japanese=self.t('Japanese original','日語原聲'),background=self.t('Music / sound effects','背景音樂／音效'),backgroundHint=self.t('Separated audio appears here','分離後嘅背景音會顯示喺呢度'),caption=self.t('Subtitles','字幕'),voice=self.t('Dubbing window · trim','配音時段 · 可 trim'),yue=self.t('Hong Kong Cantonese','香港廣東話'),**dict(ENGINES))
        self.timeline.duration=max(1,self.player.duration()/1000,self.snapshot.get('review',{}).get('config',{}).get('duration',0));self.timeline.setMinimumHeight(28+26*len(self.timeline.tracks()));self.timeline_scroll.setRange(0,max(0,int(self.timeline.duration*self.timeline.scale-max(1,self.timeline.width()-240))));self.timeline.update()
    def zoom_timeline(self,n):self.timeline.zoom=n/10;self.zoom_label.setText(f'{n/10:.1f}×');self.refresh_timeline()
    def scroll_timeline(self,n):self.timeline.offset=n/self.timeline.scale;self.timeline.update()
    def timeline_edit(self,index,start,end,key):
        if not self.draft or not 0<=index<len(self.draft['segments']):return
        self.checkpoint_edit();row=self.draft['segments'][index];row.update({'captionStart':start,'captionEnd':end} if key=='caption' else {'start':start,'end':end});self.dirty=True;self.populate_editor()
    def add_dialogue(self):
        if not self.draft:return
        self.checkpoint_edit();start=self.player.position()/1000;end=min(start+2,self.timeline.duration)
        if end-start<.05:return
        row=dict(id='manual-'+uuid.uuid4().hex,sources=[],manual=True,start=start,end=end,captionStart=start,captionEnd=end,original='',text=self.t('New line','新對白'),english='New line',speakerId='',enabled=True,rate=1,take=42)
        self.draft['segments'].append(row);self.draft['segments'].sort(key=lambda r:r['start']);self.dirty=True;self.populate_editor();self.select_cue(self.draft['segments'].index(row))
    def split_clip(self):
        if not self.draft:return
        self.read_clips();sec=self.player.position()/1000;clips=self.draft.get('clips') or [dict(start=0,end=self.timeline.duration,enabled=True,ripple=True)]
        for index,row in enumerate(clips):
            if row['start']+.04<sec<row['end']-.04:
                self.checkpoint_edit();clips[index:index+1]=[dict(row,end=sec),dict(row,start=sec)];self.draft['clips']=clips;self.dirty=True;self.populate_editor();break
    def apply_selected_role(self):
        if not self.draft:return
        role=self.cue_role.currentData();indices={x.row() for x in self.cue_table.selectedItems()} or {self.cue_index};self.checkpoint_edit()
        for i in indices:
            if i>=0:self.draft['segments'][i]['speakerId']=role;self.draft['segments'][i].pop('audioTake',None)
        self.dirty=True;self.populate_editor()
    def replace_all_role(self):
        if not self.draft or self.cue_index<0:return
        old=self.draft['segments'][self.cue_index].get('speakerId','');new=self.cue_role.currentData();self.checkpoint_edit()
        for row in self.draft['segments']:
            if row.get('speakerId','')==old:row['speakerId']=new;row.pop('audioTake',None)
        self.dirty=True;self.populate_editor()
    def duration_changed(self,value):
        self.backend_duration_changed(value)
        if hasattr(self,'duration_label'):self.duration_label.setText(self.timecode(value/1000))
        self.refresh_timeline()
    def playhead(self,value):
        self.backend_playhead(value)
        mode=getattr(self,'caption_preview_mode','yue')
        self.video.set_caption('' if mode in ('none','original') else self.caption.text())
        if hasattr(self,'basic_script'):self.basic_script.setText(self.caption.text() or self.t('No dialogue at this position','呢個位置冇對白'))
        if self.loop.isChecked() and self.draft and 0<=self.cue_index<len(self.draft['segments']):
            cue=self.draft['segments'][self.cue_index]
            if value/1000>=cue['end'] and self.player.playbackState()==QMediaPlayer.PlayingState:self.seek(cue['start'])
        if self.follow_captions.isChecked() and self.draft:
            i=next((i for i,r in enumerate(self.draft['segments']) if r['start']<=value/1000<r['end']),None)
            if i is not None and i!=getattr(self,'transcript_index',-1):self.select_cue(i,False)
    def caption_menu(self):
        menu=QMenu(self)
        for label,key in [(self.t('Original subtitles','原片字幕'),'original'),(self.t('Cantonese','廣東話'),'yue'),('English','english'),(self.t('Hide captions','隱藏字幕'),'none')]:menu.addAction(label,lambda k=key:self.set_caption_preview(k))
        self.caption_popup=menu;menu.popup(self.mapToGlobal(self.rect().center()))
    def set_caption_preview(self,key):
        self.caption_preview_mode=key
        if key=='original':self.player.setActiveSubtitleTrack(0 if self.player.subtitleTracks() else -1)
        else:self.player.setActiveSubtitleTrack(-1)
        if key in ('yue','english'):self.take_language.setCurrentIndex(0 if key=='yue' else 1)
    def select_ocr_region(self):
        from studio_regions import RegionDialog
        dialog=RegionDialog(self,self.store.settings.get('ocrRect'))
        if dialog.exec()==QDialog.Accepted:self.set_setting('ocrRect',dialog.region(),False)
    def reveal_output(self):
        row=self.store.row() or {};self.reveal(row.get('output') or self.root/'exports')
    def show_failure(self,row):
        error=row.get('lastError')
        if error and hasattr(self,'failure_banner'):
            self.failure_text.setText(self.t('Conversion stopped: ','轉換停止：')+str(error.get('message',''))[:180]);self.failure_text.setToolTip(str(error.get('message','')));self.failure_text.setMaximumHeight(48);self.failure_banner.show()
    def open_failure(self):
        row=self.store.row() or {};self.nav.setCurrentRow(5);self.set_mode('expert')
        if row.get('lastError'):self.terminal.appendPlainText('\n'+self.t('Last failure','上次失敗')+'\n'+json.dumps(row['lastError'],ensure_ascii=False,indent=2)+'\n'+self.t('Process log: ','程序紀錄：')+str(Path(row.get('attempt',{}).get('path',self.root/'logs'))/'process.log'))
        path=Path(row.get('attempt',{}).get('path',self.root/'logs'))/'process.log'
        def tail():
            if not path.is_file():return ''
            with path.open('rb') as stream:stream.seek(max(0,path.stat().st_size-262144));return stream.read().decode('utf-8','replace')
        self.background(tail,self.terminal.appendPlainText,self.log)
    def retry_failed(self):
        row=self.store.row()
        if not row or self.running:return
        row['status']='paused' if row.get('request') else 'waiting';self.store.save();self.start_selected()
    def refresh_status(self):
        self.backend_refresh_status()
        if not hasattr(self,'footer_state'):return
        row=self.store.row() or {};self.expert_status.setVisible(self.store.mode=='expert' and self.running is not None);self.footer_state.setText(self.t('Processing','處理中') if self.running else self.status_name(row.get('status','waiting')));self.update_edit_buttons()
        self.output_feedback.setVisible(bool(row.get('output')));self.output_label.setText(self.t('✓ Output saved','✓ 成品已保存') if row.get('output') else '')
        self.pause_button.setVisible(self.store.mode=='expert' and (bool(self.running) or row.get('status')=='paused'))
        self.start_button.setText(self.t('Pause and save','暫停並保存') if self.running else self.t('Resume processing','繼續處理') if row.get('status')=='paused' else self.t('Produce a new version','製作新版') if self.draft and row.get('output') else self.t('Start automatic production','開始自動製作'))
        self.batch_button.setVisible(sum(r['status'] in ('waiting','paused') for r in self.store.queue)>1)
    def start_selected(self):
        if self.running:self.pause();return
        row=self.store.row()
        if row and self.draft and row.get('output') and row.get('status')!='paused':self.submit_edit();return
        self.selected_only=True;self.start_all()
    def start_next(self):
        if getattr(self,'selected_only',False):
            self.selected_only=False;self.batch_running=False;row=self.store.row()
            if row is None:return
            self.store.selected=row['id'];self.restore_queue();request=self.store.submit(row);self.launch_worker('batch',request,row['id']);return
        self.backend_start_next()
    def submit_edit(self,preview=False,overrides=None):
        if self.running or not self.draft:return
        try:
            self.save_draft();draft=copy.deepcopy(self.draft);draft['id']=uuid.uuid4().hex;draft['created']=time.time()
            draft['settings']=validated(dict(self.store.settings,**draft['settings']));draft['settings']['previewNativeAudio']=True
            if self.store.mode=='basic' and draft['settings'].get('roleAnalysisMode')=='audiovisual':draft['settings'].update(roleAnalysisMode='audio',visualRoleAnalysisEnabled=False)
            draft['settings'].update(overrides or {})
            if not preview and hasattr(self,'produce_operation'):
                operation=self.produce_operation.currentData()
                if operation=='subtitles':draft['settings'].update(subtitlesOnly=True,scriptLanguages=self.store.settings['dubLanguages'],scriptRevisionMode=self.script_revision.currentData())
                elif operation=='samples':draft['settings'].update(voiceSamplesOnly=True,audioRerunToken=uuid.uuid4().hex)
                if self.force_regenerate.isChecked():draft['settings']['audioRerunToken']=uuid.uuid4().hex
                draft['settings']['reanalyzeRoles']=self.reanalyze_roles.isChecked()
            if preview:
                draft.update(previewSegment=draft['segments'][self.cue_index]['id'],previewEngine=self.take_engine.currentData(),previewLanguage=self.take_language.currentData());draft['settings'].update(self.inference_settings,audioRerunToken=uuid.uuid4().hex)
            from project_edit import materialize,spans_for
            source=self.snapshot['review'];materialize(source,draft);spans_for(draft,float(source['config']['duration']))
            folder=self.root/'requests';path=folder/('edit-'+draft['id']+'.json');write(path,draft);cfg=folder/('render-'+draft['id']+'.json');write(cfg,dict(storage=str(self.root),submission=str(path),selectedEngines=draft['settings']['selectedEngines'],ttsBackend=draft['settings']['ttsBackend']))
            self.active_preview=preview;self.batch_running=False;self.launch_worker('render-project',cfg,self.store.selected)
        except (OSError,ValueError,KeyError) as error:self.notice(str(error))
    def compare_ab(self):
        if not self.draft or self.cue_index<0 or self.running:return
        self.ab_pending=self.ab_engine.currentData();self.retake()
    def sync_generic(self):
        for key,widgets in getattr(self,'generic_controls',{}).items():
            value=self.draft['settings'].get(key,self.store.settings.get(key)) if self.draft and key in ('backgroundGain','backgroundDucking','captionBottom','captionSize') else self.store.settings.get(key)
            for w in widgets:
                w.blockSignals(True)
                if isinstance(w,QCheckBox):w.setChecked(bool(value))
                elif isinstance(w,(QDoubleSpinBox,QSpinBox)) and value is not None:w.setValue(value)
                elif isinstance(w,QComboBox):w.setCurrentIndex(max(0,w.findData(value)))
                elif isinstance(w,QLineEdit):w.setText(str(value or ''))
                elif isinstance(w,QPlainTextEdit):w.setPlainText(str(value or ''))
                w.blockSignals(False)
    def update_defaults(self):
        self.sync_generic()
    def select_welcome_mode(self,mode):self.store.mode=mode;self.store.save()
    def sync_controls(self):
        self.backend_sync_controls()
        if hasattr(self,'fast_mode_combo'):self.fast_mode_combo.setCurrentIndex(int(self.fast.isChecked()))
        self.sync_generic()
    def settings_changed(self,*unused):
        before=copy.deepcopy(self.store.settings);self.backend_settings_changed(*unused)
        if self.draft and not self.loading:
            for key,value in self.store.settings.items():
                if before.get(key)!=value:self.draft['settings'][key]=copy.deepcopy(value);self.dirty=True
        self.update_edit_buttons()
    def refresh_history(self,*unused):
        self.backend_refresh_history()
        if hasattr(self,'issue_filter'):
            key=self.issue_filter.currentData()
            for i,row in enumerate(self.snapshot.get('history',[])):
                reason=str(row.get('reason','')).lower();query=self.issue_search.text().lower() if hasattr(self,'issue_search') else '';hide=bool(query and query not in json.dumps(row,ensure_ascii=False).lower()) or key=='failed' and not any(s in reason for s in ('fail','generation','缺聲','失敗')) or key=='repaired' and not row.get('repaired') or key=='review' and row.get('repaired',False)
                self.history.setRowHidden(i,hide)
    def log(self,text):
        if not text:return
        if hasattr(self,'terminal_lines'):self.terminal_lines=(self.terminal_lines+[str(text)])[-4000:]
        try:self.backend_log(text)
        except OSError as error:
            if hasattr(self,'terminal'):self.terminal.appendPlainText('Log storage error: '+str(error))
    def work_finished(self,code,status):
        previous=self.store.row(self.running);preview=getattr(self,'active_preview',False)
        self.backend_work_finished(code,status)
        if preview and code==0 and self.ab_pending:
            engine=self.ab_pending;self.ab_pending=None;self.take_engine.setCurrentIndex(self.take_engine.findData(engine));QTimer.singleShot(100,self.retake)
        if previous and hasattr(self,'produce_result'):
            versions=sorted((Path(previous.get('review','/nonexistent')).parent/'versions').glob('*/version.json'))
            self.produce_result.setPlainText('\n'.join((read(p,{}).get('status','')+' · '+str(read(p,{}).get('output') or read(p,{}).get('error') or p.parent)) for p in versions))

    def language_audition_changed(self,*unused):
        self.commit_transcript();self.refresh_take()
        if self.cue_index>=0:self.select_cue(self.cue_index,False)
    def record_preflight_error(self,row,request,action,message):
        from diagnostics import start,finish
        start(self.root,row,action,request);self.store.event(row,dict(stage='Error',errorCode='preflight',message=message));finish(self.root,row,1);row['status']='attention';self.store.save();self.batch_running=False;self.show_failure(row);self.log(message);self.restore_queue();self.refresh_status()

    def role_changed(self,item):
        if self.loading or item.column()==0:return
        self.checkpoint_edit();self.backend_role_changed(item);self.refresh_role_cards();self.update_edit_buttons()
    def replace_reference(self):
        self.checkpoint_edit();self.backend_replace_reference();self.update_edit_buttons()

    def find_drawer_text(self,words):
        from PySide6.QtGui import QTextCursor
        cursor=self.drawer_text.textCursor();cursor.movePosition(QTextCursor.Start);self.drawer_text.setTextCursor(cursor)
        if words:self.drawer_text.find(words)
