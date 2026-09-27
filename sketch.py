"""Reference-inspired flat pastel, charcoal-grain line art, native animated vector."""
import math
import random
from functools import lru_cache
from PySide6.QtCore import Qt,QPointF,QRectF
from PySide6.QtGui import QPainter,QPainterPath,QColor,QPen,QFont

INK=QColor('#3c3332')

def blink_at(clock):
    # Short blinks separated by varied pauses; occasional double blink.
    t=clock%12.9
    for center in (2.7,6.8,7.16,11.4):
        distance=abs(t-center)
        if distance<.13:return max(.04,distance/.13)
    return 1.

def rough(p,path,fill=None,seed=1,width=2.8):
    if fill:p.fillPath(path,QColor(fill))
    rng=random.Random(seed)
    for n in range(2):
        line=QPainterPath()
        for i in range(110):
            point=path.pointAtPercent(i/109); point+=QPointF(rng.uniform(-.65,.65),rng.uniform(-.65,.65))
            if i==0:line.moveTo(point)
            else:line.lineTo(point)
        p.setPen(QPen(QColor(60,51,50,205 if n==0 else 90),width if n==0 else 1,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin))
        p.setBrush(Qt.NoBrush); p.drawPath(line)

def ellipse(x,y,w,h):
    path=QPainterPath(); path.addEllipse(QRectF(x,y,w,h)); return path

def polygon(points):
    path=QPainterPath(QPointF(*points[0]))
    for point in points[1:]:path.lineTo(*point)
    path.closeSubpath(); return path

def paint_hat(p,hat):
    if hat=='none':return
    p.save(); p.translate(0,-79); p.rotate(-8)
    if hat=='sprout':
        stem=QPainterPath(QPointF(0,0)); stem.quadTo(-3,-17,0,-28); rough(p,stem,seed=12)
        leaf=QPainterPath(QPointF(0,-18)); leaf.cubicTo(-30,-18,-34,-42,0,-28); leaf.cubicTo(25,-53,37,-26,0,-18)
        rough(p,leaf,'#b8cc8f',13)
    elif hat=='beret':
        rough(p,ellipse(-53,-33,108,42),'#ce9ba8',15); rough(p,polygon([(-37,1),(38,1),(34,8),(-34,8)]),'#bb8695',16)
        rough(p,polygon([(-4,-29),(-3,-41),(3,-41),(4,-29)]),'#bc8d9b',17)
    elif hat=='cap':
        top=QPainterPath(QPointF(-43,0)); top.cubicTo(-41,-57,38,-52,40,1); top.closeSubpath(); rough(p,top,'#c5d5b7',20)
        brim=QPainterPath(QPointF(-3,0)); brim.quadTo(88,-7,67,13); brim.quadTo(32,15,-3,0); rough(p,brim,'#a8bd9a',21)
    elif hat=='straw':
        rough(p,ellipse(-70,-2,140,24),'#eed9a5',22)
        top=QPainterPath(QPointF(-39,5)); top.lineTo(-31,-38); top.quadTo(0,-50,32,-37); top.lineTo(40,5); top.closeSubpath(); rough(p,top,'#efdfb9',23)
        rough(p,polygon([(-36,-8),(36,-8),(40,4),(-39,4)]),'#cc9a90',24,1.5)
    elif hat in ('party','witch'):
        color='#ded0e9' if hat=='witch' else '#f0c6a8'
        rough(p,ellipse(-59,-3,118,18),color,25)
        shape=QPainterPath(QPointF(-39,3))
        if hat=='witch':
            shape.cubicTo(-25,-45,-15,-83,27,-72); shape.lineTo(53,-53); shape.quadTo(8,-67,20,-35)
        else:shape.lineTo(-4,-63); shape.quadTo(12,-74,22,-48)
        shape.lineTo(39,3); shape.closeSubpath(); rough(p,shape,color,26)
        p.setPen(Qt.NoPen); p.setBrush(QColor('#f8edb8')); p.drawEllipse(QRectF(-5,-31,12,12)); p.drawEllipse(QRectF(12,-10,7,7))
    elif hat=='santa':
        shape=QPainterPath(QPointF(-41,0)); shape.cubicTo(-23,-60,45,-76,61,-21); shape.quadTo(31,-38,37,0); shape.closeSubpath(); rough(p,shape,'#cf9690',28)
        rough(p,ellipse(-48,-9,98,24),'#fff8e9',29); rough(p,ellipse(49,-30,20,20),'#fff8e9',30)
    elif hat=='crown':
        rough(p,polygon([(-40,0),(-48,-36),(-21,-20),(0,-47),(21,-19),(46,-36),(38,0)]),'#edcf80',32)
        p.setBrush(QColor('#c78f9b')); p.setPen(Qt.NoPen); p.drawEllipse(QRectF(-5,-16,10,10))
    p.restore()

