"""Role album, staged assignments and source portraits use stable cue identities."""
import copy,uuid
from pathlib import Path
from PySide6.QtCore import Qt,QSize
from PySide6.QtGui import QIcon,QPixmap
from PySide6.QtWidgets import *
from desktop_state import write,read
from studio_regions import RegionCanvas
class StudioRoleTools:
    def enhance_roles(self,page,layout):
        self.role_changes={};self.role_tabs=QTabWidget();album=QWidget();a=QHBoxLayout(album);a.setContentsMargins(0,0,0,0);layout.removeWidget(self.role_cards);a.addWidget(self.role_cards,1)
        detail=QWidget();detail.setMaximumWidth(270);dv=QVBoxLayout(detail);self.role_image=QLabel();self.role_image.setMinimumHeight(180);self.role_image.setAlignment(Qt.AlignCenter);dv.addWidget(self.role_image);self.role_detail=self.label('Select a role to view its references.','選擇角色查看相片及參考聲。',True);dv.addWidget(self.role_detail);self.button('Use current video frame…','使用目前影片畫面⋯',self.capture_role_portrait,dv);self.button('Choose portrait…','選擇角色相片⋯',self.choose_role_portrait,dv);self.button('Remove cover','移除封面',self.clear_role_portrait,dv);dv.addStretch();a.addWidget(detail);self.role_tabs.addTab(album,self.t('Role album','角色總覽'))
        match=QWidget();mv=QVBoxLayout(match);self.role_assignments=QTableWidget(0,4);self.role_assignments.setHorizontalHeaderLabels([self.t('Time','時間'),self.t('Japanese','日文'),self.t('Dubbed dialogue','配音台詞'),self.t('Role','角色')]);self.role_assignments.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch);self.role_assignments.horizontalHeader().setSectionResizeMode(2,QHeaderView.Stretch);self.role_assignments.setSelectionBehavior(QAbstractItemView.SelectRows);self.role_assignments.cellDoubleClicked.connect(lambda i,c:(self.nav.setCurrentRow(0),self.select_cue(i)));mv.addWidget(self.role_assignments,1);mr=QHBoxLayout();mr.addWidget(self.label('Assignments are staged until you apply them. Previous exports are kept.','配對改動會暫存，套用後先更新草稿；保留先前成品。',True),1);self.button('Cancel changes','取消修改',self.cancel_role_assignments,mr);self.commit_roles=self.button('Apply assignments','套用角色修改',self.commit_role_assignments,mr,True);mv.addLayout(mr);self.role_tabs.addTab(match,self.t('Matching and changes','配對與修改'))
        gallery=QWidget();gv=QVBoxLayout(gallery);gv.addWidget(self.label('Observed character portraits are appearance references, not proof of who is speaking.','全片頭像只供外觀參考，唔代表已確認講者身份。',True));self.observations=QListWidget();self.observations.setViewMode(QListWidget.IconMode);self.observations.setResizeMode(QListWidget.Adjust);self.observations.setIconSize(QSize(130,140));self.observations.setGridSize(QSize(170,195));gv.addWidget(self.observations,1);self.button('Use selected portrait for current role','所選頭像設為目前角色封面',self.use_observed_portrait,gv);self.role_tabs.addTab(gallery,self.t('Source portraits','畫面素材庫'));layout.insertWidget(2,self.role_tabs,2);self.role_cards.currentRowChanged.connect(self.role_detail_changed)
    def role_detail_changed(self,index):
        profiles=self.draft['settings'].get('voiceProfiles',[]) if self.draft else []
        if not 0<=index<len(profiles):self.role_detail.setText(self.t('Select a role','請選擇角色'));self.role_image.clear();return
        row=profiles[index];image=QPixmap(str(row.get('avatar') or row.get('sourceFrame') or ''));self.role_image.setPixmap(image.scaled(240,220,Qt.KeepAspectRatio,Qt.SmoothTransformation) if not image.isNull() else QPixmap());count=sum(r.get('speakerId')==row['id'] for r in self.draft['segments']);self.role_detail.setText(row.get('name',row['id'])+'\n'+str(count)+self.t(' lines',' 句對白')+'\n'+row.get('promptText',''))
    def refresh_role_tools(self):
        if not hasattr(self,'role_assignments'):return
        segments=self.draft.get('segments',[]) if self.draft else [];profiles=self.draft['settings'].get('voiceProfiles',[]) if self.draft else []
        self.role_assignments.setRowCount(len(segments))
        for i,row in enumerate(segments):
            for c,value in enumerate([self.timecode(row['start']),row.get('original',''),row.get('text','')]):
                item=QTableWidgetItem(value);item.setFlags(item.flags()&~Qt.ItemIsEditable);self.role_assignments.setItem(i,c,item)
            combo=QComboBox();combo.addItem(self.t('Unassigned','未指定'),'')
            for role in profiles:combo.addItem(role.get('name',role['id']),role['id'])
            combo.setCurrentIndex(max(0,combo.findData(self.role_changes.get(row['id'],row.get('speakerId','')))));combo.activated.connect(lambda index,r=row,w=combo:self.stage_role(r['id'],w.currentData()));self.role_assignments.setCellWidget(i,3,combo)
        self.observations.clear();self.observed_rows=[r for entry in self.snapshot.get('portraitAtlas',{}).get('gallery',[]) for r in entry.get('observations',[])]
        for row in self.observed_rows:
            item=QListWidgetItem(row.get('visualId','')+' · '+self.timecode(row.get('time',0)));item.setIcon(QIcon(row.get('avatar','')));self.observations.addItem(item)
        for i in range(self.roles.rowCount()):
            if self.roles.item(i,0):self.roles.item(i,0).setFlags(self.roles.item(i,0).flags()&~Qt.ItemIsEditable)
        self.commit_roles.setEnabled(bool(self.role_changes));self.role_detail_changed(self.role_cards.currentRow())
    def stage_role(self,ident,role):self.role_changes[ident]=role;self.commit_roles.setEnabled(True);self.commit_roles.setText(self.t('Apply assignments','套用角色修改')+f' ({len(self.role_changes)})')
    def commit_role_assignments(self):
        if not self.draft or not self.role_changes:return
        self.checkpoint_edit()
        for row in self.draft['segments']:
            if row['id'] in self.role_changes:row['speakerId']=self.role_changes[row['id']];row.pop('audioTake',None)
        self.role_changes={};self.dirty=True;self.populate_editor();self.save_draft()
    def cancel_role_assignments(self):self.role_changes={};self.refresh_role_tools()
    def save_portrait(self,path,source=None,time=None):
        index=self.role_cards.currentRow();profiles=self.draft['settings'].get('voiceProfiles',[]) if self.draft else []
        if not 0<=index<len(profiles):return
        self.checkpoint_edit();row=profiles[index];record=dict(avatar=str(path),sourceFrame=str(source or path),time=time if time is not None else self.player.position()/1000);row.update(avatar=record['avatar'],sourceFrame=record['sourceFrame'],avatarTime=record['time']);row['portraits']=row.get('portraits',[])+[record];self.dirty=True;self.refresh_role_cards();self.refresh_role_tools();self.save_draft()
    def choose_role_portrait(self):
        if not self.draft or self.role_cards.currentRow()<0:return
        file,_=QFileDialog.getOpenFileName(self,self.t('Choose portrait','選擇角色相片'),'','Images (*.png *.jpg *.jpeg *.webp)')
        if not file:return
        folder=Path(self.draft['review']).parent/'role-portraits';folder.mkdir(exist_ok=True);target=folder/(uuid.uuid4().hex+'.png');image=QPixmap(file)
        if not image.isNull() and image.save(str(target),'PNG'):self.save_portrait(target)
    def capture_role_portrait(self):
        if not self.draft or self.role_cards.currentRow()<0:return
        image=self.video.videoSink().videoFrame().toImage()
        if image.isNull():self.notice(self.t('Open a video frame in Edit first.','請先喺剪輯頁開啟影片畫面。'));return
        dialog=QDialog(self);dialog.setWindowTitle(self.t('Crop role portrait','裁切角色相片'));v=QVBoxLayout(dialog);canvas=RegionCanvas(image,[.25,.1,.5,.8]);v.addWidget(canvas);buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);v.addWidget(buttons)
        if dialog.exec()!=QDialog.Accepted:return
        r=canvas.selection
        if r.width()<.01 or r.height()<.01:return
        folder=Path(self.draft['review']).parent/'role-portraits';folder.mkdir(exist_ok=True);key=uuid.uuid4().hex;source=folder/(key+'-frame.png');target=folder/(key+'.png');image.save(str(source));image.copy(round(r.x()*image.width()),round(r.y()*image.height()),round(r.width()*image.width()),round(r.height()*image.height())).save(str(target));self.save_portrait(target,source)
    def clear_role_portrait(self):
        profiles=self.draft['settings'].get('voiceProfiles',[]) if self.draft else [];i=self.role_cards.currentRow()
        if 0<=i<len(profiles):self.checkpoint_edit();profiles[i].pop('avatar',None);self.dirty=True;self.refresh_role_cards();self.refresh_role_tools();self.save_draft()
    def use_observed_portrait(self):
        i=self.observations.currentRow()
        if 0<=i<len(self.observed_rows):
            row=self.observed_rows[i]
            if Path(row.get('avatar','')).is_file():self.save_portrait(row['avatar'],row.get('sourceFrame'),row.get('time'))
