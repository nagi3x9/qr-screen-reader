import sys
from pathlib import Path
import ctypes
from ctypes import wintypes
from io import BytesIO
from PIL import Image
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QAbstractNativeEventFilter, QRectF, QUrl, QBuffer, QIODevice
from PySide6.QtGui import QPainter, QColor, QPen, QPixmap, QIcon, QDesktopServices
from PySide6.QtWidgets import QApplication,QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,QPlainTextEdit,QFileDialog,QMessageBox
import windows
from core import decode, load_file, safe_url

class HotkeyFilter(QAbstractNativeEventFilter):
    def __init__(self, action):
        super().__init__(); self.action = action
    def nativeEventFilter(self, event_type, message):
        if sys.platform == 'win32':
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x0312 and msg.wParam == windows.HOTKEY_ID:
                QTimer.singleShot(0,self.action)
                return True, 0
        return False, 0

class Worker(QThread):
    success = Signal(object)
    failure = Signal(str)
    def __init__(self, image=None, path=None):
        super().__init__(); self.image=image; self.path=path
    def run(self):
        try:
            image = load_file(self.path) if self.path else self.image
            self.success.emit(decode(image))
        except Exception as exc:
            from core import ReadError
            self.failure.emit(str(exc) if isinstance(exc,ReadError) else '解析中にエラーが発生しました。画像を変えて再試行してください。')
        finally:
            self.image = None; self.path = None

class Overlay(QWidget):
    def __init__(self, controller, physical):
        super().__init__(); self.c=controller; self.physical=physical
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.winId()
        windows.place_overlay(int(self.winId()),physical)
        self.setCursor(Qt.CrossCursor)
        x,y,w,h=self.physical; dx,dy,_,_=self.c.bounds
        crop=self.c.image.crop((x-dx,y-dy,x-dx+w,y-dy+h))
        b=BytesIO(); crop.save(b,format='PNG')
        self.pixmap=QPixmap(); self.pixmap.loadFromData(b.getvalue())
        self.setMouseTracking(True)
    def paintEvent(self,event):
        p=QPainter(self); p.drawPixmap(self.rect(),self.pixmap)
        p.fillRect(self.rect(),QColor(0,0,0,115))
        if self.c.start and self.c.end:
            a,b=self.c.start,self.c.end; x,y,w,h=self.physical
            r=QRectF((min(a[0],b[0])-x)*self.width()/w,(min(a[1],b[1])-y)*self.height()/h,abs(a[0]-b[0])*self.width()/w,abs(a[1]-b[1])*self.height()/h)
            p.save(); p.setClipRect(r); p.drawPixmap(self.rect(),self.pixmap); p.restore()
            p.setPen(QPen(QColor('#6ee7ff'),2)); p.drawRect(r)
        p.setPen(Qt.white); p.drawText(20,32,'QRコードを余白ごとドラッグで選択  /  Escでキャンセル')
    def mousePressEvent(self,event):
        if event.button()==Qt.LeftButton:
            self.c.start=windows.cursor_position(); self.c.end=self.c.start
    def mouseMoveEvent(self,event):
        if self.c.start:
            self.c.end=windows.cursor_position()
            for o in self.c.overlays: o.update()
    def mouseReleaseEvent(self,event):
        if event.button()==Qt.LeftButton and self.c.start:
            self.c.end=windows.cursor_position(); self.c.finish()
    def keyPressEvent(self,event):
        if event.key()==Qt.Key_Escape: self.c.cancel()

