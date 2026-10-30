"""AniCanto Windows studio. All production uses native_worker → shared worker.

The GUI owns selection and drafts, not conversion policy. Heavy model work is
isolated in owned processes; disk projections use a bounded background pool.
"""
import codecs
import copy
import html
import json
import os
from pathlib import Path
import random
import sys
import time
import uuid

HERE=Path(__file__).resolve().parent
SHARED=HERE/'shared' if (HERE/'shared').is_dir() else HERE.parent/'Resources'
sys.path[:0]=[str(HERE),str(SHARED)]
from desktop_state import Store,ENGINES,PHASES,read,write,job_snapshot,editor_draft,review_fingerprint,load_draft,find_take,accept_history
from desktop_widgets import IO,Journey,Timeline,theme
from gpu import data_root
from install import env_python
from workflow_settings import COMBINED
from PySide6.QtCore import Qt,QProcess,QProcessEnvironment,QThreadPool,QTimer,QUrl,Signal,QSize
from PySide6.QtGui import QAction,QDesktopServices,QPixmap,QIcon
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,
    QFrame,QLabel,QPushButton,QToolButton,QStackedWidget,QSplitter,QListWidget,QListWidgetItem,
    QComboBox,QCheckBox,QPlainTextEdit,QTextBrowser,QLineEdit,QDoubleSpinBox,QSpinBox,
    QSlider,QFileDialog,QMenu,QTableWidget,QTableWidgetItem,QHeaderView,QTabWidget,QScrollArea,
    QMessageBox,QAbstractItemView,QProgressBar)
from PySide6.QtMultimedia import QMediaPlayer,QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget

def tc(value):
    value=max(0,float(value or 0));return f'{int(value)//3600:02}:{int(value)//60%60:02}:{value%60:04.1f}'

class Cover(QLabel):
    def __init__(self,path):super().__init__();self.image=QPixmap(str(path));self.setMinimumSize(180,180);self.setAlignment(Qt.AlignCenter)
    def resizeEvent(self,event):
        if not self.image.isNull():self.setPixmap(self.image.scaled(self.size(),Qt.KeepAspectRatio,Qt.SmoothTransformation))

