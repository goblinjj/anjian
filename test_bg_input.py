"""
后台窗口消息测试脚本 —— 验证 PostMessage + PrintWindow 能否操控/截取指定窗口。

用途:
    用于测试"不控制真实鼠标, 直接给游戏窗口发消息"的可行性。
    本脚本完全独立, 不依赖/不影响主程序任何现有模块。

运行环境:
    仅 Windows。依赖 pywin32 (未加入 requirements.txt, 单独安装):
        pip install pywin32

启动:
    python test_bg_input.py

删除方法:
    直接删除本文件即可, 无其它副作用。

注意事项:
    - 点击坐标为"客户区相对坐标", 不是屏幕坐标。(0,0) 是游戏画面的左上角。
    - 若目标程序以管理员身份运行, 本脚本也需以管理员身份启动, 否则消息会被 UIPI 拦截。
    - 若截图为黑屏, 切换模式 1 → 3 再试; 仍黑屏通常说明游戏使用了 DirectX 全屏独占。
"""
import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

try:
    import win32gui
    import win32con
    import win32api
    import win32ui
    from ctypes import windll
    from PIL import Image, ImageTk
except ImportError as e:
    print(f"缺少依赖: {e}")
    print("请先安装: pip install pywin32 Pillow")
    sys.exit(1)


# ---------- 底层功能 ----------

def enum_windows():
    """枚举所有可见、有标题的窗口, 返回 [(hwnd, title), ...]"""
    result = []

    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title.strip():
                result.append((hwnd, title))

    win32gui.EnumWindows(callback, None)
    return result


def post_click(hwnd, x, y):
    """向指定窗口客户区 (x,y) 发送一次左键单击。"""
    lparam = win32api.MAKELONG(x, y)
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
    time.sleep(0.05)
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam)


def key_name_to_vk(name):
    """把键名转为虚拟键码。只支持最简单的: 单字母/数字 + 若干常用键。"""
    name = name.strip().lower()
    if len(name) == 1 and name.isalnum():
        return ord(name.upper())
    specials = {
        'space': win32con.VK_SPACE,
        'enter': win32con.VK_RETURN,
        'esc': win32con.VK_ESCAPE,
        'tab': win32con.VK_TAB,
        'up': win32con.VK_UP, 'down': win32con.VK_DOWN,
        'left': win32con.VK_LEFT, 'right': win32con.VK_RIGHT,
        'f1': win32con.VK_F1, 'f2': win32con.VK_F2,
        'f3': win32con.VK_F3, 'f4': win32con.VK_F4,
        'f5': win32con.VK_F5, 'f6': win32con.VK_F6,
        'f7': win32con.VK_F7, 'f8': win32con.VK_F8,
        'f9': win32con.VK_F9, 'f10': win32con.VK_F10,
        'f11': win32con.VK_F11, 'f12': win32con.VK_F12,
    }
    return specials.get(name)


def post_key(hwnd, vk):
    """向指定窗口发送 WM_KEYDOWN + WM_KEYUP。"""
    win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, vk, 0)
    time.sleep(0.05)
    win32gui.PostMessage(hwnd, win32con.WM_KEYUP, vk, 0)


def capture_window(hwnd, flag=1):
    """对指定窗口用 PrintWindow 截图。

    flag: 1=仅客户区, 2=包含 DWM 渲染, 3=两者合并。
    返回: PIL.Image 对象。
    """
    left, top, right, bot = win32gui.GetClientRect(hwnd)
    w, h = right - left, bot - top
    if w <= 0 or h <= 0:
        raise ValueError(f"窗口尺寸无效: {w}x{h}")

    hwndDC = win32gui.GetWindowDC(hwnd)
    mfcDC = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()
    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
    saveDC.SelectObject(saveBitMap)

    windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), flag)

    bmpinfo = saveBitMap.GetInfo()
    bmpstr = saveBitMap.GetBitmapBits(True)
    img = Image.frombuffer(
        'RGB',
        (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
        bmpstr, 'raw', 'BGRX', 0, 1,
    )

    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwndDC)
    return img