class Selection:
    def __init__(self, main):
        self.main=main; self.image=None; self.overlays=[]; self.start=None; self.end=None; self.active=True
    def begin(self):
        if not self.active or self.main.selection is not self:
            return
        stage='画面キャプチャ'

        try:
            self.image,self.bounds=windows.capture_desktop()
            stage='選択画面の作成・モニター座標の取得'
            for physical in windows.physical_monitors():
                self.overlays.append(Overlay(self,physical))
            if not self.overlays:
                raise RuntimeError('利用できるモニターがありません。')
            stage='選択画面の表示'
            for o in self.overlays:
                o.show()
                windows.place_overlay(int(o.winId()),o.physical)
                o.raise_()
            self.overlays[0].activateWindow(); self.overlays[0].setFocus()
        except Exception as exc:
            message=f'{stage}に失敗しました。\n{type(exc).__name__}: {exc}'
            self.cancel(message)
            QMessageBox.warning(self.main,'画面読み取りエラー',message)
    def clear(self):
        self.active=False
        self.main.capture_timer.stop()
        for o in self.overlays: o.close(); o.deleteLater()
        self.overlays=[]; self.image=None
        self.main.selection=None
    def cancel(self, message='範囲選択をキャンセルしました。'):
        self.clear(); self.main.restore(); self.main.status.setText(message)
    def finish(self):
        x,y,w,h=self.bounds; a,b=self.start,self.end
        left=max(x,min(a[0],b[0])); top=max(y,min(a[1],b[1]))
        right=min(x+w,max(a[0],b[0])); bottom=min(y+h,max(a[1],b[1]))
        if right-left < 8 or bottom-top < 8:
            self.cancel('範囲が小さすぎます。選択し直してください。'); return
        image=self.image.crop((left-x,top-y,right-x,bottom-y))
        self.clear(); self.main.restore(); self.main.read(image=image)

