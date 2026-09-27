"""Linked, snapshot-faithful review: score window <-> transcript <-> radar."""
import html
import math
from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QPolygonF, QFont
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QPushButton,QTextBrowser,QSplitter
from rubric import DIMENSIONS

KEYS=list(DIMENSIONS)
LABELS=['打破预期','提问互动','记忆点','价值推进','理解连贯']
TIPS={
 'surprise':('把“新颖”说成一个可验证的反差','先说听众通常会怎样做，再给出这次不同的结果和原因；没有依据时不必制造惊喜。','通常我们会___；这次却___，因为___。'),
 'interaction':('给听众一个能回答的小任务','把泛泛的“对不对”换成具体选择、预测或经历回想，然后用后面的内容回应它。讲解阶段无需每段都插入问题。','如果只能先解决一个问题，你会选 A 还是 B？接下来用___来检验。'),
 'memory':('让这段话剩下一句能带走的结论','删去并列卖点，留下一个核心结论，用刚才的具体例子支撑它；不要添加未经验证的数字。','记住这一点：___。刚才的___就是一个例子。'),
 'value':('把功能连接到听众的实际任务','说清谁在什么场景卡住了、当前步骤解决什么，以及如何判断是否有用。','当你需要___时，原本要___；这一步帮你___，可以用___检查。'),
 'clarity':('补上听众需要的那一步解释','把术语换成日常说法，拆开长句，先给结论再讲原因；确认“它”“这个”指向明确。','先看___。它的意思是___。因此下一步是___。')
}

def stamp(t):
    t=max(0,float(t)); minutes=int(t)//60; seconds=t-minutes*60
    return f'{minutes:02}:{seconds:04.1f}'

def matched_indices(score,segments):
    """IDs survive ASR corrections. Legacy sessions use exact timestamps, never proximity."""
    result=[]
    for item in score.get('window',[]):
        for i,s in enumerate(segments):
            same=(str(s.get('id'))==str(item['id'])) if item.get('id') is not None and s.get('id') is not None else abs(s['t']-item['t'])<.001
            if same and i not in result:result.append(i)
    return result

def suggestions(score):
    valid=[k for k in KEYS if k in score.get('dimensions',{})]
    return sorted(valid,key=lambda k:score['dimensions'][k]['score'])[:2]

