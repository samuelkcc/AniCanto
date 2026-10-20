"""Apply studio preferences and keep assistant motion independent of media playback."""
from pathlib import Path
from PySide6.QtCore import Qt,QTimer,QPoint
from PySide6.QtGui import QPixmap,QPainter,QColor,QPalette
from PySide6.QtWidgets import QApplication,QWidget,QMenu
from desktop_widgets import theme
from studio_icons import icon
from studio_layout import CONTRACT,SHARED

class Assistant(QWidget):
    def __init__(self,owner):
        super().__init__(owner,Qt.Tool|Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint)
        self.owner=owner;self.pose=QPixmap();self.frame=0;self.drag=None;self.steps=0
        self.setAttribute(Qt.WA_TranslucentBackground);self.resize(120,120)
        self.clock=QTimer(self);self.clock.setInterval(180);self.clock.timeout.connect(self.advance)
    def advance(self):
        if not self.owner.isVisible() or self.owner.isMinimized():self.hide();return
        self.frame=(self.frame+1)%4;self.steps+=1
        if self.owner.store.settings.get('desktopPetRoaming') and not self.drag:
            area=self.screen().availableGeometry();x=self.x()+3
            if x>area.right()-self.width():x=area.left()
            self.move(x,self.y())
        self.update()
    def paintEvent(self,event):
        if self.pose.isNull():return
        painter=QPainter(self);tile=self.pose.copy(self.frame*self.pose.width()//4,2*self.pose.height()//3,self.pose.width()//4,self.pose.height()//3)
        image=tile.scaled(self.size(),Qt.KeepAspectRatio,Qt.SmoothTransformation);painter.drawPixmap((self.width()-image.width())//2,(self.height()-image.height())//2,image)
    def mousePressEvent(self,event):
        if event.button()==Qt.LeftButton:self.drag=event.globalPosition().toPoint()-self.pos()
    def mouseMoveEvent(self,event):
        if self.drag is not None:self.move(event.globalPosition().toPoint()-self.drag)
    def mouseReleaseEvent(self,event):self.drag=None
    def contextMenuEvent(self,event):
        menu=QMenu(self);menu.addAction(self.owner.t('Return to studio','返回工作室'),self.owner.activateWindow);menu.addAction(self.owner.t('Hide companion','隱藏助手'),lambda:self.owner.set_setting('showStudioCompanion',False));menu.exec(event.globalPos())

class StudioPreferences:
    def apply_preferences(self):
        settings=self.store.settings;key=settings.get('animeTheme') or self.cover_path.stem.replace('welcome-','');key=key if key in CONTRACT['themes'] else 'studio'
        self.accent=CONTRACT['themes'][key];appearance=settings.get('appearance','system')
        dark=appearance=='dark' or appearance=='system' and QApplication.styleHints().colorScheme()==Qt.ColorScheme.Dark
        theme(QApplication.instance(),self.accent,dark,17 if settings.get('controlDensity')=='large' else 15)
        for i,button in enumerate(self.nav_buttons):button.setIcon(icon(CONTRACT['navigation'][i][3],self.accent))
        from PySide6.QtWidgets import QToolButton
        for button in self.findChildren(QToolButton):
            if button.property('studioTint') and button.property('studioIcon'):button.setIcon(icon(button.property('studioIcon'),self.accent))
        for journey in (self.basic_journey,self.expert_journey):journey.accent=QColor(self.accent);journey.update()
        self.runner_path=SHARED/('pet-'+key+'.png');self.basic_journey.pose=QPixmap(str(self.runner_path));self.basic_journey.sprite_sheet=True
        self.timeline.dark=dark;self.timeline.update()
        if hasattr(self,'model_table'):self.model_table.resizeRowsToContents()
        if hasattr(self,'background_volume') and self.draft:
            self.background_volume.blockSignals(True);self.background_volume.setValue(int(self.draft['settings'].get('backgroundGain',1)*100));self.background_volume.blockSignals(False)
            self.ducking.blockSignals(True);self.ducking.setChecked(self.draft['settings'].get('backgroundDucking',True));self.ducking.blockSignals(False)
        if not hasattr(self,'companion'):self.companion=Assistant(self)
        self.companion.pose=QPixmap(str(self.runner_path))
        visible=settings.get('showStudioCompanion',False) and self.shell.currentIndex()==1
        if visible:
            if not self.companion.isVisible():
                area=self.screen().availableGeometry();self.companion.move(area.right()-150,area.bottom()-150);self.companion.show()
            if settings.get('companionMotion',True):self.companion.clock.start()
            else:self.companion.clock.stop()
        else:self.companion.clock.stop();self.companion.hide()
