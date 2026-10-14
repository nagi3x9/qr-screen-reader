"""Native physical-pixel capture and hotkey registration, Windows only."""
import ctypes
from ctypes import wintypes
import sys
from PIL import Image

HOTKEY_ID = 0x5147

def dpi_awareness():
    if sys.platform == 'win32':
        # Before QApplication: PMv2 keeps physical coordinates consistent.
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))

def register_hotkey():
    if sys.platform != 'win32':
        return False, 'グローバルショートカットはWindows専用です。'
    user = ctypes.WinDLL('user32', use_last_error=True)
    ok = user.RegisterHotKey(None, HOTKEY_ID, 0x0002 | 0x0004 | 0x4000, ord('Q'))
    return bool(ok), '' if ok else f'Ctrl + Shift + Qを登録できません（競合など、エラー{ctypes.get_last_error()}）。ボタンは利用できます。'

def unregister_hotkey():
    if sys.platform == 'win32':
        ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_ID)

def capture_desktop():
    u = ctypes.windll.user32
    g = ctypes.windll.gdi32
    u.GetDC.argtypes = [wintypes.HWND]
    # Handles are pointer-sized on 64-bit Windows.
    for fn in ('GetDC',):
        getattr(u, fn).restype = wintypes.HDC
    g.CreateCompatibleDC.restype = wintypes.HDC
    g.CreateCompatibleBitmap.restype = wintypes.HBITMAP
    g.SelectObject.restype = wintypes.HANDLE
    g.CreateCompatibleDC.argtypes = [wintypes.HDC]
    g.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
    g.SelectObject.argtypes = [wintypes.HDC, wintypes.HANDLE]
    g.BitBlt.argtypes = [wintypes.HDC,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,wintypes.HDC,ctypes.c_int,ctypes.c_int,wintypes.DWORD]
    g.DeleteObject.argtypes = [wintypes.HANDLE]
    g.DeleteDC.argtypes = [wintypes.HDC]
    u.ReleaseDC.argtypes = [wintypes.HWND,wintypes.HDC]
    x,y,w,h = (u.GetSystemMetrics(i) for i in (76,77,78,79))
    if w <= 0 or h <= 0 or w*h > 80_000_000:
        raise RuntimeError('画面構成を取得できないか、画面が大きすぎます。')
    dc = u.GetDC(None); mem = g.CreateCompatibleDC(dc); bmp = g.CreateCompatibleBitmap(dc,w,h)
    old = g.SelectObject(mem,bmp)
    try:
        if not dc or not mem or not bmp or not g.BitBlt(mem,0,0,w,h,dc,x,y,0x00CC0020 | 0x40000000):
            raise RuntimeError('画面キャプチャに失敗しました。')
        class Header(ctypes.Structure):
            _fields_ = [('size',wintypes.DWORD),('width',wintypes.LONG),('height',wintypes.LONG),('planes',wintypes.WORD),('bits',wintypes.WORD),('compression',wintypes.DWORD),('image_size',wintypes.DWORD),('xppm',wintypes.LONG),('yppm',wintypes.LONG),('used',wintypes.DWORD),('important',wintypes.DWORD)]
        info = Header(ctypes.sizeof(Header),w,-h,1,32,0,0,0,0,0,0)
        data = ctypes.create_string_buffer(w*h*4)
        g.GetDIBits.argtypes = [wintypes.HDC,wintypes.HBITMAP,wintypes.UINT,wintypes.UINT,ctypes.c_void_p,ctypes.c_void_p,wintypes.UINT]
        g.SelectObject(mem,old)
        if g.GetDIBits(mem,bmp,0,h,data,ctypes.byref(info),0) != h:
            raise RuntimeError('画面データ取得に失敗しました。')
        return Image.frombytes('RGB',(w,h),data.raw,'raw','BGRX'), (x,y,w,h)
    finally:
        g.SelectObject(mem,old); g.DeleteObject(bmp); g.DeleteDC(mem); u.ReleaseDC(None,dc)

def cursor_position():
    p = wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(p))
    return p.x,p.y


def physical_monitors():
    user=ctypes.WinDLL('user32',use_last_error=True)
    callback_type=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HANDLE,wintypes.HDC,ctypes.POINTER(wintypes.RECT),wintypes.LPARAM)
    rectangles=[]
    def callback(handle,dc,rect,data):
        r=rect.contents
        value=(r.left,r.top,r.right-r.left,r.bottom-r.top)
        if value[2]>0 and value[3]>0 and value not in rectangles:
            rectangles.append(value)
        return True
    cb=callback_type(callback)
    user.EnumDisplayMonitors.argtypes=[wintypes.HDC,ctypes.c_void_p,callback_type,wintypes.LPARAM]
    user.EnumDisplayMonitors.restype=wintypes.BOOL
    if not user.EnumDisplayMonitors(None,None,cb,0) or not rectangles:
        raise RuntimeError('Windowsからモニター一覧を取得できませんでした。')
    return rectangles

def place_overlay(hwnd, rect):
    user=ctypes.WinDLL('user32',use_last_error=True)
    user.SetWindowPos.argtypes=[wintypes.HWND,wintypes.HWND,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,wintypes.UINT]
    user.SetWindowPos.restype=wintypes.BOOL
    x,y,w,h=rect
    if not user.SetWindowPos(wintypes.HWND(hwnd),wintypes.HWND(-1),x,y,w,h,0x0010):
        raise RuntimeError(f'モニターへの配置に失敗しました（エラー{ctypes.get_last_error()}）。')
    # Verify actual physical rectangle; do not silently capture the wrong screen.
    user.GetWindowRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)]
    user.GetWindowRect.restype=wintypes.BOOL
    actual=wintypes.RECT()
    if not user.GetWindowRect(wintypes.HWND(hwnd),ctypes.byref(actual)):
        raise RuntimeError('選択ウィンドウの座標を確認できませんでした。')
    if (actual.left,actual.top,actual.right-actual.left,actual.bottom-actual.top)!=rect:
        raise RuntimeError('選択ウィンドウの座標がモニターと一致しません。')
