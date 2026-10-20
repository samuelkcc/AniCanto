"""PC desktop using the Mac studio's navigation, docks, palette and caption layout."""
import json
from pathlib import Path
import time

from PySide6.QtCore import Qt, QUrl, QTimer, QRectF, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap, QFont
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSplitter, QTabWidget, QPlainTextEdit, QLineEdit, QComboBox, QSlider, QFormLayout,
    QTableWidget, QTableWidgetItem, QDialog, QListWidget, QListWidgetItem,
    QProgressBar, QFileDialog, QScrollArea, QFrame, QCheckBox, QStackedWidget, QMenu)
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from app import Window, HERE

WORDS = {
 'Studio': '剪輯工作區', 'Voice library': '常用聲線', 'Model centre': '模型中心', 'Preferences': '偏好設定',
 'Import video': '匯入影片', 'Import subtitles': '加入字幕', 'Production defaults': '製作預設',
 'Save': '儲存', 'Character album': '角色相簿', 'Workspace': '工作區', 'Generate edited version': '生成修改版本',
 'Project browser': '專案庫', 'Video information': '影片資訊', 'Animated companion': '動畫助手',
 'Ready when you are.': '準備好就開始。', 'Inspector': '檢查器', 'Convert': '轉換', 'Dialogue': '對白',
 'Roles': '角色', 'Exports': '成品', 'Production settings': '製作設定', 'Voice engine': '配音引擎',
 'Target language': '配音語言', 'Processing range': '處理範圍', 'Start': '開始時間', 'Length': '長度',
 'Output movie': '輸出影片', 'Source': '原片', 'Play output': '播放成品', 'Subtitle list': '對白清單',
 'Subtitles and script': '字幕與台詞', 'Japanese transcription text': '日語原文',
 'Original Chinese subtitles': '原裝中文字幕', 'No separate caption imported': '未匯入獨立原裝中文字幕',
 'Cantonese dubbing script': '廣東話配音台詞', 'English dubbing script': '英文配音台詞',
 'Previous': '上一句', 'Next': '下一句', 'Loop': '循環', 'Follow playback subtitles': '跟隨播放字幕',
 'Original': '原聲', 'Timeline': '時間軸', 'Video': '影片', 'Japanese speech': '日語對白',
 'Music / effects': '背景音樂／音效', 'Subtitles': '字幕', 'Dub timing': '配音時段',
 'Waiting to generate': '等待生成', 'No separated background': '未提供分離背景',
 'Ready': '就緒', 'Windows desktop test': 'Windows 桌面測試版', 'Translate draft': '翻譯草稿',
 'Open project': '開啟專案', 'Cancel': '取消並保留錄音', 'Preview recording not available': '呢句暫時未有錄音',
 'Open reports': '開啟報告', 'Choose reference': '選擇角色參考', 'Reference recording': '角色參考錄音',
 'Model setup': '部署模型', 'Interface language': '介面語言', 'Appearance': '外觀',
 'Light': '淺色', 'Dark': '深色', 'Saved projects': '已儲存專案', 'Role ID': '角色編號',
 'Double-click a subtitle to edit it.': '按字幕可定位，按「對白清單」可編輯所有句子。',
 'Import a movie to preview.': '匯入影片開始預覽。',
}


def timecode(seconds):
    seconds=max(0, float(seconds))
    return f'{int(seconds)//3600:02}:{int(seconds)//60%60:02}:{seconds%60:04.1f}'


