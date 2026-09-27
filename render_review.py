"""Native UI render using labeled synthetic examples, never live evaluation evidence."""
from pathlib import Path
from PySide6.QtWidgets import QApplication,QDialog,QVBoxLayout,QLabel
from PySide6.QtGui import QFont
from PySide6.QtCore import QTimer
from floaty import STYLE
from review import ReviewPane
from test_review import fixtures

app=QApplication([]); app.setFont(QFont('Microsoft YaHei UI',9))
d=QDialog(); d.setStyleSheet(STYLE); d.resize(1080,740); box=QVBoxLayout(d)
heading=QLabel('Floaty 内容复盘  /  交互预览 · 示例评分，非 Jev 实测'); heading.setStyleSheet('font-size:19px;font-weight:600'); box.addWidget(heading)
scores,segments=fixtures(); pane=ReviewPane(scores,segments); box.addWidget(pane); pane.selector.setCurrentIndex(1)
d.show()
def capture():
    d.grab().save(str(Path(__file__).parent/'Floaty-review-v3.png')); app.quit()
QTimer.singleShot(200,capture); app.exec()
