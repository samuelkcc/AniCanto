"""Subtitle-region selection in normalised source coordinates."""
from PySide6.QtCore import Qt,QRectF
from PySide6.QtGui import QPainter,QColor,QPen
from PySide6.QtWidgets import QDialog,QDialogButtonBox,QVBoxLayout,QLabel,QWidget
class RegionCanvas(QWidget):
 def __init__(self,image,rect):
  super().__init__();self.image=image;self.selection=QRectF(*(rect or [.03,.72,.94,.25]));self.origin=None;self.setMinimumSize(560,315)
 def paintEvent(self,event):
  p=QPainter(self);p.fillRect(self.rect(),QColor('#191921'))
  if not self.image.isNull():p.drawImage(self.rect(),self.image)
  p.setPen(QPen(QColor('#8c72cc'),2));r=self.selection;p.drawRect(QRectF(r.x()*self.width(),r.y()*self.height(),r.width()*self.width(),r.height()*self.height()))
 def mousePressEvent(self,event):self.origin=event.position()
 def mouseMoveEvent(self,event):
  if self.origin is None:return
  r=QRectF(self.origin,event.position()).normalized().intersected(QRectF(self.rect()));self.selection=QRectF(r.x()/self.width(),r.y()/self.height(),r.width()/self.width(),r.height()/self.height());self.update()
 def mouseReleaseEvent(self,event):self.origin=None
class RegionDialog(QDialog):
 def __init__(self,parent,rect):
  super().__init__(parent);self.setWindowTitle(parent.t('Select subtitle area','框選字幕'));v=QVBoxLayout(self);v.addWidget(QLabel(parent.t('Drag a rectangle over the subtitle area. Coordinates follow the source video.','拖曳框選原片字幕範圍。')))
  self.canvas=RegionCanvas(parent.video.videoSink().videoFrame().toImage(),[rect[k] for k in ('x','y','width','height')] if isinstance(rect,dict) and all(k in rect for k in ('x','y','width','height')) else None);v.addWidget(self.canvas);buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);v.addWidget(buttons)
 def region(self):
  r=self.canvas.selection;return dict(x=round(r.x(),4),y=round(r.y(),4),width=round(r.width(),4),height=round(r.height(),4))