@lru_cache(maxsize=1)
def grain():
    rng=random.Random(21)
    return [(rng.uniform(-77,77),rng.uniform(-88,64),rng.uniform(.3,.8)) for _ in range(260)]

def paint_sketch(p,rect,value=100,state='live',clock=0,hat='none',listening=False):
    p.save(); p.setRenderHint(QPainter.Antialiasing)
    p.translate(rect.center().x(),rect.center().y()+20)
    scale=min(rect.width()/260,rect.height()/330); p.scale(scale,scale)
    size=.73+.27*math.sqrt(max(0,min(100,value))/100); p.scale(size,size)
    p.translate(0,math.sin(clock*1.7)*3); p.rotate(math.sin(clock*.9)*2.3)
    live=state in ('idle','initial','live')
    color=('#b8d8e6' if value>=85 else '#bec9e5' if value>=65 else '#d2c3df' if value>=45 else '#c9bfce') if live else '#e0d9da'
    body=QPainterPath(QPointF(0,70)); body.cubicTo(-64,46,-93,-18,-74,-64); body.cubicTo(-46,-111,54,-101,77,-60); body.cubicTo(99,-9,55,47,0,70)
    rough(p,body,color,1)
    p.save(); p.setClipPath(body); p.setPen(Qt.NoPen)
    for x,y,r in grain():
        p.setBrush(QColor(70,58,52,23)); p.drawEllipse(QRectF(x,y,r,r))
    p.restore()
    # Thin imperfect highlight, no glossy gradient.
    shine=QPainterPath(QPointF(-53,-47)); shine.quadTo(-48,-65,-35,-68)
    p.setPen(QPen(QColor('#eaf2ef'),4,Qt.SolidLine,Qt.RoundCap)); p.drawPath(shine)
    rough(p,polygon([(0,68),(-7,80),(8,80)]),color,3,2)
    string=QPainterPath(QPointF(0,81)); string.cubicTo(-18,95,20,107,0,132); rough(p,string,seed=5,width=1.5)
    eyes=blink_at(clock) if listening or state in ('idle','initial','live','waiting') else .1
    p.setPen(Qt.NoPen); p.setBrush(QColor('#deb5b7')); p.drawEllipse(QRectF(-41,-12,17,7)); p.drawEllipse(QRectF(26,-12,17,7))
    for x in (-21,21):
        if eyes<.2:
            eye=QPainterPath(QPointF(x-4,-23)); eye.quadTo(x,-20,x+4,-23); rough(p,eye,seed=int(x+33),width=2)
        else:
            p.setPen(Qt.NoPen); p.setBrush(INK); p.drawEllipse(QRectF(x-3,-26,6,9*eyes))
    mouth=QPainterPath(QPointF(-5,-14)); mouth.quadTo(0,-8,6,-14); rough(p,mouth,seed=6,width=2)
    p.setPen(INK); font=QFont('Comic Sans MS',27,QFont.Bold); p.setFont(font)
    text=f'{round(value)}%' if live else {'waiting':'…','error':'!','stopping':'···','paused':'zZ'}.get(state,'—')
    p.drawText(QRectF(-70,1,140,43),Qt.AlignCenter,text)
    paint_hat(p,hat)
    p.restore()
