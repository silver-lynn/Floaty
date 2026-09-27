from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QPushButton,QScrollArea,QGridLayout
from growth import HATS,level
from sketch import paint_sketch

class HatPreview(QWidget):
    def __init__(self,hat):super().__init__(); self.hat=hat; self.setMinimumSize(140,185)
    def paintEvent(self,event):
        p=QPainter(self); paint_sketch(p,QRectF(self.rect()),100,'live',0,self.hat); p.end()

class Wardrobe(QWidget):
    def __init__(self,owner):
        super().__init__(); self.owner=owner
        box=QVBoxLayout(self); self.heading=QLabel(); self.heading.setStyleSheet('font-size:20px;font-weight:600;color:#4b4140'); box.addWidget(self.heading)
        self.note=QLabel('每次有效练习 +10 星点；每 3 次升一级，升级额外 +5。\n有效练习：至少 60 秒、80 字确认转写，且发言跨越 20 秒。分数高低不影响奖励。')
        self.note.setWordWrap(True); box.addWidget(self.note)
        self.message=QLabel(); self.message.setWordWrap(True); box.addWidget(self.message)
        area=QScrollArea(); area.setWidgetResizable(True); content=QWidget(); grid=QGridLayout(content)
        self.buttons={}
        for i,(key,(name,cost,required)) in enumerate(HATS.items()):
            card=QWidget(); card.setStyleSheet('QWidget {background:#f7efea;}'); layout=QVBoxLayout(card)
            layout.addWidget(HatPreview(key)); layout.addWidget(QLabel(name))
            layout.addWidget(QLabel('免费' if key=='none' else f'{cost} 星点 · Lv.{required} 解锁'))
            button=QPushButton(); button.clicked.connect(lambda checked=False,k=key:self.choose(k)); layout.addWidget(button)
            self.buttons[key]=button; grid.addWidget(card,i//3,i%3)
        area.setWidget(content); box.addWidget(area,1); self.refresh()
    def refresh(self):
        try:data=self.owner.growth.read()
        except Exception:
            self.message.setText('成长记录暂时无法读取，已保留原文件。')
            for button in self.buttons.values():button.setEnabled(False)
            return
        self.heading.setText(f"Floaty 的帽子屋  ·  Lv.{level(data)}  ·  {data['coins']} 星点")
        self.message.setText(f"已完成 {data['sessions']} 次有效练习，距离下一级还需 {3-data['sessions']%3} 次。")
        for key,button in self.buttons.items():
            owned=key in data['owned']; _,cost,required=HATS[key]
            button.setText('已佩戴' if data['equipped']==key else '佩戴' if owned else '等级未解锁' if level(data)<required else '星点不足' if data['coins']<cost else '兑换并佩戴')
            button.setEnabled(data['equipped']!=key and (owned or (level(data)>=required and data['coins']>=cost)))
    def choose(self,key):
        try:
            self.owner.profile=self.owner.growth.redeem(key)
            self.owner.balloon_variant='sketch'; self.owner.update(); self.refresh()
        except ValueError as e:self.message.setText(str(e))
        except Exception:self.message.setText('未能保存装饰，兑换未完成，请稍后重试。')