class AttentionCurve(QWidget):
    """Actual raw scores only; long missing intervals are never interpolated."""
    pointSelected=Signal(int)
    def __init__(self,scores,segments):
        super().__init__(); self.selected=None; self.setMinimumHeight(190); self.setMaximumHeight(240)
        self.setFocusPolicy(Qt.StrongFocus); self.setMouseTracking(True)
        self.setAccessibleName('注意力指数变化曲线，点击评分点或使用左右方向键选择')
        self.points=[]
        for i,s in enumerate(scores):
            try:t=float(s['t']); v=float(s['raw'])
            except (KeyError,TypeError,ValueError):continue
            if math.isfinite(t) and math.isfinite(v) and t>=0 and 0<=v<=100:self.points.append((i,t,v))
        self.points.sort(key=lambda item:item[1])
        times=[t for _,t,_ in self.points]
        for s in segments:
            try:t=float(s['t'])
            except (KeyError,TypeError,ValueError):continue
            if math.isfinite(t) and t>=0:times.append(t)
        self.duration=max([1]+times)
    def plot_rect(self):return QRectF(46,32,max(1,self.width()-76),max(1,self.height()-65))
    def position(self,point):
        _,t,value=point; r=self.plot_rect()
        return QPointF(r.left()+r.width()*t/self.duration,r.bottom()-r.height()*value/100)
    def connections(self):
        return [(a,b) for a,b in zip(self.points,self.points[1:]) if 0<b[1]-a[1]<=30]
    def select(self,index):self.selected=index; self.update()
    def closest(self,pos):
        if not self.points:return None
        p=min(self.points,key=lambda item:(self.position(item)-pos).manhattanLength())
        q=self.position(p)
        return p if math.hypot(q.x()-pos.x(),q.y()-pos.y())<=14 else None
    def mousePressEvent(self,event):
        if event.button()==Qt.LeftButton:
            p=self.closest(event.position())
            if p is not None:self.pointSelected.emit(p[0])
        super().mousePressEvent(event)
    def mouseMoveEvent(self,event):
        p=self.closest(event.position())
        self.setToolTip(f'{stamp(p[1])} · {p[2]:.0f}%' if p else '')
        self.setCursor(Qt.PointingHandCursor if p else Qt.ArrowCursor)
    def keyPressEvent(self,event):
        if event.key() in (Qt.Key_Left,Qt.Key_Right) and self.points:
            order=[p[0] for p in self.points]
            current=order.index(self.selected) if self.selected in order else (-1 if event.key()==Qt.Key_Right else len(order))
            target=max(0,min(len(order)-1,current+(1 if event.key()==Qt.Key_Right else -1)))
            self.pointSelected.emit(order[target]); event.accept(); return
        super().keyPressEvent(event)
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing); r=self.plot_rect()
        p.setFont(QFont('Microsoft YaHei UI',9)); p.setPen(QColor('#465b75'))
        p.drawText(QRectF(0,0,self.width(),24),Qt.AlignLeft,'注意力指数变化 · 内容吸引力估计（原始评分）')
        for value in (0,50,100):
            y=r.bottom()-r.height()*value/100
            p.setPen(QPen(QColor('#dce4ee'),1)); p.drawLine(QPointF(r.left(),y),QPointF(r.right(),y))
            p.setPen(QColor('#718197')); p.drawText(QRectF(0,y-10,38,20),Qt.AlignRight,str(value))
        for i in range(5):
            x=r.left()+r.width()*i/4
            p.drawText(QRectF(x-34,r.bottom()+7,68,22),Qt.AlignCenter,stamp(self.duration*i/4))
        p.setPen(QPen(QColor('#398ae6'),2))
        for a,b in self.connections():p.drawLine(self.position(a),self.position(b))
        for point in self.points:
            q=self.position(point); selected=point[0]==self.selected
            if selected:
                p.setPen(QPen(QColor('#b87339'),1,Qt.DashLine)); p.drawLine(QPointF(q.x(),r.top()),QPointF(q.x(),r.bottom()))
            p.setPen(QPen(QColor('#ffffff'),1)); p.setBrush(QColor('#b87339' if selected else '#398ae6'))
            p.drawEllipse(q,5 if selected else 3,5 if selected else 3)
        if not self.points:
            p.setPen(QColor('#8492a6')); p.drawText(r,Qt.AlignCenter,'暂无有效评分，仅有转写时不绘制曲线')
        p.end()

class Radar(QWidget):
    def __init__(self):
        super().__init__(); self.values=None; self.average=None; self.setMinimumSize(290,265)
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        cx=self.width()/2; cy=self.height()/2+6; radius=min(self.width()*.31,self.height()*.32)
        def pt(i,r):
            a=-math.pi/2+i*math.tau/5; return QPointF(cx+math.cos(a)*r,cy+math.sin(a)*r)
        p.setFont(QFont('Microsoft YaHei UI',9))
        for level in (.25,.5,.75,1):
            p.setPen(QPen(QColor('#e0e7f0'),1)); p.setBrush(Qt.NoBrush)
            p.drawPolygon(QPolygonF([pt(i,radius*level) for i in range(5)]))
        for i,label in enumerate(LABELS):
            p.drawLine(QPointF(cx,cy),pt(i,radius))
            point=pt(i,radius+34); p.setPen(QColor('#465b75'))
            text=label+('\n'+str(round(self.values[i])) if self.values is not None else '')
            p.drawText(QRectF(point.x()-52,point.y()-23,104,46),Qt.AlignCenter,text)
        p.setPen(QColor('#95a3b5')); p.drawText(QRectF(cx+3,cy-radius+2,45,18),Qt.AlignLeft,'100')
        for values,color,dashed in [(self.average,'#a6b4c6',True),(self.values,'#398ae6',False)]:
            if values is None:continue
            p.setPen(QPen(QColor(color),2,Qt.DashLine if dashed else Qt.SolidLine))
            p.setBrush(Qt.NoBrush if dashed else QColor(57,138,230,48))
            polygon=QPolygonF([pt(i,radius*max(0,min(100,v))/100) for i,v in enumerate(values)])
            p.drawPolygon(polygon)
            if not dashed:
                p.setBrush(QColor(color))
                for point in polygon:p.drawEllipse(point,3,3)
        if self.values is None:
            p.setPen(QColor('#8492a6')); p.drawText(self.rect(),Qt.AlignCenter,'此处尚无评分')
        p.end()

