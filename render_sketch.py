"""Render the actual native illustration and animation, using labeled sample values."""
from pathlib import Path
from PIL import Image
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QRectF,Qt
from PySide6.QtGui import QImage,QPainter,QColor,QFont
from sketch import paint_sketch
from mascots import STATES
from growth import HATS

app=QApplication([]); root=Path(__file__).parent
def page(title,subtitle):
    im=QImage(1500,950,QImage.Format_RGBA8888); im.fill(QColor('#f3e7e1')); p=QPainter(im)
    p.setPen(QColor('#423634')); p.setFont(QFont('Microsoft YaHei UI',24,QFont.Bold)); p.drawText(40,54,title)
    p.setPen(QColor('#94807d')); p.setFont(QFont('Microsoft YaHei UI',11)); p.drawText(42,88,subtitle)
    return im,p
im,p=page('Floaty / 手绘气球','参考画风：炭笔颗粒轮廓 × 柔和粉彩平涂 · 全状态视觉示例，非实际 Jev 评分')
for i,(state,value,label) in enumerate(STATES):
    rect=QRectF(12+i%5*298,105+i//5*385,275,325)
    paint_sketch(p,rect,value,state,0,'none',state=='live')
    p.setPen(QColor('#73615f')); p.setFont(QFont('Microsoft YaHei UI',12)); p.drawText(QRectF(rect.x(),rect.y()+334,275,28),Qt.AlignCenter,label)
p.end(); im.save(str(root/'Floaty-sketch-states.png'))
im,p=page('Floaty / 小小帽子屋','装饰预览，不代表已获得 · 练习攒星点，升级解锁更多帽子')
for i,(hat,(name,cost,required)) in enumerate(list(HATS.items())[1:]):
    rect=QRectF(28+i%4*369,98+i//4*395,340,325)
    paint_sketch(p,rect,100,'live',0,hat,True)
    p.setPen(QColor('#564442')); p.setFont(QFont('Microsoft YaHei UI',12)); p.drawText(QRectF(rect.x(),rect.y()+328,340,26),Qt.AlignCenter,name)
    p.setPen(QColor('#94807d')); p.setFont(QFont('Microsoft YaHei UI',10)); p.drawText(QRectF(rect.x(),rect.y()+357,340,24),Qt.AlignCenter,f'{cost} 星点 · Lv.{required}')
p.end(); im.save(str(root/'Floaty-hats.png'))
frames=[]
for frame in range(75):
    im=QImage(420,500,QImage.Format_RGBA8888); im.fill(QColor('#f3e7e1')); p=QPainter(im)
    paint_sketch(p,QRectF(40,25,340,410),94,'live',frame*.067,'beret',True)
    p.setPen(QColor('#73615f')); p.setFont(QFont('Microsoft YaHei UI',11)); p.drawText(QRectF(0,457,420,25),Qt.AlignCenter,'眨眼聆听 · 动画与装饰示例')
    p.end(); frames.append(Image.frombytes('RGBA',(420,500),bytes(im.bits())).convert('RGB'))
frames[0].save(root/'Floaty-listening.gif',save_all=True,append_images=frames[1:],duration=67,loop=0)
