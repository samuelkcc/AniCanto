"""Mac studio lane layout with shared cue identities and non-destructive edits."""
import math
from PySide6.QtCore import Qt,Signal,QRectF
from PySide6.QtGui import QColor,QPainter,QPen,QFont
from PySide6.QtWidgets import QWidget
COLORS=['#c5b8df','#9dd6bb','#efc1b9','#a7c9e3','#d5d59d','#d7accd']
class Timeline(QWidget):
    cueSelected=Signal(int);seek=Signal(float);regionEdited=Signal(int,float,float,str)
    def __init__(self):
        super().__init__();self.cues=[];self.takes=[];self.position=0;self.duration=30;self.selected=-1;self.engine='Drama 3';self.labels={};self.engines=[];self.language='yue';self.languages=['yue'];self.all_tracks=True;self.zoom=31.6;self.offset=0;self.drag=None;self.dark=False;self.setMinimumHeight(185);self.setMouseTracking(True)
    @property
    def scale(self):return max(.6,self.zoom*.6)
    def tracks(self):
        rows=[('video',self.labels.get('video','Video')),('japanese',self.labels.get('japanese','Japanese original')),('background',self.labels.get('background','Music / sound effects')),('caption',self.labels.get('caption','Subtitles')),('voice',self.labels.get('voice','Dubbing window · trim'))]
        pairs=list(dict.fromkeys([(e,l) for e in self.engines or [self.engine] for l in self.languages]+[(t.get('engine',self.engine),t.get('language','yue')) for t in self.takes]))
        if not self.all_tracks:pairs=[(self.engine,self.language)]
        return rows+[(f'take:{e}:{l}',self.labels.get(e,e)+' · '+('English' if l=='en' else self.labels.get('yue','Hong Kong Cantonese'))) for e,l in pairs]
    def x(self,sec):return 240+(sec-self.offset)*self.scale
    def time_at(self,x):return max(0,min(self.duration,self.offset+(x-240)/self.scale))
    def regions(self,key):
        if key in ('caption','voice'):
            for i,row in enumerate(self.cues):
                a=row.get('captionStart',row['start']) if key=='caption' else row['start'];b=row.get('captionEnd',row['end']) if key=='caption' else row['end'];yield i,row,a,b
        elif key.startswith('take:'):
            _,engine,language=key.split(':',2)
            for take in self.takes:
                if take.get('engine')==engine and take.get('language')==language:yield take.get('index',1)-1,take,take.get('start',0),take.get('end',0)
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.fillRect(self.rect(),QColor('#242733' if self.dark else '#f6f5fa'));p.setFont(QFont('Segoe UI',9));tracks=self.tracks();h=26
        step=max(1,5*2**max(0,math.ceil(math.log2(24/max(1,self.scale)))))
        start=math.floor(self.offset/step)*step
        for sec in range(int(start),int(self.offset+(self.width()-240)/self.scale)+step,step):
            x=self.x(sec);p.setPen(QColor('#dfdce7'));p.drawLine(int(x),25,int(x),self.height());p.setPen(QColor('#727078'));p.drawText(int(x)+3,17,f'{sec//60:02}:{sec%60:02}')
        p.fillRect(QRectF(0,0,240,self.height()),QColor('#242733' if self.dark else '#f5f4f8'))
        for n,(key,title) in enumerate(tracks):
            y=28+n*h;p.setPen(QColor('#e1deea'));p.drawLine(0,y+h-2,self.width(),y+h-2);p.setPen(QColor('#c7c9d2' if self.dark else '#6e6878'));p.drawText(QRectF(13,y,222,22),Qt.AlignVCenter,title)
            p.save();p.setClipRect(QRectF(240,y,max(0,self.width()-240),h))
            if key in ('video','japanese'):
                p.fillRect(QRectF(self.x(0),y+1,self.duration*self.scale,20),QColor('#8ac3fa' if key=='video' else '#83d6df'))
            elif key=='background':
                p.setPen(QColor('#9b96a1'));p.drawText(248,y+16,self.labels.get('backgroundHint','Separated audio appears here'))
            for i,row,a,b in self.regions(key):
                if self.drag and hasattr(self,'preview_edit') and self.preview_edit[0]==i and self.preview_edit[3]==key:_,a,b,_=self.preview_edit
                rect=QRectF(self.x(a),y+1,max(2,(b-a)*self.scale),21)
                if rect.right()<240 or rect.left()>self.width():continue
                speaker=row.get('speakerId',row.get('speaker',''));color=QColor(COLORS[sum(map(ord,str(speaker)))%len(COLORS)])
                p.setBrush(color);p.setPen(QPen(QColor('#db8c50') if i==self.selected else color.darker(110),1.4 if i==self.selected else .7));p.drawRoundedRect(rect,3,3)
                if rect.width()>30:
                    p.save();p.setClipRect(rect.adjusted(3,0,-3,0));p.setPen(QColor('#34313a'));text=speaker
                    if key=='caption':text+=' · '+row.get('text','')
                    p.drawText(rect.adjusted(4,0,-3,0),Qt.AlignVCenter,text);p.restore()
            p.restore()
        x=self.x(self.position)
        if x>=240:p.setPen(QPen(QColor('#ec6e77'),1.3));p.drawLine(int(x),24,int(x),self.height())
    def mousePressEvent(self,event):
        if event.position().x()<240:return
        sec=self.time_at(event.position().x());lane=int((event.position().y()-28)//26);tracks=self.tracks()
        if not 0<=lane<len(tracks):return
        key=tracks[lane][0]
        for i,row,a,b in self.regions(key):
            if a<=sec<=b:
                self.selected=i;self.cueSelected.emit(i)
                if key in ('caption','voice'):
                    edge='start' if abs(event.position().x()-self.x(a))<7 else 'end' if abs(event.position().x()-self.x(b))<7 else 'move'
                    self.drag=(i,a,b,key,edge,sec)
                self.update();return
        self.seek.emit(sec)
    def mouseMoveEvent(self,event):
        if self.drag:
            i,a,b,key,edge,origin=self.drag;now=self.time_at(event.position().x());delta=now-origin
            start=max(0,min(b-.04,a+delta)) if edge=='start' else a if edge=='end' else max(0,min(self.duration-(b-a),a+delta))
            end=min(self.duration,max(a+.04,b+delta)) if edge=='end' else b if edge=='start' else start+(b-a)
            self.preview_edit=(i,round(start,3),round(end,3),key);self.setToolTip(f'{start:.2f} – {end:.2f} s');self.update();return
    def mouseReleaseEvent(self,event):
        if self.drag and hasattr(self,'preview_edit'):self.regionEdited.emit(*self.preview_edit);del self.preview_edit
        self.drag=None
