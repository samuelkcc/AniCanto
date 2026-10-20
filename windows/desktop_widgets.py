"""Native Qt studio controls; media callbacks read only in-memory projections."""
from pathlib import Path
from PySide6.QtCore import Qt,QObject,Signal,QRunnable,QRectF,QTimer
from PySide6.QtGui import QColor,QPainter,QPen,QPixmap,QFont
from PySide6.QtWidgets import QWidget,QApplication

class Result(QObject):
    done=Signal(object)
    failed=Signal(str)

class IO(QRunnable):
    def __init__(self,fn):super().__init__();self.fn=fn;self.signals=Result()
    def run(self):
        try:self.signals.done.emit(self.fn())
        except Exception as error:self.signals.failed.emit(str(error))

def theme(app,accent='#7350b8',dark=False,font_size=15):
    app.setStyle('Fusion');font=QFont('Segoe UI');font.setPixelSize(font_size);app.setFont(font)
    tint='rgba('+','.join(str(int(accent[i:i+2],16)) for i in (1,3,5))+',25)'
    base,panel,text,muted,line=('#191b24','#242733','#eef0f8','#a5acbe','#393f50') if dark else ('#f5f5f8','#ffffff','#252832','#747b89','#e3e5ec')
    arrow=(Path(__file__).parent/'assets/chevron-down.svg').as_posix()
    app.setStyleSheet(f'''
    QWidget {{color:{text};background:{panel};}} QMainWindow,QStackedWidget {{background:{base};}}
    QLabel#brand {{font-size:17px;font-weight:700;}} QLabel#heading {{font-size:24px;font-weight:700;}}
    QLabel#muted {{color:{muted};}} QLabel#caption {{font-size:17px;padding:8px;}}
    QFrame#card {{border:1px solid {line};border-radius:12px;padding:10px;background:{panel};}}
    QPushButton,QToolButton {{border:1px solid {line};border-radius:6px;padding:6px 10px;min-height:20px;background:{panel};}}
    QPushButton:hover,QToolButton:hover {{border-color:{accent};}}
    QPushButton:checked,QPushButton#primary {{background:{accent};color:white;border-color:{accent};font-weight:600;}}
    QPushButton:disabled {{color:{muted};}} QComboBox,QLineEdit,QDoubleSpinBox,QSpinBox {{border:1px solid {line};border-radius:5px;padding:7px;}}
    QComboBox::drop-down {{width:24px;border:0;}} QComboBox::down-arrow {{image:url("{arrow}");width:12px;height:12px;}} QPlainTextEdit,QTextBrowser,QTableWidget,QListWidget {{border:1px solid {line};border-radius:5px;background:{panel};}}
    QListWidget::item {{padding:0;}} QListWidget::item:selected {{background:{accent};color:white;}} QListWidget#categorySide {{border:0;background:{base};}} QListWidget#categorySide::item {{padding:14px 16px;}} QListWidget#categorySide::item:selected {{background:{tint};color:{accent};}}
    QHeaderView::section {{background:{base};padding:8px;border:0;border-bottom:1px solid {line};}}
    QSplitter::handle {{background:{line};width:4px;height:4px;}}
    QTabBar::tab {{padding:8px 12px;background:{base};}} QTabBar::tab:selected {{color:{accent};border-bottom:2px solid {accent};}}
    QProgressBar {{border:0;background:{line};height:6px;border-radius:3px;}} QProgressBar::chunk {{background:{accent};border-radius:3px;}}
    QSlider::groove:horizontal {{height:4px;background:{line};}} QSlider::handle:horizontal {{background:{accent};width:12px;margin:-5px 0;border-radius:6px;}}
    QWidget#welcomeArt {{background:{base};}} QWidget#welcomeArt QLabel {{background:transparent;}}
    QFrame#panelHeader {{background:{base};border-bottom:1px solid {line};}}
    QToolButton#navItem {{border:0;border-radius:9px;padding:4px;font-size:10px;color:{muted};}}
    QToolButton#navItem:checked {{background:{tint};color:{accent};font-weight:600;}}
    QToolButton#iconButton {{min-width:22px;min-height:22px;padding:5px;}}
    QFrame#shelfCard {{background:{panel};border:1px solid {line};border-radius:10px;}}
    QToolButton#modeCard {{text-align:left;padding:18px;border-radius:14px;}}
    QToolButton#modeCard:checked {{background:{base};color:{text};border:2px solid {accent};}}
    QPlainTextEdit#transcript {{border:0;border-radius:0;background:{panel};font-size:18px;}}
    QMenu {{padding:5px;border:1px solid {line};}} QMenu::item {{padding:7px 25px;}} QMenu::item:selected {{background:{accent};color:white;}}
    ''')

class Journey(QWidget):
    def __init__(self,asset=None):
        super().__init__();self.value=0;self.rows=[];self.basic=True;self.accent=QColor('#7350b8');self.labels=[]
        self.pose=QPixmap(str(asset)) if asset and Path(asset).is_file() else QPixmap()
        self.sprite_sheet=bool(asset and Path(asset).name.startswith('pet-'));self.frame=0
        self.animation=QTimer(self);self.animation.setInterval(180);self.animation.timeout.connect(self.next_frame)
        self.setMinimumHeight(98)
    def next_frame(self):self.frame=(self.frame+1)%4;self.update()
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        width=max(1,self.width()-28);y=38 if self.basic else 12
        p.setPen(QPen(QColor('#e5e5ed'),5,Qt.SolidLine,Qt.RoundCap));p.drawLine(14,y,14+width,y)
        p.setPen(QPen(self.accent,5,Qt.SolidLine,Qt.RoundCap));p.drawLine(14,y,14+int(width*self.value),y)
        if self.basic and not self.pose.isNull():
            # Entire assistant artwork is contained, never cropped at the ends.
            source=self.pose.copy(self.frame*self.pose.width()//4,2*self.pose.height()//3,self.pose.width()//4,self.pose.height()//3) if self.sprite_sheet else self.pose
            sprite=source.scaled(48,48,Qt.KeepAspectRatio,Qt.SmoothTransformation)
            x=min(self.width()-sprite.width()-4,max(4,int(width*self.value)))
            p.drawPixmap(x,0,sprite)
        p.setFont(QFont('Segoe UI',9));count=max(1,len(self.labels))
        for i,label in enumerate(self.labels):
            row=next((r for r in self.rows if r.get('id')==['prepare','recognition','roles','translation','voice','repair','export'][i]),{})
            x=14+width*(i+.5)/count
            p.setPen(self.accent if row.get('state') in ('complete','running','prepared','saved') else QColor('#9297a3'))
            p.drawEllipse(QRectF(x-3,y-3,6,6))
            p.drawText(QRectF(x-width/count/2,y+9,width/count,20),Qt.AlignCenter,label)
            sec=row.get('seconds',0);duration='—' if not sec else f'{int(sec)//60}:{int(sec)%60:02}'
            if row.get('state') in ('prepared','saved') and not sec:duration='✓'
            p.drawText(QRectF(x-width/count/2,y+28,width/count,18),Qt.AlignCenter,duration)
    def set_data(self,data,basic,labels):
        self.basic=basic;self.value=data.get('progress',0);self.rows=data.get('milestones',[]);self.labels=labels
        if basic and any(r.get('state')=='running' for r in self.rows):self.animation.start()
        else:self.animation.stop()
        self.setFixedHeight(102 if basic else 55);self.update()

from studio_timeline import Timeline
