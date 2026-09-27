"""Floaty — native Windows corner companion. No browser or local web server."""
import json
import math
import sys
import threading
import time
import urllib.error
import uuid
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal, QObject, QRectF, QProcess
from PySide6.QtGui import QPainter, QColor, QPen, QIcon, QPixmap, QAction, QFont, QPainterPath
from PySide6.QtWidgets import (QApplication, QWidget, QSystemTrayIcon, QMenu, QDialog,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QComboBox, QTextEdit,
    QFileDialog, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QScrollArea, QCheckBox)

from engine import evaluate, key_from_store, smooth
from rubric import VERSION, DIMENSIONS, WEIGHTS, EVENTS
from speech import Speech, cloud_key, verify_key
from subtitles import Subtitles
from key_status import KeyStatus
from preferences import load_keys, save_keys
from review import ReviewPane
from mascots import paint_mascot,NAMES
from visual import paint_balloon
from sketch import paint_sketch
from growth import Growth,default as growth_default
from wardrobe import Wardrobe

ROOT=Path(__file__).resolve().parent
STYLE='''
QDialog { background:#f6f8fc; color:#27354d; }
QLabel { color:#34435c; font-size:13px; }
QLineEdit,QComboBox,QTextEdit,QTableWidget { background:white; color:#27354d; border:1px solid #dce3ef; border-radius:8px; padding:9px; selection-background-color:#d9eaff; }
QPushButton { background:#e8edf6; color:#34435c; border:0; border-radius:9px; padding:11px 18px; font-size:13px; }
QPushButton:hover { background:#d9e6fa; }
QPushButton#primary { background:#358ce9; color:white; }
QPushButton:disabled { background:#e5e8ed; color:#9ca5b5; }
QTabWidget::pane { border:0; }
QTabBar::tab { padding:12px 16px; color:#69768c; }
QTabBar::tab:selected { color:#277edb; border-bottom:2px solid #358ce9; }
QMenu { background:#fff; color:#27354d; border:1px solid #dce3ef; padding:7px; }
QMenu::item { padding:8px 24px; }
QMenu::item:selected { background:#e7f1ff; border-radius:5px; }
'''

class Bus(QObject):
    speech=Signal(int,object)
    result=Signal(int,object)
    failure=Signal(int,str)
    credential=Signal(str,str,str,str)

class Chart(QWidget):
    def __init__(self, scores):
        super().__init__(); self.scores=scores; self.setMinimumHeight(180)
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w=self.width()-58; h=self.height()-42
        p.fillRect(self.rect(),QColor('white'))
        for n in (0,25,50,75,100):
            y=12+h*(1-n/100); p.setPen(QColor('#e6ebf3')); p.drawLine(38,int(y),self.width()-20,int(y))
            p.setPen(QColor('#8b96a9')); p.drawText(QRectF(0,y-8,30,18),Qt.AlignRight,str(n))
        if not self.scores:
            p.drawText(self.rect(),Qt.AlignCenter,'尚无有效 Jev 评分'); return
        end=max(1,self.scores[-1]['t'])
        for field,color in [('raw','#b9cbe5'),('display','#348ce9')]:
            path=QPainterPath()
            for i,s in enumerate(self.scores):
                x=38+w*s['t']/end; y=12+h*(1-s[field]/100)
                if i==0: path.moveTo(x,y)
                else: path.lineTo(x,y)
                p.setBrush(QColor(color)); p.setPen(Qt.NoPen); p.drawEllipse(QRectF(x-2,y-2,4,4))
            p.setPen(QPen(QColor(color),2)); p.setBrush(Qt.NoBrush); p.drawPath(path)
        p.setPen(QColor('#8b96a9')); p.drawText(38,self.height()-6,'00:00')
        p.drawText(self.width()-65,self.height()-6,stamp(end))

def stamp(t): return f'{int(t)//60:02}:{int(t)%60:02}'

