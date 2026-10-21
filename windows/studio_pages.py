"""Mac-aligned embedded studio pages. Controls bind to real shared worker settings."""
import json,copy,time
from pathlib import Path
from PySide6.QtCore import Qt,QSize
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import *
from studio_layout import CONTRACT,SHARED,CommitText
from studio_icons import icon
from desktop_state import ENGINES,read,write
from workflow_settings import COMBINED,validated
class StudioPages:
    def page(self,en,zh,detail=None):
        page=QWidget();v=QVBoxLayout(page);v.setContentsMargins(24,24,24,24);v.setSpacing(18);self.heading(v,en,zh,detail);return page,v
    def field(self,form,key,en,zh,kind='check',default=None,options=None,limits=(0,100),project=False):
        self.generic_controls.setdefault(key,[])
        if kind=='check':
            w=QCheckBox(self.t(en,zh));form.addRow(w);w.toggled.connect(lambda value:self.set_setting(key,value,project))
        elif kind=='choice':
            w=QComboBox()
            for a,b,value in options:w.addItem(self.t(a,b),value)
            form.addRow(self.t(en,zh),w);w.activated.connect(lambda i:self.set_setting(key,w.currentData(),project))
        elif kind=='number':
            w=QDoubleSpinBox();w.setRange(*limits);w.setDecimals(3);w.setSingleStep(.05);form.addRow(self.t(en,zh),w);w.editingFinished.connect(lambda:self.set_setting(key,w.value(),project))
        elif kind=='text':
            w=QLineEdit();form.addRow(self.t(en,zh),w);w.editingFinished.connect(lambda:self.set_setting(key,w.text(),project))
        else:
            w=CommitText();w.setMinimumHeight(100);w.setMaximumHeight(170);form.addRow(self.label(en,zh));form.addRow(w);w.committed.connect(lambda:self.set_setting(key,w.toPlainText(),project))
        if key not in self.store.settings and default is not None:self.store.settings[key]=default
        self.generic_controls[key].append(w);return w
    def build_roles(self):
        page,v=self.page('Roles','角色',('Voice references, portraits and assignments for this episode.','本片嘅參考聲線、角色相片同對白配對。'))
        self.role_cards=QListWidget();self.role_cards.setViewMode(QListWidget.IconMode);self.role_cards.setResizeMode(QListWidget.Adjust);self.role_cards.setGridSize(QSize(175,208));self.role_cards.setSelectionMode(QAbstractItemView.SingleSelection);self.role_cards.currentRowChanged.connect(lambda i:self.roles.selectRow(i));v.addWidget(self.role_cards,2)
        self.roles=QTableWidget(0,4);self.roles.setHorizontalHeaderLabels(['ID',self.t('Name','名稱'),self.t('Reference recording','參考錄音'),self.t('Reference transcript','參考台詞')]);self.roles.horizontalHeader().setSectionResizeMode(2,QHeaderView.Stretch);self.roles.horizontalHeader().setSectionResizeMode(3,QHeaderView.Stretch);self.roles.itemChanged.connect(self.role_changed);self.roles.setMaximumHeight(180);v.addWidget(self.roles)
        row=QHBoxLayout();self.button('Audition reference','試聽參考聲',self.play_reference,row);self.button('Replace reference…','更換參考錄音⋯',self.replace_reference,row);self.button('New role','新增角色',self.add_role,row);self.button('Merge roles','合併角色',self.merge_roles,row);self.button('Save','儲存',self.save_draft,row);row.addStretch();v.addLayout(row);self.enhance_roles(page,v);self.pages.addWidget(page)
    def refresh_role_cards(self):
        if not hasattr(self,'role_cards'):return
        selected=self.role_cards.currentRow();self.role_cards.clear()
        profiles=self.draft['settings'].get('voiceProfiles',[]) if self.draft else self.snapshot.get('roles',[])
        for row in profiles:
            item=QListWidgetItem(row.get('name',row['id'])+'\n'+row['id']);item.setSizeHint(QSize(165,195))
            image=next((row.get(k) for k in ('avatar','sourceFrame','image','portrait','thumbnail') if row.get(k) and Path(str(row[k])).is_file()),None)
            if image:item.setIcon(__import__('PySide6.QtGui',fromlist=['QIcon']).QIcon(str(image)))
            else:item.setIcon(icon('roles',self.accent,72))
            self.role_cards.addItem(item)
        self.role_cards.setIconSize(QSize(130,140))
        if profiles:self.role_cards.setCurrentRow(max(0,min(selected,len(profiles)-1)))
        self.refresh_role_tools()
    def add_role(self):
        if not self.draft:return
        name,ok=QInputDialog.getText(self,self.t('New role','新增角色'),self.t('Name','名稱'))
        if ok and name.strip():
            import uuid
            self.checkpoint_edit();self.draft['settings'].setdefault('voiceProfiles',[]).append(dict(id='role-'+uuid.uuid4().hex[:8],name=name.strip(),reference='',promptText=''));self.dirty=True;self.populate_editor()
    def merge_roles(self):
        if not self.draft:return
        profiles=self.draft['settings'].get('voiceProfiles',[]);i=self.roles.currentRow()
        if not 0<=i<len(profiles):return
        target,ok=QInputDialog.getItem(self,self.t('Merge role','合併角色'),self.t('Target role','目標角色'),[r['id']+' · '+r.get('name','') for j,r in enumerate(profiles) if j!=i],0,False)
        if ok:
            old=profiles[i]['id'];new=target.split(' · ')[0];self.checkpoint_edit()
            for cue in self.draft['segments']:
                if cue.get('speakerId')==old:cue['speakerId']=new;cue.pop('audioTake',None)
            del profiles[i];self.dirty=True;self.populate_editor()
    def build_review(self):
        page,v=self.page('Review report','校對報告',('Compare rejected recordings before accepting a complete take.','比較未採用嘅錄音，再決定係咪採用完整版本。'))
        filterrow=QHBoxLayout();filterrow.addWidget(self.label('Issue filter','問題篩選'));self.issue_filter=QComboBox()
        for en,zh,value in [('All','全部','all'),('Generation failures','生成失敗','failed'),('Needs review','待覆核','review'),('Repaired','已補聲','repaired')]:self.issue_filter.addItem(self.t(en,zh),value)
        self.issue_filter.currentIndexChanged.connect(self.refresh_history);filterrow.addWidget(self.issue_filter);self.issue_search=QLineEdit();self.issue_search.setPlaceholderText(self.t('Find words, engine or reason','搜尋台詞、引擎或原因'));self.issue_search.textChanged.connect(self.refresh_history);filterrow.addWidget(self.issue_search,1);v.addLayout(filterrow)
        self.history=QTableWidget(0,6);self.history.setHorizontalHeaderLabels([self.t('Line','對白'),self.t('Engine','引擎'),self.t('Language','語言'),self.t('Words','台詞'),self.t('Reason','原因'),self.t('Created','時間')]);self.history.horizontalHeader().setSectionResizeMode(3,QHeaderView.Stretch);self.history.horizontalHeader().setSectionResizeMode(4,QHeaderView.Stretch);self.history.setSelectionBehavior(QAbstractItemView.SelectRows);self.history.setEditTriggers(QAbstractItemView.NoEditTriggers);v.addWidget(self.history,1)
        row=QHBoxLayout();self.report_hint=self.label('Rejected takes remain available after regeneration.','重錄後仍可比較先前未採用錄音。',True);row.addWidget(self.report_hint,1);self.button('Audition rejected take','試聽未採用錄音',self.play_history,row);self.button('Accept complete take','採用完整錄音',self.accept_take,row);self.button('Edit / retake','編輯／重錄',self.history_edit,row);v.addLayout(row)
        self.report_text=QTextBrowser();self.report_text.setMaximumHeight(170);v.addWidget(self.report_text);self.pages.addWidget(page)
    def build_produce(self):
        page,v=self.page('Produce and export','製作與匯出',('Reuse saved scripts, voice references and timing. Each submission creates a separate version.','沿用已保存原文、角色及時間；每次提交建立獨立版本。'))
        form=QFormLayout();self.produce_operation=QComboBox()
        for en,zh,k in [('Dubbing','配音','voice'),('Subtitles','字幕','subtitles'),('Voice samples','試音','samples')]:self.produce_operation.addItem(self.t(en,zh),k)
        form.addRow(self.t('Production item','製作項目'),self.produce_operation);self.script_revision=QComboBox();self.script_revision.addItem(self.t('Fill missing subtitles','補齊欠缺字幕'),'missing');self.script_revision.addItem(self.t('Regenerate all subtitles','重譯全部字幕'),'all');form.addRow(self.t('Subtitle handling','字幕處理'),self.script_revision);self.force_regenerate=QCheckBox(self.t('Regenerate every selected voice track','所選音軌全部重新配音'));form.addRow(self.force_regenerate);self.reanalyze_roles=QCheckBox(self.t('Reanalyse roles before export','匯出前重新分析人物'));form.addRow(self.reanalyze_roles)
        self.field(form,'aiAutoFix','Automatically repair selected voice tracks','自動修復所選音軌',default=True);self.field(form,'captionSize','Subtitle size (video-height fraction)','字幕大小（畫面高度比例）','number',.043,limits=(.015,.12),project=True);self.field(form,'captionBottom','Subtitle bottom margin','字幕下方邊距','number',.045,limits=(0,.8),project=True);self.field(form,'burnOutputCaptions','Burn captions into the video','燒入字幕到影片',default=False);v.addLayout(form)
        v.addWidget(self.label('Non-destructive clips','非破壞式剪輯'));self.clips=QTableWidget(0,4);self.clips.setHorizontalHeaderLabels([self.t('Start','開始'),self.t('End','結束'),self.t('Enabled','保留'),self.t('Ripple','收緊時間線')]);self.clips.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);self.clips.setMaximumHeight(180);v.addWidget(self.clips)
        self.cut_placeholder.addWidget(self.clips) # One real clip editor is also visible in Picture inspector.
        row=QHBoxLayout();self.button('Add clip','加入片段',lambda:self.add_clip(),row);self.button('Remove clip','移除片段',lambda:self.clips.removeRow(self.clips.currentRow()),row);self.button('Clip settings','剪接設定',lambda:(self.nav.setCurrentRow(0),self.inspector_tabs.setCurrentIndex(2)),row);self.button('Export new version','匯出新版',self.export_edit,row,True);self.button('Open output folder','開啟成品資料夾',lambda:self.reveal(self.root/'exports'),row);v.addLayout(row)
        self.produce_result=QTextBrowser();v.addWidget(self.produce_result,1);self.pages.addWidget(self.scroll(page))
    def build_terminal(self):
        page,v=self.page('Terminal','終端機');row=QHBoxLayout();self.terminal_filter=QLineEdit();self.terminal_filter.setPlaceholderText(self.t('Search log','搜尋紀錄'));self.terminal_filter.textChanged.connect(self.filter_terminal);row.addWidget(self.terminal_filter,1);self.terminal_errors=QCheckBox(self.t('Errors only','只顯示錯誤'));self.terminal_errors.toggled.connect(self.filter_terminal);row.addWidget(self.terminal_errors);self.button('Copy all','複製全部',lambda:QApplication.clipboard().setText('\n'.join(self.terminal_lines)),row);self.button('Log folder','紀錄資料夾',lambda:self.reveal(self.root/'logs'),row);v.addLayout(row);self.terminal=QPlainTextEdit();self.terminal.setReadOnly(True);self.terminal.setMaximumBlockCount(4000);self.terminal_lines=[];v.addWidget(self.terminal,1);self.pages.addWidget(page)
    def filter_terminal(self,*unused):
        if not hasattr(self,'terminal_lines'):return
        key=self.terminal_filter.text().lower();errors=self.terminal_errors.isChecked();rows=[r for r in self.terminal_lines if (not key or key in r.lower()) and (not errors or any(s in r.lower() for s in ('error','failed','traceback','錯誤','失敗','缺聲')))];self.terminal.setPlainText('\n'.join(rows[-4000:]));self.terminal.verticalScrollBar().setValue(self.terminal.verticalScrollBar().maximum())
    def build_defaults(self):
        page=QWidget();v=QVBoxLayout(page);v.setContentsMargins(0,0,0,0);head=QHBoxLayout();head.setContentsMargins(24,20,24,20);title=self.label('Production defaults','製作預設');title.setObjectName('heading');head.addWidget(title);head.addStretch();head.addWidget(self.label('Shared by single videos and batches','單片與批量共用',True));v.addLayout(head)
        body=QHBoxLayout();self.default_categories=QListWidget();self.default_categories.setObjectName('categorySide');self.default_categories.setFixedWidth(240);self.default_stack=QStackedWidget();body.addWidget(self.default_categories);body.addWidget(self.default_stack,1)
        for key,en,zh in CONTRACT['defaults']:
            self.default_categories.addItem(self.t(en,zh));p=QWidget();pv=QVBoxLayout(p);pv.setContentsMargins(28,24,28,24);self.heading(pv,en,zh);form=QFormLayout();form.setVerticalSpacing(16);self.default_fields(key,form,pv);pv.addLayout(form);pv.addStretch();self.default_stack.addWidget(self.scroll(p))
        self.default_categories.currentRowChanged.connect(self.default_stack.setCurrentIndex);self.default_categories.setCurrentRow(0);v.addLayout(body,1);foot=QHBoxLayout();foot.setContentsMargins(16,12,16,12);self.button('Save production preset','儲存製作預設',self.save_preset,foot);foot.addWidget(self.label('Changes apply to videos started afterwards.','改動會套用至之後開始嘅影片。',True),1);self.button('Load preset…','載入預設⋯',self.load_preset,foot);v.addLayout(foot);self.pages.addWidget(page)
    def default_fields(self,key,f,v):
        check=lambda k,en,zh,d=False:self.field(f,k,en,zh,default=d)
        choice=lambda k,en,zh,options,d=None:self.field(f,k,en,zh,'choice',d,options=options)
        if key=='general':
            choice('productionMode','Production mode','製作模式',[('Standard','標準','standard'),('High speed','高速','fast')],'standard');choice('limit','Range','處理範圍',[('60 sec','60 秒',60),('3 min','3 分鐘',180),('Full video','全片',0)],0);self.field(f,'startOffset','Start seconds','開始秒數','number',0,limits=(0,86400));choice('translationSource','Translation source','翻譯來源',[('Japanese + subtitles','日語＋字幕',COMBINED),('Japanese audio only','只用日文辨識','audio-only')],COMBINED);check('batchAutoSubtitles','Select subtitles automatically per video','逐片自動選字幕',True);check('autoSkipOP','Detect openings and endings','偵測片頭及片尾',True);check('translateOPED','Translate dialogue in OP / ED','翻譯 OP／ED 對白',False)
        elif key=='voices':
            choice('ttsBackend','Default engine','預設引擎',[(t,t,k) for k,t in ENGINES],'drama3');check('includeOriginal','Keep Japanese original track','保留日文原聲音軌',True);self.field(f,'gsvDevice','GPT inference device','GPT 運行裝置','choice','auto',options=[('Automatic','自動','auto'),('CPU','CPU','cpu'),('CUDA (verified)','CUDA（已驗證）','cuda')]);self.field(f,'voxcpmDevice','VoxCPM device','VoxCPM 裝置','choice','auto',options=[('Automatic','自動','auto'),('CPU','CPU','cpu'),('CUDA','CUDA','cuda')]);self.button('Open model centre','開啟模型中心',lambda:self.nav.setCurrentRow(7),v)
        elif key=='models':
            v.addWidget(self.label('Installed model variants and active roles are managed in Model centre.','喺模型中心選用已下載模型及配音版本。',True));self.button('Open active models','開啟模型選用',lambda:self.nav.setCurrentRow(7),v)
        elif key=='subtitles':
            choice('subtitleSource','Subtitle source','字幕來源',[('Embedded tracks','內置字幕軌','embedded'),('Screen OCR','畫面 OCR','burned'),('External file','外掛字幕','external'),('Japanese audio','日語語音辨識','none')],'embedded');check('translate','Use local AI translation','使用本機 AI 翻譯',True);choice('ocrColor','OCR colour','OCR 字色',[('Original','原色','original'),('White','白色','white'),('Yellow','黃色','yellow')],'original');check('ocrStable','Ignore one-frame OCR detections','忽略單一取樣畫面文字',True);self.button('Select subtitle area','框選字幕',self.select_ocr_region,v)
        elif key=='roles':
            check('autoSpeakers','Automatically match characters','自動配對角色',True);choice('roleAnalysisMode','Role analysis','角色分析',[('Audio groups (default)','聲音分組（預設）','audio'),('Per-line voice reference','逐句聲音模仿','independent')],'audio');check('visualRoleAnalysisEnabled','Visual role analysis (slow; off by default)','影像角色分析（較慢，預設關閉）',False);v.addWidget(self.label('Expert option: samples every dialogue and compares portraits. Automatic dubbing does not require it.','專家選項：逐段分析畫面及比對角色；自動配音唔需要啟用。',True));choice('voiceStyleMode','Voice style','聲線方式',[('Clone original','模仿原聲','clone'),('Role voice','角色聲線','role')],'clone');check('autoFit','Fit to Japanese speech length','跟日語長度調整語速',True);check('allowCrossEngineRepair','Allow selected engines to repair each other','允許已選引擎互相補聲');check('separateBackground','Separate original dialogue and music','分離日語對白及音樂',True);self.field(f,'backgroundGain','Background level','背景音量','number',1,limits=(0,1.5));check('backgroundDucking','Lower background while speaking','講嘢時降低背景音',True);self.field(f,'pronunciationText','Pronunciation dictionary','讀音字典','multiline','');self.field(f,'cantonesePronunciationText','Hong Kong Cantonese Jyutping corrections','香港廣東話粵拼修正','multiline','')
        else:
            check('autoApprove','Approve subtitles automatically','自動批核字幕',True);check('aiAutoFix','Automatically repair selected tracks','自動修復所選音軌',True);check('continueOnError','Keep completed work and continue','保留完成工作並繼續',True);self.field(f,'exportFolder','Output folder (blank uses app exports)','輸出資料夾（留空用本機成品）','text','');check('burnOutputCaptions','Burn subtitles into video','燒入字幕',False)
    def save_preset(self):
        file,_=QFileDialog.getSaveFileName(self,self.t('Save production preset','儲存製作預設'),str(self.root/'production-preset.json'),'JSON (*.json)')
        if file:write(file,dict(schemaVersion=1,settings=self.store.settings))
    def load_preset(self):
        file,_=QFileDialog.getOpenFileName(self,self.t('Load production preset','載入製作預設'),'','JSON (*.json)')
        if not file:return
        obj=read(file,{})
        if not isinstance(obj.get('settings'),dict):self.notice(self.t('Invalid preset','無效預設'));return
        settings=copy.deepcopy(obj['settings']);settings.pop('storage',None);settings.pop('video',None)
        if any(k not in dict(ENGINES) for k in settings.get('selectedEngines',[])):self.notice(self.t('Unknown voice engine','未知配音引擎'));return
        try:settings=validated(settings)
        except ValueError as error:self.notice(str(error));return
        self.store.settings.update(settings);self.store.save();self.sync_controls();self.sync_generic()
    def build_models(self):
        page=QWidget();h=QHBoxLayout(page);h.setContentsMargins(0,0,0,0);self.model_categories=QListWidget();self.model_categories.setObjectName('categorySide');self.model_categories.setFixedWidth(220)
        for key,en,zh in CONTRACT['modelCategories']:self.model_categories.addItem(self.t(en,zh))
        h.addWidget(self.model_categories);right=QWidget();v=QVBoxLayout(right);v.setContentsMargins(24,24,24,24);self.heading(v,'Model centre','模型中心');self.models_text=QPlainTextEdit();self.models_text.setReadOnly(True);self.models_text.setMaximumHeight(140);v.addWidget(self.models_text)
        self.model_system_memory=self.label('System RAM · checking…','系統 RAM · 正在檢查…',True);v.addWidget(self.model_system_memory)
        self.model_system_bar=QProgressBar();self.model_system_bar.setRange(0,1000);self.model_system_bar.setValue(0);self.model_system_bar.setTextVisible(False);v.addWidget(self.model_system_bar)
        self.model_gpu_memory=self.label('GPU VRAM · checking…','GPU VRAM · 正在檢查…',True);v.addWidget(self.model_gpu_memory)
        self.model_gpu_bar=QProgressBar();self.model_gpu_bar.setRange(0,1000);self.model_gpu_bar.setValue(0);self.model_gpu_bar.setTextVisible(False);v.addWidget(self.model_gpu_bar)
        self.model_table=QTableWidget(0,5);self.model_table.setHorizontalHeaderLabels([self.t('Model','模型'),self.t('Size','大小'),self.t('Status','狀態'),self.t('Use','選用'),self.t('Manage','管理')]);self.model_table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch);self.model_table.setEditTriggers(QAbstractItemView.NoEditTriggers);v.addWidget(self.model_table,1);self.model_categories.currentRowChanged.connect(self.refresh_model_catalog)
        row=QHBoxLayout();self.backend=QComboBox()
        for en,zh,key in [('Automatic','自動','auto'),('NVIDIA CUDA','NVIDIA CUDA','nvidia'),('AMD ROCm (supported GPUs)','AMD ROCm（支援型號）','amd'),('CPU','CPU','cpu')]:self.backend.addItem(self.t(en,zh),key)
        row.addWidget(self.backend);self.cpu_drama=QCheckBox(self.t('Full Drama 3 on CPU (large / slow)','完整 Drama 3 用 CPU（較大／慢）'));self.cpu_drama.setChecked(self.store.settings.get('nativeDramaCPU',False));row.addWidget(self.cpu_drama);v.addLayout(row);buttons=QHBoxLayout();self.button('Review download plan','檢視下載清單',self.show_plan,buttons);self.button('Deploy selected engine','部署所選引擎',self.deploy,buttons,True);self.button('Pause download','暫停下載',self.pause_setup,buttons);v.addLayout(buttons);h.addWidget(right,1);self.pages.addWidget(page);self.model_categories.setCurrentRow(0)
    def refresh_model_catalog(self,*unused):
        from native_setup import catalog,complete
        category=CONTRACT['modelCategories'][max(0,self.model_categories.currentRow())][0];rows=[r for r in catalog() if r.get('nativeFormat') and (category=='presets' or r.get('category')==dict(voices='voice',text='text',speech='speech',audio='classifier').get(category))]
        if category=='speech':rows=[r for r in catalog() if r.get('nativeFormat') and r.get('category') in ('speech','asr')]
        if category=='runtime':
            from setup_inventory import RUNTIMES
            rows=[dict(id=name,title=name+' runtime',kind='runtime') for name in RUNTIMES]
            self.model_table.setRowCount(len(rows))
            for i,row in enumerate(rows):
                installed=(self.root/'runtimes'/row['id']/'Scripts/python.exe').is_file()
                for c,value in enumerate([row['title'],'—',self.t('Installed','已安裝') if installed else self.t('Not installed','未安裝')]):self.model_table.setItem(i,c,QTableWidgetItem(value))
                self.model_table.setCellWidget(i,3,QLabel(''))
                b=QToolButton();b.setText('⋯');menu=QMenu(b)
                for action,en,zh in [('repair','Check / install','檢查／安裝'),('redownload','Download again','重新下載'),('remove','Remove files','移除檔案')]:menu.addAction(self.t(en,zh),lambda checked=False,r=row,a=action:self.manage_package(r,a))
                b.setMenu(menu);b.setPopupMode(QToolButton.InstantPopup);self.model_table.setCellWidget(i,4,b)
            return
        self.model_table.setRowCount(len(rows));selected=read(self.root/'model-selections.json',{})
        from memory_plan import fit_model
        hardware=self.setup_plan.get('hardware',{})
        for i,row in enumerate(rows):
            ready=complete(self.root,row);role=dict(voice='voice',text='text',speech='speech',asr='asr').get(row.get('category'))
            fits,pool=fit_model(row,hardware) if hardware else (False,'unknown-memory')
            status=self.t('Installed','已安裝') if ready else self.t('Not downloaded','未下載')
            if hardware and not fits:status+=' · '+(self.t('NVIDIA required','需要 NVIDIA') if pool=='requires-nvidia' else self.t('Memory too low','記憶體不足') if pool in ('system','gpu') else self.t('Unavailable','未能使用'))
            for c,value in enumerate([row['title'],f'{row["bytes"]/1e9:.2f} GB · {row.get("estimatedMemoryGB",0):g} GB '+('RAM' if pool=='system' else 'VRAM' if pool=='gpu' else ''),status]):self.model_table.setItem(i,c,QTableWidgetItem(value))
            use=self.button('Selected' if role and selected.get(role)==row['id'] else 'Use','已選用' if role and selected.get(role)==row['id'] else '選用',lambda checked=False,r=row:self.activate_model(r));use.setEnabled(ready and role is not None and fits);self.model_table.setCellWidget(i,3,use)
            menu=QToolButton();menu.setText('⋯');popup=QMenu(menu)
            for action,en,zh in [('repair','Check / install','檢查／安裝'),('redownload','Download again','重新下載'),('remove','Remove files','移除檔案')]:popup.addAction(self.t(en,zh),lambda checked=False,r=row,a=action:self.manage_package(dict(r,kind='model'),a))
            menu.setMenu(popup);menu.setPopupMode(QToolButton.InstantPopup);self.model_table.setCellWidget(i,4,menu)
    def activate_model(self,row):
        selected=read(self.root/'model-selections.json',{});role=dict(voice='voice',text='text',speech='speech',asr='asr').get(row.get('category'))
        from memory_plan import fit_model
        fits,pool=fit_model(row,self.setup_plan.get('hardware',{}))
        if not fits:
            self.notice(self.t('This model cannot fit the selected device. Review system RAM and GPU VRAM first.','呢個模型唔適合目前裝置；請先檢查系統 RAM 同 GPU VRAM。'));return
        if role:
            selected[role]=row['id'];write(self.root/'model-selections.json',selected)
            if role=='voice':
                engine=row['engine'];self.store.settings.update(ttsBackend=engine,selectedEngines=[engine],defaultAudioEngine=engine,nativeDramaCPU=row['id']=='drama3-native-q2')
                self.cpu_drama.setChecked(row['id']=='drama3-native-q2');self.store.save();self.sync_controls()
            self.ready={};write(self.root/'setup-invalidated.json',dict(reason='model-selection-changed'));self.refresh_model_catalog();self.show_plan()
    def build_preferences(self):
        page,v=self.page('Preferences','偏好設定');form=QFormLayout();self.field(form,'appearance','Appearance','外觀','choice','system',options=[('System','跟隨系統','system'),('Light','淺色','light'),('Dark','深色','dark')]);self.field(form,'controlDensity','Control size','控制項大小','choice','comfortable',options=[('Comfortable · 15 px','舒適 · 15 px','comfortable'),('Larger · 17 px','較大 · 17 px','large')]);self.field(form,'animeTheme','Companion theme','助手主題','choice',self.cover_path.stem.replace('welcome-',''),options=[(k.title(),k.title(),k) for k in CONTRACT['themes']]);self.field(form,'showStudioCompanion','Show animated companion','顯示動畫助手',default=False);self.field(form,'companionMotion','Animate companion','角色動態效果',default=True);self.field(form,'desktopPetRoaming','Roam on desktop','桌面自由走動',default=False);v.addLayout(form);self.button('Interface language and Welcome','介面語言與首頁',self.welcome,v);self.button('Open app data folder','開啟資料資料夾',lambda:self.reveal(self.root),v);self.button('About and licences','關於與授權',self.about,v);v.addStretch();self.pages.addWidget(self.scroll(page))
    def build_projects(self):
        page,v=self.page('Projects and exports','專案／成品管理',('Projects contain scripts and recordings. Exported movies are kept separately.','專案包含台詞同錄音；成品影片另外保存。'))
        self.project_tabs=QTabWidget();projects=QWidget();pl=QVBoxLayout(projects);self.projects=QListWidget();pl.addWidget(self.projects,1);pr=QHBoxLayout();self.button('Open project','開啟專案',self.open_project,pr);self.button('Delete project, keep exports','刪除專案，保留成品',self.delete_project,pr);self.button('Refresh','重新整理',self.refresh_projects,pr);pl.addLayout(pr);self.project_tabs.addTab(projects,self.t('Projects','專案'));exports=QWidget();el=QVBoxLayout(exports);self.exports_list=QListWidget();el.addWidget(self.exports_list,1);er=QHBoxLayout();self.button('Play','播放',self.play_export_selection,er);self.button('Show file','顯示檔案',self.reveal_export_selection,er);self.button('Delete selected export…','刪除所選成品⋯',self.delete_export_selection,er);el.addLayout(er);self.project_tabs.addTab(exports,self.t('Exported MP4s','輸出 MP4'));v.addWidget(self.project_tabs,1);row=QHBoxLayout();self.button('Open output folder','開啟成品資料夾',lambda:self.reveal(self.root/'exports'),row);self.button('Delete all projects, keep exports…','刪除全部專案，保留成品⋯',self.delete_all_projects,row);v.addLayout(row);self.pages.addWidget(page)
    def refresh_projects(self):
        self.backend_refresh_projects()
        if hasattr(self,'exports_list'):
            self.exports_list.clear()
            for file in sorted((self.root/'exports').glob('*.mp4')):
                item=QListWidgetItem(file.name);item.setData(Qt.UserRole,str(file));self.exports_list.addItem(item)
    def play_export_selection(self):
        item=self.exports_list.currentItem()
        if item:self.player.setSource(__import__('PySide6.QtCore',fromlist=['QUrl']).QUrl.fromLocalFile(item.data(Qt.UserRole)));self.set_mode('basic');self.shell.setCurrentIndex(1);self.player.play()
    def reveal_export_selection(self):
        if self.exports_list.currentItem():self.reveal(self.exports_list.currentItem().data(Qt.UserRole))
    def delete_export_selection(self):
        item=self.exports_list.currentItem()
        if not item:return
        path=Path(item.data(Qt.UserRole))
        if QMessageBox.question(self,'AniCanto',self.t('Delete this exported movie? Original videos and projects are kept.','刪除呢個成品？原片同專案會保留。'))!=QMessageBox.Yes:return
        if path.parent.resolve()!=(self.root/'exports').resolve():return
        path.unlink();self.refresh_projects()
    def delete_project(self):
        item=self.projects.currentItem()
        if not item:return
        review=item.data(Qt.UserRole)
        for i,row in enumerate(self.store.queue):
            if row.get('review')==review:self.queue_list.setCurrentRow(i);self.remove_video();return
        self.notice(self.t('Open this project first, then remove it from the video list.','請先開啟專案，再喺影片清單移除。'))
    def delete_all_projects(self):
        if self.running:return
        if QMessageBox.question(self,'AniCanto',self.t('Delete all project processing data? Source videos, models and exports are kept.','刪除全部專案處理資料？原片、模型及成品會保留。'))!=QMessageBox.Yes:return
        from desktop_cleanup import remove
        rows=copy.deepcopy(self.store.queue)
        def work():
            known={r.get('review') for r in rows}
            for review in (self.root/'jobs').glob('*/review.json'):
                if str(review) not in known:
                    config=read(review,{}).get('config',{})
                    if config.get('video'):rows.append(dict(review=str(review),video=config['video']))
            for row in rows:remove(self.root,row)
        def done(_):self.store.queue=[];self.store.selected=None;self.store.save();self.draft=None;self.snapshot={};self.restore_queue();self.refresh_projects()
        self.background(work,done,self.notice)
