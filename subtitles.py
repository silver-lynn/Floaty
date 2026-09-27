"""Transparent, outlined native live captions. Draft text never enters scoring."""
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter, QPainterPath, QPen, QColor, QFont, QFontMetricsF
from PySide6.QtWidgets import QWidget, QApplication

class Subtitles(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.Tool|Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint|Qt.WindowDoesNotAcceptFocus)
        self.setWindowTitle('Floaty · 悬浮字幕')
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.text=''; self.enabled=True; self.font_size=48; self.drag=None; self.passthrough=False
        self.expiry=QTimer(self); self.expiry.setSingleShot(True); self.expiry.timeout.connect(self.clear)
        self.reset_position()
        self.setToolTip('拖动字幕调整位置 · 右键气球可调整字号或关闭字幕')

    def caption_font(self):
        font=QFont('Microsoft YaHei UI'); font.setPixelSize(self.font_size); font.setWeight(QFont.DemiBold)
        return font

    def reset_position(self):
        area=(self.screen() or QApplication.primaryScreen()).availableGeometry()
        self.resize(min(1400,int(area.width()*.88)),int(self.font_size*3.1))
        self.move(area.center().x()-self.width()//2,area.bottom()-self.height()-48)

    def set_size(self,size):
        self.font_size=size; self.resize(self.width(),int(size*3.1)); self.update()

    def set_enabled(self,enabled):
        self.enabled=enabled
        self.setVisible(bool(enabled and self.text))

    def set_passthrough(self,enabled):
        self.passthrough=enabled; self.setWindowFlag(Qt.WindowTransparentForInput,enabled)
        self.setVisible(bool(self.enabled and self.text))

    def set_caption(self,text):
        self.text=' '.join(str(text).split())[-400:]
        self.expiry.start(8000)
        self.setVisible(bool(self.enabled and self.text)); self.update()

    def clear(self):
        self.expiry.stop(); self.text=''; self.hide()

    def lines(self):
        fm=QFontMetricsF(self.caption_font()); width=max(1,self.width()-36)
        lines=[]; line=''
        for char in self.text:
            if line and fm.horizontalAdvance(line+char)>width:
                lines.append(line.rstrip()); line=char.lstrip()
            else:line+=char
        if line:lines.append(line.rstrip())
        return lines[-2:]

    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        font=self.caption_font(); fm=QFontMetricsF(font); lines=self.lines()
        gap=fm.height()*1.16; top=(self.height()-gap*len(lines))/2
        for i,line in enumerate(lines):
            path=QPainterPath(); path.addText((self.width()-fm.horizontalAdvance(line))/2,top+i*gap+fm.ascent(),font,line)
            p.strokePath(path,QPen(QColor(15,24,40,230),max(3,self.font_size*.085),Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin))
            p.fillPath(path,QColor('white'))
        p.end()

    def mousePressEvent(self,event):
        if event.button()==Qt.LeftButton:self.drag=event.globalPosition().toPoint()-self.pos()
    def mouseMoveEvent(self,event):
        if self.drag is not None:self.move(event.globalPosition().toPoint()-self.drag)
    def mouseReleaseEvent(self,event):self.drag=None
