#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
独立窗口截图方法对比测试。

目的: 找一种被遮挡时也能拿到游戏画面、且不闪烁的窗口截图方案,
      验证后再决定整合进主程序。

测试方法:
    1. mss                          屏幕区域抓取 (基线; 被遮挡截到遮挡物)
    2. BitBlt (WindowDC)            从窗口 DC 拷贝
    3. BitBlt (ClientDC)            从客户区 DC 拷贝
    4. PrintWindow flag=0           默认全窗口
    5. PrintWindow flag=1           PW_CLIENTONLY
    6. PrintWindow flag=2           PW_RENDERFULLCONTENT (主程序当前用)
    7. PrintWindow flag=3           1|2
    8. WGC (Windows.Graphics.Capture) GPU 级捕获 (Win10 1803+)

使用建议:
    A. 选目标窗口
    B. 不遮挡: 各方法点一次, 看耗时和预览是否正常
    C. 完全盖住游戏: 各方法再点一次, 比较哪些拿到正常画面 (黑屏的就 fail)
    D. 选定方法后开"连续采集 5fps", 盯游戏窗口看是否闪烁

预期结论:
    - mss 被遮挡必然失败
    - BitBlt 通常被遮挡也黑 (除非 DWM 重定向位图刚好可用)
    - PrintWindow 系列被遮挡时常拿到画面但会触发游戏重绘 → 闪烁
    - WGC 被遮挡仍正常, 不触发重绘 → 不闪烁 (最理想方案)

