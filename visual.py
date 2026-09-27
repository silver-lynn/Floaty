"""Shared native vector renderer: translucent balloon, no image assets."""
import math
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QFont, QRadialGradient, QLinearGradient

def color_at(value):
    stops=[(0,(139,137,162)),(44,(154,139,203)),(65,(125,120,227)),(85,(72,141,245)),(100,(43,164,255))]
    v=max(0,min(100,value))
    for (lo,a),(hi,b) in zip(stops,stops[1:]):
        if v<=hi:
            t=(v-lo)/(hi-lo)
            return QColor(*(round(x+(y-x)*t) for x,y in zip(a,b)))
    return QColor(*stops[-1][1])

def paint_balloon(p, rect, value=100, state='idle', clock=0):
    p.save(); p.setRenderHint(QPainter.Antialiasing)
    scale=min(rect.width()/240,rect.height()/300)
    p.translate(rect.x()+rect.width()/2,rect.y()+rect.height()/2)
    p.scale(scale,scale)
    v=max(0,min(100,value))
    size=.68+.32*math.sqrt(v/100)
    bob=math.sin(clock*1.4)*3 if state in ('live','initial','idle') else 0
    p.translate(0,bob+(100-v)*.12)
    p.scale(size,size)
    color=color_at(v) if state in ('idle','initial','live') else QColor('#aaaec2')
    string=QPainterPath(QPointF(0,69)); string.cubicTo(-22,90,24,100,-2,122)
    p.setPen(QPen(QColor('#a7b8d1'),2)); p.drawPath(string)
    body=QPainterPath(QPointF(0,68))
    body.cubicTo(-28,52,-82,7,-82,-45)
    body.cubicTo(-83,-148,83,-148,82,-45)
    body.cubicTo(82,7,28,52,0,68)
    gradient=QRadialGradient(QPointF(-32,-91),170)
    gradient.setColorAt(0,color.lighter(155)); gradient.setColorAt(.4,color.lighter(112)); gradient.setColorAt(1,color.darker(122))
    p.setBrush(gradient); p.setPen(QPen(color.lighter(125),1.2)); p.drawPath(body)
    knot=QPainterPath(QPointF(0,65)); knot.lineTo(-8,77); knot.quadTo(0,81,8,77); knot.closeSubpath()
    p.setBrush(color.darker(112)); p.setPen(Qt.NoPen); p.drawPath(knot)
    p.save(); p.translate(-43,-81); p.rotate(32)
    p.setBrush(QColor(255,255,255,110)); p.drawEllipse(QRectF(-7,-19,14,38)); p.restore()
    p.setBrush(QColor(255,255,255,105)); p.drawEllipse(QRectF(30,19,12,6))
    face=QColor('#204579') if state in ('idle','initial','live') else QColor('#626980')
    p.setPen(QPen(face,3,Qt.SolidLine,Qt.RoundCap))
    if state in ('paused','waiting','error','stopping'):
        p.drawLine(QPointF(-23,-50),QPointF(-15,-50)); p.drawLine(QPointF(15,-50),QPointF(23,-50))
    else:
        p.drawLine(QPointF(-19,-53),QPointF(-19,-48)); p.drawLine(QPointF(19,-53),QPointF(19,-48))
    mouth=QPainterPath(QPointF(-5,-44)); mouth.quadTo(0,-39 if v>44 else -44,5,-44); p.drawPath(mouth)
    p.setPen(QColor('white')); font=QFont('Segoe UI',32,QFont.DemiBold); p.setFont(font)
    text=f'{round(v)}%' if state in ('idle','initial','live') else ('Ⅱ' if state=='paused' else '—')
    p.drawText(QRectF(-77,-32,154,52),Qt.AlignCenter,text)
    p.restore()
