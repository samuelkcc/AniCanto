"""One video surface for both modes, with real translated subtitle overlays."""
from PySide6.QtCore import Qt,QRectF,QSizeF
from PySide6.QtGui import QColor,QPainter
from PySide6.QtWidgets import QGraphicsView,QGraphicsScene,QGraphicsTextItem,QFrame
from PySide6.QtMultimediaWidgets import QGraphicsVideoItem
class StudioVideo(QGraphicsView):
 def __init__(self):
  super().__init__();self.setScene(QGraphicsScene(self));self.setFrameShape(QFrame.NoFrame);self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff);self.setBackgroundBrush(QColor('black'));self.setRenderHint(QPainter.Antialiasing)
  self.videoItem=QGraphicsVideoItem();self.videoItem.setAspectRatioMode(Qt.KeepAspectRatio);self.scene().addItem(self.videoItem);self.caption=QGraphicsTextItem();self.caption.setZValue(2);self.scene().addItem(self.caption);self.words=''
 def videoSink(self):return self.videoItem.videoSink()
 def set_caption(self,text):
  if self.words==text:return
  import html
  self.words=text;self.caption.setHtml('<div style="color:white;background-color:rgba(0,0,0,185);font-size:17px;text-align:center;font-weight:600;">'+html.escape(text).replace('\n','<br>')+'</div>' if text else '');self.place_caption()
 def place_caption(self):
  width=max(1,self.viewport().width());self.caption.setTextWidth(width*.87);rect=self.caption.boundingRect();self.caption.setPos(width*.065,max(0,self.viewport().height()-rect.height()-18))
 def resizeEvent(self,event):
  super().resizeEvent(event)
  if hasattr(self,'videoItem'):self.videoItem.setSize(QSizeF(self.viewport().size()));self.setSceneRect(QRectF(0,0,self.viewport().width(),self.viewport().height()));self.place_caption()
