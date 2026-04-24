"""
Frida GetCursorPos Hook 测试 —— 验证"真后台 + 真实鼠标不动"方案。

原理:
    游戏在收到点击消息时调用 GetCursorPos() 读取真实光标位置。
    用 Frida 注入 JS 代码, 劫持 user32!GetCursorPos 的返回值,
    让它返回我们伪造的 (fakeX, fakeY)。
    之后 PostMessage 发送点击消息 —— 游戏"以为"光标在假坐标那里,
    真实鼠标原地不动。

依赖 (已由 PyInstaller 打包进 exe, 独立运行):
    frida, pywin32

删除方法: 直接删除本文件即可。

注意事项:
    - 仅 Windows。
    - 魔力宝贝通常是 32 位老游戏, Frida 会自动使用 32 位 agent, 无需手动处理。
    - 若目标游戏以管理员身份运行, 本程序也必须以管理员身份启动, 否则注入会失败。
    - 假光标坐标是"屏幕坐标"(整个桌面范围), 不是窗口内坐标。
    - 杀毒软件很可能误报 Frida, 请加白名单。
"""
import sys
import time
import queue
import tkinter as tk
from tkinter import ttk, messagebox

try:
    import frida
    import win32gui
    import win32con
    import win32api
    import win32process
except ImportError as e:
    print(f"缺少依赖: {e}")
    print("请先安装: pip install frida pywin32")
    sys.exit(1)


HOOK_SCRIPT = r"""
var fakeX = 0;
var fakeY = 0;

rpc.exports = {
    setpos: function (x, y) { fakeX = x; fakeY = y; },
    getpos: function () { return [fakeX, fakeY]; }
};

var pGetCursorPos = Module.findExportByName('user32.dll', 'GetCursorPos');
if (pGetCursorPos === null) {
    send('ERROR: GetCursorPos not found');
} else {
    Interceptor.attach(pGetCursorPos, {
        onEnter: function (args) { this.lp = args[0]; },
        onLeave: function (retval) {
            if (!this.lp.isNull()) {
                this.lp.writeS32(fakeX);
                this.lp.add(4).writeS32(fakeY);
            }
        }
    });
    send('HOOKED: GetCursorPos');
}

// 顺手 hook 一下 GetCursorInfo, 某些游戏用它代替 GetCursorPos
var pGetCursorInfo = Module.findExportByName('user32.dll', 'GetCursorInfo');
if (pGetCursorInfo !== null) {
    Interceptor.attach(pGetCursorInfo, {
        onEnter: function (args) { this.lp = args[0]; },
        onLeave: function (retval) {
            if (!this.lp.isNull()) {
                // CURSORINFO 结构: DWORD cbSize; DWORD flags; HCURSOR hCursor; POINT ptScreenPos;
                // POINT 在 32 位系统是偏移 12, 在 64 位系统是偏移 16 (HCURSOR 是指针)
                var ptrSize = Process.pointerSize;
                var offset = 4 + 4 + ptrSize;
                this.lp.add(offset).writeS32(fakeX);
                this.lp.add(offset + 4).writeS32(fakeY);
            }
        }
    });
    send('HOOKED: GetCursorInfo');
}
"""


# ---------- 底层 ----------

def enum_windows():
    result = []

    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            t = win32gui.GetWindowText(hwnd)
            if t.strip():
                result.append((hwnd, t))

    win32gui.EnumWindows(cb, None)
    return result


def pid_of(hwnd):
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    return pid


def post_click(hwnd):
    """发送一次左键点击。lparam 里的坐标我们不关心,
    因为游戏会去调 GetCursorPos (已被 hook 劫持返回假坐标)。"""
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, 0)
    time.sleep(0.05)
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, 0)


# ---------- GUI ----------

