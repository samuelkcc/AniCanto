"""Windows rendering of the Mac studio's layout and navigation contract."""
import json,copy
from pathlib import Path
from PySide6.QtCore import Qt,QSize,QTimer
from PySide6.QtGui import QIcon,QPixmap,QKeySequence,QShortcut
from PySide6.QtWidgets import *
from studio_icons import icon
from desktop_widgets import Journey,Timeline
from desktop_state import ENGINES
HERE=Path(__file__).resolve().parent;SHARED=HERE/'shared' if (HERE/'shared').is_dir() else HERE.parent/'Resources'
CONTRACT=json.loads((SHARED/'studio-interface.json').read_text());M=CONTRACT['metrics']
class CommitText(QPlainTextEdit):
    from PySide6.QtCore import Signal
    committed=Signal()
    def focusOutEvent(self,event):super().focusOutEvent(event);self.committed.emit()
class StudioLayout:
    def panel_header(self,en,zh,parent=None,icon_name=None):
        frame=QFrame();frame.setObjectName('panelHeader');frame.setFixedHeight(M['panelHeader']);layout=QHBoxLayout(frame);layout.setContentsMargins(12,0,12,0)
        if icon_name:
            image=QLabel();image.setPixmap(icon(icon_name,size=16).pixmap(16,16));layout.addWidget(image)
        label=self.label(en,zh);font=label.font();font.setBold(True);font.setPixelSize(14);label.setFont(font);layout.addWidget(label);layout.addStretch()
        if parent:parent.addWidget(frame)
        return frame,layout,label
    def tool(self,name,en,zh,fn,parent=None,checkable=False):
        button=QToolButton();button.setObjectName('iconButton');button.setIcon(icon(name,self.accent if checkable else '#5d6067'));button.setIconSize(QSize(18,18));button.setToolTip(self.t(en,zh));button.setAccessibleName(self.t(en,zh));button.setProperty('studioIcon',name);button.setProperty('studioTint',checkable);button.setCheckable(checkable);button.clicked.connect(fn)
        if parent:parent.addWidget(button)
        return button
    def segmented(self,combo,parent):
        widget=QWidget();row=QHBoxLayout(widget);row.setContentsMargins(0,0,0,0);row.setSpacing(0);group=QButtonGroup(widget);group.setExclusive(True)
        for i in range(combo.count()):
            b=QPushButton(combo.itemText(i));b.setCheckable(True);b.setChecked(i==combo.currentIndex());row.addWidget(b);group.addButton(b,i);b.clicked.connect(lambda checked=False,index=i:combo.setCurrentIndex(index))
        combo.currentIndexChanged.connect(lambda index:group.button(index).setChecked(True) if group.button(index) else None);combo.hide();widget._combo=combo;widget._buttons=group;parent.addWidget(widget);return widget
    def scroll(self,widget):
        area=QScrollArea();area.setWidgetResizable(True);area.setFrameShape(QFrame.NoFrame);area.setWidget(widget);return area
    def heading(self,layout,en,zh,detail=None):
        label=self.label(en,zh);label.setObjectName('heading');layout.addWidget(label)
        if detail:layout.addWidget(self.label(*detail,True))
    def build_workspace(self):
        page=QWidget();whole=QVBoxLayout(page);whole.setContentsMargins(0,0,0,0);whole.setSpacing(0)
        appbar=QWidget();appbar.setFixedHeight(M['appBar']);bar=QHBoxLayout(appbar);bar.setContentsMargins(20,0,20,0);bar.setSpacing(6)
        emblem=QLabel();emblem.setPixmap(QPixmap(str(SHARED/'AniCanto-icon.png')).scaled(24,24,Qt.KeepAspectRatio,Qt.SmoothTransformation));bar.addWidget(emblem);brand=self.label('AniCanto','AniCanto');brand.setObjectName('brand');bar.addWidget(brand);bar.addStretch()
        self.expert_tools=QWidget();actions=QHBoxLayout(self.expert_tools);actions.setContentsMargins(0,0,0,0);actions.setSpacing(4)
        self.undo_button=self.tool('undo','Undo','撤銷',self.undo,actions);self.redo_button=self.tool('redo','Redo','重做',self.redo,actions);self.save_button=self.tool('save','Save','儲存',self.save_draft,actions)
        self.panel_actions=[];self.panel_toggles=[]
        for i,(key,en,zh) in enumerate([('navigation','Navigation','工作選單'),('browser','Project library','專案庫'),('inspector','Inspector','檢查器')]):
            action=self.tool(key,en,zh,lambda checked=False,index=i:self.toggle_panel(index,checked),actions,True);action.setChecked(self.store.ui.get(key,True));self.panel_actions.append(action);self.panel_toggles.append(action)
        self.panel_button=self.tool('layout','Layout','佈局',lambda:None,actions);menu=QMenu(self.panel_button)
        menu.addAction(self.t('Reset panel layout','重設面板配置'),self.reset_layout);menu.addAction(self.t('Focus preview','放大預覽'),self.focus_preview);menu.addAction(self.t('Full screen','全螢幕'),lambda:self.showNormal() if self.isFullScreen() else self.showFullScreen());self.panel_button.setMenu(menu);self.panel_button.setPopupMode(QToolButton.InstantPopup);bar.addWidget(self.expert_tools)
        self.mode_button=QPushButton();mode_menu=QMenu(self.mode_button)
        for en,zh,mode in [('Basic mode','基本模式','basic'),('Expert mode','專家模式','expert')]:
            a=mode_menu.addAction(self.t(en,zh),lambda m=mode:self.set_mode(m));a.setCheckable(True)
        self.mode_button.setMenu(mode_menu);bar.addWidget(self.mode_button)
        self.tool('guide','Quick guide','使用教學',self.guide,bar);self.tool('about','About and licences','關於與授權',self.about,bar);self.tool('welcome','Welcome','返回歡迎畫面',self.welcome,bar)
        self.pause_button=self.tool('pause','Pause and save','暫停並保存',self.pause,bar);self.export_button=self.button('Export video','匯出影片',lambda:self.nav.setCurrentRow(3),bar,True);self.export_button.setIcon(icon('export','white'));whole.addWidget(appbar)
        self.expert_status=QWidget();status=QVBoxLayout(self.expert_status);status.setContentsMargins(12,5,12,5);status.setSpacing(2)
        sr=QHBoxLayout();self.status_title=self.label('Ready','就緒');sr.addWidget(self.status_title,1);self.status_time=self.label('','',True);self.status_time.setAlignment(Qt.AlignRight);sr.addWidget(self.status_time);status.addLayout(sr)
        self.expert_journey=Journey();status.addWidget(self.expert_journey);self.status_detail=self.label('','',True);status.addWidget(self.status_detail);whole.addWidget(self.expert_status)
        body=QHBoxLayout();body.setContentsMargins(0,0,0,0);body.setSpacing(0)
        navpanel=QWidget();nl=QVBoxLayout(navpanel);nl.setContentsMargins(8,8,8,8);nl.setSpacing(5);self.tool('plus','Import videos','匯入影片',self.add_videos,nl)
        self.nav=QListWidget();self.nav.setFrameShape(QFrame.NoFrame);self.nav.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded);self.nav_buttons=[]
        for index,(key,en,zh,name) in enumerate(CONTRACT['navigation']):
            item=QListWidgetItem();item.setSizeHint(QSize(76,64 if index!=6 else 77));self.nav.addItem(item)
            widget=QWidget();vl=QVBoxLayout(widget);vl.setContentsMargins(0,13 if index==6 else 0,0,0)
            b=QToolButton();b.setObjectName('navItem');b.setIcon(icon(name,self.accent));b.setIconSize(QSize(21,21));b.setText(self.t(en,zh).replace(' ','\n',1) if index>=6 else self.t(en,zh));b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon);b.setCheckable(True);b.setMinimumHeight(58);b.setAccessibleName(self.t(en,zh));b.clicked.connect(lambda checked=False,i=index:self.nav.setCurrentRow(i));vl.addWidget(b);self.nav.setItemWidget(item,widget);self.nav_buttons.append(b)
        self.nav.currentRowChanged.connect(self.navigate);nl.addWidget(self.nav,1);nl.addWidget(self.label('v'+self.version,'v'+self.version,True));navpanel.setFixedWidth(M['navigation']);self.navigation=navpanel;body.addWidget(navpanel)
        content=QWidget();main=QVBoxLayout(content);main.setContentsMargins(0,0,0,0);main.setSpacing(0)
        self.workspace_bar=QWidget();wb=QHBoxLayout(self.workspace_bar);wb.setContentsMargins(16,0,16,0);self.workspace_bar.setFixedHeight(M['workspaceBar']);self.basic_return=self.button('Back to preview','返回預覽',lambda:self.nav.setCurrentRow(0),wb);self.basic_return.setIcon(icon('chevron-left'));self.basic_return.hide();self.workspace_name=self.label('Dubbing studio','聲演剪輯室');wb.addWidget(self.workspace_name);wb.addWidget(self.label('│','│',True));self.workspace_file=self.label('Import a video to begin','匯入影片開始製作',True);wb.addWidget(self.workspace_file,1);main.addWidget(self.workspace_bar)
        self.failure_banner=QFrame();self.failure_banner.setObjectName('card');fl=QHBoxLayout(self.failure_banner);self.failure_text=self.label('','');fl.addWidget(self.failure_text,1);self.button('Details','詳細紀錄',self.open_failure,fl);self.button('Retry / repair','重試／修復',self.retry_failed,fl);self.failure_banner.hide();main.addWidget(self.failure_banner)
        self.pages=QStackedWidget();main.addWidget(self.pages,1)
        self.build_editor();self.build_roles();self.build_review();self.build_produce();self.build_queue();self.build_terminal();self.build_defaults();self.build_models();self.build_preferences();self.build_projects()
        self.footer=QWidget();footer=QHBoxLayout(self.footer);footer.setContentsMargins(12,0,12,0);self.footer.setFixedHeight(M['statusBar']);self.footer_state=self.label('✓ Ready','✓ 就緒');footer.addWidget(self.footer_state);self.dirty_label=self.label('','');footer.addWidget(self.dirty_label);footer.addStretch();self.footer_file=self.label('','',True);footer.addWidget(self.footer_file);footer.addWidget(self.label('v'+self.version,'v'+self.version,True));main.addWidget(self.footer);body.addWidget(content,1);whole.addLayout(body,1);self.shell.addWidget(page)
        for key,fn in [('Ctrl+Z',self.undo),('Ctrl+Shift+Z',self.redo),('Ctrl+S',self.save_draft),('Ctrl+O',self.add_videos)]:QShortcut(QKeySequence(key),self,activated=fn)
        self.nav.setCurrentRow(0)
        # Information slides over the workspace instead of squeezing its layout.
        outer=self.central.layout();outer.removeWidget(self.drawer);self.drawer.setParent(self.central);self.drawer.setObjectName('card');self.drawer.hide()
    def build_editor(self):
        page=QWidget();layout=QVBoxLayout(page);layout.setContentsMargins(0,0,0,0);layout.setSpacing(0)
        self.editor_split=QSplitter(Qt.Vertical);self.top_split=QSplitter(Qt.Horizontal);self.top_split.setChildrenCollapsible(False)
        self.browser=QWidget();bl=QVBoxLayout(self.browser);bl.setContentsMargins(0,0,0,0);bl.setSpacing(0);_,bh,self.browser_title=self.panel_header('Project library','專案庫',bl,'folder')
        filterrow=QHBoxLayout();self.queue_filter=QComboBox()
        for en,zh,value in [('All','全部','all'),('Waiting','待處理','waiting'),('Paused','已暫停','paused'),('Complete','已完成','complete'),('Needs attention','需要處理','attention')]:self.queue_filter.addItem(self.t(en,zh),value)
        self.queue_filter.currentIndexChanged.connect(self.filter_queue);filterrow.addWidget(self.queue_filter);self.tool('trash','Manage projects and exports','管理專案及成品',lambda:self.nav.setCurrentRow(9),filterrow);bl.addLayout(filterrow)
        self.queue_list=QListWidget();self.queue_list.setFrameShape(QFrame.NoFrame);self.queue_list.setMinimumWidth(185);self.queue_list.currentRowChanged.connect(self.select_queue);bl.addWidget(self.queue_list,1)
        self.browser_info=self.label('Video information','影片資訊',True);self.browser_info.setContentsMargins(12,12,12,12);bl.addWidget(self.browser_info);self.browser_cleanup=self.label('Removing a project keeps its source and exports.','移除會清理處理資料，保留原片同成品。',True);self.browser_cleanup.setContentsMargins(12,10,12,10);bl.addWidget(self.browser_cleanup)
        buttons=QHBoxLayout();self.tool('plus','Add videos','加入影片',self.add_videos,buttons);self.tool('trash','Remove selected','移除所選影片',self.remove_video,buttons);self.tool('folder','Open output folder','開啟成品資料夾',lambda:self.reveal(self.root/'exports'),buttons);bl.addLayout(buttons);self.top_split.addWidget(self.browser)
        self.center_stack=QStackedWidget();self.expert_center=QSplitter(Qt.Vertical);self.expert_center.setChildrenCollapsible(False)
        self.monitor=QWidget();ml=QVBoxLayout(self.monitor);ml.setContentsMargins(0,0,0,0);ml.setSpacing(0)
        self.monitor_header,mh,_=self.panel_header('Video preview','影片預覽',ml,'play');self.tool('captions','Preview subtitles','預覽字幕',self.caption_menu,mh);self.mute_button=self.tool('volume','Mute preview','靜音預覽',lambda:self.audio.setMuted(not self.audio.isMuted()),mh);self.tool('crop','Select subtitle area','框選字幕',self.select_ocr_region,mh)
        from studio_video import StudioVideo
        self.video=StudioVideo();self.video.setMinimumHeight(160);self.player.setVideoOutput(self.video.videoItem);ml.addWidget(self.video,1)
        from PySide6.QtGui import QPalette
        palette=self.video.palette();palette.setColor(QPalette.Window,Qt.black);self.video.setPalette(palette);self.video.setAutoFillBackground(True)
        playback=QHBoxLayout();playback.setContentsMargins(12,7,12,7);self.tool('play','Play or pause','播放／暫停',self.toggle_play,playback);self.clock=self.label('00:00:00.0','00:00:00.0');playback.addWidget(self.clock)
        self.scrubber=QSlider(Qt.Horizontal);self.scrubber.sliderMoved.connect(self.player.setPosition);playback.addWidget(self.scrubber,1);self.duration_label=self.label('00:00:00.0','00:00:00.0',True);playback.addWidget(self.duration_label);self.follow=QCheckBox(self.t('Follow processing','跟隨處理'));self.follow.toggled.connect(self.follow_changed);playback.addWidget(self.follow);self.tool('captions','Subtitle tracks','字幕音軌',self.caption_menu,playback);ml.addLayout(playback)
        self.caption=self.label('','');self.caption.hide();self.expert_center.addWidget(self.monitor)
        transcript=QWidget();tl=QVBoxLayout(transcript);tl.setContentsMargins(0,0,0,0);tl.setSpacing(0);self.cue_toolbar=QWidget();ct=QHBoxLayout(self.cue_toolbar);ct.setContentsMargins(12,6,12,6);ct.addWidget(self.label('Subtitles and script','字幕與台詞'));self.cue_count=self.label('0 / 0','0 / 0');ct.addWidget(self.cue_count);self.tool('chevron-left','Previous line','上一句',lambda:self.select_cue(self.cue_index-1),ct);self.tool('chevron-right','Next line','下一句',lambda:self.select_cue(self.cue_index+1),ct);ct.addStretch()
        self.loop=QCheckBox(self.t('Loop','循環'));ct.addWidget(self.loop);self.follow_captions=QCheckBox(self.t('Follow subtitles','跟隨播放字幕'));ct.addWidget(self.follow_captions)
        self.preview_language=QComboBox();self.preview_language.setMaximumWidth(180);self.preview_language.addItem(self.t('Hong Kong Cantonese','香港廣東話'),'yue');self.preview_language.addItem('English','en');ct.addWidget(self.preview_language);self.tool('stop','Stop audition','停止試聽',lambda:self.audition.stop(),ct);tl.addWidget(self.cue_toolbar)
        texts=QSplitter(Qt.Horizontal);originals=QWidget();ol=QVBoxLayout(originals);ol.setContentsMargins(12,8,12,8);ol.addWidget(self.label('Japanese recognition','日文辨識文字'));self.source_text=CommitText();self.source_text.setObjectName('transcript');ol.addWidget(self.source_text,1);ol.addWidget(self.label('Original subtitles · source timing','原裝字幕 · 原時間'));self.original_caption=self.label('No original subtitle at this position','本時段冇原裝字幕',True);ol.addWidget(self.original_caption);texts.addWidget(originals)
        translated=QWidget();xl=QVBoxLayout(translated);xl.setContentsMargins(12,8,12,8);xl.addWidget(self.label('Dubbed dialogue','配音台詞'));self.translated_text=CommitText();self.translated_text.setObjectName('transcript');xl.addWidget(self.translated_text,1);self.caption_override=QLineEdit();self.caption_override.setPlaceholderText(self.t('Display subtitle (blank follows dialogue)','顯示字幕（留空跟配音台詞）'));xl.addWidget(self.caption_override);texts.addWidget(translated);tl.addWidget(texts,1)
        self.source_text.committed.connect(self.commit_transcript);self.translated_text.committed.connect(self.commit_transcript);self.caption_override.editingFinished.connect(self.commit_transcript)
        self.cue_table=QTableWidget(0,6);self.cue_table.setHorizontalHeaderLabels(['Start','End','Japanese','Cantonese','English','Role']);self.cue_table.itemSelectionChanged.connect(self.cue_selected);self.cue_table.itemChanged.connect(self.edit_cue);self.cue_table.hide();tl.addWidget(self.cue_table);self.transcript_area=self.scroll(transcript);self.expert_center.addWidget(self.transcript_area);self.expert_center.setSizes([380,M['transcript']]);self.center_stack.addWidget(self.expert_center)
        basic=QWidget();bc=QVBoxLayout(basic);bc.setContentsMargins(22,0,22,22);bc.setSpacing(18);heading=QHBoxLayout();titles=QVBoxLayout();title=self.label('Preview and audition','預覽與試聽');title.setObjectName('heading');titles.addWidget(title);self.video_title=self.label('Import a video to begin','匯入影片開始製作',True);titles.addWidget(self.video_title);heading.addLayout(titles,1);self.button('Add videos','加入影片',self.add_videos,heading);bc.addLayout(heading)
        self.basic_monitor_slot=QVBoxLayout();bc.addLayout(self.basic_monitor_slot)
        self.basic_status=QFrame();self.basic_status.setObjectName('card');bs=QVBoxLayout(self.basic_status);sr=QHBoxLayout();self.basic_title=self.label('Ready when you are','準備好就開始');sr.addWidget(self.basic_title,1);self.basic_time=self.label('','',True);sr.addWidget(self.basic_time);bs.addLayout(sr);self.basic_detail=self.label('','',True);bs.addWidget(self.basic_detail);self.basic_journey=Journey(self.runner_path);bs.addWidget(self.basic_journey);bc.addWidget(self.basic_status)
        self.basic_audition_row=QFrame();self.basic_audition_row.setObjectName('card');ba=QVBoxLayout(self.basic_audition_row);ba.addWidget(self.label('Current line','本段試聽'));self.basic_script=self.label('Completed recordings appear here while processing.','完成嘅配音會即時出現，可以邊轉換邊試聽。');self.basic_script.setObjectName('caption');ba.addWidget(self.basic_script);buttons=QHBoxLayout();self.button('Japanese original','日文原聲',self.play_original,buttons);self.basic_audition=self.button('Audition dubbed take','試聽配音',self.play_take,buttons);self.basic_english=self.button('English','英文',lambda:self.play_language('en'),buttons);ba.addLayout(buttons);bc.addWidget(self.basic_audition_row)
        self.output_feedback=QWidget();of=QHBoxLayout(self.output_feedback);self.output_label=self.label('','');of.addWidget(self.output_label,1);self.button('Play output','播放成品',self.play_output,of);self.button('Show file','顯示檔案',self.reveal_output,of);bc.addWidget(self.output_feedback);bc.addStretch();self.basic_center=basic;self.basic_scroll=self.scroll(basic);self.center_stack.addWidget(self.basic_scroll);self.top_split.addWidget(self.center_stack)
        self.inspector=QWidget();self.inspector.setMinimumWidth(280);il=QVBoxLayout(self.inspector);il.setContentsMargins(0,0,0,0);il.setSpacing(0);_,_,self.inspector_title=self.panel_header('Dialogue workbench','對白工作台',il,'sliders')
        self.inspector_tabs=QTabWidget();production=QWidget();pl=QVBoxLayout(production);pl.setContentsMargins(18,14,18,14);self.settings_box=self.production_controls(pl);pl.addStretch();self.inspector_tabs.addTab(self.scroll(production),self.t('Production','製作'))
        self.retake_box=self.dialogue_inspector();self.inspector_tabs.addTab(self.scroll(self.retake_box),self.t('Dialogue','對白'));self.inspector_tabs.addTab(self.picture_inspector(),self.t('Picture','畫面'));self.inspector_tabs.addTab(self.sound_inspector(),self.t('Mix','混音'));il.addWidget(self.inspector_tabs,1)
        self.production_footer=QWidget();pf=QVBoxLayout(self.production_footer);pf.setContentsMargins(20,14,20,20);pf.addWidget(self.label('Automatic translation · repair · export','自動翻譯 · 修復 · 匯出',True));self.start_button=self.button('Start automatic production','開始自動製作',self.start_selected,pf,True);self.batch_button=self.button('Start all waiting videos','開始全部待處理',self.start_all,pf);il.addWidget(self.production_footer);self.top_split.addWidget(self.inspector);self.top_split.setSizes([M['browser'],700,M['inspector']]);self.editor_split.addWidget(self.top_split)
        self.timeline_panel=QWidget();tp=QVBoxLayout(self.timeline_panel);tp.setContentsMargins(0,0,0,0);tp.setSpacing(0);tools=QHBoxLayout();tools.setContentsMargins(12,6,12,6);tools.addWidget(self.label('Timeline','時間軸'));self.button('Split video','分割影片',self.split_clip,tools).setIcon(icon('scissors'));self.button('Clip settings','剪接設定',lambda:self.inspector_tabs.setCurrentIndex(2),tools);self.button('Add dialogue','新增對白',self.add_dialogue,tools);self.all_tracks=QCheckBox(self.t('All voice tracks','全部配音軌'));self.all_tracks.setChecked(True);tools.addWidget(self.all_tracks);tools.addStretch();self.tool('zoom-out','Zoom out','縮小',lambda:self.timeline_zoom.setValue(max(10,self.timeline_zoom.value()-30)),tools);self.timeline_zoom=QSlider(Qt.Horizontal);self.timeline_zoom.setRange(10,800);self.timeline_zoom.setValue(316);self.timeline_zoom.setFixedWidth(135);tools.addWidget(self.timeline_zoom);self.tool('zoom-in','Zoom in','放大',lambda:self.timeline_zoom.setValue(min(800,self.timeline_zoom.value()+30)),tools);self.zoom_label=self.label('31.6×','31.6×',True);tools.addWidget(self.zoom_label);tp.addLayout(tools)
        self.timeline=Timeline();self.timeline.cueSelected.connect(self.select_cue);self.timeline.seek.connect(self.seek);self.timeline.regionEdited.connect(self.timeline_edit);self.timeline_area=self.scroll(self.timeline);self.timeline_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);tp.addWidget(self.timeline_area,1);self.timeline_scroll=QScrollBar(Qt.Horizontal);self.timeline_scroll.valueChanged.connect(lambda n:self.scroll_timeline(n));tp.addWidget(self.timeline_scroll);self.timeline_zoom.valueChanged.connect(self.zoom_timeline);self.all_tracks.toggled.connect(lambda value:(setattr(self.timeline,'all_tracks',value),self.refresh_timeline()));self.editor_split.addWidget(self.timeline_panel);self.editor_split.setSizes([630,M['timeline']]);layout.addWidget(self.editor_split);self.pages.addWidget(page)
    def production_controls(self,parent):
        box=QWidget();v=QVBoxLayout(box);v.setContentsMargins(0,0,0,0);v.setSpacing(16)
        self.fast=QCheckBox();self.fast.hide();self.fast_mode_combo=QComboBox();self.fast_mode_combo.addItems([self.t('Standard mode','標準模式'),self.t('High speed','高速模式')]);self.segmented(self.fast_mode_combo,v);self.fast_mode_combo.currentIndexChanged.connect(lambda i:self.fast.setChecked(i==1));self.fast.toggled.connect(lambda b:self.fast_mode_combo.setCurrentIndex(int(b)))
        self.fast_warning=self.label('Skips quality checks. Exported speech may have defects.','跳過所有品質檢查；生成影片可能存在配音缺陷。',True);v.addWidget(self.fast_warning)
        v.addWidget(self.label('01   Voice engine','01   配音聲音'));self.engine=QComboBox()
        for key,title in ENGINES:self.engine.addItem(title,key)
        v.addWidget(self.engine);self.extra_tracks_hint=self.label('','',True);v.addWidget(self.extra_tracks_hint)
        self.extra_engines_box=QWidget();ex=QVBoxLayout(self.extra_engines_box);ex.setContentsMargins(0,0,0,0);ex.addWidget(self.label('Additional voice tracks','額外配音音軌',True));self.extra_engines={}
        for key,title in ENGINES:
            c=QCheckBox(title);self.extra_engines[key]=c;ex.addWidget(c);c.toggled.connect(self.settings_changed)
        v.addWidget(self.extra_engines_box)
        v.addWidget(self.label('Dubbing languages','配音語言'));self.dub_language=QComboBox()
        for en,zh,value in [('Hong Kong Cantonese','香港廣東話',['yue']),('English','英文',['en']),('Both','雙語',['yue','en'])]:self.dub_language.addItem(self.t(en,zh),value)
        self.dub_language_segments=self.segmented(self.dub_language,v);self.original=QCheckBox(self.t('Keep Japanese original audio track','保留日文原聲音軌'));v.addWidget(self.original)
        line=QFrame();line.setFrameShape(QFrame.HLine);v.addWidget(line);v.addWidget(self.label('02   Output subtitles','02   輸出字幕'));v.addWidget(self.label('Select multiple; switch during playback.','可多選，播放時隨時切換。',True));self.sub_checks={}
        for key,en,zh in [('yue','Cantonese subtitles','廣東話字幕'),('english','English subtitles','英文字幕'),('original','Original subtitles','原片字幕')]:
            c=QCheckBox(self.t(en,zh));self.sub_checks[key]=c;v.addWidget(c);c.toggled.connect(self.settings_changed)
        self.advanced=QToolButton();self.advanced.setToolButtonStyle(Qt.ToolButtonTextBesideIcon);self.advanced.setText(self.t('Opening / ending settings','片頭、片尾及更多設定'));self.advanced.setCheckable(True);self.advanced.setArrowType(Qt.RightArrow);v.addWidget(self.advanced)
        self.advanced_settings=QWidget();ad=QVBoxLayout(self.advanced_settings);ad.setContentsMargins(0,0,0,0)
        self.source=QComboBox()
        for en,zh,key in [('Automatic subtitles','自動選擇字幕','auto'),('External subtitle file…','外掛字幕檔案⋯','external'),('Japanese audio only','只用日文語音辨識','audio-only')]:self.source.addItem(self.t(en,zh),key)
        ad.addWidget(self.label('Translation source','翻譯來源'));ad.addWidget(self.source)
        self.op=QComboBox();self.op.addItem(self.t('Keep original Japanese','保留日文原聲'),False);self.op.addItem(self.t('Translate all dialogue','全部對白翻譯'),True);ad.addWidget(self.label('OP / ED treatment','OP／ED 處理'));ad.addWidget(self.op)
        self.range_box=QWidget();rl=QFormLayout(self.range_box);rl.setContentsMargins(0,0,0,0);self.start_offset=QDoubleSpinBox();self.start_offset.setRange(0,86400);self.start_offset.setSuffix(' s');rl.addRow(self.t('Start time','開始時間'),self.start_offset)
        self.range_limit=QComboBox()
        for en,zh,n in [('Full video','全片',0),('60 seconds','60 秒',60),('3 minutes','3 分鐘',180)]:self.range_limit.addItem(self.t(en,zh),n)
        rl.addRow(self.t('Range','處理範圍'),self.range_limit);ad.addWidget(self.range_box);self.advanced_settings.hide();self.advanced.toggled.connect(lambda b:(self.advanced_settings.setVisible(b),self.advanced.setArrowType(Qt.DownArrow if b else Qt.RightArrow)));v.addWidget(self.advanced_settings)
        for ctrl,signal in [(self.engine,'currentIndexChanged'),(self.dub_language,'currentIndexChanged'),(self.original,'toggled'),(self.source,'activated'),(self.fast,'toggled'),(self.op,'currentIndexChanged'),(self.start_offset,'valueChanged'),(self.range_limit,'currentIndexChanged')]:getattr(ctrl,signal).connect(self.settings_changed)
        self.sync_controls();parent.addWidget(box);return box
    def dialogue_inspector(self):
        widget=QWidget();v=QVBoxLayout(widget);v.setContentsMargins(16,12,16,12);v.setSpacing(12);self.line_title=self.label('Select a line','選擇對白');v.addWidget(self.line_title)
        self.take_language=QComboBox();self.take_language.addItem(self.t('Hong Kong Cantonese','香港廣東話'),'yue');self.take_language.addItem('English','en');self.segmented(self.take_language,v);self.take_language.currentIndexChanged.connect(self.language_audition_changed)
        self.preview_language.currentIndexChanged.connect(self.take_language.setCurrentIndex);self.take_language.currentIndexChanged.connect(self.preview_language.setCurrentIndex)
        self.dialogue_tools=QTabWidget();listen=QWidget();ll=QVBoxLayout(listen);ll.setContentsMargins(0,10,0,0);ll.addWidget(self.label('Recordings for this line','本段錄音'));self.take_rows={}
        for key,title in ENGINES:
            frame=QFrame();frame.setObjectName('card');row=QHBoxLayout(frame);lab=self.label(title,title);row.addWidget(lab,1);b=self.tool('play','Audition '+title,'試聽 '+title,lambda checked=False,k=key:self.play_engine(k),row);self.take_rows[key]=(frame,lab,b);ll.addWidget(frame)
        self.take_status=self.label('No recording selected','未選擇錄音',True);ll.addWidget(self.take_status);self.take_engine=QComboBox()
        for key,title in ENGINES:self.take_engine.addItem(title,key)
        self.take_engine.currentIndexChanged.connect(self.refresh_take);ll.addWidget(self.label('Adopt engine','採用引擎'));ll.addWidget(self.take_engine);self.audition_button=self.button('Audition take','試聽錄音',self.play_take,ll);self.adopt_button=self.button('Adopt recording','採用錄音',self.adopt_audition,ll,True);self.button('Compare previous recordings','比較先前錄音',lambda:self.nav.setCurrentRow(2),ll);ll.addStretch();self.dialogue_tools.addTab(listen,self.t('Listen','試聽'))
        record=QWidget();rv=QVBoxLayout(record);rv.setContentsMargins(0,12,0,0);rv.addWidget(self.label('Generate a new recording','重新生成配音'));rv.addWidget(self.label('Only the selected line changes. Previous recordings are kept.','只重錄所選對白；先前錄音會保留。',True));self.record_engine=QComboBox()
        for key,title in ENGINES:self.record_engine.addItem(title,key)
        self.record_engine.currentIndexChanged.connect(lambda i:self.take_engine.setCurrentIndex(i));self.take_engine.currentIndexChanged.connect(self.record_engine.setCurrentIndex);rv.addWidget(self.record_engine);self.button('Generate new take','生成新錄音',self.retake,rv,True)
        self.inference_form=QFormLayout();self.inference_fields={}
        for key,en,zh,value,lo,hi in [('gptTemperature','Temperature','溫度',1,.6,1.2),('gptTopP','Top P','Top P',1,.6,1),('gptTopK','Top K','Top K',15,5,30),('gptRepetitionPenalty','Repetition penalty','重複懲罰',1.35,1,1.6),('cosyTemperature','Cosy temperature','Cosy 溫度',.7,.3,1)]:
            spin=QDoubleSpinBox();spin.setRange(lo,hi);spin.setValue(value);spin.setSingleStep(.05);spin.valueChanged.connect(lambda n,k=key:self.set_inference(k,n));self.inference_fields[key]=spin;self.inference_form.addRow(self.t(en,zh),spin)
        rv.addLayout(self.inference_form);self.ab_engine=QComboBox()
        for key,title in ENGINES:self.ab_engine.addItem(title,key)
        rv.addWidget(self.label('Compare A / B with another engine','使用另一引擎比較 A／B'));rv.addWidget(self.ab_engine);self.button('Generate A + B auditions','生成 A＋B 試音',self.compare_ab,rv);rv.addStretch();self.dialogue_tools.addTab(record,self.t('Retake','重錄'))
        adjust=QWidget();av=QFormLayout(adjust);av.setContentsMargins(0,12,0,0);self.cue_role=QComboBox();self.cue_role.activated.connect(lambda i:self.change_segment('speakerId',self.cue_role.currentData()));av.addRow(self.t('Role','角色'),self.cue_role)
        self.cue_enabled=QCheckBox(self.t('Enable this line','啟用對白'));self.cue_enabled.toggled.connect(lambda value:self.change_segment('enabled',value));av.addRow(self.cue_enabled);self.cue_preserve=QCheckBox(self.t('Keep Japanese here','此段保留日文原聲'));self.cue_preserve.toggled.connect(lambda value:self.change_segment('preserveOriginalSpeech',value));av.addRow(self.cue_preserve)
        self.segment_fields={}
        for key,en,zh,hi in [('start','Voice start','配音開始',86400),('end','Voice end','配音結束',86400),('captionStart','Caption start','字幕開始',86400),('captionEnd','Caption end','字幕結束',86400),('rate','Speech rate','語速',2),('trimStart','Audio trim start','聲音開頭裁切',3600),('trimEnd','Audio trim end','聲音結尾裁切',3600),('take','Random seed','隨機種子',999999)]:
            n=QDoubleSpinBox();n.setDecimals(3 if key!='take' else 0);n.setRange(.5 if key=='rate' else 0,hi);n.setSingleStep(.05 if key=='rate' else .1);n.editingFinished.connect(lambda k=key,w=n:self.change_segment(k,w.value()));av.addRow(self.t(en,zh),n);self.segment_fields[key]=n
        self.cue_rate=self.segment_fields['rate'];self.button('Apply role to selected lines','套用角色到所選對白',self.apply_selected_role,av);self.button('Replace this role throughout episode','取代全部同角色對白',self.replace_all_role,av);self.dialogue_tools.addTab(self.scroll(adjust),self.t('Adjust','調整'));v.addWidget(self.dialogue_tools);return widget
    def picture_inspector(self):
        widget=QWidget();v=QVBoxLayout(widget);v.setContentsMargins(14,12,14,12);v.addWidget(self.label('Clip settings','剪接設定'));v.addWidget(self.label('Split and trim without changing the original video.','分割及裁切，原片保持不變。',True));self.cut_placeholder=QVBoxLayout();v.addLayout(self.cut_placeholder)
        self.button('Split at playhead','喺播放位置分割',self.split_clip,v);self.button('Add clip','加入片段',lambda:self.add_clip(),v);v.addStretch();return widget
    def sound_inspector(self):
        widget=QWidget();v=QVBoxLayout(widget);v.setContentsMargins(16,16,16,16);v.addWidget(self.label('Volume and mix','音量與混音'));v.addWidget(self.label('Preview volume','試聽音量'));self.preview_volume=QSlider(Qt.Horizontal);self.preview_volume.setRange(0,100);self.preview_volume.setValue(100);self.preview_volume.valueChanged.connect(lambda n:(self.audio.setVolume(n/100),self.audition_audio.setVolume(n/100)));v.addWidget(self.preview_volume);v.addWidget(self.label('Preview only; exported audio is unchanged.','只影響試聽，唔會改動成品。',True));v.addWidget(self.label('Exported background audio','成品背景音'));self.background_volume=QSlider(Qt.Horizontal);self.background_volume.setRange(0,150);self.background_volume.setValue(100);self.background_volume.valueChanged.connect(lambda n:self.set_setting('backgroundGain',n/100,True));v.addWidget(self.background_volume);self.ducking=QCheckBox(self.t('Lower background while speaking','有人講嘢時降低背景音'));self.ducking.toggled.connect(lambda value:self.set_setting('backgroundDucking',value,True));v.addWidget(self.ducking);v.addStretch();return widget
    def update_mode(self):
        basic=self.store.mode=='basic';self.mode_button.setText(self.t('Current: Basic mode','目前：基本模式') if basic else self.t('Current: Expert mode','目前：專家模式'));self.mode_button.setIcon(icon('sparkles' if basic else 'sliders',self.accent))
        for index,a in enumerate(self.mode_button.menu().actions()):a.setChecked(index==(0 if basic else 1))
        self.navigation.setVisible(not basic and self.panel_actions[0].isChecked());self.expert_tools.setVisible(not basic);self.expert_status.setVisible(not basic and self.running is not None);self.workspace_bar.setVisible(not basic);self.footer.setVisible(not basic);self.timeline_panel.setVisible(not basic);self.basic_status.setVisible(basic);self.production_footer.setVisible(basic);self.export_button.setVisible(not basic);self.pause_button.setVisible(not basic and (self.running is not None or bool(self.store.row() and self.store.row().get('status')=='paused')))
        self.range_box.setVisible(not basic);self.extra_engines_box.setVisible(not basic);self.extra_tracks_hint.setVisible(not basic);self.advanced.setVisible(basic);self.advanced_settings.setVisible(not basic or self.advanced.isChecked());self.source.model().item(2).setEnabled(not basic)
        for i in range(1,4):self.inspector_tabs.setTabVisible(i,not basic)
        self.inspector_tabs.tabBar().setVisible(not basic);self.inspector_title.setText(self.t('Production settings','製作設定') if basic else self.t('Dialogue workbench','對白工作台'));self.browser_title.setText(self.t('Video list','影片清單') if basic else self.t('Project library','專案庫'))
        self.browser.setVisible(basic or self.panel_actions[1].isChecked());self.inspector.setVisible(basic or self.panel_actions[2].isChecked())
        if basic:
            self.monitor.setMinimumHeight(340);self.basic_monitor_slot.addWidget(self.monitor);self.center_stack.setCurrentIndex(1);self.inspector_tabs.setCurrentIndex(0);self.nav.setCurrentRow(0);self.pages.setCurrentIndex(0);self.top_split.setSizes([M['basicBrowser'],max(400,self.width()-M['basicBrowser']-M['basicInspector']),M['basicInspector']])
        else:
            self.monitor.setMinimumHeight(246);self.expert_center.insertWidget(0,self.monitor);self.center_stack.setCurrentIndex(0);self.inspector_tabs.setCurrentIndex(1 if self.draft else 0);self.top_split.setSizes([M['browser'],max(400,self.width()-M['navigation']-M['browser']-M['inspector']),M['inspector']]);self.expert_center.setSizes([380,M['transcript']])
        self.monitor_header.setVisible(not basic);self.browser_cleanup.setVisible(basic);self.restore_queue();self.filter_queue();self.refresh_status();self.update_defaults()
        if hasattr(self,'companion'):self.apply_preferences()
    def toggle_panel(self,index,checked):
        [self.navigation,self.browser,self.inspector][index].setVisible(checked);self.panel_actions[index].setChecked(checked);self.store.ui[['navigation','browser','inspector'][index]]=checked;self.store.save()
    def reset_layout(self):
        for i in range(3):self.toggle_panel(i,True)
        self.top_split.setSizes([M['browser'],700,M['inspector']]);self.editor_split.setSizes([630,M['timeline']]);self.expert_center.setSizes([380,M['transcript']])
    def focus_preview(self):
        self.preview_focused=not getattr(self,'preview_focused',False)
        for w in [self.browser,self.inspector,self.timeline_panel]:w.setVisible(not self.preview_focused)
        self.expert_center.widget(1).setVisible(not self.preview_focused)
    def navigate(self,index):
        if index<0:return
        self.pages.setCurrentIndex(index)
        if hasattr(self,'basic_return'):
            basic=self.store.mode=='basic';self.basic_return.setVisible(basic and index!=0);self.workspace_bar.setVisible(not basic or index!=0);self.workspace_bar.setFixedHeight(44 if basic and index!=0 else M['workspaceBar'])
        if hasattr(self,'nav_buttons'):
            for i,b in enumerate(self.nav_buttons):b.setChecked(i==index)
        if hasattr(self,'workspace_name'):self.workspace_name.setText(self.t(CONTRACT['navigation'][index][1],CONTRACT['navigation'][index][2]))
        if index==9:self.refresh_projects()
        if index==7:self.show_plan()
        if index==6:self.update_defaults()
    def filter_queue(self,*unused):
        if not hasattr(self,'queue_filter'):return
        key=self.queue_filter.currentData()
        for i,row in enumerate(self.store.queue):
            if self.queue_list.item(i):self.queue_list.item(i).setHidden(key!='all' and row['status']!=key)
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'drawer'):
            width=min(780,max(360,round(self.central.width()*.62)));self.drawer.setGeometry(self.central.width()-width,0,width,self.central.height());self.drawer.raise_()
        if hasattr(self,'timeline'):self.refresh_timeline()