def studio_theme(app, dark=False):
    base, panel, field, line, text, muted, select = (('#141521','#202133','#181923','#424058','#eeeaf8','#b4aec9','#41335f') if dark else
          ('#f3f0fa','#f7f3ff','#ffffff','#dcd4ed','#24212e','#777180','#e0d5f5'))
    app.setStyle('Fusion')
    app.setFont(QFont('',11))
    app.setStyleSheet(f'''
       QWidget {{ background:{panel}; color:{text}; }} QMainWindow {{ background:{base}; }}
       QVideoWidget {{ background:black; }}
       QLabel#emptyMonitor {{ background:black; color:#bcb6ce; }}
       QLabel#panelHeader {{ background:{select}; font-weight:600; padding:9px 12px; border-bottom:1px solid {line}; }}
       QLabel#muted {{ color:{muted}; }} QLabel#brand {{ font-size:20px; font-weight:700; }}
       QPushButton {{ background:{select}; border:1px solid {line}; border-radius:5px; padding:8px 10px; font-size:14px; }}
       QPushButton:checked {{ background:#7050c8; color:white; }} QPushButton:hover {{ border-color:#9373d7; }}
       QPushButton:disabled {{ color:{muted}; }} QPushButton#primary {{ background:#7050c8; color:white; font-weight:600; }}
       QLineEdit,QPlainTextEdit,QTableWidget,QComboBox,QSpinBox,QDoubleSpinBox {{ background:{field}; border:1px solid {line}; border-radius:4px; padding:5px; selection-background-color:#b9a0e8; }}
       QTableWidget {{ gridline-color:{line}; }} QHeaderView::section {{ background:{select}; padding:8px; border:1px solid {line}; }}
       QListWidget {{ border:0; background:{panel}; }} QListWidget::item {{ padding:12px; }} QListWidget::item:selected {{ background:{select}; color:{text}; }}
       QSplitter::handle {{ background:{line}; }} QSplitter::handle:horizontal {{ width:5px; }} QSplitter::handle:vertical {{ height:5px; }}
       QTabBar::tab {{ background:{select}; padding:7px 12px; }} QTabBar::tab:selected {{ background:#bba4e8; }}
       QSlider::groove:horizontal {{ height:5px; background:{line}; }} QSlider::handle:horizontal {{ width:14px; margin:-5px 0; background:white; border:1px solid {line}; border-radius:7px; }}
       QProgressBar {{ border:0; background:{line}; max-height:7px; }} QProgressBar::chunk {{ background:#7956cc; }}
    ''')


class Timeline(QWidget):
    selected = Signal(int)
    seek = Signal(float)
    def __init__(self, owner):
        super().__init__()
        self.owner=owner
        self.setMinimumHeight(168)
        self.setMouseTracking(True)
    def span(self):
        return max(30., self.owner.player.duration()/1000, max((r['end'] for r in self.owner.live_rows()),default=0))
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        dark=self.owner.dark
        p.fillRect(self.rect(),QColor('#202133' if dark else '#f7f3ff'))
        rows=self.owner.live_rows();left=160;width=max(1,self.width()-left-12);span=self.span()
        p.setPen(QColor('#c3bcd3' if dark else '#5c536a'));p.setFont(QFont('',9))
        step=max(5, int(span/8/5)*5)
        for s in range(0,int(span)+1,step):
            x=left+s/span*width;p.drawLine(int(x),0,int(x),self.height());p.drawText(int(x)+3,16,timecode(s))
        tracks=['Video','Japanese speech','Music / effects','Subtitles','Dub timing',{'cosy':'CosyVoice 3','gpt':'GPT-SoVITS','qwen':'Qwen3-TTS'}.get(self.owner.engine.currentData(),'Voice') if hasattr(self.owner,'engine') else 'GPT / CosyVoice']
        colors=['#8cb9f8','#7ad9df','#bdb7c7','#b39cdf','#e5ac50','#ba9bd3']
        for i,title in enumerate(tracks):
            y=25+i*24;p.setPen(QColor('#d5cfe2' if dark else '#473b57'));p.drawText(10,y+15,self.owner.tr(title))
            p.setPen(QColor('#494157' if dark else '#ded6e9'));p.drawLine(0,y+22,self.width(),y+22)
            if i<2 and self.owner.movie.text():
                p.fillRect(QRectF(left,y,width,19),QColor(colors[i]))
            elif i==2:
                p.drawText(left+5,y+15,self.owner.tr('Music / effects' if self.owner.background.text() else 'No separated background'))
            elif i>=3:
                if i==5 and self.owner.find_take(self.owner.engine.currentData()) is None:
                    p.setPen(QColor('#8c819d'));p.drawText(left+5,y+15,self.owner.tr('Waiting to generate'));continue
                for n,row in enumerate(rows):
                    x=left+row['start']/span*width;w=max(3,(row['end']-row['start'])/span*width)
                    rect=QRectF(x,y,w,20);p.fillRect(rect,QColor(colors[i]))
                    if n==self.owner.selected_cue:p.setPen(QPen(QColor('#f49f28'),2));p.drawRect(rect)
                    if w>34:
                        p.setPen(QColor('#322440'));p.drawText(rect.adjusted(3,0,-2,0),Qt.AlignVCenter,row.get('role','A')+' '+row.get('target',''))
        if self.owner.player.position():
            x=left+self.owner.player.position()/1000/span*width;p.setPen(QPen(QColor('#e06555'),2));p.drawLine(int(x),0,int(x),self.height())
    def mousePressEvent(self,event):
        if event.position().x()<160:return
        sec=max(0,(event.position().x()-160)/max(1,self.width()-172)*self.span())
        rows=self.owner.live_rows();hits=[i for i,r in enumerate(rows) if r['start']<=sec<r['end']]
        if hits:self.selected.emit(hits[0])
        self.seek.emit(sec)