删除方法: 直接删除本文件即可。
"""

import sys
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

try:
    import win32gui
    import win32ui
    import win32con
    import ctypes
    import ctypes.wintypes
    from PIL import Image, ImageTk
    import mss
except ImportError as e:
    print(f"缺少基础依赖: {e}")
    sys.exit(1)

try:
    from windows_capture import WindowsCapture, Frame, InternalCaptureControl
    HAS_WGC = True
except Exception as _e:
    HAS_WGC = False
    _WGC_ERR = str(_e)


user32 = ctypes.windll.user32
user32.PrintWindow.argtypes = [
    ctypes.wintypes.HWND, ctypes.wintypes.HDC, ctypes.wintypes.UINT,
]
user32.PrintWindow.restype = ctypes.wintypes.BOOL


# ============ 截图方法 ============

def cap_mss(hwnd):
    l, t, r, b = win32gui.GetWindowRect(hwnd)
    with mss.mss() as sct:
        monitor = {"left": l, "top": t, "width": r - l, "height": b - t}
        s = sct.grab(monitor)
        return Image.frombytes("RGB", s.size, s.bgra, "raw", "BGRX")


def _gdi_capture(hwnd, op, use_window_dc=True):
    """GDI 通用流程; op(hwnd, save_dc_safehdc, src_mfc_dc, save_dc, w, h) -> bool"""
    if use_window_dc:
        l, t, r, b = win32gui.GetWindowRect(hwnd)
        w, h = r - l, b - t
        get_dc = win32gui.GetWindowDC
    else:
        rc = win32gui.GetClientRect(hwnd)
        w, h = rc[2], rc[3]
        get_dc = win32gui.GetDC
    if w <= 0 or h <= 0:
        return None

    hdc = get_dc(hwnd)
    mfc = win32ui.CreateDCFromHandle(hdc)
    save = mfc.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(mfc, w, h)
    save.SelectObject(bmp)

    img = None
    try:
        ok = op(hwnd, save.GetSafeHdc(), mfc, save, w, h)
        if ok:
            info = bmp.GetInfo()
            bits = bmp.GetBitmapBits(True)
            img = Image.frombytes('RGB', (info['bmWidth'], info['bmHeight']),
                                  bits, 'raw', 'BGRX', 0, 1)
    finally:
        try: win32gui.DeleteObject(bmp.GetHandle())
        except Exception: pass
        try: save.DeleteDC()
        except Exception: pass
        try: mfc.DeleteDC()
        except Exception: pass
        try: win32gui.ReleaseDC(hwnd, hdc)
        except Exception: pass
    return img


def cap_bitblt_window(hwnd):
    def op(h, hdc, src, dst, w, h_):
        dst.BitBlt((0, 0), (w, h_), src, (0, 0), win32con.SRCCOPY)
        return True
    return _gdi_capture(hwnd, op, use_window_dc=True)


def cap_bitblt_client(hwnd):
    def op(h, hdc, src, dst, w, h_):
        dst.BitBlt((0, 0), (w, h_), src, (0, 0), win32con.SRCCOPY)
        return True
    return _gdi_capture(hwnd, op, use_window_dc=False)


def cap_printwindow(hwnd, flag):
    def op(h, hdc, src, dst, w, h_):
        return bool(user32.PrintWindow(h, hdc, flag))
    return _gdi_capture(hwnd, op, use_window_dc=True)


# ----- WGC -----

class WGCSession:
    """启动一个 WGC 后台采集, 主线程通过 grab() 取最新一帧。
    注意: windows-capture 通过窗口标题匹配, 多窗口同名会绑到第一个。"""
    def __init__(self, title):
        self.last_frame = None  # (w, h, bytes BGRA)
        self.lock = threading.Lock()
        self.capture = WindowsCapture(
            cursor_capture=False,
            draw_border=False,
            window_name=title,
        )

        @self.capture.event
        def on_frame_arrived(frame, ctrl):
            with self.lock:
                self.last_frame = (
                    frame.width, frame.height, bytes(frame.frame_buffer)
                )

        @self.capture.event
        def on_closed():
            pass

        self.capture.start_free_threaded()

    def grab(self):
        with self.lock:
            f = self.last_frame
        if f is None:
            return None
        w, h, buf = f
        return Image.frombytes('RGB', (w, h), buf, 'raw', 'BGRX', 0, 1)

    def stop(self):
        try:
            self.capture.stop()
        except Exception:
            pass


_wgc_state = {'session': None, 'hwnd': None}


def cap_wgc(hwnd):
    if not HAS_WGC:
        return None
    if _wgc_state['hwnd'] != hwnd:
        if _wgc_state['session']:
            _wgc_state['session'].stop()
            _wgc_state['session'] = None
        title = win32gui.GetWindowText(hwnd)
        if not title.strip():
            return None
        _wgc_state['session'] = WGCSession(title)
        _wgc_state['hwnd'] = hwnd
        time.sleep(0.5)  # 等首帧
    return _wgc_state['session'].grab()


def stop_wgc():
    if _wgc_state['session']:
        _wgc_state['session'].stop()
        _wgc_state['session'] = None
        _wgc_state['hwnd'] = None


METHODS = [
    ("1. mss (屏幕)",                cap_mss),
    ("2. BitBlt WindowDC",           cap_bitblt_window),
    ("3. BitBlt ClientDC",           cap_bitblt_client),
    ("4. PrintWindow flag=0",        lambda h: cap_printwindow(h, 0)),
    ("5. PrintWindow flag=1 Client", lambda h: cap_printwindow(h, 1)),
    ("6. PrintWindow flag=2 Render", lambda h: cap_printwindow(h, 2)),
    ("7. PrintWindow flag=3 (1|2)",  lambda h: cap_printwindow(h, 3)),
    ("8. WGC (GPU 级)",              cap_wgc),
]


# ============ 工具 ============

def enum_windows():
    result = []

    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            t = win32gui.GetWindowText(hwnd)
            if t.strip():
                result.append((hwnd, t))

    win32gui.EnumWindows(cb, None)
    return result


def img_brightness_black(img):
    small = img.resize((32, 32))
    pixels = list(small.getdata())
    avg = sum(sum(p[:3]) for p in pixels) / (len(pixels) * 3)
    is_black = all(max(p[:3]) < 5 for p in pixels)
    return avg, is_black


# ============ GUI ============

class CaptureTestGUI:
    def __init__(self, root):
        self.root = root
        root.title("窗口截图方法对比测试")
        root.geometry("1000x780")

        self.windows = []
        self.hwnd = None
        self.continuous = False
        self.last_image = None

        self._build_ui()
        self._refresh_windows()

        if not HAS_WGC:
            self._log(f"提示: windows-capture 未安装, 方法 8 (WGC) 不可用 ({_WGC_ERR})")

    def _build_ui(self):
        pad = {'padx': 8, 'pady': 4}

        # 1. 选窗口
        f1 = ttk.LabelFrame(self.root, text="1. 选目标窗口")
        f1.pack(fill='x', **pad)
        r = ttk.Frame(f1); r.pack(fill='x', padx=6, pady=6)
        ttk.Label(r, text="窗口:").pack(side='left')
        self.cbo = ttk.Combobox(r, state='readonly', width=72)
        self.cbo.pack(side='left', padx=4)
        self.cbo.bind('<<ComboboxSelected>>', self._on_select)
        ttk.Button(r, text="刷新", command=self._refresh_windows).pack(side='left', padx=4)
        self.lbl_info = ttk.Label(f1, text="未选择", foreground='gray')
        self.lbl_info.pack(anchor='w', padx=6, pady=2)

        # 2. 单次测试
        f2 = ttk.LabelFrame(self.root, text="2. 单次采集 (各方法点一次, 比较结果)")
        f2.pack(fill='x', **pad)
        for i, (name, _) in enumerate(METHODS):
            row = i // 4
            col = i % 4
            ttk.Button(f2, text=name, width=28,
                       command=lambda idx=i: self._capture_once(idx)
                       ).grid(row=row, column=col, padx=2, pady=2, sticky='w')

        # 3. 连续采集
        f3 = ttk.LabelFrame(self.root, text="3. 连续采集 5fps (盯游戏窗口看是否闪烁)")
        f3.pack(fill='x', **pad)
        r = ttk.Frame(f3); r.pack(fill='x', padx=6, pady=6)
        ttk.Label(r, text="方法:").pack(side='left')
        self.cbo_method = ttk.Combobox(r, state='readonly', width=40,
                                       values=[m[0] for m in METHODS])
        self.cbo_method.current(5)  # 默认 PrintWindow flag=2
        self.cbo_method.pack(side='left', padx=4)
        self.btn_start = ttk.Button(r, text="开始", command=self._start_loop)
        self.btn_start.pack(side='left', padx=4)
        self.btn_stop = ttk.Button(r, text="停止", command=self._stop_loop, state='disabled')
        self.btn_stop.pack(side='left', padx=4)
        ttk.Button(r, text="保存当前帧", command=self._save).pack(side='left', padx=8)

        # 预览
        f4 = ttk.LabelFrame(self.root, text="预览")
        f4.pack(fill='both', expand=True, **pad)
        self.canvas = tk.Canvas(f4, bg='#222')
        self.canvas.pack(fill='both', expand=True, padx=6, pady=6)
        self._photo = None

        # 日志
        f5 = ttk.LabelFrame(self.root, text="日志")
        f5.pack(fill='x', **pad)
        self.txt = tk.Text(f5, height=8, wrap='word')
        self.txt.pack(fill='x', padx=6, pady=6)

    def _log(self, m):
        self.txt.insert('end', m + '\n')
        self.txt.see('end')

    def _refresh_windows(self):
        self.windows = enum_windows()
        self.cbo['values'] = [f"[{h}] {t}" for h, t in self.windows]
        self._log(f"枚举 {len(self.windows)} 个窗口")

    def _on_select(self, _evt):
        i = self.cbo.current()
        if 0 <= i < len(self.windows):
            self.hwnd, title = self.windows[i]
            try:
                l, t, r, b = win32gui.GetWindowRect(self.hwnd)
                self.lbl_info.config(
                    text=f"HWND={self.hwnd} 标题='{title}' "
                         f"窗口区域 ({l},{t})→({r},{b}) 尺寸 {r - l}×{b - t}",
                    foreground='black')
            except Exception as e:
                self._log(f"读取窗口失败: {e}")

    def _capture_once(self, idx):
        if not self.hwnd:
            messagebox.showwarning("", "请先选窗口"); return
        if self.continuous:
            messagebox.showwarning("", "正在连续采集中, 请先停止"); return
        name, fn = METHODS[idx]
        if name.startswith("8.") and not HAS_WGC:
            self._log(f"[{name}] windows-capture 未安装, 跳过")
            return
        try:
            t0 = time.time()
            img = fn(self.hwnd)
            elapsed = (time.time() - t0) * 1000
            if img is None:
                self._log(f"[{name}] 失败 (None) 耗时 {elapsed:.1f}ms")
                return
            avg, is_black = img_brightness_black(img)
            self._log(f"[{name}] OK 耗时 {elapsed:.1f}ms 尺寸 {img.size} "
                      f"亮度 {avg:.1f} 黑屏={is_black}")
            self.last_image = img
            self._show_preview(img)
        except Exception as e:
            self._log(f"[{name}] 异常: {e}")

    def _start_loop(self):
        if not self.hwnd:
            messagebox.showwarning("", "请先选窗口"); return
        idx = self.cbo_method.current()
        if idx < 0:
            return
        name = METHODS[idx][0]
        if name.startswith("8.") and not HAS_WGC:
            messagebox.showerror("", "windows-capture 未安装"); return
        self.continuous = True
        self.btn_start.config(state='disabled')
        self.btn_stop.config(state='normal')
        self._log(f"开始连续采集 [{name}]")
        self._loop_tick()

    def _stop_loop(self):
        self.continuous = False
        self.btn_start.config(state='normal')
        self.btn_stop.config(state='disabled')
        self._log("停止连续采集")

    def _loop_tick(self):
        if not self.continuous:
            return
        idx = self.cbo_method.current()
        if 0 <= idx < len(METHODS):
            name, fn = METHODS[idx]
            try:
                img = fn(self.hwnd)
                if img is not None:
                    self.last_image = img
                    self._show_preview(img)
            except Exception as e:
                self._log(f"[{name}] 异常: {e}")
        self.root.after(200, self._loop_tick)

    def _show_preview(self, img):
        cw = self.canvas.winfo_width() or 800
        ch = self.canvas.winfo_height() or 400
        if cw < 10 or ch < 10:
            return
        scale = min(cw / img.width, ch / img.height, 1.0)
        if scale < 1.0:
            preview = img.resize((max(1, int(img.width * scale)),
                                  max(1, int(img.height * scale))))
        else:
            preview = img
        self._photo = ImageTk.PhotoImage(preview)
        self.canvas.delete('all')
        self.canvas.create_image(cw // 2, ch // 2, image=self._photo, anchor='center')

    def _save(self):
        if self.last_image is None:
            messagebox.showwarning("", "还没有截图"); return
        path = filedialog.asksaveasfilename(
            defaultextension='.png',
            filetypes=[('PNG', '*.png')],
            initialfile=f'capture_{int(time.time())}.png')
        if path:
            self.last_image.save(path)
            self._log(f"已保存: {path}")

    def on_close(self):
        self.continuous = False
        try:
            stop_wgc()
        except Exception:
            pass
        self.root.destroy()


def main():
    if sys.platform != 'win32':
        print("仅支持 Windows"); sys.exit(1)
    root = tk.Tk()
    app = CaptureTestGUI(root)
    root.protocol('WM_DELETE_WINDOW', app.on_close)
    root.mainloop()


if __name__ == '__main__':
    main()