class Floaty(QWidget):
    def __init__(self):
        super().__init__(None,Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint|Qt.Tool)
        self.setWindowTitle('Floaty'); self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(230,290); self.setMouseTracking(True)
        area=QApplication.primaryScreen().availableGeometry()
        self.move(area.right()-250,area.top()+70)
        self.state='idle'; self.value=100.; self.target=100.; self.active=False; self.finishing=False
        self.generation=0; self.busy=False; self.segments=[]; self.scores=[]; self.memory=[]
        self.started=0.; self.last_request=-100.; self.last_fingerprint=''; self.last_success=0.
        saved=load_keys()
        self.key=saved.get('jev',''); self.speech_key=saved.get('asr',''); self.device=None; self.speaker=None
        self.growth=Growth(); self.session_id=None; self.practice_duration=None; self.reward_message=''
        try:self.profile=self.growth.read()
        except Exception:self.profile=growth_default()
        self.balloon_variant='sketch'; self.key_status=KeyStatus(); self.key_checks=set(); self.subtitles=Subtitles(self)
        self.audience='首次接触产品、熟悉一般软件的潜在用户'; self.message='右键开始排练 · 双击打开设置'
        self.dialogs=[]; self.locked=False; self.passthrough=False; self.drag=None; self.ticks=0
        self.bus=Bus(); self.bus.speech.connect(self.on_speech); self.bus.result.connect(self.on_result); self.bus.failure.connect(self.on_failure); self.bus.credential.connect(self.on_credential)
        self.timer=QTimer(self); self.timer.timeout.connect(self.tick); self.timer.start(33)
        icon=QPixmap(64,64); icon.fill(Qt.transparent); p=QPainter(icon)
        paint_sketch(p,QRectF(0,-4,64,80),100,'idle'); p.end()
        self.setWindowIcon(QIcon(icon)); self.tray=QSystemTrayIcon(QIcon(icon),self)
        self.tray.setToolTip('Floaty · 你的演讲浮力'); self.tray.activated.connect(self.tray_click)
        self.menu=QMenu(); self.menu.setStyleSheet(STYLE); self.menu.aboutToShow.connect(self.update_menu)
        self.start_action=self.menu.addAction('开始排练',self.toggle)
        self.menu.addAction('设置 / Jev 密钥',self.settings)
        self.menu.addAction('本次复盘',self.review)
        self.menu.addAction('成长 / 帽子屋',self.wardrobe)
        skins=self.menu.addMenu('气球外观')
        skins.addAction('手绘 Floaty（默认）',lambda:self.set_balloon_variant('sketch'))
        skins.addAction('原版',lambda:self.set_balloon_variant('classic'))
        for variant,label in NAMES.items():skins.addAction(label,lambda checked=False,v=variant:self.set_balloon_variant(v))
        self.caption_action=self.menu.addAction('显示悬浮字幕',self.toggle_subtitles); self.caption_action.setCheckable(True)
        sizes=self.menu.addMenu('字幕字号')
        for size,label in [(36,'大 · 36'),(48,'更大 · 48（默认）'),(64,'超大 · 64')]:
            sizes.addAction(label,lambda checked=False,n=size:self.subtitles.set_size(n))
        self.menu.addAction('字幕回到屏幕底部',self.subtitles.reset_position)
        self.menu.addSeparator()
        self.lock_action=self.menu.addAction('锁定位置',self.lock); self.lock_action.setCheckable(True)
        self.pass_action=self.menu.addAction('鼠标穿透（从托盘恢复）',self.pass_through); self.pass_action.setCheckable(True)
        self.menu.addAction('收回屏幕角落',self.reset_position)
        self.menu.addSeparator(); self.menu.addAction('重启应用',self.restart)
        self.menu.addAction('退出 Floaty',self.quit)
        self.tray.setContextMenu(self.menu); self.tray.show()
        self.setToolTip(self.message)

    def update_menu(self):
        self.start_action.setText('结束排练' if self.active else '开始新排练')
        self.start_action.setEnabled(not self.finishing)
        self.lock_action.setChecked(self.locked); self.pass_action.setChecked(self.passthrough)
        self.caption_action.setChecked(self.subtitles.enabled)

    def set_subtitles_enabled(self,enabled):
        self.subtitles.set_enabled(enabled)
        if hasattr(self,'caption_checkbox') and self.settings_window in self.dialogs:
            self.caption_checkbox.blockSignals(True); self.caption_checkbox.setChecked(enabled); self.caption_checkbox.blockSignals(False)
        self.caption_action.setChecked(enabled)

    def toggle_subtitles(self):self.set_subtitles_enabled(not self.subtitles.enabled)

    def reset_position(self):
        area=QApplication.primaryScreen().availableGeometry(); self.move(area.right()-250,area.top()+70)
        if self.passthrough: self.pass_through()
        self.show(); self.raise_()

    def tray_click(self,reason):
        if reason==QSystemTrayIcon.DoubleClick: self.settings()

    def lock(self):
        self.drag=None
        self.locked=not self.locked

    def pass_through(self):
        self.drag=None
        self.passthrough=not self.passthrough
        self.setWindowFlag(Qt.WindowTransparentForInput,self.passthrough); self.show()
        self.subtitles.set_passthrough(self.passthrough)

    def contextMenuEvent(self,event):
        self.drag=None
        self.menu.popup(event.globalPos())
    def mouseDoubleClickEvent(self,event):
        self.drag=None
        self.settings()
    def mousePressEvent(self,event):
        self.drag=None
        if event.button()==Qt.LeftButton and not self.locked:
            self.drag=event.globalPosition().toPoint()-self.pos()
    def mouseMoveEvent(self,event):
        # A dialog can consume the release event after a double-click.
        # Never continue an old drag when the left button is no longer held.
        if self.locked or not (event.buttons() & Qt.LeftButton):
            self.drag=None
            return
        if self.drag is not None: self.move(event.globalPosition().toPoint()-self.drag)
    def mouseReleaseEvent(self,event): self.drag=None
    def set_balloon_variant(self,variant):
        self.balloon_variant=variant; self.update()

    def paintEvent(self,event):
        p=QPainter(self)
        if self.balloon_variant=='sketch':paint_sketch(p,QRectF(self.rect()),self.value,self.state,self.ticks*.033,self.profile['equipped'],self.active)
        elif self.balloon_variant=='classic':paint_balloon(p,QRectF(self.rect()),self.value,self.state,self.ticks*.033)
        else:paint_mascot(p,QRectF(self.rect()),self.value,self.state,self.ticks*.033,self.balloon_variant)
        p.end()

    def status(self,state,message):
        self.state=state; self.message=message
        self.setToolTip('Floaty · '+message)
        self.tray.setToolTip('Floaty · '+message[:100]); self.update()

    def tick(self):
        self.ticks+=1
        self.value+=(self.target-self.value)*.025
        if abs(self.value-self.target)<.02: self.value=self.target
        if self.active and self.ticks%15==0:
            now=time.monotonic()-self.started
            if now>=12 and self.state=='initial' and not self.scores:
                self.status('waiting','正在积累语音并等待 Jev 首次评分')
            if self.segments and now-self.segments[-1]['t']>30:
                self.status('waiting','最近 30 秒没有新的完整语句')
            elif self.scores and now-self.last_success>35:
                self.status('waiting','评分已过期，等待新内容或服务恢复')
            if now-self.last_request>=8: self.request_score(now)
        self.update()

    def toggle(self):
        if self.active: self.stop()
        else: self.start()

    def start(self):
        if self.finishing: return
        if self.speaker and self.speaker.thread and self.speaker.thread.is_alive():
            self.notify('上一场语音连接正在结束，请稍后重试。'); return
        if not (self.key or key_from_store()) or not (self.speech_key or cloud_key()):
            self.settings(); self.notify('请先填写 Jev 和语音识别密钥。'); return
        if (self.segments or self.scores) and not getattr(self,'exported',False):
            answer=QMessageBox.question(self,'开始新排练','新排练将清空上次未导出的复盘。继续？',QMessageBox.Yes|QMessageBox.No)
            if answer!=QMessageBox.Yes: return
        self.session_id=str(uuid.uuid4()); self.practice_duration=None; self.reward_message=''
        self.generation+=1; token=self.generation
        self.active=True; self.busy=False; self.segments=[]; self.scores=[]; self.memory=[]; self.exported=False
        self.started=time.monotonic(); self.last_request=-100; self.last_fingerprint=''; self.last_success=0
        self.value=self.target=100
        self.subtitles.clear(); self.subtitles.set_caption('正在聆听…')
        self.status('initial','100% 为开场初始状态；正在连接麦克风')
        self.speaker=Speech(lambda d:self.bus.speech.emit(token,d),self.speech_key or cloud_key(),self.device)
        self.speaker.start()

    def stop(self):
        if not self.active: return
        self.practice_duration=time.monotonic()-self.started
        self.active=False; self.finishing=True; self.status('stopping','正在收取最后一句语音')
        if self.speaker: self.speaker.stop()
        token=self.generation
        QTimer.singleShot(12000,lambda:self.finish_stop() if token==self.generation else None)

    def finish_stop(self):
        if not self.finishing:return
        self.finishing=False; self.generation+=1; self.busy=False
        self.settle_practice()
        self.subtitles.clear()
        self.status('paused','排练已结束 · 右键查看复盘')
        self.review()

    def on_speech(self,token,event):
        if token!=self.generation: return
        if event['type']=='ready':
            self.status('initial','正在聆听 · 100% 为初始状态，等待 Jev 评分')
        elif event['type']=='partial' and self.active:
            self.subtitles.set_caption(event.get('text',''))
        elif event['type']=='final' and (self.active or self.finishing):
            text=event.get('text','').strip()
            if not text:return
            now=time.monotonic()-self.started
            old=next((s for s in self.segments if s['id']==event.get('id')),None)
            if old: old['text']=text
            else:self.segments.append({'id':event.get('id',str(len(self.segments))),'t':now,'text':text})
            if not old or old is self.segments[-1]:self.subtitles.set_caption(text)
        elif event['type']=='error':
            self.settle_practice()
            self.active=False; self.finishing=False; self.generation+=1; self.busy=False
            self.subtitles.clear()
            self.status('error',event['message']); self.notify(event['message'])
        elif event['type']=='finished' and self.finishing:
            # Final confirmed transcript is retained. No invented tail score.
            self.finish_stop()

    def request_score(self,now):
        if self.busy or not self.active:return
        current=[s for s in self.segments if s['t']>now-30]
        if sum(len(s['text']) for s in current)<12:return
        fingerprint=json.dumps(current,ensure_ascii=False)
        if fingerprint==self.last_fingerprint:return
        self.busy=True; self.last_request=now; token=self.generation
        segments=[dict(s) for s in self.segments[-5000:]]; memory=[dict(m) for m in self.memory[-16:]]
        key=self.key or key_from_store(); audience=self.audience
        def worker():
            try:
                result=evaluate(segments,now,audience,key,memory)
                result['_fingerprint']=fingerprint; self.bus.result.emit(token,result)
                self.bus.credential.emit('jev',key,'valid','验证通过 · Jev 可用')
            except urllib.error.HTTPError as e:
                self.bus.credential.emit('jev',key,'failed',f'验证失败 · HTTP {e.code}')
                self.bus.failure.emit(token,f'Jev 返回 HTTP {e.code}。请检查密钥、额度和权限。')
            except Exception:
                self.bus.failure.emit(token,'Jev 连接超时或返回无效数据，本次没有产生分数。')
        threading.Thread(target=worker,daemon=True).start()

    def on_result(self,token,result):
        if token!=self.generation:return
        self.busy=False
        if not self.active:return
        self.last_fingerprint=result.pop('_fingerprint','')
        prev=self.scores[-1] if self.scores else None
        result['display']=smooth(result['raw'],prev['display'] if prev else None,result['t']-prev['t'] if prev else 8)
        self.scores.append(result); self.target=result['display']; self.last_success=time.monotonic()-self.started
        self.status('live',f"Jev · {result['model']} · 内容吸引力指数，非实际留存率")
        for key,probability in result['events'].items():
            evidence=result.get('event_evidence',{}).get(key)
            if evidence and probability>=.8:
                m={'t':evidence['t'],'text':evidence['text'][:700],'events':[EVENTS[key][0]]}
                existing=next((x for x in self.memory if x['t']==m['t'] and x['text']==m['text']),None)
                if existing:
                    if EVENTS[key][0] not in existing['events']:existing['events'].append(EVENTS[key][0])
                else:self.memory.append(m)
        self.memory=self.memory[-16:]

    def on_failure(self,token,message):
        if token!=self.generation:return
        self.busy=False; self.status('error',message)
        # Rate-limit repeated failures, permit recovery without fabricated fallback.
        self.last_request=time.monotonic()-self.started+12
        if not getattr(self,'last_notified','')==message:self.notify(message)
        self.last_notified=message

    def notify(self,message): self.tray.showMessage('Floaty',message,QSystemTrayIcon.Information,6000)

    def window(self,title,w=560,h=600):
        d=QDialog(self,Qt.Window); d.setWindowTitle(title); d.resize(w,h); d.setStyleSheet(STYLE)
        d.setAttribute(Qt.WA_DeleteOnClose); self.dialogs.append(d)
        d.destroyed.connect(lambda:self.dialogs.remove(d) if d in self.dialogs else None)
        return d

    def settings(self):
        if hasattr(self,'settings_window') and self.settings_window in self.dialogs:
            self.settings_window.show(); self.settings_window.raise_(); self.settings_window.activateWindow(); return
        d=self.window('Floaty · 让好内容浮起来',560,min(780,self.screen().availableGeometry().height()-70)); self.settings_window=d
        outer=QVBoxLayout(d); outer.setContentsMargins(0,0,0,0)
        scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QScrollArea.NoFrame)
        content=QWidget(); scroll.setWidget(content); outer.addWidget(scroll)
        box=QVBoxLayout(content); box.setContentsMargins(26,20,26,20); box.setSpacing(10)
        title=QLabel('Floaty'); title.setStyleSheet('font-size:32px; font-weight:600; color:#358ce9'); box.addWidget(title)
        intro=QLabel('你的演讲浮力。\n右键管理排练，拖动气球改变位置；托盘图标可恢复鼠标操作。'); intro.setWordWrap(True); box.addWidget(intro)
        self.caption_checkbox=QCheckBox('显示悬浮字幕（演讲时也可随时开关）')
        self.caption_checkbox.setChecked(self.subtitles.enabled)
        self.caption_checkbox.setStyleSheet('font-size:14px;color:#34435c;padding:8px 0;')
        self.caption_checkbox.toggled.connect(self.set_subtitles_enabled); box.addWidget(self.caption_checkbox)
        box.addWidget(QLabel('TypeSafe / Jev API 密钥'))
        jev=QLineEdit(self.key or key_from_store()); jev.setEchoMode(QLineEdit.Password); jev.setPlaceholderText('填写 Jev 密钥'); box.addWidget(jev)
        jev_state=QLabel(); box.addWidget(jev_state)
        box.addWidget(QLabel('豆包语音 API 密钥'))
        asr=QLineEdit(self.speech_key or cloud_key()); asr.setEchoMode(QLineEdit.Password); asr.setPlaceholderText('填写流式语音识别密钥'); box.addWidget(asr)
        asr_state=QLabel(); box.addWidget(asr_state)
        self.key_fields={'jev':jev,'asr':asr}; self.key_labels={'jev':jev_state,'asr':asr_state}
        jev.textChanged.connect(self.refresh_key_labels); asr.textChanged.connect(self.refresh_key_labels)
        self.refresh_key_labels()
        box.addWidget(QLabel('麦克风')); device=QComboBox(); device.addItem('系统默认麦克风',None)
        try:
            import sounddevice as sd
            for i,item in enumerate(sd.query_devices()):
                if item['max_input_channels']>0:device.addItem(item['name'],i)
        except Exception:pass
        device.setCurrentIndex(max(0,device.findData(self.device))); box.addWidget(device)
        box.addWidget(QLabel('这次讲给谁听')); audience=QLineEdit(self.audience); box.addWidget(audience)
        note=QLabel('密钥加密保存在本机，输入框始终用掩码显示。\n字幕默认开启：透明底、大号白字。音频交给豆包，文字交给 Jev。'); note.setWordWrap(True); note.setStyleSheet('color:#7b879c;font-size:12px'); box.addWidget(note)
        status=QLabel(self.message); status.setWordWrap(True); box.addWidget(status)
        row=QHBoxLayout(); save=QPushButton('应用并验证密钥'); begin=QPushButton('开始排练'); begin.setObjectName('primary')
        row.addWidget(save); row.addWidget(begin); box.addLayout(row)
        restart_button=QPushButton('重启应用'); restart_button.clicked.connect(self.restart); box.addWidget(restart_button)
        def apply():
            for field in (jev,asr):
                v=field.text().strip()
                if v and (len(v)<8 or any(c.isspace() for c in v)):
                    status.setText('密钥格式不正确，请完整粘贴且不要包含空格。'); return False
            if jev.text().strip():self.key=jev.text().strip()
            if asr.text().strip():self.speech_key=asr.text().strip()
            jev.setText(self.key or key_from_store()); asr.setText(self.speech_key or cloud_key())
            self.device=device.currentData(); self.audience=audience.text().strip() or self.audience
            try:
                save_keys(self.key or key_from_store(),self.speech_key or cloud_key())
                status.setText('已加密保存，密钥以掩码保留。')
            except Exception:
                status.setText('已应用，但本机加密保存失败；此次只在内存中保留。')
            self.refresh_key_labels(); return True
        def apply_and_verify():
            if apply():self.verify_credentials()
        save.clicked.connect(apply_and_verify)
        def launch():
            if apply():d.close(); self.start()
        begin.clicked.connect(launch); begin.setEnabled(not self.active and not self.finishing)
        d.show(); d.raise_(); d.activateWindow()

    def refresh_key_labels(self):
        if not hasattr(self,'key_fields') or self.settings_window not in self.dialogs:return
        colors={'empty':'#8793a6','pending':'#96733b','checking':'#357fc8','valid':'#20845d','failed':'#bd4e57'}
        for provider,field in self.key_fields.items():
            state,message=self.key_status.get(provider,field.text().strip())
            self.key_labels[provider].setText(('✓ ' if state=='valid' else '● ')+message)
            self.key_labels[provider].setStyleSheet('font-size:12px;color:'+colors[state])

    def on_credential(self,provider,key,state,message):
        self.key_checks.discard((provider,self.key_status.fingerprint(key)))
        current=(self.key or key_from_store()) if provider=='jev' else (self.speech_key or cloud_key())
        if key!=current:return
        self.key_status.set(provider,key,state,message)
        self.refresh_key_labels()

    def verify_credentials(self):
        for provider,key in [('jev',self.key or key_from_store()),('asr',self.speech_key or cloud_key())]:
            if not key:continue
            identity=(provider,self.key_status.fingerprint(key))
            if identity in self.key_checks:continue
            self.key_checks.add(identity); self.key_status.set(provider,key,'checking','正在验证服务可用性…')
            def run(provider=provider,key=key):
                try:
                    if provider=='jev':
                        r=evaluate([{'t':8,'text':'这个工具把每个结论链接到原话，先核对证据，再采用结论。'}],8,key=key)
                        message=f"验证通过 · {r['model']} 可用"
                    else:
                        verify_key(key); message='验证通过 · 豆包语音可用'
                    self.bus.credential.emit(provider,key,'valid',message)
                except urllib.error.HTTPError as e:
                    self.bus.credential.emit(provider,key,'failed',f'验证失败 · HTTP {e.code}')
                except Exception as e:
                    code=getattr(getattr(e,'response',None),'status_code',None)
                    message=f'验证失败 · HTTP {code}' if code else '暂不可用 · 请检查网络、密钥或服务权限'
                    self.bus.credential.emit(provider,key,'failed',message)
            threading.Thread(target=run,daemon=True).start()
        self.refresh_key_labels()

    def settle_practice(self):
        if not self.session_id:return
        duration=self.practice_duration if self.practice_duration is not None else max(0,time.monotonic()-self.started)
        try:
            self.profile,self.reward_message=self.growth.reward(self.session_id,duration,self.segments)
            self.session_id=None
        except Exception:self.reward_message='成长记录未能保存，请保留本次记录后稍后重试。'

    def wardrobe(self):
        d=self.window('Floaty · 成长与帽子屋',740,min(800,self.screen().availableGeometry().height()-60))
        box=QVBoxLayout(d); box.addWidget(Wardrobe(self)); d.show()

    def review(self):
        area=self.screen().availableGeometry()
        d=self.window('Floaty · 内容复盘',min(1120,area.width()-50),min(820,area.height()-60))
        box=QVBoxLayout(d); box.setContentsMargins(20,16,20,16)
        heading=QLabel('找到原句，再改进表达。'); heading.setStyleSheet('font-size:22px;font-weight:600'); box.addWidget(heading)
        if self.reward_message:
            reward=QLabel(self.reward_message); reward.setWordWrap(True); box.addWidget(reward)
        self.review_pane=ReviewPane(self.scores,self.segments); box.addWidget(self.review_pane,1)
        row=QHBoxLayout(); row.addWidget(QLabel('内容吸引力指数，非实际留存率。开场 100% 不计入评分。')); row.addStretch()
        export=QPushButton('导出本次记录'); export.clicked.connect(self.export); row.addWidget(export); box.addLayout(row)
        d.show()

    def export(self):
        path,_=QFileDialog.getSaveFileName(self,'保存 Floaty 复盘',f'floaty-{time.strftime("%Y%m%d-%H%M%S")}.json','JSON (*.json)')
        if path:
            try:
                Path(path).write_text(json.dumps({'product':'Floaty','rubric':VERSION,'createdAt':time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'audience':self.audience,'initialState':{'value':100,'measured':False},'segments':self.segments,'scores':self.scores,'memory':self.memory,'meaning':'内容吸引力指数，非实际注意力或留存率'},ensure_ascii=False,indent=2),encoding='utf-8')
                self.exported=True
            except OSError:QMessageBox.warning(self,'保存失败','无法写入所选位置，请选择其他文件夹。')

    def restart(self):
        if self.active or self.finishing or self.busy:
            QMessageBox.information(self,'先结束排练','请先结束排练，等待转写和评分完成，再重启。'); return
        if (self.segments or self.scores) and not getattr(self,'exported',False):
            self.export()
            if not getattr(self,'exported',False):return
        self.quit(restarting=True)

    def quit(self,restarting=False):
        self.settle_practice()
        self.active=False; self.generation+=1
        if self.speaker:self.speaker.stop()
        self.subtitles.clear(); self.subtitles.close()
        self.tray.hide(); QApplication.exit(75 if restarting else 0)

