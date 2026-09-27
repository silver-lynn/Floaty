"""Render the actual native widget renderer, with explicitly illustrative values."""
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QPainter, QColor, QFont
from PySide6.QtCore import Qt, QRectF
from visual import paint_balloon

app=QApplication([])
image=QImage(1280,600,QImage.Format_ARGB32); image.fill(QColor('#f6f8fc'))
p=QPainter(image); p.setRenderHint(QPainter.Antialiasing)
p.setPen(QColor('#2776c9')); p.setFont(QFont('Segoe UI',30,QFont.DemiBold)); p.drawText(52,65,'Floaty')
p.setPen(QColor('#7b879c')); p.setFont(QFont('Microsoft YaHei UI',12)); p.drawText(54,100,'让好内容浮起来。')
for i,(value,state,label) in enumerate([(100,'initial','开场初始状态'),(78,'live','蓝紫 · 视觉示例'),(52,'live','柔紫 · 视觉示例'),(26,'live','灰紫 · 视觉示例'),(50,'waiting','等待 / 连接中断')]):
    rect=QRectF(20+i*248,135,248,310)
    paint_balloon(p,rect,value,state)
    p.setPen(QColor('#65738a')); p.setFont(QFont('Microsoft YaHei UI',11)); p.drawText(QRectF(rect.x(),455,248,35),Qt.AlignCenter,label)
p.setPen(QColor('#8793a6')); p.setFont(QFont('Microsoft YaHei UI',10)); p.drawText(54,553,'原生桌面组件渲染 · 示例值仅展示颜色与尺寸变化，不是 Jev 实测结果')
p.end(); image.save(str(Path(__file__).parent/'Floaty-preview.png'))