class ReviewPane(QWidget):
    def __init__(self,scores,segments):
        super().__init__(); self.scores=list(scores); self.segments=[dict(s) for s in segments]; self.selected=None
        box=QVBoxLayout(self); box.setContentsMargins(0,0,0,0)
        row=QHBoxLayout(); row.addWidget(QLabel('评分时间点'))
        self.selector=QComboBox(); self.selector.setPlaceholderText('当前转写尚未评分')
        for s in scores:self.selector.addItem(f"{stamp(s['t'])}  ·  {s['raw']:.0f}%")
        self.selector.setEnabled(bool(scores)); row.addWidget(self.selector,1)
        prev=QPushButton('上一处'); next_=QPushButton('下一处'); row.addWidget(prev); row.addWidget(next_); box.addLayout(row)
        prev.clicked.connect(lambda:self.selector.setCurrentIndex(max(0,self.selector.currentIndex()-1)))
        next_.clicked.connect(lambda:self.selector.setCurrentIndex(min(len(scores)-1,self.selector.currentIndex()+1)))
        self.window_label=QLabel(); self.window_label.setWordWrap(True); box.addWidget(self.window_label)
        self.curve=AttentionCurve(self.scores,self.segments); box.addWidget(self.curve)
        self.curve.pointSelected.connect(self.selector.setCurrentIndex)
        curve_hint=QLabel('点击曲线评分点联动原文与雷达图 · 超过 30 秒未评分处断开 · 不含开场初始 100%')
        curve_hint.setStyleSheet('color:#8793a6;font-size:11px'); curve_hint.setWordWrap(True); box.addWidget(curve_hint)
        split=QSplitter(Qt.Horizontal); box.addWidget(split,1)
        left=QWidget(); left_box=QVBoxLayout(left); left_box.setContentsMargins(0,0,8,0)
        self.radar=Radar(); left_box.addWidget(self.radar)
        legend=QLabel('蓝色：当前片段  ·  灰色虚线：各次评分均值'); legend.setStyleSheet('color:#8793a6;font-size:11px'); left_box.addWidget(legend)
        self.advice=QTextBrowser(); self.advice.setOpenLinks(False); self.advice.setMinimumHeight(140); left_box.addWidget(self.advice,1)
        split.addWidget(left)
        right=QWidget(); right_box=QVBoxLayout(right); right_box.setContentsMargins(8,0,0,0)
        right_box.addWidget(QLabel('完整转写 · 蓝色段落为本次评分内容 · 点击时间可反查评分'))
        self.transcript=QTextBrowser(); self.transcript.setOpenLinks(False); self.transcript.anchorClicked.connect(self.from_transcript)
        right_box.addWidget(self.transcript,1); split.addWidget(right); split.setSizes([410,510])
        self.radar.average=[sum(s['dimensions'][k]['score'] for s in scores)/len(scores) for k in KEYS] if scores else None
        self.selector.currentIndexChanged.connect(self.select_score)
        if scores:self.select_score(0)
        else:
            self.window_label.setText('没有有效 Jev 评分。原文仍可查看；不会生成雷达数据或诊断。')
            self.advice.setPlainText('获得有效 Jev 评分后，这里会显示与当前片段对应的练习方向。')
            self.render_transcript([])

    def render_transcript(self,selected):
        parts=[]
        for i,s in enumerate(self.segments):
            bg='#e7f1ff' if i in selected else '#ffffff'
            parts.append(f'<a name="s{i}"></a><table width="100%" bgcolor="{bg}" cellpadding="10"><tr><td><a href="segment:{i}" style="color:#287cc9">{stamp(s["t"])}</a><br>{html.escape(s["text"])}</td></tr></table><br>')
        self.transcript.setHtml(''.join(parts) or '<p>尚无转写。</p>')

    def select_score(self,index):
        if not 0<=index<len(self.scores):return
        self.selected=index; s=self.scores[index]; indices=matched_indices(s,self.segments)
        self.curve.select(index)
        self.window_label.setText(f"评分时间 {stamp(s['t'])}  ·  评估窗口 {stamp(max(0,s['t']-30))}—{stamp(s['t'])}  ·  原始指数 {s['raw']:.0f}%")
        self.radar.values=[s['dimensions'][k]['score'] for k in KEYS]; self.radar.update()
        self.render_transcript(indices)
        if indices:self.transcript.scrollToAnchor('s'+str(indices[0]))
        parts=['<h3>这段内容，下一次怎么练？</h3>']
        for key in suggestions(s):
            title,action,frame=TIPS[key]; value=s['dimensions'][key]['score']
            level='优先练习' if value<65 else '可进一步打磨'
            parts.append(f'<p><b>{level} · {DIMENSIONS[key][0]} {value:.0f}/100</b><br>{title}<br>{action}</p><p style="color:#357bc2">句式提示：{frame}</p>')
            target=s.get('improvement_targets',{}).get(key)
            if target:parts.append(f'<p><b>Jev 建议关注的原句 · {stamp(target["t"])}</b><br>「{html.escape(target["text"])}」</p>')
        parts.append('<p style="color:#8793a6">练习方向按本段评分匹配，不是对观众反应的实测诊断；请结合下面的原文判断。</p><h4>评分时的原文快照</h4>')
        for item in s.get('window',[]):
            parts.append(f'<p><b>{stamp(item["t"])}</b> {html.escape(item["text"])}</p>')
        current_text={str(self.segments[i].get('id')):self.segments[i]['text'] for i in indices}
        if any(item.get('id') is not None and str(item['id']) in current_text and current_text[str(item['id'])]!=item['text'] for item in s.get('window',[])):
            parts.insert(0,'<p style="color:#a27132">这段转写后来有修正。评分依据是下方快照，右侧显示最新转写。</p>')
        self.advice.setHtml(''.join(parts))

    def from_transcript(self,url):
        try:index=int(url.toString().split(':')[1])
        except (ValueError,IndexError):return
        if not 0<=index<len(self.segments):return
        matches=[i for i,s in enumerate(self.scores) if index in matched_indices(s,self.segments)]
        if matches:
            chosen=self.selected if self.selected in matches else matches[0]
            self.selector.setCurrentIndex(chosen); self.select_score(chosen)
            self.transcript.scrollToAnchor('s'+str(index))
        else:
            self.selector.setCurrentIndex(-1)
            self.selected=None; self.radar.values=None; self.radar.update()
            self.curve.select(None)
            self.window_label.setText(f'{stamp(self.segments[index]["t"])} · 这句话没有对应评分，不使用邻近分数替代。')
            self.advice.setPlainText('这句话尚未被任何有效评分窗口覆盖。可能位于排练尾部、服务异常期间，或文字不足以评分。')
            self.render_transcript([index]); self.transcript.scrollToAnchor('s'+str(index))