class TestGUI:
    def __init__(self, root):
        self.root = root
        root.title("Frida Hook 测试 (真后台点击)")
        root.geometry("820x680")

        self.windows = []
        self.hwnd = None
        self.pid = None
        self.session = None
        self.script = None
        self.msg_q = queue.Queue()

        self._build_ui()
        self._refresh_windows()
        self.root.after(100, self._drain_msgs)

    def _build_ui(self):
        pad = {'padx': 8, 'pady': 4}

        # 1. 窗口选择
        f1 = ttk.LabelFrame(self.root, text="1. 选择目标窗口 (魔力宝贝)")
        f1.pack(fill='x', **pad)
        r = ttk.Frame(f1); r.pack(fill='x', padx=6, pady=6)
        ttk.Label(r, text="窗口:").pack(side='left')
        self.cbo = ttk.Combobox(r, state='readonly', width=72)
        self.cbo.pack(side='left', padx=4)
        self.cbo.bind('<<ComboboxSelected>>', self._on_select)
        ttk.Button(r, text="刷新", command=self._refresh_windows).pack(side='left', padx=4)
        self.lbl_info = ttk.Label(f1, text="未选择", foreground='gray')
        self.lbl_info.pack(anchor='w', padx=6, pady=2)

        # 2. 注入
        f2 = ttk.LabelFrame(self.root, text="2. 注入 Hook (锁定假光标在屏幕坐标 X,Y)")
        f2.pack(fill='x', **pad)
        r = ttk.Frame(f2); r.pack(fill='x', padx=6, pady=6)
        ttk.Label(r, text="假光标 屏幕X:").pack(side='left')
        self.ent_x = ttk.Entry(r, width=8); self.ent_x.insert(0, "500"); self.ent_x.pack(side='left', padx=4)
        ttk.Label(r, text="Y:").pack(side='left')
        self.ent_y = ttk.Entry(r, width=8); self.ent_y.insert(0, "400"); self.ent_y.pack(side='left', padx=4)
        ttk.Button(r, text="注入并锁定", command=self._attach).pack(side='left', padx=8)
        ttk.Button(r, text="更新坐标", command=self._update_pos).pack(side='left', padx=4)
        ttk.Button(r, text="解除注入", command=self._detach).pack(side='left', padx=4)
        self.lbl_status = ttk.Label(f2, text="未注入", foreground='gray')
        self.lbl_status.pack(anchor='w', padx=6, pady=2)

        # 3. 点击
        f3 = ttk.LabelFrame(self.root, text="3. 发送点击 (游戏会按假光标位置响应, 真实鼠标不动)")
        f3.pack(fill='x', **pad)
        r = ttk.Frame(f3); r.pack(fill='x', padx=6, pady=6)
        ttk.Button(r, text="发送左键点击到游戏窗口", command=self._click).pack(side='left', padx=8)
        ttk.Label(r, text="← 点这个前, 把真实鼠标移到远离游戏的位置, 观察游戏是否仍按假坐标响应",
                  foreground='gray').pack(side='left')

        # 日志
        f4 = ttk.LabelFrame(self.root, text="日志")
        f4.pack(fill='both', expand=True, **pad)
        self.txt = tk.Text(f4, height=18, wrap='word')
        self.txt.pack(fill='both', expand=True, padx=6, pady=6)

    def _log(self, m):
        self.txt.insert('end', m + '\n')
        self.txt.see('end')

    def _drain_msgs(self):
        try:
            while True:
                self._log(self.msg_q.get_nowait())
        except queue.Empty:
            pass
        self.root.after(100, self._drain_msgs)

    def _refresh_windows(self):
        self.windows = enum_windows()
        self.cbo['values'] = [f"[{h}] {t}" for h, t in self.windows]
        self._log(f"枚举 {len(self.windows)} 个窗口")

    def _on_select(self, _evt):
        i = self.cbo.current()
        if not (0 <= i < len(self.windows)):
            return
        self.hwnd, title = self.windows[i]
        try:
            self.pid = pid_of(self.hwnd)
            cl, ct, cr, cb = win32gui.GetClientRect(self.hwnd)
            pt1 = win32gui.ClientToScreen(self.hwnd, (0, 0))
            pt2 = win32gui.ClientToScreen(self.hwnd, (cr, cb))
            cx = (pt1[0] + pt2[0]) // 2
            cy = (pt1[1] + pt2[1]) // 2
            self.lbl_info.config(
                text=f"HWND={self.hwnd} PID={self.pid}  客户区 {cr - cl}x{cb - ct}  "
                     f"屏幕范围 {pt1}→{pt2}  屏幕中心 ({cx},{cy})",
                foreground='black')
            self._log(f"选中: {title}")
            self._log(f"  PID={self.pid}  客户区屏幕范围 {pt1}→{pt2}")
            self._log(f"  客户区中心(屏幕坐标) = ({cx},{cy})")
            self._log(f"  建议测试: 假光标填 ({cx + 100},{cy + 100}), 看人物是否向右下角走 1 格左右")
        except Exception as e:
            self._log(f"读取窗口失败: {e}")

    def _attach(self):
        if not self.pid:
            messagebox.showwarning("", "请先选择窗口"); return
        if self.session:
            messagebox.showwarning("", "已经注入过, 请先解除注入"); return
        try:
            x = int(self.ent_x.get()); y = int(self.ent_y.get())
        except ValueError:
            messagebox.showerror("", "X/Y 必须是整数"); return
        try:
            self._log(f"正在 attach PID={self.pid} ...")
            self.session = frida.attach(self.pid)
            self.script = self.session.create_script(HOOK_SCRIPT)
            self.script.on('message', self._on_script_msg)
            self.script.load()
            self.script.exports_sync.setpos(x, y)
            self.lbl_status.config(
                text=f"已注入 PID={self.pid}, 假光标锁定在屏幕 ({x},{y})",
                foreground='darkgreen')
            self._log(f"注入成功, 假光标锁定在屏幕 ({x},{y})")
        except Exception as e:
            self._log(f"注入失败: {e}")
            self._log("  常见原因: 1) 没用管理员身份启动  2) 游戏已关闭  3) 被杀毒拦截")
            self._cleanup()

    def _update_pos(self):
        if not self.script:
            messagebox.showwarning("", "还未注入"); return
        try:
            x = int(self.ent_x.get()); y = int(self.ent_y.get())
            self.script.exports_sync.setpos(x, y)
            self.lbl_status.config(
                text=f"已注入 PID={self.pid}, 假光标锁定在屏幕 ({x},{y})",
                foreground='darkgreen')
            self._log(f"已更新假光标坐标: ({x},{y})")
        except Exception as e:
            self._log(f"更新失败: {e}")

    def _detach(self):
        self._cleanup()
        self._log("已解除注入")

    def _cleanup(self):
        try:
            if self.script:
                self.script.unload()
        except Exception:
            pass
        try:
            if self.session:
                self.session.detach()
        except Exception:
            pass
        self.script = None
        self.session = None
        self.lbl_status.config(text="未注入", foreground='gray')

    def _click(self):
        if not self.hwnd:
            messagebox.showwarning("", "请先选择窗口"); return
        if not win32gui.IsWindow(self.hwnd):
            messagebox.showerror("", "窗口已失效, 请刷新"); return
        try:
            post_click(self.hwnd)
            self._log(f"已发送左键点击到 HWND={self.hwnd} (游戏应读取到假光标位置)")
        except Exception as e:
            self._log(f"点击失败: {e}")

    def _on_script_msg(self, msg, _data):
        # 此回调在 frida 线程, 用队列跨线程送到主线程显示
        if msg.get('type') == 'send':
            self.msg_q.put(f"[frida] {msg.get('payload')}")
        elif msg.get('type') == 'error':
            self.msg_q.put(f"[frida error] {msg.get('stack') or msg.get('description')}")


def main():
    if sys.platform != 'win32':
        print("仅支持 Windows"); sys.exit(1)
    root = tk.Tk()
    TestGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