def main():
    app=QApplication(sys.argv); app.setQuitOnLastWindowClosed(False); app.setApplicationName('Floaty'); app.setFont(QFont('Microsoft YaHei UI',9))
    # Single instance: a second launch asks the existing app to show its settings.
    from PySide6.QtNetwork import QLocalServer, QLocalSocket
    socket=QLocalSocket(); socket.connectToServer('floaty-desktop-v1')
    if socket.waitForConnected(300):socket.write(b'show'); socket.waitForBytesWritten(500); return 0
    server=QLocalServer(); server.listen('floaty-desktop-v1')
    window=Floaty(); window.show()
    def incoming():
        client=server.nextPendingConnection()
        if client:client.disconnectFromServer(); client.deleteLater()
        window.settings()
    server.newConnection.connect(incoming)
    window.notify('Floaty 已在屏幕右上角就位。右键开始排练，双击气球填写 Jev 密钥。')
    result=app.exec()
    if result==75:
        server.close()
        ok,_=QProcess.startDetached(sys.executable,[str(ROOT/'floaty.py')],str(ROOT))
        if not ok:
            server.listen('floaty-desktop-v1'); window.tray.show(); window.show()
            QMessageBox.warning(window,'重启未成功','无法启动新进程，已保留当前应用。请稍后再试。')
            return app.exec()
        return 0
    return result

if __name__=='__main__':sys.exit(main())
