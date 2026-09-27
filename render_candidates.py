from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage,QPainter,QColor,QFont
from PySide6.QtCore import Qt,QRectF
from mascots import paint_mascot,NAMES,STATES

app=QApplication([]); root=Path(__file__).parent
for variant,title in NAMES.items():
    image=QImage(1500,890,QImage.Format_ARGB32); image.fill(QColor('#f5f7fc'))
    p=QPainter(image); p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QColor('#344b70')); p.setFont(QFont('Microsoft YaHei UI',25,QFont.Bold)); p.drawText(44,56,'Floaty  /  '+title)
    p.setPen(QColor('#8493aa')); p.setFont(QFont('Microsoft YaHei UI',11)); p.drawText(46,89,'同一角色的完整状态 · 百分数为视觉示例 · 颜色与尺寸随指数变化')
    for i,(state,value,label) in enumerate(STATES):
        col=i%5; row=i//5; rect=QRectF(18+col*295,116+row*365,280,300)
        paint_mascot(p,rect,value,state,variant=variant)
        p.setPen(QColor('#63748e')); p.setFont(QFont('Microsoft YaHei UI',12)); p.drawText(QRectF(rect.x(),rect.y()+302,280,33),Qt.AlignCenter,label)
    p.setPen(QColor('#94a0b3')); p.setFont(QFont('Microsoft YaHei UI',10)); p.drawText(46,864,'等待、异常、结束状态不显示伪造分数。新外观待你选择；现有默认气球保持不变。')
    p.end(); image.save(str(root/f'Floaty-{variant}-states.png'))
