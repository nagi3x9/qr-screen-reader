import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import qrcode
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QEventLoop,QTimer
from PySide6.QtGui import QImage
from app import Main

def test_clipboard_result_copy(tmp_path):
    app=QApplication.instance() or QApplication([])
    window=Main(); window.show()
    text='日本語\nQRコピー'; p=tmp_path/'画像.png'; qrcode.make(text).save(p)
    app.clipboard().setImage(QImage(str(p)))
    window.clipboard()
    loop=QEventLoop(); window.worker.finished.connect(loop.quit); QTimer.singleShot(10000,loop.quit); loop.exec(); app.processEvents()
    assert window.result.text==text
    assert not app.clipboard().image().isNull() # Reading did not overwrite clipboard
    window.copy_text(); assert app.clipboard().text()==text
    assert not window.open.isEnabled()
    window.close()

def test_empty_clipboard():
    app=QApplication.instance() or QApplication([]); window=Main()
    app.clipboard().setText('leave me'); window.clipboard()
    assert '画像がありません' in window.status.text()
    assert app.clipboard().text()=='leave me'
    window.close()

def wait_worker(window):
    app=QApplication.instance(); loop=QEventLoop(); window.worker.finished.connect(loop.quit); QTimer.singleShot(10000,loop.quit); loop.exec(); app.processEvents()

def test_failure_then_retry(tmp_path):
    from PIL import Image
    app=QApplication.instance() or QApplication([]); window=Main()
    window.read(image=Image.new('RGB',(200,200),'white')); wait_worker(window)
    assert window.result is None and not window.copy.isEnabled()
    window.read(image=qrcode.make('https://example.com').get_image()); wait_worker(window)
    assert window.open.isEnabled() and window.result.url=='https://example.com'
    assert all(b.isEnabled() for b in window.inputs)
    window.close()

def test_selection_negative_origin_and_cancel(monkeypatch):
    from PIL import Image
    from app import Selection
    app=QApplication.instance() or QApplication([]); window=Main()
    received=[]
    monkeypatch.setattr(window,'read',lambda **kw: received.append(kw['image']))
    selection=Selection(window); window.selection=selection
    selection.bounds=(-1920,-200,3840,1280); selection.image=Image.new('RGB',(3840,1280),'white')
    selection.start=(-1900,-180); selection.end=(-1800,-80); selection.finish()
    assert received[0].size==(100,100) and window.selection is None
    selection=Selection(window); window.selection=selection; selection.cancel()
    assert window.selection is None and 'キャンセル' in window.status.text()
    window.close()

def test_delayed_overlay_and_restore(monkeypatch):
    import windows
    from PIL import Image
    from app import Selection
    app=QApplication.instance() or QApplication([]); window=Main(); window.show()
    monkeypatch.setattr(windows,'capture_desktop',lambda:(Image.new('RGB',(400,400),'white'),(0,0,400,400)))
    monkeypatch.setattr(windows,'physical_monitors',lambda:[(0,0,400,400)])
    monkeypatch.setattr(windows,'place_overlay',lambda hwnd,rect:None)
    window.selection=Selection(window); window.hide(); window.capture_timer.start(1)
    loop=QEventLoop(); QTimer.singleShot(100,loop.quit); loop.exec()
    assert window.selection.overlays and all(o.isVisible() for o in window.selection.overlays)
    window.selection.cancel(); app.processEvents()
    assert window.isVisible() and window.selection is None
    window.close()

def test_capture_exception_restores_window(monkeypatch):
    import windows
    from app import Selection,QMessageBox
    app=QApplication.instance() or QApplication([]); window=Main(); warnings=[]
    def fail(): raise OSError('capture test failure')
    monkeypatch.setattr(windows,'capture_desktop',fail)
    monkeypatch.setattr(QMessageBox,'warning',lambda *args: warnings.append(args[2]))
    window.selection=Selection(window); window.hide(); window.selection.begin()
    assert window.isVisible() and window.selection is None
    assert 'OSError' in warnings[0] and '画面キャプチャ' in warnings[0]
    assert not window.capture_timer.isActive()
    window.close()


def test_monitor_query_failure_restores_window(monkeypatch):
    import windows
    from PIL import Image
    from app import Selection,QMessageBox
    app=QApplication.instance() or QApplication([]); window=Main(); warnings=[]
    monkeypatch.setattr(windows,'capture_desktop',lambda:(Image.new('RGB',(400,400),'white'),(0,0,400,400)))
    def fail(): raise RuntimeError('native monitor query failed')
    monkeypatch.setattr(windows,'physical_monitors',fail)
    monkeypatch.setattr(QMessageBox,'warning',lambda *args: warnings.append(args[2]))
    window.selection=Selection(window); window.hide(); window.selection.begin()
    assert window.isVisible() and window.selection is None
    assert 'モニター座標' in warnings[0]
    window.close()


def test_native_monitor_layout_used_without_qt_names(monkeypatch):
    import windows
    from PIL import Image
    from app import Selection
    app=QApplication.instance() or QApplication([]); window=Main(); placements=[]
    rects=[(-200,0,200,200),(0,0,300,200)]
    monkeypatch.setattr(windows,'capture_desktop',lambda:(Image.new('RGB',(500,200),'white'),(-200,0,500,200)))
    monkeypatch.setattr(windows,'physical_monitors',lambda:rects)
    monkeypatch.setattr(windows,'place_overlay',lambda hwnd,rect:placements.append(rect))
    window.selection=Selection(window); window.hide(); window.selection.begin()
    assert [o.physical for o in window.selection.overlays]==rects
    assert placements==rects+rects
    assert all(o.isVisible() for o in window.selection.overlays)
    window.selection.cancel(); window.close()
