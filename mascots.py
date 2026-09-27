"""Three selectable native vector balloon candidates; all runtime states covered."""
import math
from PySide6.QtCore import Qt,QPointF,QRectF
from PySide6.QtGui import QPainter,QPainterPath,QColor,QPen,QFont,QRadialGradient
from visual import color_at

NAMES={'mochi':'A · 糯米团','bunny':'B · 兔耳泡泡','star':'C · 星星糖'}
STATES=[('idle',100,'待机'),('initial',100,'开场 / 初始'),('live',94,'专注 / 高分'),('live',74,'平稳 / 中高'),('live',52,'走低 / 中段'),('live',25,'低分 / 鼓励'),('waiting',55,'等待语音或评分'),('error',55,'连接异常'),('stopping',55,'正在结束'),('paused',55,'结束 / 休息')]

def paint_mascot(p,rect,value,state,clock=0,variant='mochi'):
    p.save(); p.setRenderHint(QPainter.Antialiasing)
    p.translate(rect.center()); scale=min(rect.width()/260,rect.height()/300); p.scale(scale,scale)
    live=state in ('idle','initial','live'); size=.72+.28*math.sqrt(max(0,min(100,value))/100)
    p.translate(0,(100-value)*.10+math.sin(clock*1.4)*2); p.scale(size,size)
    base=color_at(value) if live else QColor('#b9c5d9')
    if state=='error':base=QColor('#b9add6')
    ink=QColor('#354a70'); blush=QColor(255,172,195,145)
    anchor=46 if variant=='star' else 58
    string=QPainterPath(QPointF(0,anchor)); string.cubicTo(-19,81,24,92,0,120)
    p.setPen(QPen(QColor('#b9c8dc'),2,Qt.SolidLine,Qt.RoundCap)); p.setBrush(Qt.NoBrush); p.drawPath(string)
    body=QPainterPath()
    if variant=='mochi':
        body.moveTo(0,62); body.cubicTo(-70,50,-102,-1,-90,-59); body.cubicTo(-76,-126,78,-126,90,-59); body.cubicTo(103,0,66,52,0,62)
    elif variant=='bunny':
        body.moveTo(0,62); body.cubicTo(-79,49,-97,-17,-71,-60)
        body.cubicTo(-93,-130,-57,-151,-37,-72)
        body.quadTo(0,-91,32,-74); body.cubicTo(49,-151,86,-134,66,-61)
        body.cubicTo(102,-15,80,49,0,62)
    else:
        points=[]
        for i in range(10):
            angle=-math.pi/2+i*math.pi/5; r=110 if i%2==0 else 69
            points.append(QPointF(math.cos(angle)*r,math.sin(angle)*r-30))
        mid=lambda a,b:QPointF((a.x()+b.x())/2,(a.y()+b.y())/2)
        body.moveTo(mid(points[-1],points[0]))
        for i,point in enumerate(points):body.quadTo(point,mid(point,points[(i+1)%10]))
        body.closeSubpath()
    gradient=QRadialGradient(QPointF(-40,-95),195)
    gradient.setColorAt(0,QColor('#eefbff')); gradient.setColorAt(.35,base.lighter(145)); gradient.setColorAt(.8,base); gradient.setColorAt(1,base.darker(110))
    p.setBrush(gradient); p.setPen(QPen(base.lighter(115),1.5)); p.drawPath(body)
    knot=QPainterPath(QPointF(0,anchor)); knot.lineTo(-7,anchor+11); knot.quadTo(0,anchor+15,7,anchor+11); knot.closeSubpath()
    p.setPen(Qt.NoPen); p.setBrush(base); p.drawPath(knot)
    if variant=='bunny':
        p.setBrush(QColor(255,207,224,155)); p.save(); p.translate(-53,-100); p.rotate(-14); p.drawEllipse(QRectF(-5,-20,10,37)); p.restore()
        p.save(); p.translate(49,-100); p.rotate(12); p.drawEllipse(QRectF(-5,-20,10,37)); p.restore()
    p.save(); p.translate(-51,-69); p.rotate(36); p.setBrush(QColor(255,255,255,125)); p.drawEllipse(QRectF(-7,-17,14,34)); p.restore()
    p.setBrush(blush); p.drawEllipse(QRectF(-43,-29,19,10)); p.drawEllipse(QRectF(25,-29,19,10))
    p.setPen(QPen(ink,3,Qt.SolidLine,Qt.RoundCap)); p.setBrush(ink)
    for x in (-21,21):
        if state in ('paused','stopping'):
            eye=QPainterPath(QPointF(x-5,-42)); eye.quadTo(x,-36,x+5,-42); p.drawPath(eye)
        elif state=='error':
            p.drawLine(QPointF(x-4,-45),QPointF(x+4,-37)); p.drawLine(QPointF(x+4,-45),QPointF(x-4,-37))
        elif state=='waiting':p.drawEllipse(QRectF(x-3,-44,6,7))
        elif value>=85 and state=='live':
            eye=QPainterPath(QPointF(x-5,-39)); eye.quadTo(x,-49,x+5,-39); p.drawPath(eye)
        else:
            p.drawEllipse(QRectF(x-3,-46,6,10)); p.setPen(Qt.NoPen); p.setBrush(QColor('white')); p.drawEllipse(QRectF(x-2,-45,2,3)); p.setPen(QPen(ink,3,Qt.SolidLine,Qt.RoundCap)); p.setBrush(ink)
    mouth=QPainterPath(QPointF(-6,-32)); mouth.quadTo(0,-24 if live else -30,6,-32); p.setBrush(Qt.NoBrush); p.drawPath(mouth)
    p.setFont(QFont('Segoe UI',29,QFont.Bold)); p.setPen(ink)
    text=f'{round(value)}%' if live else {'waiting':'…','error':'!','stopping':'···','paused':'zZ'}.get(state,'—')
    p.drawText(QRectF(-78,-15,156,47),Qt.AlignCenter,text)
    if live and value<45:
        # Small encouraging arms, no alarm-red or distressed face.
        p.setPen(QPen(base.darker(112),4,Qt.SolidLine,Qt.RoundCap)); p.drawLine(QPointF(-72,2),QPointF(-91,-7)); p.drawLine(QPointF(72,2),QPointF(91,-7))
    if state=='paused':
        p.setFont(QFont('Segoe UI',12,QFont.Bold)); p.setPen(QColor('#899bb7')); p.drawText(60,-83,'z')
    p.restore()