class Main(QWidget):
    def __init__(self):
        super().__init__(); self.worker=None; self.selection=None; self.result=None; self.last='screen'
        self.capture_timer=QTimer(self); self.capture_timer.setSingleShot(True); self.capture_timer.timeout.connect(self.begin_selection)
        self.setWindowTitle('QR Screen Reader 1.0.4'); self.resize(560,410)
        layout=QVBoxLayout(self); title=QLabel('QR Screen Reader'); title.setStyleSheet('font-size:22px;font-weight:600'); layout.addWidget(title)
        self.hotkey_label=QLabel('ショートカット：Ctrl + Shift + Q（起動中のみ）'); self.hotkey_label.setWordWrap(True); layout.addWidget(self.hotkey_label)
        row=QHBoxLayout(); layout.addLayout(row); self.inputs=[]
        for text,action in [('画面から読み取り',self.screen),('クリップボード',self.clipboard),('画像ファイル',self.file)]:
            b=QPushButton(text); b.clicked.connect(action); row.addWidget(b); self.inputs.append(b)
        self.status=QLabel('読み取り方法を選んでください。'); self.status.setWordWrap(True); layout.addWidget(self.status)
        self.output=QPlainTextEdit(); self.output.setReadOnly(True); self.output.setPlaceholderText('読み取った内容をここに表示'); layout.addWidget(self.output)
        row=QHBoxLayout(); layout.addLayout(row)
        self.copy=QPushButton('コピー'); self.copy.clicked.connect(self.copy_text); row.addWidget(self.copy)
        self.open=QPushButton('URLを開く'); self.open.clicked.connect(self.open_url); row.addWidget(self.open)
        retry=QPushButton('再読み取り'); retry.clicked.connect(self.retry); row.addWidget(retry); self.inputs.append(retry)
        layout.addWidget(QLabel('ローカル解析・履歴保存なし。URLは確認後に開きます。'))
        self.copy.setEnabled(False); self.open.setEnabled(False)
        self.filter=HotkeyFilter(self.screen); QApplication.instance().installNativeEventFilter(self.filter)
        ok,message=windows.register_hotkey()
        if not ok: self.hotkey_label.setText(message)
        self.screen_changed=lambda *_: self.selection.cancel('画面構成が変更されました。選択し直してください。') if self.selection else None
        QApplication.instance().screenAdded.connect(self.screen_changed); QApplication.instance().screenRemoved.connect(self.screen_changed)
        for screen in QApplication.screens(): screen.geometryChanged.connect(self.screen_changed)
    def busy(self): return self.selection is not None or (self.worker is not None and self.worker.isRunning())
    def reset_result(self):
        self.result=None; self.output.clear(); self.copy.setEnabled(False); self.open.setEnabled(False)
    def restore(self): self.showNormal(); self.raise_(); self.activateWindow()
    def screen(self):
        if self.busy(): return
        if sys.platform!='win32': self.status.setText('画面選択はWindows専用です。'); return
        self.last='screen'; self.reset_result(); self.selection=Selection(self); self.hide()
        self.capture_timer.start(180)
    def begin_selection(self):
        if self.selection:
            self.selection.begin()
    def clipboard(self):
        if self.busy(): return
        self.last='clipboard'; self.reset_result()
        qimage=QApplication.clipboard().image()
        if qimage.isNull(): self.status.setText('クリップボードに画像がありません。'); return
        buf=QBuffer(); buf.open(QIODevice.WriteOnly); qimage.save(buf,'PNG')
        try: self.read(image=Image.open(BytesIO(bytes(buf.data()))).copy())
        except Exception: self.status.setText('クリップボード画像を読み込めませんでした。')
    def file(self):
        if self.busy(): return
        path,_=QFileDialog.getOpenFileName(self,'QR画像を選択','','画像 (*.png *.jpg *.jpeg *.bmp *.webp)')
        if path: self.last='file'; self.read(path=path)
    def retry(self): {'screen':self.screen,'clipboard':self.clipboard,'file':self.file}[self.last]()
    def read(self, image=None, path=None):
        self.reset_result(); self.status.setText('解析しています…')
        for b in self.inputs: b.setEnabled(False)
        self.worker=Worker(image,path); self.worker.success.connect(self.success); self.worker.failure.connect(self.failure); self.worker.finished.connect(self.finished); self.worker.start()
    def success(self,result):
        self.result=result; self.output.setPlainText(result.text); self.copy.setEnabled(True); self.open.setEnabled(bool(result.url))
        controls=any(ord(c)<32 and c not in '\r\n\t' or 127<=ord(c)<160 for c in result.text)
        self.status.setText(('読み取り成功：HTTP/HTTPS URL' if result.url else '読み取り成功：文字列')+('（制御文字あり。コピーは原文を保持）' if controls else ''))
        self.restore()
    def failure(self,message): self.status.setText(message); self.restore()
    def finished(self):
        for b in self.inputs: b.setEnabled(True)
        self.worker.deleteLater(); self.worker=None
    def copy_text(self):
        if self.result: QApplication.clipboard().setText(self.result.text); self.status.setText('コピーしました。')
    def open_url(self):
        if not self.result or not safe_url(self.result.text): return
        box=QMessageBox(self); box.setWindowTitle('URLを開く確認'); box.setText('次のURLをブラウザで開きますか？'); box.setTextFormat(Qt.PlainText); box.setDetailedText(self.result.url); box.setInformativeText(self.result.url); box.setStandardButtons(QMessageBox.Yes|QMessageBox.No); box.setDefaultButton(QMessageBox.No)
        if box.exec()==QMessageBox.Yes:
            if not QDesktopServices.openUrl(QUrl(self.result.url, QUrl.StrictMode)): self.status.setText('ブラウザを起動できませんでした。')
    def closeEvent(self,event):
        if self.worker and self.worker.isRunning():
            self.status.setText('解析が終わってから閉じてください。'); event.ignore(); return
        if self.selection: self.selection.clear()
        self.capture_timer.stop(); windows.unregister_hotkey(); QApplication.instance().removeNativeEventFilter(self.filter); event.accept(); QApplication.instance().quit()

def main():
    windows.dpi_awareness(); app=QApplication(sys.argv); app.setQuitOnLastWindowClosed(False); app.setStyle('Fusion'); app.setWindowIcon(QIcon(str(Path(__file__).resolve().parent/'assets'/'app_icon.ico'))); window=Main(); window.show(); return app.exec()
if __name__=='__main__': sys.exit(main())