class StudioWindow(Window):
    def tr(self,text):
        return WORDS.get(text,text) if self.ui_language=='zh-HK' else text
    def label(self,text,header=False):
        label=QLabel(self.tr(text));label.setWordWrap(True)
        if header:label.setObjectName('panelHeader')
        return label
    def action(self,text,callback,layout,job=False,primary=False):
        button=self.button(self.tr(text),callback,layout,job)
        if primary:button.setObjectName('primary')
        return button
    def workspace(self):
        prefs=self.root/'studio-preferences.json'
        preference=json.loads(prefs.read_text()) if prefs.is_file() else {}
        self.ui_language=preference.get('language','zh-HK');self.dark=preference.get('dark',False)
        self.selected_cue=0;self.updating_caption=False;self.project_files=[]
        self.resize(1680,1050);self.setMinimumSize(1280,820)
        root=QWidget();whole=QVBoxLayout(root);whole.setContentsMargins(0,0,0,0);whole.setSpacing(0)
        self.takeCentralWidget()  # Keep the existing stacked pages alive.
        self.setCentralWidget(root)
        nav=QHBoxLayout();nav.setContentsMargins(16,8,16,8)
        brand=self.label('◈  AniCanto');brand.setObjectName('brand');nav.addWidget(brand)
        self.nav_buttons=[]
        for name,index in [('Studio',0),('Voice library',2),('Model centre',1),('Preferences',3)]:
            button=self.action(name,lambda checked=False,i=index:self.change_page(i),nav);button.setCheckable(True);self.nav_buttons.append((button,index))
        nav.addStretch();self.action('⌘',self.show_terminal,nav).setToolTip('Terminal / 終端機')
        whole.addLayout(nav)
        self.tabs.tabBar().hide();whole.addWidget(self.tabs,1)
        page=QWidget();layout=QVBoxLayout(page);layout.setContentsMargins(0,0,0,0);layout.setSpacing(0);self.tabs.addTab(page,self.tr('Studio'))
        tools=QHBoxLayout();tools.setContentsMargins(10,6,10,6)
        self.action('Import video',self.import_movie,tools,True)
        subtitle_button=self.action('Import subtitles',lambda:None,tools,True)
        subtitle_menu=QMenu(subtitle_button);subtitle_menu.addAction('SRT…',self.import_srt);subtitle_menu.addAction('Extract embedded SRT / 擷取內置字幕',self.extract_srt);subtitle_button.setMenu(subtitle_menu)
        self.action('Production defaults',lambda:self.inspector.setCurrentIndex(0),tools)
        self.action('Save',self.save_project,tools)
        self.action('Character album',lambda:self.change_page(2),tools)
        tools.addStretch();self.action('Translate draft',lambda:self.start_job('translate'),tools,True)
        self.action('Generate edited version',lambda:self.start_job('render'),tools,True,True)
        layout.addLayout(tools)
        self.progress=QProgressBar();self.progress.setTextVisible(False);self.progress.setRange(0,100);self.progress.setValue(0);layout.addWidget(self.progress)
        self.movie=QLineEdit();self.output=QLineEdit();self.movie.hide()
        main=QSplitter(Qt.Vertical);main.setChildrenCollapsible(False)
        docks=QSplitter(Qt.Horizontal);docks.setChildrenCollapsible(False)
        browser=QWidget();bl=QVBoxLayout(browser);bl.setContentsMargins(0,0,0,0);bl.addWidget(self.label('Project browser',True))
        self.projects=QListWidget();self.projects.itemClicked.connect(self.select_project);bl.addWidget(self.projects,1)
        self.action('Open project',self.open_project,bl,True)
        bl.addWidget(self.label('Video information',True));self.video_info=self.label('—');bl.addWidget(self.video_info)
        companion=QWidget();cl=QVBoxLayout(companion);cl.setContentsMargins(0,0,0,0);cl.addWidget(self.label('Animated companion',True))
        mascot=QLabel();mascot.setAlignment(Qt.AlignCenter);asset=HERE/'artwork/companion-studio.png'
        if not asset.is_file():asset=HERE.parent/'Resources/companion-studio.png'
        if asset.is_file():
            sheet=QPixmap(str(asset));pose=sheet.copy(0,0,sheet.width()//4,sheet.height()//2)
            mascot.setPixmap(pose.scaled(190,155,Qt.KeepAspectRatio,Qt.SmoothTransformation))
        else:mascot.setText('◈')
        cl.addWidget(mascot);cl.addWidget(self.label('Ready when you are.'));bl.addWidget(companion)
        browser.setMinimumWidth(200);docks.addWidget(browser)
        center=QSplitter(Qt.Vertical);center.setChildrenCollapsible(False)
        monitor=QWidget();ml=QVBoxLayout(monitor);ml.setContentsMargins(0,0,0,0);ml.setSpacing(0)
        title=QHBoxLayout();self.movie_title=self.label('AniCanto');title.addWidget(self.movie_title);title.addStretch();self.action('Source',self.play_source,title);self.action('Play output',self.play_output,title);ml.addLayout(title)
        self.video=QVideoWidget();self.video.setStyleSheet('background:black');self.video.setMinimumHeight(150)
        from PySide6.QtGui import QPalette
        palette=self.video.palette();palette.setColor(QPalette.Window,Qt.black);self.video.setPalette(palette);self.video.setAutoFillBackground(True)
        self.monitor_stack=QStackedWidget();placeholder=self.label('Import a movie to preview.');placeholder.setObjectName('emptyMonitor');placeholder.setAlignment(Qt.AlignCenter);self.monitor_stack.addWidget(placeholder);self.monitor_stack.addWidget(self.video);ml.addWidget(self.monitor_stack,1)
        self.player=QMediaPlayer(self);self.audio=QAudioOutput(self);self.player.setAudioOutput(self.audio);self.player.setVideoOutput(self.video)
        self.player.mediaStatusChanged.connect(lambda status:self.monitor_stack.setCurrentIndex(0 if status in (QMediaPlayer.NoMedia,QMediaPlayer.InvalidMedia) else 1))
        self.audition=QMediaPlayer(self);self.audition_audio=QAudioOutput(self);self.audition.setAudioOutput(self.audition_audio)
        controls=QHBoxLayout();self.action('▶ / ❚❚',self.toggle_play,controls);self.clock=self.label('00:00:00.0');controls.addWidget(self.clock)
        self.scrubber=QSlider(Qt.Horizontal);controls.addWidget(self.scrubber,1);self.end_clock=self.label('00:00:00.0');controls.addWidget(self.end_clock)
        self.scrubber.sliderMoved.connect(self.player.setPosition);self.player.durationChanged.connect(self.duration_changed);self.player.positionChanged.connect(self.position_changed);ml.addLayout(controls)
        center.addWidget(monitor)
        captions=QWidget();cv=QVBoxLayout(captions);cv.setContentsMargins(10,0,10,10)
        cap_head=QHBoxLayout();cap_head.addWidget(self.label('Subtitles and script'));self.cue_number=self.label('0 / 0');cap_head.addWidget(self.cue_number)
        self.action('‹',lambda:self.select_cue(self.selected_cue-1),cap_head);self.action('›',lambda:self.select_cue(self.selected_cue+1),cap_head);cap_head.addStretch()
        self.loop=QCheckBox(self.tr('Loop'));self.follow=QCheckBox(self.tr('Follow playback subtitles'));self.follow.setChecked(True);cap_head.addWidget(self.loop);cap_head.addWidget(self.follow)
        self.action('Subtitle list',self.show_dialogue_list,cap_head);cv.addLayout(cap_head)
        columns=QHBoxLayout();left=QVBoxLayout();left.addWidget(self.label('Japanese transcription text'))
        self.source_caption=QPlainTextEdit();self.source_caption.setReadOnly(True);self.source_caption.setFont(QFont('',17));left.addWidget(self.source_caption,1)
        left.addWidget(self.label('Original Chinese subtitles'));left.addWidget(self.label('No separate caption imported'));columns.addLayout(left,1)
        right=QVBoxLayout();right.addWidget(self.label('Cantonese dubbing script'))
        auditions=QHBoxLayout();self.action('Original',self.audition_source,auditions)
        self.gpt_audition=self.action('◖ GPT',lambda:self.audition_take('gpt'),auditions)
        self.cosy_audition=self.action('◖ CosyVoice',lambda:self.audition_take('cosy'),auditions);right.addLayout(auditions)
        body=QHBoxLayout();self.role_badge=self.label('A');self.role_badge.setAlignment(Qt.AlignCenter);self.role_badge.setFixedWidth(80);self.role_badge.setFont(QFont('',20));body.addWidget(self.role_badge)
        self.target_caption=QPlainTextEdit();self.target_caption.setFont(QFont('',17));self.target_caption.textChanged.connect(self.edit_target);body.addWidget(self.target_caption,1);right.addLayout(body,1);columns.addLayout(right,1);cv.addLayout(columns,1)
        captions.setMinimumHeight(250);center.addWidget(captions);center.setSizes([320,330]);docks.addWidget(center)
        self.inspector=QTabWidget();self.inspector.setMinimumWidth(315);self.inspector.setMaximumWidth(500);docks.addWidget(self.inspector);docks.setSizes([225,950,370]);main.addWidget(docks)
        bottom=QWidget();tl=QVBoxLayout(bottom);tl.setContentsMargins(0,0,0,0);tl.setSpacing(0);bar=QHBoxLayout();bar.setContentsMargins(10,5,10,5);bar.addWidget(self.label('Timeline'));bar.addWidget(self.label('Double-click a subtitle to edit it.'));bar.addStretch();self.cancel=self.action('Cancel',self.stop_job,bar);self.cancel.setEnabled(False);tl.addLayout(bar)
        self.timeline=Timeline(self);self.timeline.selected.connect(self.select_cue);self.timeline.seek.connect(self.seek_seconds);tl.addWidget(self.timeline,1);main.addWidget(bottom);main.setSizes([655,195]);layout.addWidget(main,1)
        status=QHBoxLayout();status.setContentsMargins(10,4,10,4);self.status_text=self.label('Ready');status.addWidget(self.status_text);status.addStretch();status.addWidget(self.label('Windows desktop test'));layout.addLayout(status)
        self.dialogue_dialog=QDialog(self);self.dialogue_dialog.setWindowTitle(self.tr('Subtitle list'));self.dialogue_dialog.resize(1120,650);dl=QVBoxLayout(self.dialogue_dialog)
        self.table=QTableWidget(0,5);self.table.setHorizontalHeaderLabels(['Start (s)','End (s)',self.tr('Japanese transcription text'),self.tr('Cantonese dubbing script'),self.tr('Role ID')]);self.table.setColumnWidth(2,330);self.table.setColumnWidth(3,360);dl.addWidget(self.table);self.table.itemDoubleClicked.connect(lambda item:self.select_cue(item.row()));self.table.itemChanged.connect(self.table_changed)
        self.terminal=QDialog(self);self.terminal.setWindowTitle('AniCanto · Terminal');self.terminal.resize(1000,550);ll=QVBoxLayout(self.terminal);self.log=QPlainTextEdit();self.log.setReadOnly(True);self.log.setMaximumBlockCount(1500);ll.addWidget(self.log)
        self.movie.textChanged.connect(self.movie_changed)
        self.change_page(0)

    def settings(self):
        super().settings()
        # Keep the installed runtime controls on the Model centre page, using
        # the same working widgets rather than a second independent settings state.
        self.tabs.setTabText(1,self.tr('Model centre'))
        voices=QWidget();vl=QVBoxLayout(voices);vl.addWidget(self.label('Voice library',True));vl.addWidget(self.label('Reference recording'));vl.addWidget(self.roles,1)
        row=QHBoxLayout();self.action('＋',lambda:self.roles.insertRow(self.roles.rowCount()),row);self.action('Choose reference',self.choose_reference,row);vl.addLayout(row);self.tabs.addTab(voices,self.tr('Voice library'))
        preferences=QWidget();pl=QVBoxLayout(preferences);pl.addWidget(self.label('Preferences',True));form=QFormLayout()
        language=QComboBox();language.addItem('香港繁體中文','zh-HK');language.addItem('English','en');language.setCurrentIndex(max(0,language.findData(self.ui_language)))
        appearance=QComboBox();appearance.addItem(self.tr('Light'),False);appearance.addItem(self.tr('Dark'),True);appearance.setCurrentIndex(int(self.dark))
        form.addRow(self.tr('Interface language'),language);form.addRow(self.tr('Appearance'),appearance);pl.addLayout(form)
        pl.addWidget(self.label('Windows desktop test'));pl.addWidget(self.capabilities);pl.addStretch();self.tabs.addTab(preferences,self.tr('Preferences'))
        def save_preferences():
            self.dark=appearance.currentData();studio_theme(self.application(),self.dark);self.timeline.update()
            (self.root/'studio-preferences.json').write_text(json.dumps(dict(language=language.currentData(),dark=self.dark)),encoding='utf-8')
            if language.currentData()!=self.ui_language:self.status_text.setText('Restart to change language / 重開套用語言')
        language.currentIndexChanged.connect(save_preferences);appearance.currentIndexChanged.connect(save_preferences)
        convert=QWidget();form=QFormLayout(convert);form.addRow(self.label('Production settings'))
        for title,original in [('Voice engine',self.engine),('Target language',self.language)]:
            copy=QComboBox()
            for i in range(original.count()):copy.addItem(original.itemText(i),original.itemData(i))
            copy.setCurrentIndex(original.currentIndex());copy.currentIndexChanged.connect(original.setCurrentIndex);original.currentIndexChanged.connect(copy.setCurrentIndex);form.addRow(self.tr(title),copy)
        form.addRow(self.label('Processing range'));form.addRow(self.tr('Start'),self.start);form.addRow(self.tr('Length'),self.length)
        output=QHBoxLayout();output.addWidget(self.output);self.action('…',self.choose_output,output);form.addRow(self.tr('Output movie'),output)
        form.addRow(self.label('Music / effects'));form.addRow(self.background)
        go=QHBoxLayout();self.action('Model setup',lambda:self.change_page(1),go);form.addRow(go)
        self.inspector.addTab(convert,self.tr('Convert'))
        dialogue=QWidget();df=QFormLayout(dialogue);self.role_edit=QLineEdit('A');self.role_edit.textEdited.connect(self.edit_role);df.addRow(self.tr('Role ID'),self.role_edit)
        self.action('Subtitle list',self.show_dialogue_list,df);self.action('Translate draft',lambda:self.start_job('translate'),df,True);self.inspector.addTab(dialogue,self.tr('Dialogue'))
        roles=QWidget();rl=QVBoxLayout(roles);rl.addWidget(self.label('Roles',True));self.action('Character album',lambda:self.change_page(2),rl);rl.addStretch();self.inspector.addTab(roles,self.tr('Roles'))
        exports=QWidget();el=QVBoxLayout(exports);el.addWidget(self.label('Exports',True));self.action('Play output',self.play_output,el);self.action('Open reports',self.open_reports,el);self.exports_info=self.label('—');el.addWidget(self.exports_info);el.addStretch();self.inspector.addTab(exports,self.tr('Exports'))
        self.language.currentIndexChanged.connect(lambda:self.select_cue(self.selected_cue))

    def application(self):
        from PySide6.QtWidgets import QApplication
        return QApplication.instance()
    def change_page(self,index):
        self.tabs.setCurrentIndex(index)
        for button,i in self.nav_buttons:button.setChecked(i==index)
    def live_rows(self):
        rows=[]
        for i in range(self.table.rowCount()):
            try:rows.append(dict(start=float(self.table.item(i,0).text()),end=float(self.table.item(i,1).text()),text=self.table.item(i,2).text(),target=self.table.item(i,3).text(),role=self.table.item(i,4).text()))
            except (ValueError,AttributeError):pass
        return rows
    def fill_cues(self,cues):
        self.updating_caption=True
        try:super().fill_cues(cues)
        finally:self.updating_caption=False
        self.select_cue(0);self.timeline.update()
    def select_cue(self,index):
        rows=self.live_rows()
        if not rows:return
        self.selected_cue=max(0,min(index,len(rows)-1));row=rows[self.selected_cue];self.updating_caption=True
        self.source_caption.setPlainText(row['text']);self.target_caption.setPlainText(row['target']);self.role_badge.setText(row['role']);self.role_edit.setText(row['role']) if hasattr(self,'role_edit') else None
        self.cue_number.setText(f'{self.selected_cue+1} / {len(rows)}');self.updating_caption=False;self.timeline.update()
        self.gpt_audition.setEnabled(self.find_take('gpt') is not None);self.cosy_audition.setEnabled(self.find_take('cosy') is not None)
    def edit_target(self):
        if self.updating_caption or not self.table.rowCount():return
        self.updating_caption=True
        self.table.setItem(self.selected_cue,3,QTableWidgetItem(self.target_caption.toPlainText()));self.updating_caption=False;self.timeline.update()
    def edit_role(self,text):
        if self.table.rowCount():self.table.setItem(self.selected_cue,4,QTableWidgetItem(text));self.role_badge.setText(text)
    def table_changed(self,item):
        if self.updating_caption:return
        if item.row()==self.selected_cue:self.select_cue(item.row())
        self.timeline.update()
    def import_movie(self):
        path,_=QFileDialog.getOpenFileName(self,self.tr('Import video'),'','Movies (*.mp4 *.mkv *.mov *.avi)')
        if path:self.movie.setText(path);self.output.setText(str(Path(path).with_name(Path(path).stem+'-AniCanto.mp4')))
    def movie_changed(self,text):
        self.movie_title.setText(Path(text).name or 'AniCanto');self.video_info.setText(Path(text).name+'\n'+str(Path(text).parent) if text else '—');self.projects.clear()
        if text:self.projects.addItem(Path(text).name+'\n'+self.tr('Ready'))
        self.timeline.update()
    def select_project(self,item):
        path=item.data(Qt.UserRole)
        if path:self.apply_project(json.loads(Path(path).read_text(encoding='utf-8')))
    def choose_output(self):
        path,_=QFileDialog.getSaveFileName(self,self.tr('Output movie'),'','MP4 (*.mp4)')
        if path:self.output.setText(path)
    def show_dialogue_list(self):self.dialogue_dialog.show();self.dialogue_dialog.raise_()
    def show_terminal(self):
        if hasattr(self,'terminal'):self.terminal.show();self.terminal.raise_()
    def toggle_play(self):
        if self.player.playbackState()==QMediaPlayer.PlayingState:self.player.pause()
        elif self.player.source().isEmpty():self.play_source()
        else:self.player.play()
    def seek_seconds(self,seconds):
        if self.player.source()!=QUrl.fromLocalFile(self.movie.text()):self.player.setSource(QUrl.fromLocalFile(self.movie.text()))
        self.player.setPosition(round(seconds*1000))
    def duration_changed(self,value):self.scrubber.setMaximum(value);self.end_clock.setText(timecode(value/1000));self.timeline.update()
    def position_changed(self,value):
        self.clock.setText(timecode(value/1000))
        if not self.scrubber.isSliderDown():self.scrubber.setValue(value)
        rows=self.live_rows()
        if self.follow.isChecked():
            current=next((i for i,row in enumerate(rows) if row['start']<=value/1000<row['end']),None)
            if current is not None and current!=self.selected_cue:self.select_cue(current)
        if self.loop.isChecked() and rows and value/1000>=rows[self.selected_cue]['end']:self.player.setPosition(round(rows[self.selected_cue]['start']*1000))
        self.timeline.update()
    def audition_source(self):
        rows=self.live_rows()
        if not rows:return
        self.follow.setChecked(False);self.seek_seconds(rows[self.selected_cue]['start']);self.player.play()
        QTimer.singleShot(round((rows[self.selected_cue]['end']-rows[self.selected_cue]['start'])*1000),self.player.pause)
    def find_take(self,engine):
        report=Path(self.output.text()).with_suffix('.report.json') if self.output.text() else None
        if report is None or not report.is_file():return None
        try:
            data=json.loads(report.read_text());rows=self.live_rows()
            if data.get('engine')!=engine or not rows:return None
            source_start=float(data.get('sourceStart',self.start.value()))
            selected=rows[self.selected_cue]
            take=next((r for r in data.get('timings',[]) if abs(r.get('plannedEnd',-1)+source_start-selected['end'])<.03),None)
            if take and Path(take['audio']).is_file():return Path(take['audio'])
        except (ValueError,OSError,KeyError):pass
        return None
    def audition_take(self,engine):
        path=self.find_take(engine)
        if path:self.audition.setSource(QUrl.fromLocalFile(str(path)));self.audition.play()
    def open_reports(self):
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.root)))
    def launch(self,program,args,action):
        super().launch(program,args,action);self.status_text.setText(action+'…');self.show_terminal() if action in ('setup','GPU test','graphics detection') else None
    def finished(self,code,status):
        super().finished(code,status);self.status_text.setText(self.tr('Ready') if code==0 else 'Needs review / 待覆核');self.select_cue(self.selected_cue)
        self.exports_info.setText(self.output.text() if Path(self.output.text()).is_file() else '—')
        if code!=0:self.show_terminal()
    def closeEvent(self,event):
        self.audition.stop();super().closeEvent(event)