# ---------- GUI ----------

class TestGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("后台窗口消息测试")
        self.root.geometry("740x680")

        self.windows = []
        self.selected_hwnd = None
        self.preview_img = None  # 防止被 GC

        self._build_ui()
        self._refresh_windows()

    def _build_ui(self):
        pad = {'padx': 8, 'pady': 4}

        # 1. 窗口选择
        frm_win = ttk.LabelFrame(self.root, text="1. 选择目标窗口")
        frm_win.pack(fill='x', **pad)
        top = ttk.Frame(frm_win)
        top.pack(fill='x', padx=6, pady=6)
        ttk.Label(top, text="窗口:").pack(side='left')
        self.combo_win = ttk.Combobox(top, state='readonly', width=72)
        self.combo_win.pack(side='left', padx=4)
        self.combo_win.bind('<<ComboboxSelected>>', self._on_win_selected)
        ttk.Button(top, text="刷新", command=self._refresh_windows).pack(side='left', padx=4)
        self.lbl_hwnd = ttk.Label(frm_win, text="当前 HWND: 未选择", foreground='gray')
        self.lbl_hwnd.pack(anchor='w', padx=6, pady=2)

        # 2. 点击测试
        frm_click = ttk.LabelFrame(self.root, text="2. 后台点击测试 (坐标为客户区相对坐标)")
        frm_click.pack(fill='x', **pad)
        row = ttk.Frame(frm_click)
        row.pack(fill='x', padx=6, pady=6)
        ttk.Label(row, text="X:").pack(side='left')
        self.ent_x = ttk.Entry(row, width=6); self.ent_x.insert(0, "100"); self.ent_x.pack(side='left', padx=4)
        ttk.Label(row, text="Y:").pack(side='left')
        self.ent_y = ttk.Entry(row, width=6); self.ent_y.insert(0, "100"); self.ent_y.pack(side='left', padx=4)
        ttk.Button(row, text="发送左键单击", command=self._test_click).pack(side='left', padx=8)

        # 3. 按键测试
        frm_key = ttk.LabelFrame(self.root, text="3. 后台按键测试 (单键: a-z, 0-9, space, enter, esc, f1-f12, 方向键)")
        frm_key.pack(fill='x', **pad)
        row = ttk.Frame(frm_key)
        row.pack(fill='x', padx=6, pady=6)
        ttk.Label(row, text="键:").pack(side='left')
        self.ent_key = ttk.Entry(row, width=10); self.ent_key.insert(0, "a"); self.ent_key.pack(side='left', padx=4)
        ttk.Button(row, text="发送按键", command=self._test_key).pack(side='left', padx=8)

        # 4. 截图测试
        frm_cap = ttk.LabelFrame(self.root, text="4. 后台截图测试")
        frm_cap.pack(fill='both', expand=True, **pad)
        row = ttk.Frame(frm_cap)
        row.pack(fill='x', padx=6, pady=6)
        ttk.Label(row, text="模式:").pack(side='left')
        self.cmb_flag = ttk.Combobox(row, values=['1 (客户区)', '2 (含DWM)', '3 (合并)'],
                                     state='readonly', width=12)
        self.cmb_flag.current(0)
        self.cmb_flag.pack(side='left', padx=4)
        ttk.Button(row, text="截图预览", command=self._test_capture).pack(side='left', padx=8)
        ttk.Button(row, text="截图并保存…", command=self._test_capture_save).pack(side='left', padx=4)
        self.lbl_preview = ttk.Label(frm_cap, text="(截图预览区)", anchor='center',
                                     background='#dddddd')
        self.lbl_preview.pack(fill='both', expand=True, padx=6, pady=6)

        # 日志
        frm_log = ttk.LabelFrame(self.root, text="日志")
        frm_log.pack(fill='x', **pad)
        self.txt_log = tk.Text(frm_log, height=7, wrap='word')
        self.txt_log.pack(fill='x', padx=6, pady=6)

    def _log(self, msg):
        self.txt_log.insert('end', msg + '\n')
        self.txt_log.see('end')

    def _refresh_windows(self):
        self.windows = enum_windows()
        labels = [f"[{hwnd}] {title}" for hwnd, title in self.windows]
        self.combo_win['values'] = labels
        self._log(f"已枚举 {len(labels)} 个窗口")

    def _on_win_selected(self, _event):
        idx = self.combo_win.current()
        if 0 <= idx < len(self.windows):
            hwnd, title = self.windows[idx]
            self.selected_hwnd = hwnd
            self.lbl_hwnd.config(text=f"当前 HWND: {hwnd}  标题: {title}", foreground='black')
            try:
                l, t, r, b = win32gui.GetClientRect(hwnd)
                self._log(f"已选择 HWND={hwnd}, 客户区 {r-l}x{b-t}, 标题: {title}")
            except Exception as e:
                self._log(f"读取窗口信息失败: {e}")

    def _ensure_selected(self):
        if not self.selected_hwnd:
            messagebox.showwarning("未选择窗口", "请先在上方选择一个目标窗口")
            return False
        if not win32gui.IsWindow(self.selected_hwnd):
            messagebox.showerror("窗口失效", "目标窗口已关闭, 请刷新并重新选择")
            return False
        return True

    def _test_click(self):
        if not self._ensure_selected():
            return
        try:
            x = int(self.ent_x.get()); y = int(self.ent_y.get())
        except ValueError:
            messagebox.showerror("坐标错误", "X/Y 必须是整数")
            return
        try:
            post_click(self.selected_hwnd, x, y)
            self._log(f"点击已发送: HWND={self.selected_hwnd}, 客户区 ({x},{y})")
        except Exception as e:
            self._log(f"点击失败: {e}")

    def _test_key(self):
        if not self._ensure_selected():
            return
        name = self.ent_key.get().strip()
        vk = key_name_to_vk(name)
        if vk is None:
            messagebox.showerror("按键错误", f"不支持的键: {name}")
            return
        try:
            post_key(self.selected_hwnd, vk)
            self._log(f"按键已发送: '{name}' (VK=0x{vk:02X})")
        except Exception as e:
            self._log(f"按键失败: {e}")

    def _get_flag(self):
        return int(self.cmb_flag.get().split()[0])

    def _test_capture(self):
        if not self._ensure_selected():
            return
        try:
            img = capture_window(self.selected_hwnd, self._get_flag())
            self._show_preview(img)
            self._log(f"截图成功 (模式 {self._get_flag()}): {img.size}")
        except Exception as e:
            self._log(f"截图失败: {e}")

    def _test_capture_save(self):
        if not self._ensure_selected():
            return
        try:
            img = capture_window(self.selected_hwnd, self._get_flag())
            path = filedialog.asksaveasfilename(defaultextension='.png',
                                                filetypes=[('PNG', '*.png')])
            if path:
                img.save(path)
                self._show_preview(img)
                self._log(f"截图已保存: {path}")
        except Exception as e:
            self._log(f"截图失败: {e}")

    def _show_preview(self, img):
        max_w, max_h = 700, 340
        w, h = img.size
        ratio = min(max_w / w, max_h / h, 1.0)
        if ratio < 1.0:
            img = img.resize((int(w * ratio), int(h * ratio)))
        self.preview_img = ImageTk.PhotoImage(img)
        self.lbl_preview.config(image=self.preview_img, text='')


def main():
    if sys.platform != 'win32':
        print("本脚本仅支持 Windows 运行")
        sys.exit(1)
    root = tk.Tk()
    TestGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