class NativeProcess(QProcess):
    event=Signal(dict)
    log=Signal(str)
    def __init__(self,parent):
        super().__init__(parent);self.out='';self.err='';self.log_path=None;self.decoder=codecs.getincrementaldecoder('utf-8')('replace');self.error_decoder=codecs.getincrementaldecoder('utf-8')('replace')
        self.readyReadStandardOutput.connect(self.read_out);self.readyReadStandardError.connect(self.read_err)
        self.finished.connect(self.drain)
    def retain(self,text):
        if self.log_path:
            try:
                with Path(self.log_path).open('a',encoding='utf-8') as file:file.write(text)
            except OSError:pass
    def read_out(self):
        self.out+=self.decoder.decode(bytes(self.readAllStandardOutput()))
        while '\n' in self.out:
            line,self.out=self.out.split('\n',1)
            self.retain(line+'\n')
            try:
                obj=json.loads(line)
                if isinstance(obj,dict):self.event.emit(obj)
                else:self.log.emit(line)
            except ValueError:self.log.emit(line)
    def read_err(self):
        text=self.error_decoder.decode(bytes(self.readAllStandardError()));self.err=(self.err+text)[-12000:];self.retain(text);self.log.emit(text.rstrip())
    def drain(self,*unused):
        self.read_out();self.read_err()
        tail=self.out+self.decoder.decode(b'',final=True);self.out=''
        if tail.strip():
            self.retain(tail+'\n')
            try:
                obj=json.loads(tail)
                if isinstance(obj,dict):self.event.emit(obj)
                else:self.log.emit(tail)
            except (ValueError,TypeError):self.log.emit(tail)
    def launch(self,python,script,args,root):
        self.out='';self.err='';self.decoder.reset();self.error_decoder.reset()
        env=QProcessEnvironment.systemEnvironment()
        for key,value in dict(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',PYTHONPATH=os.pathsep.join([str(HERE),str(SHARED)]),CANTOSYNC_WINDOWS_DATA=str(root),PIP_CACHE_DIR=str(root/'cache/pip'),HF_HOME=str(root/'cache/huggingface')).items():env.insert(key,value)
        self.setProcessEnvironment(env);self.setWorkingDirectory(str(HERE));self.setProgram(str(python));self.setArguments([str(HERE/script),*map(str,args)]);self.start()

from studio_layout import StudioLayout
from studio_pages import StudioPages
from studio_editing import StudioEditing
from studio_preferences import StudioPreferences
from studio_roles import StudioRoleTools

class Studio(StudioRoleTools,StudioPreferences,StudioEditing,StudioPages,StudioLayout,QMainWindow):
    def __init__(self,root=None):
        super().__init__();self.store=Store(root or data_root());self.root=self.store.root
        self.pool=QThreadPool(self);self.pool.setMaxThreadCount(2);self.tasks=set();self.snapshot_busy=False
        self.snapshot={};self.draft=None;self.dirty=False;self.cue_index=-1;self.loading=False
        self.running=None;self.pausing=False;self.batch_running=False;self.run_started=0;self.phase_sample=None
        self.start_after_setup=False;self.ab_pending=None;self.pending_launch=None
        self.undo_stack=[];self.redo_stack=[];self.inference_settings={};self.generic_controls={};self.transcript_index=-1
        self.setup_started=0;self.setup_plan={};self.setup_step='check';self.setup_transfer=None
        self.edit_journey={};self.previous_status='attention';self.active_preview=False
        self.ready=read(self.root/'native-ready.json',{})
        from desktop_state import restore_requested_drama
        from drama_cuda import capable
        if restore_requested_drama(self.store,self.ready,capable()):self.ready={}
        self.version=read(HERE/'VERSION.json',read(HERE.parent/'VERSION.json',{})).get('version','development')
        self.setWindowTitle('AniCanto · '+self.version);self.resize(1550,990);self.setMinimumSize(1080,700)
        self.accent=random.choice(['#7350b8','#2d796e','#bb6327','#057c91'])
        covers=sorted((SHARED/'welcome-art').glob('welcome-*.png'));self.cover_path=random.choice(covers) if covers else SHARED/'companion-studio.png'
        key=self.cover_path.stem.replace('welcome-','');key='studio' if key=='ensemble' else key
        self.accent=__import__('studio_layout').CONTRACT['themes'].get(key,'#7050B9')
        self.runner_path=SHARED/('pet-'+key+'.png')
        self.ui_process=NativeProcess(self);self.ui_process.event.connect(self.setup_event);self.ui_process.log.connect(self.log);self.ui_process.finished.connect(self.setup_finished)
        self.worker=NativeProcess(self);self.worker.event.connect(self.work_event);self.worker.log.connect(self.log);self.worker.finished.connect(self.work_finished)
        self.worker.errorOccurred.connect(lambda error:self.process_error(self.worker,error))
        self.ui_process.errorOccurred.connect(lambda error:self.process_error(self.ui_process,error))
        self.player=QMediaPlayer(self);self.audio=QAudioOutput(self);self.player.setAudioOutput(self.audio)
        self.audition=QMediaPlayer(self);self.audition_audio=QAudioOutput(self);self.audition.setAudioOutput(self.audition_audio)
        self.audition.mediaStatusChanged.connect(self.audition_status)
        self.player.positionChanged.connect(self.playhead);self.player.durationChanged.connect(self.duration_changed)
        self.central=QWidget();self.setCentralWidget(self.central);outer=QHBoxLayout(self.central);outer.setContentsMargins(0,0,0,0);outer.setSpacing(0)
        self.shell=QStackedWidget();outer.addWidget(self.shell,1)
        self.drawer=QFrame();self.drawer.setMinimumWidth(360);self.drawer.setMaximumWidth(780);dl=QVBoxLayout(self.drawer)
        dh=QHBoxLayout();self.drawer_title=QLabel();dh.addWidget(self.drawer_title);dh.addStretch();self.button('Close','關閉',self.close_drawer,dh);dl.addLayout(dh)
        self.drawer_search=QLineEdit();self.drawer_search.setPlaceholderText(self.t('Find in this page','搜尋本頁'));dl.addWidget(self.drawer_search);self.drawer_search.textChanged.connect(self.find_drawer_text)
        self.drawer_text=QTextBrowser();self.drawer_text.setOpenExternalLinks(True);dl.addWidget(self.drawer_text);outer.addWidget(self.drawer);self.drawer.hide()
        self.build_welcome();self.build_workspace();self.apply_preferences()
        self.timer=QTimer(self);self.timer.setInterval(2000);self.timer.timeout.connect(self.refresh_snapshot);self.timer.start()
        self.clock_timer=QTimer(self);self.clock_timer.setInterval(1000);self.clock_timer.timeout.connect(self.refresh_clock);self.clock_timer.start()
        self.restore_queue();self.update_mode();self.shell.setCurrentIndex(0)
        self.refresh_busy()
        if sys.platform=='win32':QTimer.singleShot(100,self.show_plan)
        self.setup_status.setText(self.t('Setup is verified on this PC. Existing models will be reused.','本機部署已驗證；會沿用已下載模型。') if self.ready.get('speechInferencePassed') else self.t('First use: review the download plan, then deploy once.','首次使用：先檢視下載清單，再一按部署。'))
    def t(self,en,zh):return zh if self.store.language=='zh-HK' else en
    def label(self,en,zh,muted=False):
        w=QLabel(self.t(en,zh));w.setWordWrap(True)
        if muted:w.setObjectName('muted')
        return w
    def button(self,en,zh,callback,layout=None,primary=False):
        w=QPushButton(self.t(en,zh).replace('&','&&'));w.clicked.connect(callback)
        if primary:w.setObjectName('primary')
        if layout:layout.addWidget(w)
        return w
    def background(self,fn,done,failed=None):
        task=IO(fn);self.tasks.add(task)
        def finish(value):
            try:done(value)
            finally:self.tasks.discard(task)
        def fail(error):
            self.tasks.discard(task)
            if failed:failed(error)
            else:self.log(error)
        task.signals.done.connect(finish);task.signals.failed.connect(fail);self.pool.start(task)
    def build_welcome(self):
        page=QWidget();layout=QHBoxLayout(page);layout.setContentsMargins(30,35,30,30);layout.setSpacing(40)
        left_widget=QWidget();left_widget.setObjectName('welcomeArt');left=QVBoxLayout(left_widget);left.setContentsMargins(30,30,30,30);brand=self.label('AniCanto','AniCanto');brand.setObjectName('brand');left.addWidget(brand)
        title=self.label('Your anime. A whole new voice.','你嘅動畫，另一把聲音。');title.setObjectName('heading');left.addWidget(title)
        left.addWidget(self.label('Hong Kong Cantonese · Mandarin · English · Just for fun','香港廣東話 · 普通話 · English · Just for fun',True));left.addWidget(Cover(self.cover_path),1)
        left.addWidget(self.label('SCKC / ANIME DUBBING PLAYGROUND','SCKC / ANIME DUBBING PLAYGROUND',True));layout.addWidget(left_widget,1)
        right=QVBoxLayout();right.setSpacing(15)
        line=QHBoxLayout();line.addStretch();line.addWidget(self.label('Interface language','介面語言'))
        self.language=QComboBox();self.language.addItem('English','en');self.language.addItem('香港繁體中文','zh-HK');self.language.setMinimumWidth(180);self.language.setCurrentIndex(max(0,self.language.findData(self.store.language)));line.addWidget(self.language);right.addLayout(line)
        self.language.currentIndexChanged.connect(self.change_language)
        heading=self.label('Welcome to your dubbing studio','歡迎返到聲演工作室');heading.setObjectName('heading');right.addWidget(heading)
        right.addWidget(self.label('Bring in an episode. Pick a voice. Let the studio handle production.','放入動畫，揀把聲，其餘交畀工作室。',True))
        from PySide6.QtWidgets import QButtonGroup,QSizePolicy
        from studio_icons import icon
        self.welcome_modes=QButtonGroup(self);self.welcome_modes.setExclusive(True)
        for en,zh,detail_en,detail_zh,mode,name in [('Basic mode','基本模式','Choose an engine and subtitles. Start automatic production.','揀引擎同字幕，一按自動製作。','basic','sparkles'),('Expert mode','專家模式','A timeline, line-by-line auditions, retakes and detailed editing.','時間線、逐句試聽、重錄與精細編輯。','expert','sliders')]:
            button=QToolButton();button.setObjectName('modeCard');button.setIcon(icon(name,self.accent));button.setProperty('studioIcon',name);button.setProperty('studioTint',True);button.setIconSize(QSize(24,24));button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon);button.setText(self.t(en,zh)+'\n'+self.t(detail_en,detail_zh));button.setCheckable(True);button.setChecked(self.store.mode==mode);button.setMinimumHeight(84);button.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Preferred);self.welcome_modes.addButton(button);button.clicked.connect(lambda checked=False,m=mode:self.select_welcome_mode(m));right.addWidget(button)
        card=QFrame();card.setObjectName('card');cl=QVBoxLayout(card);cl.addWidget(self.label('Local models & setup','本機模型與部署'))
        self.setup_status=self.label('Checking local setup…','正在檢查本機部署⋯',True);cl.addWidget(self.setup_status)
        self.setup_steps=self.label('Check → Install → Download → Verify → Ready','檢查 → 安裝 → 下載 → 驗證 → 就緒',True);cl.addWidget(self.setup_steps)
        self.setup_progress=QProgressBar();self.setup_progress.setRange(0,1000);self.setup_progress.setValue(0);self.setup_progress.setTextVisible(False);cl.addWidget(self.setup_progress)
        self.setup_detail=self.label('Completed files are reused; interrupted downloads resume.','沿用已完成檔案；中斷下載可以續傳。',True);cl.addWidget(self.setup_detail)
        self.welcome_system_memory=self.label('System RAM · checking…','系統 RAM · 正在檢查…',True);cl.addWidget(self.welcome_system_memory)
        self.welcome_system_bar=QProgressBar();self.welcome_system_bar.setRange(0,1000);self.welcome_system_bar.setValue(0);self.welcome_system_bar.setTextVisible(False);cl.addWidget(self.welcome_system_bar)
        self.welcome_gpu_memory=self.label('GPU VRAM · checking…','GPU VRAM · 正在檢查…',True);cl.addWidget(self.welcome_gpu_memory)
        self.welcome_gpu_bar=QProgressBar();self.welcome_gpu_bar.setRange(0,1000);self.welcome_gpu_bar.setValue(0);self.welcome_gpu_bar.setTextVisible(False);cl.addWidget(self.welcome_gpu_bar)
        cl.addWidget(self.label('Full Drama 3 Q2 uses CPU and about 22 GB system RAM; 32 GB RAM or more is recommended. At least 8 GB is reserved for Windows. VRAM is shown separately for GPU-capable models.','完整 Drama 3 Q2 用 CPU，估計佔約 22 GB 系統 RAM；建議 32 GB RAM 或以上。至少預留 8 GB 畀 Windows。支援 GPU 嘅模型會另外顯示 VRAM。',True))
        self.inventory=QPlainTextEdit();self.inventory.setReadOnly(True);self.inventory.setMaximumHeight(100);cl.addWidget(self.inventory)
        self.plan_table=QTableWidget(0,4);self.plan_table.setHorizontalHeaderLabels([self.t('Purpose','用途'),self.t('Model','模型'),self.t('Size','大小'),self.t('Action','處理')]);self.plan_table.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch);self.plan_table.setEditTriggers(QAbstractItemView.NoEditTriggers);self.plan_table.setMaximumHeight(190);self.plan_table.hide();cl.addWidget(self.plan_table)
        actions=QHBoxLayout();self.button('Review download plan','檢視下載清單',self.show_plan,actions);self.deploy_button=self.button('Deploy / repair','一按部署／修復',self.deploy,actions,True);self.button('Pause download','暫停下載',self.pause_setup,actions);cl.addLayout(actions);self.setup_card=card;self.setup_disclosure=QToolButton();self.setup_disclosure.setToolButtonStyle(Qt.ToolButtonTextBesideIcon);self.setup_disclosure.setText(self.t('Local models & setup','本機模型與部署').replace('&','&&'));self.setup_disclosure.setCheckable(True);self.setup_disclosure.setChecked(not self.ready.get('speechInferencePassed',False));self.setup_disclosure.setArrowType(Qt.DownArrow if self.setup_disclosure.isChecked() else Qt.RightArrow);self.setup_disclosure.toggled.connect(lambda checked:(self.setup_card.setVisible(checked),self.setup_disclosure.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)));right.addWidget(self.setup_disclosure);card.setVisible(self.setup_disclosure.isChecked());right.addWidget(card)
        manage=QToolButton();manage.setText(self.t('Manage models & runtimes','管理模型與執行環境').replace('&','&&'));manage.setCheckable(True);manage.setToolButtonStyle(Qt.ToolButtonTextBesideIcon);manage.setArrowType(Qt.RightArrow);right.addWidget(manage)
        self.package_table=QTableWidget(0,3);self.package_table.setHorizontalHeaderLabels([self.t('Component','元件'),self.t('Status','狀態'),self.t('Actions','操作')]);self.package_table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch);self.package_table.setEditTriggers(QAbstractItemView.NoEditTriggers);self.package_table.setMaximumHeight(180);self.package_table.hide();right.addWidget(self.package_table)
        self.cleanup_controls=QWidget();cleanup=QVBoxLayout(self.cleanup_controls);cleanup.setContentsMargins(0,0,0,0)
        self.storage_label=self.label('Downloaded files are stored here:','下載檔案儲存位置：',True);cleanup.addWidget(self.storage_label);cleanup.addWidget(self.label(str(self.root),str(self.root),True))
        cr=QHBoxLayout();self.cleanup_buttons=[self.button('Delete downloaded models…','刪除已下載模型⋯',lambda:self.cleanup_downloads('models'),cr),self.button('Delete all downloads & close…','清除全部下載並關閉⋯',lambda:self.cleanup_downloads('all'),cr)];cleanup.addLayout(cr)
        self.button('Open storage folder','開啟儲存資料夾',lambda:self.reveal(self.root),cleanup)
        cleanup.addWidget(self.label('Videos, projects, recordings and exports are kept. Shared caches outside this folder are not removed.','保留影片、專案、錄音及成品；唔會移除呢個資料夾以外嘅共用快取。',True));self.cleanup_controls.hide();right.addWidget(self.cleanup_controls)
        manage.toggled.connect(lambda checked:(self.package_table.setVisible(checked),self.cleanup_controls.setVisible(checked),manage.setArrowType(Qt.DownArrow if checked else Qt.RightArrow),self.show_plan() if checked and not self.setup_plan else None))
        right.addWidget(self.label('Models and runtimes download once into the local app cache. Verified matching models are reused.','模型及執行環境只需下載一次，儲存喺本機快取；已驗證嘅相符模型會直接沿用。',True))
        self.button('Enter the studio','進入工作室',lambda:self.enter(self.store.mode),right,True).setMinimumHeight(40)
        links=QHBoxLayout();self.button('Quick guide','使用教學',self.guide,links);links.addStretch();self.button('About & licences','關於與授權',self.about,links);right.addLayout(links);right.addStretch()
        right.addWidget(self.label('A hobby project by SCKC, sharing the fun of dubbing and Hong Kong Cantonese culture.','由 SCKC 為興趣製作，分享配音樂趣，同時探索香港廣東話文化。',True))
        right_widget=QWidget();right_widget.setLayout(right);right_scroll=QScrollArea();right_scroll.setWidgetResizable(True);right_scroll.setFrameShape(QFrame.NoFrame);right_scroll.setWidget(right_widget);layout.addWidget(right_scroll,1);self.shell.addWidget(page)
    def build_queue(self):
        page=QWidget();l=QVBoxLayout(page);row=QHBoxLayout();row.addWidget(self.label('Work queue','工作佇列'),1);self.button('Add videos','加入影片',self.add_videos,row);self.button('Start waiting videos','開始待處理影片',self.start_all,row,True);l.addLayout(row)
        self.queue_table=QTableWidget(0,4);self.queue_table.setHorizontalHeaderLabels([self.t('Video','影片'),self.t('Status','狀態'),self.t('Processing time','處理時間'),self.t('Output','成品')]);self.queue_table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch);self.queue_table.horizontalHeader().setSectionResizeMode(3,QHeaderView.Stretch);self.queue_table.setEditTriggers(QAbstractItemView.NoEditTriggers);self.queue_table.cellDoubleClicked.connect(lambda row,col:self.open_queue_row(row,col));l.addWidget(self.queue_table,1);self.pages.addWidget(page)
    def backend_sync_controls(self):
        self.loading=True;s=self.store.settings
        self.engine.setCurrentIndex(max(0,self.engine.findData(s['selectedEngines'][0])))
        for key,check in self.extra_engines.items():check.setChecked(key in s['selectedEngines'][1:])
        self.extra_tracks_hint.setText((self.t('Additional tracks: ','額外音軌：')+str(len(s['selectedEngines'])-1)) if len(s['selectedEngines'])>1 else '')
        self.dub_language.setCurrentIndex(max(0,self.dub_language.findData(s['dubLanguages'])))
        self.original.setChecked(s.get('includeOriginal',True));self.fast.setChecked(s.get('productionMode')=='fast');self.fast_warning.setVisible(self.fast.isChecked())
        self.op.setCurrentIndex(int(s.get('translateOPED',False)))
        self.start_offset.setValue(s.get('startOffset',0));self.range_limit.setCurrentIndex(max(0,self.range_limit.findData(s.get('limit',0))))
        self.source.setCurrentIndex(max(0,self.source.findData('audio-only' if s.get('translationSource')=='audio-only' else 'external' if s.get('subtitle') else 'auto')))
        for key,check in self.sub_checks.items():check.setChecked(key in s.get('subtitleModes',[]))
        self.loading=False
    def backend_settings_changed(self,*unused):
        if self.loading:return
        s=self.store.settings;engine=self.engine.currentData();languages=self.dub_language.currentData()
        selected=[engine]+[key for key,check in self.extra_engines.items() if check.isChecked() and key!=engine]
        if self.store.mode=='basic' and self.sender() is self.engine:
            selected=[engine]
            for check in self.extra_engines.values():
                check.blockSignals(True);check.setChecked(False);check.blockSignals(False)
        if selected==['wsyue'] and 'en' in languages:
            self.notice(self.t('WenetSpeech-Yue supports Cantonese only. Choose a different engine for English.','WenetSpeech-Yue 只支援廣東話；英文配音請揀其他引擎。'));self.sync_controls();return
        s.update(selectedEngines=selected,ttsBackend=engine,defaultAudioEngine=engine,dubLanguages=languages,includeOriginal=self.original.isChecked(),subtitleModes=[k for k,w in self.sub_checks.items() if w.isChecked()],productionMode='fast' if self.fast.isChecked() else 'standard',translateOPED=self.op.currentData(),autoSkipOP=not self.op.currentData())
        s.update(startOffset=self.start_offset.value(),limit=self.range_limit.currentData())
        self.fast_warning.setVisible(self.fast.isChecked())
        choice=self.source.currentData()
        if choice=='external' and not s.get('subtitle'):
            path,_=QFileDialog.getOpenFileName(self,self.t('Subtitle file','字幕檔案'),'','Subtitles (*.srt *.ass *.vtt)')
            if path:s.update(subtitle=path,subtitleSource='external',batchAutoSubtitles=False,batchExplicitSubtitle=True,translationSource=COMBINED)
            else:self.source.setCurrentIndex(0)
        elif choice=='audio-only':s.update(translationSource='audio-only',batchAutoSubtitles=False,subtitleSource='none',ocr=False)
        elif choice=='auto':s.update(translationSource=COMBINED,batchAutoSubtitles=True,subtitleSource='embedded');s.pop('subtitle',None)
        self.store.save();self.update_defaults()
        self.extra_tracks_hint.setText((self.t('Additional tracks: ','額外音軌：')+str(len(selected)-1)) if len(selected)>1 else '')
    def change_language(self):
        language=self.language.currentData()
        if language==self.store.language:return
        self.store.language_default(language)
        # Recreate widgets without changing the one shared Store or submissions.
        self.save_draft();self.player.stop();self.audition.stop()
        new=Studio(self.root);new.show();self.timer.stop();self.clock_timer.stop();self.hide();QApplication.instance().studio=new
        self.deleteLater()
    def enter(self,mode):self.set_mode(mode);self.shell.setCurrentIndex(1);self.close_drawer();self.apply_preferences()
    def set_mode(self,mode):
        self.store.mode=mode;self.store.save();self.update_mode()
    def navigate_editor_settings(self):self.nav.setCurrentRow(0);self.inspector.show();self.inspector_tabs.setCurrentIndex(0)
    def welcome(self):
        if self.running:self.notice(self.t('Pause and save the video conversion before returning to Welcome.','返回首頁前請先暫停並保存影片轉換。'));return
        self.save_draft();self.shell.setCurrentIndex(0);self.apply_preferences()
    def add_videos(self):
        paths,_=QFileDialog.getOpenFileNames(self,self.t('Add videos','加入影片'),'','Videos (*.mp4 *.mkv *.mov *.avi *.m4v *.webm)')
        if paths:self.store.add(paths);self.restore_queue()
    def status_name(self,status):
        return dict(waiting=self.t('Waiting','等待'),running=self.t('Processing','處理中'),paused=self.t('Paused','已暫停'),complete=self.t('Complete','已完成'),attention=self.t('Needs attention','需要處理')).get(status,status)
    def backend_restore_queue(self):
        self.queue_list.blockSignals(True);self.queue_list.clear();selected=0
        self.queue_table.setRowCount(len(self.store.queue))
        for i,row in enumerate(self.store.queue):
            self.queue_list.addItem(Path(row['video']).name+'\n'+self.status_name(row['status']))
            if row['id']==self.store.selected:selected=i
            for col,value in enumerate([Path(row['video']).name,self.status_name(row['status']),tc(row.get('processingSeconds',0)),row.get('output','')]):self.queue_table.setItem(i,col,QTableWidgetItem(value))
        self.queue_list.blockSignals(False)
        if self.store.queue:self.queue_list.setCurrentRow(selected);self.select_queue(selected)
    def backend_select_queue(self,index):
        if not 0<=index<len(self.store.queue):return
        row=self.store.queue[index]
        if self.store.selected!=row['id']:self.save_draft();self.snapshot={};self.draft=None;self.dirty=False;self.cue_index=-1
        self.store.selected=row['id'];self.store.save();self.video_title.setText(Path(row['video']).name)
        if self.player.source().toLocalFile()!=row['video']:self.player.setSource(QUrl.fromLocalFile(row['video']))
        self.refresh_snapshot();self.refresh_status()
    def remove_video(self):
        row=self.store.row()
        if not row:return
        if self.running==row['id']:self.notice(self.t('Pause this video before removing it.','請先暫停呢條影片再移除。'));return
        # Cleanup is conservative: only this app-owned job tree is removed;
        # generated movies are moved to exports first, original media untouched.
        if QMessageBox.question(self,'AniCanto',self.t('Remove this project and its processing data? Original videos and exported movies are kept.','移除呢個專案及處理資料？原片同已輸出影片會保留。'))!=QMessageBox.Yes:return
        self.save_draft();self.draft=None;self.dirty=False
        from desktop_cleanup import remove
        copied=copy.deepcopy(row)
        def done(value):
            self.store.queue=[r for r in self.store.queue if r['id']!=copied['id']];self.store.selected=None;self.store.save();self.snapshot={};self.restore_queue()
        self.background(lambda:remove(self.root,copied),done,self.notice)
    def start_all(self):
        if self.running:return
        if self.ui_process.state()!=QProcess.NotRunning:
            self.start_after_setup=True;self.shell.setCurrentIndex(0);self.setup_status.setText(self.t('Setup continues. Your videos will start automatically after verification.','部署仍在進行；驗證完成後會自動開始處理影片。'));return
        if not self.store.queue:self.add_videos();return
        if not self.ready.get('speechInferencePassed'):
            self.start_after_setup=True;self.shell.setCurrentIndex(0);self.deploy();return
        from native_models import missing_setup
        self.store.settings['nativeDramaCPU']=self.cpu_drama.isChecked()
        missing=missing_setup(self.root,self.store.settings['selectedEngines'],self.cpu_drama.isChecked())
        if missing:
            self.start_after_setup=True;self.deploy(missing[0]);return
        if self.store.mode=='basic' and self.store.settings.get('translationSource')=='audio-only':
            self.store.settings.update(translationSource=COMBINED,batchAutoSubtitles=True,subtitleSource='embedded');self.sync_controls()
        self.batch_running=True;self.start_next()
    def backend_start_next(self):
        row=next((r for r in self.store.queue if r['status'] in ('waiting','paused')),None)
        if row is None:self.batch_running=False;return
        self.store.selected=row['id'];self.restore_queue();request=self.store.submit(row)
        self.launch_worker('batch',request,row['id'])
    def launch_worker(self,action,path,ident,repaired=False):
        python=env_python('worker')
        row=self.store.row(ident)
        if row and not Path(row['video']).is_file():
            self.record_preflight_error(row,path,action,self.t('The source video cannot be found. Reconnect its drive or import the file again.','搵唔到原片；請重新連接磁碟或再匯入影片。'));return
        missing=[name for name in ('ffmpeg','ffprobe') if not Path(self.ready.get(name) or '').is_file()]
        if not python.is_file() or missing or (self.root/'setup-invalidated.json').exists():
            if repaired:
                self.record_preflight_error(row,path,action,self.t('Setup verification did not restore the required files. Open Welcome → Manage models & runtimes to repair them; the attempt log is retained.','部署驗證後仍缺少所需檔案，請到首頁管理模型及執行環境修復；已保留紀錄。'));return
            self.batch_running=False;self.pending_launch=(action,path,ident);self.start_after_setup=False
            self.setup_status.setText(self.t('Repairing missing runtime or model components before production.','開始前正修復缺少嘅執行環境或模型元件。'))
            self.shell.setCurrentIndex(0);self.deploy();return
        self.running=ident;self.run_action=action;self.run_started=time.monotonic();self.phase_sample=None;self.pausing=False;self.edit_job=None;self.edit_output=None
        row=self.store.row(ident)
        if row:
            from diagnostics import start
            attempt=start(self.root,row,action,path);self.worker.log_path=Path(attempt['path'])/'process.log'
        self.previous_status=row.get('status','attention') if row else 'attention';self.edit_journey={}
        if row:
            row['status']='running'
            if action=='render-project' and not getattr(self,'active_preview',False):row['partial']=False
            self.store.save()
        self.worker.launch(python,'native_worker.py',[action,path],self.root);self.refresh_busy()
    def work_event(self,event):
        row=self.store.row(self.running)
        if not row:return
        if self.run_action=='render-project':
            if event.get('job'):self.edit_job=event['job']
            if event.get('output'):self.edit_output=event['output']
            # An audition output is not the episode's exported movie, and its
            # local review must never replace the episode's source draft.
            if event.get('journey'):self.edit_journey=event['journey']
            excluded=('job','review','output','journey','progress')+(('partial',) if getattr(self,'active_preview',False) else ())
            self.store.event(row,{k:v for k,v in event.items() if k not in excluded})
        else:self.store.event(row,event)
        self.log(json.dumps(event,ensure_ascii=False))
        if self.follow.isChecked() and self.audition.playbackState()!=QMediaPlayer.PlayingState:
            sec=event.get('sourceTime')
            if sec is None and isinstance(event.get('cueIndex'),int):
                cues=self.snapshot.get('review',{}).get('cues',[]);i=event['cueIndex']
                if 0<=i<len(cues):sec=cues[i]['start']
            if isinstance(sec,(int,float)) and abs(self.player.position()/1000-sec)>.4:self.seek(sec)
        complete=event.get('workCompleted');total=event.get('workTotal')
        if isinstance(complete,(float,int)) and isinstance(total,(float,int)) and total>0:
            key=(event.get('workID'),total)
            if self.phase_sample is None or self.phase_sample[0]!=key:self.phase_sample=(key,time.monotonic(),complete,complete,total)
            else:self.phase_sample=(*self.phase_sample[:3],complete,total)
        self.refresh_status()
        if event.get('review') or event.get('output'):self.refresh_snapshot()
    def backend_work_finished(self,code,status):
        row=self.store.row(self.running)
        if row:
            from diagnostics import finish
            if self.run_action=='render-project':
                result=read(Path(self.edit_job)/'version.json',{}) if self.edit_job else {}
                output=result.get('exportedOutput') or result.get('output') or self.edit_output
                preview=getattr(self,'active_preview',False)
                tool_result=result.get('status') in ('preview','audition-review','script-ready','script-partial','voice-samples','preview-script','prosody-experiment') or preview
                if output and not tool_result and Path(output).is_file():
                    row['output']=output;row['outputThisAttempt']=output
                finish(self.root,row,code,self.pausing,self.worker.err,self.worker.errorString(),success_without_movie=bool(tool_result and code==0))
                if tool_result:row['status']=self.previous_status
                else:row['status']='paused' if self.pausing else 'complete' if row.get('outputThisAttempt') and code==0 and not row.get('partial') else 'attention'
                if output:self.produce_result.setPlainText(output)
                self.store.save()
            else:
                finish(self.root,row,code,self.pausing,self.worker.err,self.worker.errorString())
                self.store.finish(row,code,self.pausing)
        self.running=None;self.refresh_busy();self.refresh_snapshot();self.restore_queue()
        if row and row.get('lastError') and not self.pausing:self.show_failure(row)
        if self.batch_running and not self.pausing:QTimer.singleShot(100,self.start_next)
    def process_error(self,process,error):
        self.log(process.errorString())
        if error==QProcess.FailedToStart:
            if process is self.worker:self.work_finished(1,QProcess.NormalExit)
            else:self.setup_finished(1,QProcess.NormalExit)
    def pause(self):
        if not self.running:
            if self.store.row() and self.store.row().get('status')=='paused':self.start_selected()
            return
        self.save_draft();self.pausing=True;self.batch_running=False;self.worker.kill()
        # Native worker owns a Windows Job Object for its descendants. Closing
        # it cannot leave a hidden model running after the UI reports paused.
    def refresh_busy(self):
        busy=self.running is not None or self.ui_process.state()!=QProcess.NotRunning
        self.settings_box.setEnabled(not busy);self.start_button.setEnabled(self.running is not None or not busy);self.pause_button.setEnabled(self.running is not None or bool(self.store.row() and self.store.row().get('status')=='paused'));self.deploy_button.setEnabled(not busy);self.export_button.setEnabled(not busy and self.draft is not None)
        self.language.setEnabled(not busy)
    def refresh_snapshot(self):
        if self.snapshot_busy:return
        row=self.store.row()
        if not row:return
        self.snapshot_busy=True;ident=row['id'];source=copy.deepcopy(row)
        def done(data):
            self.snapshot_busy=False
            if self.store.selected==ident:self.apply_snapshot(data)
        self.background(lambda:job_snapshot(source),done,lambda error:self.snapshot_failed(error))
    def snapshot_failed(self,error):self.snapshot_busy=False;self.log(error)
    def apply_snapshot(self,data):
        self.snapshot=data;row=self.store.row();review=data.get('review',{})
        if review and (self.draft is None or (not self.dirty and self.draft.get('baseFingerprint')!=review_fingerprint(review))):
            self.draft=load_draft(row['review'],review,review.get('config',{}))
            self.populate_editor()
            engine=review.get('config',{}).get('ttsBackend',self.store.settings['ttsBackend']);self.take_engine.setCurrentIndex(max(0,self.take_engine.findData(engine)))
        if data.get('time'):
            row['processingSeconds']=data['time'].get('seconds',0);self.store.save()
        self.timeline.cues=self.draft.get('segments',[]) if self.draft else review.get('cues',[])
        self.timeline.duration=max(30,review.get('config',{}).get('duration',0),self.player.duration()/1000)
        self.timeline.takes=[r for r in data.get('takes',[]) if r.get('engine')==self.take_engine.currentData() and r.get('language')==self.take_language.currentData()]
        self.timeline.engine=self.take_engine.currentText();self.timeline.update();self.refresh_take();self.refresh_history();self.refresh_status();self.refresh_busy()
        report=data.get('report',{});self.report_text.setPlainText(json.dumps(dict(quality=report.get('qualityStatus'),issues=data.get('issues',[])),ensure_ascii=False,indent=2));self.produce_result.setPlainText(row.get('output') or self.t('No exported video yet.','暫時未有輸出影片。'))
    def backend_populate_editor(self):
        if not self.draft:return
        self.loading=True;segments=self.draft['segments'];self.cue_table.setRowCount(len(segments))
        for i,row in enumerate(segments):
            for c,key in enumerate(['start','end','original','text','english','speakerId']):self.cue_table.setItem(i,c,QTableWidgetItem(str(row.get(key,''))))
        roles=self.draft['settings'].get('voiceProfiles',[]);self.roles.setRowCount(len(roles))
        for i,row in enumerate(roles):
            for c,key in enumerate(['id','name','reference','promptText']):self.roles.setItem(i,c,QTableWidgetItem(str(row.get(key,''))))
        clips=self.draft.get('clips',[]);self.clips.setRowCount(0)
        for clip in clips:self.add_clip(clip)
        self.loading=False
        if segments:self.select_cue(max(0,self.cue_index))
    def cue_selected(self):
        if not self.loading:self.select_cue(self.cue_table.currentRow(),seek=False)
    def backend_select_cue(self,index,seek=True):
        if not self.draft or not 0<=index<len(self.draft['segments']):return
        self.cue_index=index;row=self.draft['segments'][index];self.loading=True
        self.cue_table.selectRow(index);self.cue_count.setText(f'{index+1} / {len(self.draft["segments"])}');self.caption.setText(row['text'] if self.take_language.currentData()=='yue' else row.get('english',''))
        self.cue_enabled.setChecked(row.get('enabled',True));self.cue_preserve.setChecked(row.get('preserveOriginalSpeech',False));self.cue_rate.setValue(row.get('rate',1));self.loading=False
        self.timeline.selected=index;self.timeline.update();self.refresh_take()
        if seek:self.seek(row['start'])
    def backend_edit_cue(self,item):
        if self.loading or not self.draft:return
        key=['start','end','original','text','english','speakerId'][item.column()];value=item.text()
        if key in ('start','end'):
            try:value=float(value)
            except ValueError:self.populate_editor();return
        self.draft['segments'][item.row()][key]=value;self.dirty=True
    def backend_change_segment(self,key,value):
        if self.loading or not self.draft or self.cue_index<0:return
        self.draft['segments'][self.cue_index][key]=value;self.dirty=True
    def backend_role_changed(self,item):
        if self.loading or not self.draft:return
        key=['id','name','reference','promptText'][item.column()]
        if key=='id':return # Stable cue links must not be rewritten by a label edit.
        self.draft['settings']['voiceProfiles'][item.row()][key]=item.text();self.dirty=True
    def play_reference(self):
        if not self.draft:return
        rows=self.draft['settings'].get('voiceProfiles',[]);i=self.roles.currentRow()
        if 0<=i<len(rows):self.play_audio(rows[i].get('reference',''))
    def backend_replace_reference(self):
        if not self.draft or self.roles.currentRow()<0:return
        file,_=QFileDialog.getOpenFileName(self,self.t('Reference recording','參考錄音'),'','Audio (*.wav *.mp3 *.flac *.m4a)')
        if file:self.draft['settings']['voiceProfiles'][self.roles.currentRow()]['reference']=file;self.dirty=True;self.populate_editor()
    def backend_save_draft(self):
        if not self.draft:return
        self.read_clips();root=Path(self.snapshot.get('root',Path(self.draft['review']).parent));write(root/'editor-draft-windows.json',self.draft);self.dirty=False
    def add_clip(self,clip=None):
        if not isinstance(clip,dict):clip=dict(start=0,end=self.snapshot.get('review',{}).get('config',{}).get('duration',self.player.duration()/1000),enabled=True,ripple=True)
        i=self.clips.rowCount();self.clips.insertRow(i)
        for c,key in enumerate(['start','end','enabled','ripple']):self.clips.setItem(i,c,QTableWidgetItem(str(clip.get(key,''))))
    def read_clips(self):
        if not self.draft:return
        result=[]
        for i in range(self.clips.rowCount()):
            try:result.append(dict(start=float(self.clips.item(i,0).text()),end=float(self.clips.item(i,1).text()),enabled=self.clips.item(i,2).text().lower() not in ('false','0'),ripple=self.clips.item(i,3).text().lower() not in ('false','0')))
            except (ValueError,AttributeError):raise ValueError(self.t('Check clip start/end seconds.','請檢查片段開始／結束秒數。'))
        self.draft['clips']=result
    def export_edit(self):
        if not self.draft:self.notice(self.t('Select a project with translated dialogue first.','請先選擇已有翻譯對白嘅專案。'));return
        self.submit_edit()
    def retake(self):
        if self.draft and self.cue_index>=0:self.submit_edit(True)
    def backend_refresh_take(self,*unused):
        if not hasattr(self,'audition_button'):return
        row=find_take(self.snapshot,self.cue_index,self.take_engine.currentData(),self.take_language.currentData())
        self.audition_button.setEnabled(bool(row));self.take_status.setText(self.t('Available · ','可試聽 · ')+self.take_engine.currentText() if row else self.t('No take for this engine / language','此引擎／語言暫時未有錄音'))
        self.basic_audition.setEnabled(bool(row))
        self.timeline.takes=[r for r in self.snapshot.get('takes',[]) if r.get('engine')==self.take_engine.currentData() and r.get('language')==self.take_language.currentData()];self.timeline.engine=self.take_engine.currentText();self.timeline.update()
    def play_take(self):
        row=find_take(self.snapshot,self.cue_index,self.take_engine.currentData(),self.take_language.currentData())
        if row:self.play_audio(row['audio'])
    def adopt_audition(self):
        if not self.draft or self.cue_index<0:return
        row=find_take(self.snapshot,self.cue_index,self.take_engine.currentData(),self.take_language.currentData())
        if not row:return
        if row.get('skipped'):
            self.notice(self.t('This take needs review. Compare it in the recording history before accepting it.','此錄音需覆核；請先喺錄音歷史比較，再決定採用。'));return
        segment=self.draft['segments'][self.cue_index];segment['audioTake']=row['audio'];segment.pop('audioAcceptedHistoryID',None);self.dirty=True;self.save_draft()
    def play_audio(self,path):
        if not Path(path).is_file():return
        self.player.pause();self.follow.setChecked(False);self.audition.setSource(QUrl.fromLocalFile(str(path)));self.audition.play()
    def audition_status(self,status):
        if status==QMediaPlayer.EndOfMedia:self.audition.stop()
    def play_original(self):
        if self.draft and self.cue_index>=0:self.audition.stop();self.seek(self.draft['segments'][self.cue_index]['start']);self.player.play()
    def follow_changed(self,enabled):
        if enabled:self.audition.stop() # Never overlap an audition and a follow seek.
    def toggle_play(self):
        self.audition.stop()
        self.player.pause() if self.player.playbackState()==QMediaPlayer.PlayingState else self.player.play()
    def seek(self,seconds):self.player.setPosition(round(max(0,float(seconds))*1000))
    def backend_duration_changed(self,value):self.scrubber.setRange(0,value);self.timeline.duration=max(30,value/1000)
    def backend_playhead(self,value):
        self.clock.setText(tc(value/1000))
        if not self.scrubber.isSliderDown():self.scrubber.setValue(value)
        self.timeline.position=value/1000;self.timeline.update()
        # Indexed/in-memory; no filesystem or selected-engine JSON lookup here.
        cues=self.draft.get('segments',[]) if self.draft else []
        row=next((r for r in cues if r['start']<=value/1000<r['end']),None)
        if self.store.mode=='basic' and row:
            index=cues.index(row)
            if index!=self.cue_index:self.cue_index=index;self.refresh_take()
        self.caption.setText((row.get('text','') if self.take_language.currentData()=='yue' else row.get('english','')) if row else '')
    def play_output(self):
        row=self.store.row()
        if row and Path(row.get('output','')).is_file():self.player.setSource(QUrl.fromLocalFile(row['output']));self.player.play()
        else:self.notice(self.t('This video has no exported file yet. The current status and log show what remains.','呢條影片暫時未有輸出檔案；可喺狀態及紀錄查看未完成步驟。'))
    def backend_refresh_history(self):
        rows=self.snapshot.get('history',[]);selected=self.history.currentRow();self.history.setRowCount(len(rows))
        for i,row in enumerate(rows):
            values=[row.get('index'),dict(ENGINES).get(row.get('engine'),row.get('engine')),row.get('language'),row.get('text'),row.get('reason'),time.strftime('%H:%M:%S',time.localtime(row.get('created',0)))]
            for j,value in enumerate(values):self.history.setItem(i,j,QTableWidgetItem(str(value or '')))
        if 0<=selected<len(rows):self.history.selectRow(selected)
    def selected_history(self):
        i=self.history.currentRow();rows=self.snapshot.get('history',[]);return rows[i] if 0<=i<len(rows) else None
    def play_history(self):
        row=self.selected_history()
        if row:self.play_audio(row['path'])
    def history_edit(self):
        row=self.selected_history()
        if row:self.nav.setCurrentRow(0);self.select_cue(row['index']-1)
    def accept_take(self):
        row=self.selected_history()
        if not row or not self.draft:return
        i=row['index']-1
        if not 0<=i<len(self.draft['segments']):return
        segment=self.draft['segments'][i];text=segment.get('english','') if row['language']=='en' else segment['text']
        try:path,ident=accept_history(self.snapshot['root'],row,text)
        except (ValueError,OSError) as error:self.notice(str(error));return
        segment.update(audioTake=path,audioAcceptedHistoryID=ident);self.dirty=True;self.save_draft();self.report_hint.setText(self.t('Accepted for the next edited export. Previous versions remain intact.','已選作下一個修改版本；先前版本仍然保留。'))
    def refresh_clock(self):
        if self.running:self.refresh_status()
        if self.ui_process.state()!=QProcess.NotRunning and self.setup_started and not self.setup_transfer:self.setup_detail.setText(self.t('Elapsed ','已用 ')+tc(time.monotonic()-self.setup_started)+self.t(' · Installing / loading. This step has no reliable time estimate.',' · 安裝／載入中，此步驟暫時未能準確估時。'))
    def backend_refresh_status(self):
        if not hasattr(self,'basic_title'):return
        row=self.store.row() or {};data=self.snapshot if self.store.selected==row.get('id') else {}
        journey=(row.get('journey') if self.running else data.get('journey') or row.get('journey')) or dict(progress=row.get('progress',0),milestones=[])
        if self.running and self.run_action=='render-project':journey=self.edit_journey or dict(progress=0,milestones=[])
        labels=[self.t(en,zh) for en,zh in [('Prepare','準備'),('Japanese','日語辨識'),('Roles','角色分析'),('Translate','翻譯'),('Dub','配音'),('Repair / QA','修復／核對'),('Export','匯出')]]
        self.expert_journey.set_data(journey,False,labels);self.basic_journey.set_data(journey,True,labels)
        current=next((r['id'] for r in journey.get('milestones',[]) if r.get('state')=='running'),None)
        stage=labels[PHASES.index(current)] if current in PHASES else self.status_name(row.get('status','waiting'))
        title=f'{stage} · {int(journey.get("progress",0)*100)}%';self.status_title.setText(title);self.basic_title.setText(title)
        timing=data.get('time',{});elapsed=time.monotonic()-self.run_started if self.running else timing.get('currentRunSeconds',0)
        total=timing.get('seconds',row.get('processingSeconds',elapsed));time_text=self.t('Total ','累計 ')+tc(total)+'  ·  '+self.t('This run ','本次 ')+tc(elapsed)
        self.status_time.setText(time_text);self.basic_time.setText(time_text)
        detail=row.get('message','') if self.store.language=='zh-HK' else self.t('Automatic production · saved recordings are reused.','自動製作 · 沿用已保存錄音。')
        eta=self.t('Learning processing speed…','正在累積處理速度資料⋯')
        if self.phase_sample:
            key,start,initial,completed,total_work=self.phase_sample;done=completed-initial
            if done>=3:
                remaining=(time.monotonic()-start)/done*max(0,total_work-completed)
                eta=self.t('This step remaining ~','本步驟預計剩餘約 ')+tc(remaining)
                detail+=f' · {completed:g}/{total_work:g}'
        if self.running:detail+=' · '+eta
        self.status_detail.setText(detail);self.basic_detail.setText(detail)
    def show_plan(self):
        if self.ui_process.state()!=QProcess.NotRunning or self.running:return
        args=['--plan','--engine',self.store.settings['ttsBackend']]
        if self.cpu_drama.isChecked():args.append('--allow-cpu-drama')
        self.setup_action='plan';self.begin_setup('check');self.ui_process.launch(sys.executable,'native_setup.py',args,self.root);self.refresh_busy()
    def deploy(self,engine=None):
        if self.ui_process.state()!=QProcess.NotRunning or self.running:return
        args=['--engine',engine if isinstance(engine,str) else self.store.settings['ttsBackend'],'--backend',self.backend.currentData()]
        if self.cpu_drama.isChecked():args.append('--allow-cpu-drama')
        self.setup_action='deploy';self.begin_setup('check');self.ui_process.launch(sys.executable,'native_setup.py',args,self.root);self.refresh_busy()
    def begin_setup(self,step):
        self.setup_started=time.monotonic();self.setup_transfer=None;self.setup_step=step;self.setup_progress.setRange(0,0)
        self.setup_status.setText(self.t('Checking your computer and installed components…','正在檢查電腦及已安裝元件⋯'));self.setup_detail.setText(self.t('Only missing or damaged files will be installed.','只補齊缺少或損壞檔案。'))
    def manage_package(self,row,action):
        if self.ui_process.state()!=QProcess.NotRunning or self.running:return
        if action!='repair':
            title=self.t('Remove local component?','移除本機元件？') if action=='remove' else self.t('Download component again?','重新下載元件？')
            body=row['title']+'\n'+self.t('Videos, saved projects and exports are kept. The selected component must be installed again before use.','影片、專案及成品會保留；所選元件要重新安裝先可以使用。')
            if QMessageBox.question(self,title,body)!=QMessageBox.Yes:return
        args=['--manage',action,'--package',row['id'],'--kind',row['kind'],'--engine',self.store.settings['ttsBackend'],'--backend',self.backend.currentData()]
        self.setup_action='manage';self.begin_setup('check');self.ui_process.launch(sys.executable,'native_setup.py',args,self.root);self.refresh_busy()
    def cleanup_downloads(self,mode):
        launcher=os.environ.get('CANTOSYNC_LAUNCHER_PID','')
        if not launcher.isdigit():
            self.notice(self.t('Open the portable AniCanto.exe to use cleanup after exit.','請由 portable AniCanto.exe 開啟，先可以喺關閉後清理下載。'));return
        if self.running or self.ui_process.state()!=QProcess.NotRunning:
            self.notice(self.t('Pause conversion / setup and wait for it to stop before removing downloads.','請先暫停轉換／部署，等工作停止後先清理下載。'));return
        for button in self.cleanup_buttons:button.setEnabled(False)
        self.storage_label.setText(self.t('Calculating downloaded file sizes…','正在計算已下載檔案大小⋯'))
        def reset():
            for button in self.cleanup_buttons:button.setEnabled(True)
        def done(plan):
            reset();size=f'{plan["bytes"]/1e9:.2f} GB';self.storage_label.setText(self.t('Removable download files: ','可清理下載檔案：')+size)
            if not plan['files']:self.notice(self.t('No downloaded files to remove.','冇需要清理嘅下載檔案。'));return
            scope=self.t('Models, partial downloads and model receipts','模型、未完成下載及模型記錄') if mode=='models' else self.t('Models, runtimes, tools and app download caches','模型、執行環境、工具及應用程式下載快取')
            groups='\n'.join(f'{r["path"]} · {r["bytes"]/1e9:.2f} GB' for r in plan['groups'] if r['bytes']>1000000)
            body=scope+' · '+size+'\n'+groups+'\n\n'+self.t('AniCanto will close, then the portable launcher will remove these files. Videos, projects, recordings, exports and settings are kept. Required components download again next time.','AniCanto 會先關閉，再由 portable 啟動器移除檔案。影片、專案、錄音、成品及設定會保留；下次使用時會重新下載所需元件。')
            if QMessageBox.question(self,self.t('Remove downloaded files & close?','移除下載檔案並關閉？'),body)!=QMessageBox.Yes:return
            # No deletion in a running Python environment. The outer EXE
            # validates this exact plan once the GUI has fully exited.
            self.save_draft();self.store.save();write(self.root/'download-cleanup-request.json',dict(mode=mode,token=plan['token'],launcherPID=int(launcher)));self.close()
        def failed(error):reset();self.storage_label.setText(error);self.notice(error)
        from studio_core import call
        self.background(lambda:call('cleanup-plan',root=str(self.root),mode=mode),done,failed)
    def pause_setup(self):
        if self.ui_process.state()!=QProcess.NotRunning:self.ui_process.kill();self.setup_status.setText(self.t('Download paused. Verified files will be reused on resume.','下載已暫停；續做時會沿用已驗證檔案。'))
    def setup_event(self,event):
        self.log(json.dumps(event,ensure_ascii=False));deployment=event.get('deployment')
        if deployment:
            from setup_inventory import warning
            self.setup_plan=deployment
            downloads=deployment.get('downloads',[])+deployment.get('tools',[]);needed=[r for r in downloads if not r.get('installed')]
            h=deployment.get('hardware',{});ram=h.get('memoryGB',h.get('systemMemoryGB',0));gpu=h.get('acceleratorMemoryGB',0)
            from memory_plan import pools
            memory=deployment.get('memoryPools') or pools(deployment)
            system=memory['system'];accelerator=memory['gpu']
            system_text=self.t('System RAM','系統 RAM')+f" · {system['peak']:.1f} / {system['capacity']:.1f} GB · "+self.t('8 GB+ reserved for Windows','至少預留 8 GB 畀 Windows')
            gpu_name='NVIDIA' if memory['backend']=='cuda' else 'AMD' if memory['backend']=='rocm' else 'GPU'
            gpu_text=(gpu_name+' VRAM'+f" · {accelerator['peak']:.1f} / {accelerator['capacity']:.1f} GB" if memory['dedicated'] else self.t('Integrated GPU / CPU · shared system RAM','內顯／CPU · 共用系統 RAM'))
            for label,bar,value,capacity in ((self.welcome_system_memory,self.welcome_system_bar,system_text,system['capacity']), (self.welcome_gpu_memory,self.welcome_gpu_bar,gpu_text,accelerator['capacity'])):
                label.setText(value)
            for bar,pool in ((self.welcome_system_bar,system),(self.welcome_gpu_bar,accelerator)):
                bar.setValue(round(1000*min(1.,pool['peak']/pool['capacity'])) if pool['capacity'] else 0)
            if hasattr(self,'model_system_memory'):
                self.model_system_memory.setText(system_text);self.model_system_bar.setValue(self.welcome_system_bar.value())
                self.model_gpu_memory.setText(gpu_text);self.model_gpu_bar.setValue(self.welcome_gpu_bar.value())
            lines=[self.t('Voice: ','配音：')+dict(ENGINES).get(deployment.get('engine'),deployment.get('engine','')),
                   self.t('Components to download: ','元件待下載：')+f'{sum(r.get("bytes",0) for r in needed)/1e9:.2f} GB · '+self.t('Reuse ','沿用 ')+str(len(downloads)-len(needed))+self.t(' installed components',' 個已安裝元件'),
                   self.t('Runtimes and tools are additional. Models load one at a time.','另計執行環境及工具；模型會逐個載入。')]
            lines+=[warning(w,self.store.language) for w in deployment.get('warnings',[])]
            if deployment.get('verifiedVoiceBackend'):lines+=[self.t('Verified voice backend: ','已驗證配音執行方式：')+('NVIDIA CUDA' if deployment['verifiedVoiceBackend']=='cuda' else 'CPU')]
            lines+=deployment.get('blockers',[]);text='\n'.join(lines);self.inventory.setPlainText(text);self.models_text.setPlainText(text)
            roles=deployment.get('roles',{});labels=dict(text=self.t('Translation','翻譯'),visual=self.t('Visual roles','畫面角色'),voice=self.t('Dubbing','配音'),speech=self.t('Japanese timing','日語時間'),asr=self.t('Independent ASR','獨立辨識'),referenceSpeech=self.t('References','錄音文字'))
            self.plan_table.setRowCount(len(downloads))
            for i,row in enumerate(downloads):
                purpose=self.t('Music / speech detection (OP/ED)','分辨音樂／對白，輔助偵測 OP／ED') if row.get('purposeKey')=='audio-classification' or 'classifier' in row['id'] else row.get('purpose') or ' / '.join(labels.get(k,k) for k,v in roles.items() if v==row['id']) or self.t('Production component','配音流程元件')
                for j,value in enumerate([purpose,row.get('title',row['id']),f'{row.get("bytes",0)/1e9:.2f} GB',self.t('Reuse','沿用') if row.get('installed') else self.t('Download','下載')]):
                    item=QTableWidgetItem(value);item.setToolTip(value);self.plan_table.setItem(i,j,item)
            self.plan_table.setWordWrap(True);self.plan_table.setTextElideMode(Qt.ElideNone);self.plan_table.resizeRowsToContents()
            self.plan_table.setMaximumHeight(min(230,38+sum(self.plan_table.rowHeight(i) for i in range(len(downloads)))));self.plan_table.show();self.package_table.setRowCount(len(deployment.get('inventory',[])))
            for i,row in enumerate(deployment.get('inventory',[])):
                self.package_table.setItem(i,0,QTableWidgetItem(row['title']));self.package_table.setItem(i,1,QTableWidgetItem(self.t('Installed · reuse','已安裝 · 沿用') if row.get('installed') else self.t('Partial · resume ','未完成 · 可續傳 ')+f'{row["savedBytes"]/1e9:.2f} GB' if row.get('savedBytes') else self.t('Not downloaded','未下載')))
                button=QToolButton();button.setText('⋯');button.setPopupMode(QToolButton.InstantPopup);menu=QMenu(button)
                for action,en,zh in [('repair','Check & repair','檢查及修復'),('redownload','Download again…','重新下載⋯'),('remove','Remove local files…','移除本機檔案⋯')]:menu.addAction(self.t(en,zh),lambda checked=False,r=row,a=action:self.manage_package(r,a))
                button.setMenu(menu);self.package_table.setCellWidget(i,2,button)
        self.setup_status.setText(event.get('message',''))
        if deployment and hasattr(self,'model_table'):self.refresh_model_catalog()
        if event.get('componentProgress'):
            component=event['componentProgress'];fraction=component.get('fraction');self.setup_transfer=None;self.setup_status.setText(component.get('label',''))
            self.setup_progress.setRange(0,1000 if fraction is not None else 0)
            if fraction is not None:self.setup_progress.setValue(round(1000*max(0,min(1,fraction))))
            self.setup_detail.setText(self.t('Loading model… ','正在載入模型⋯ ')+(f'{fraction:.0%}' if fraction is not None else ''))
        if event.get('setupStep'):
            self.setup_disclosure.setChecked(True)
            self.setup_step=event['setupStep'];self.setup_transfer=None;self.setup_progress.setRange(0,1000 if self.setup_step=='ready' else 0)
            if self.setup_step=='ready':self.setup_progress.setValue(1000)
            self.setup_steps.setText(self.t('Current step: ','目前步驟：')+dict(check=self.t('Check installation','檢查安裝'),runtime=self.t('Install runtime','安裝元件'),models=self.t('Download models','下載模型'),verify=self.t('Load & verify models','載入及驗證模型'),ready=self.t('Ready','已就緒')).get(self.setup_step,self.setup_step))
        if event.get('download'):
            self.setup_disclosure.setChecked(True)
            transfer=event['download'];received=transfer.get('receivedBytes',transfer.get('bytesReceived',0));total=transfer.get('totalBytes') or 0;speed=transfer.get('bytesPerSecond') or 0
            state=transfer.get('state','downloading')
            label=dict(verifying=self.t('Verifying saved file','正在校驗已儲存檔案'),reused=self.t('Verified · reused without downloading','已驗證 · 沿用，無需下載'),resuming=self.t('Resuming download','繼續下載'),complete=self.t('File ready','檔案已就緒'),downloading=self.t('Downloading','正在下載')).get(state,state)
            self.setup_transfer=transfer;self.setup_status.setText(label+' · '+transfer.get('file',''))
            self.setup_progress.setRange(0,1000 if total else 0)
            if total:self.setup_progress.setValue(round(1000*min(1,received/total)))
            eta=tc((total-received)/speed) if total and speed>0 else self.t('Estimating…','估算中⋯')
            self.setup_detail.setText(f'{received/1e9:.2f} / {total/1e9:.2f} GB'+(' · '+self.t('Checking SHA-256 locally; no network download.','本機 SHA-256 校驗，並非重新下載。') if state=='verifying' else '' if state in ('reused','complete') else f' · {speed/1e6:.1f} MB/s · '+self.t('Remaining ','剩餘 ')+eta))
        if event.get('modelProgress'):
            part=event['modelProgress'];self.setup_steps.setText(self.t('Model files: ','模型檔案：')+str(part['index'])+' / '+str(part['total'])+' · '+part['title'])
        if event.get('ready'):
            self.setup_transfer=None;self.setup_progress.setRange(0,1000);self.setup_progress.setValue(1000);self.setup_detail.setText(self.t('Verification complete.','已完成驗證。'))
            self.ready=event['ready'];engine=self.ready['engine'];requested=self.ready.get('requestedEngine',engine)
            voice_backend=self.ready.get('voiceBackend')
            if engine=='drama3' and voice_backend:
                self.setup_status.setText(self.t('Ready · Drama 3 · ','已就緒 · Drama 3 · ')+('NVIDIA CUDA' if voice_backend=='cuda' else 'CPU'))
                if self.ready.get('cudaFailure'):self.inventory.appendPlainText(self.t('CUDA test failed; using CPU. Details: ','CUDA 測試未通過，會使用 CPU。原因：')+self.ready['cudaFailure'])
            self.cpu_drama.setChecked(bool(self.ready.get('allowDramaCPU')))
            self.store.settings['nativeDramaCPU']=bool(self.ready.get('allowDramaCPU'))
            if requested!=engine:
                selected=list(dict.fromkeys(engine if e==requested else e for e in self.store.settings['selectedEngines']))
                self.store.settings.update(selectedEngines=selected,ttsBackend=selected[0],defaultAudioEngine=selected[0])
            self.store.save();self.sync_controls()
    def setup_finished(self,code,status):
        self.ready=read(self.root/'native-ready.json',{});self.refresh_busy()
        self.setup_progress.setRange(0,1000);self.setup_progress.setValue(0 if code else 1000)
        self.setup_detail.setText(self.t('Elapsed ','已用 ')+tc(time.monotonic()-self.setup_started))
        if code==0 and self.setup_action=='plan':self.setup_status.setText(self.t('Plan ready. No files were downloaded.','計劃已準備好，未下載任何檔案。'))
        if code:self.setup_status.setText(self.t('Setup did not complete. Details are in Terminal; completed downloads are kept.','部署未完成；詳情喺終端機，已完成下載會保留。'))
        if code==0 and self.setup_action!='plan':
            from native_setup import plan
            message=self.setup_status.text();engine=self.store.settings['ttsBackend'];backend=self.backend.currentData()
            self.background(lambda:plan(engine,backend=backend),lambda deployment:self.setup_event(dict(deployment=deployment,message=message)),self.log)
        if self.pending_launch:
            pending=self.pending_launch;self.pending_launch=None
            if code==0:QTimer.singleShot(100,lambda:self.launch_worker(*pending,repaired=True))
        if self.start_after_setup:
            self.start_after_setup=False
            if code==0 and (self.setup_action!='deploy' or self.ready.get('speechInferencePassed')):QTimer.singleShot(100,self.start_all)
            elif code==0:
                row=self.store.row()
                if row:self.record_preflight_error(row,row.get('request',''),'batch',self.t('Setup ended without verified speech inference. Check the setup log before retrying.','部署結束但未通過配音驗證；請查看部署紀錄。'))
    def backend_refresh_projects(self):
        def scan():
            rows=[]
            for path in (self.root/'jobs').glob('*/review.json'):
                data=read(path,{})
                if data:rows.append((str(path),data.get('config',{}).get('video',path.parent.name)))
            return rows
        def done(rows):
            self.projects.clear()
            for path,video in rows:
                item=QListWidgetItem(Path(video).name);item.setData(Qt.UserRole,path);self.projects.addItem(item)
        self.background(scan,done)
    def open_project(self):
        item=self.projects.currentItem()
        if not item:return
        path=item.data(Qt.UserRole)
        def done(review):
            video=review['config']['video'];self.store.add([video]);row=next(r for r in self.store.queue if r['video']==video);row['review']=path;self.store.selected=row['id'];self.store.save();self.draft=None;self.restore_queue();self.nav.setCurrentRow(0)
        self.background(lambda:read(path,{}),done)
    def open_queue_row(self,index,col):
        if col==3:self.reveal(self.store.queue[index].get('output',self.root/'exports'))
        else:self.queue_list.setCurrentRow(index);self.nav.setCurrentRow(0)
    def backend_log(self,text):
        if not text:return
        if hasattr(self,'terminal'):self.terminal.appendPlainText(str(text))
        folder=self.root/'logs';folder.mkdir(exist_ok=True)
        with (folder/('desktop-'+time.strftime('%Y-%m-%d')+'.log')).open('a',encoding='utf-8') as file:file.write(str(text)+'\n')
    def reveal(self,path):
        path=Path(path)
        if not path.exists() and path.suffix:path=path.parent
        if not path.exists():path.mkdir(parents=True,exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
    def notice(self,text):QMessageBox.information(self,'AniCanto',str(text))
    def close_drawer(self):self.drawer.hide()
    def guide(self):
        self.drawer_title.setText(self.t('Quick guide','使用教學'))
        en='''<h2>Your first dubbed episode</h2><ol><li>On Welcome, choose an interface language and review the hardware-aware model download plan. Deploy once; later launches reuse verified models.</li><li>Enter Basic mode, add one or more videos, choose a voice engine, dubbing languages and output subtitles.</li><li>Press Start waiting videos. The studio recognises Japanese speech, translates, generates voices, repairs failures and exports in sequence.</li><li>Use the milestones to see the current step and its processing time. Pause &amp; save stops owned workers and keeps completed recordings for resume.</li><li>Play the exported video or open the output folder. Each export retains a processing-time record.</li></ol><h3>Expert studio</h3><p>Both modes share the same queue and production settings. Switching views never changes an active job. Select a line in Edit to audition an existing engine/language take, edit its scripts or regenerate it. Use Roles for reference recordings, Review report for previous rejected takes, and Produce for non-destructive clip edits and a new export.</p><p>Japanese audio only ignores OCR and original subtitles for translation. High speed skips quality review and may produce dubbing defects. Incomplete recordings remain available for comparison and cannot replace a complete line.</p><h3>Windows</h3><p>Keep one AniCanto.exe wherever you prefer. Runtimes, models and projects are stored in the local app cache. The model centre shows the actual selected engine; supported GPT fallback is used when native Drama 3 is unavailable. Models run locally after setup.</p>'''
        zh='''<h2>第一次為動畫配音</h2><ol><li>喺首頁選擇介面語言，檢視按本機配置建議嘅模型清單，再一按部署。之後會沿用已驗證模型。</li><li>進入基本模式，加入一條或多條影片，選擇配音引擎、配音語言及輸出字幕。</li><li>撳「開始所有待處理影片」。工作室會依次辨識日語、翻譯、配音、自動修復及匯出。</li><li>關卡會顯示目前步驟同耗時。「暫停並保存」會停止所屬程序，保留完成錄音，方便續做。</li><li>播放成品或開啟成品資料夾。每個成品會保留處理時間紀錄。</li></ol><h3>專家工作室</h3><p>兩個模式共用工作清單同製作設定；切換介面唔會改動進行中工作。喺剪輯頁選擇對白，可以試聽指定引擎／語言錄音、修改台詞或重錄。角色頁可更換參考聲，校對報告可比較未採用錄音，製作匯出頁可非破壞式剪輯並生成新版本。</p><p>「只用日文語音辨識」會略過 OCR 同原裝字幕作為翻譯來源。高速模式會跳過品質檢查，可能有配音缺陷。不完整錄音會保留作比較，但唔可以取代完整對白。</p><h3>Windows</h3><p>只需保留一個 AniCanto.exe；執行環境、模型同專案儲存喺本機快取。模型中心會顯示實際採用嘅引擎；原生 Drama 3 未能使用時會採用支援嘅 GPT 後備引擎。完成部署後模型喺本機執行。</p>'''
        self.drawer_text.setHtml(zh if self.store.language=='zh-HK' else en);self.drawer.show();self.drawer.raise_()
    def about(self):
        self.drawer_title.setText(self.t('About & licences','關於與授權'));self.drawer.show();self.drawer.raise_()
        def load():
            info=read(SHARED/'app-information.json',{});intro=info.get('introduction',{}).get(self.store.language,'')
            body=f'<h1>AniCanto</h1><p>Version {html.escape(self.version)} · Developer: SCKC</p><p>© 2026 SCKC · MIT</p><p>'+html.escape(intro).replace('\n','<br>')+'</p>'
            body+='<h2>'+self.t('Application licence','應用程式授權')+'</h2><pre>'+html.escape((HERE/'LICENSE' if (HERE/'LICENSE').is_file() else HERE.parent/'LICENSE').read_text())+'</pre>'
            body+='<h2>'+self.t('Third-party software & models','第三方軟件與模型')+'</h2>'
            for path in [SHARED/'THIRD-PARTY-NOTICES.txt',SHARED/'MODEL-NOTICES.txt']:
                if path.is_file():body+='<pre style="white-space:pre-wrap">'+html.escape(path.read_text())+'</pre>'
            native=HERE/'NATIVE-NOTICES.txt'
            if native.is_file():body+='<pre style="white-space:pre-wrap">'+html.escape(native.read_text())+'</pre>'
            from native_licenses import inventory
            for row in inventory(self.root):
                body+='<h3>'+html.escape(row['name']+' '+row['version'])+'</h3><p>'+html.escape(row['license'])+'</p><p>'+html.escape(', '.join(row['runtimes']))+'</p>'
                for notice in row['notices']:body+='<pre style="white-space:pre-wrap">'+html.escape(notice['text'])+'</pre>'
            for row in read(SHARED/'core-dependencies.json',[]):
                body+='<h3>'+html.escape(row['name']+' '+row['version'])+'</h3><p>'+html.escape(row['license'])+'</p>'
                for file in row['files']:
                    path=SHARED/file
                    if path.is_file():body+='<pre style="white-space:pre-wrap">'+html.escape(path.read_text())+'</pre>'
            for path in sorted((HERE/'tools/notices').rglob('*')):
                if path.is_file() and path.suffix!='.json':
                    body+='<h3>'+html.escape(str(path.relative_to(HERE/'tools/notices')))+'</h3><pre style="white-space:pre-wrap">'+html.escape(path.read_text())+'</pre>'
            return body
        self.background(load,self.drawer_text.setHtml)
    def closeEvent(self,event):
        try:self.save_draft();self.store.save()
        except (OSError,ValueError) as error:self.log(str(error))
        if self.running:self.pause()
        self.ui_process.kill();self.player.stop();self.audition.stop();self.timer.stop();self.clock_timer.stop()
        # Let QProcess deliver finished before Qt destroys the process objects.
        if self.worker.state()!=QProcess.NotRunning or self.ui_process.state()!=QProcess.NotRunning:
            event.ignore();QTimer.singleShot(150,self.close);return
        self.pool.waitForDone(5000);event.accept()

def main():
    app=QApplication(sys.argv);app.setApplicationName('AniCanto');app.setOrganizationName('SCKC')
    from PySide6.QtCore import QLockFile
    root=data_root();root.mkdir(parents=True,exist_ok=True)
    lock=QLockFile(str(root/'desktop.lock'));lock.setStaleLockTime(0)
    if not lock.tryLock(0):
        QMessageBox.information(None,'AniCanto','AniCanto is already open. / AniCanto 已經開啟。');return 0
    icon=SHARED/'AniCanto-icon.png'
    if icon.is_file():app.setWindowIcon(QIcon(str(icon)))
    app.studio=Studio();app.studio.show();return app.exec()

if __name__=='__main__':sys.exit(main())
