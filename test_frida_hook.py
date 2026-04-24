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
// 跨 Frida 版本解析导出符号 (Frida 17 移除了 Module.findExportByName)
function resolveExport(moduleName, exportName) {
    var attempts = [
        function () { return Module.findExportByName(moduleName, exportName); },
        function () { return Module.getExportByName(moduleName, exportName); },
        function () { return Module.findGlobalExportByName(exportName); },
        function () { return Module.getGlobalExportByName(exportName); },
        function () {
            var m = Process.getModuleByName(moduleName);
            return m.getExportByName(exportName);
        },
        function () {
            var m = Process.findModuleByName(moduleName);
            return m ? m.getExportByName(exportName) : null;
        }
    ];
    for (var i = 0; i < attempts.length; i++) {
        try {
            var r = attempts[i]();
            if (r) { return { addr: r, via: i }; }
        } catch (e) { /* try next */ }
    }
    return null;
}

send('Frida runtime: ' + (typeof Frida !== 'undefined' && Frida.version ? Frida.version : 'unknown')
   + ', pointerSize=' + Process.pointerSize);

var fakeX = 0;
var fakeY = 0;

// 调用计数: 用来诊断游戏到底调了哪个 API 读光标
var stats = { GetCursorPos: 0, GetCursorInfo: 0, GetMessagePos: 0 };

rpc.exports = {
    setpos: function (x, y) { fakeX = x; fakeY = y; },
    getpos: function () { return [fakeX, fakeY]; },
    stats: function () { return stats; },
    resetstats: function () {
        stats.GetCursorPos = 0;
        stats.GetCursorInfo = 0;
        stats.GetMessagePos = 0;
    }
};

var gcp = resolveExport('user32.dll', 'GetCursorPos');
if (gcp === null) {
    send('ERROR: GetCursorPos not resolvable via any API');
} else {
    Interceptor.attach(gcp.addr, {
        onEnter: function (args) { this.lp = args[0]; },
        onLeave: function (retval) {
            stats.GetCursorPos++;
            if (!this.lp.isNull()) {
                this.lp.writeS32(fakeX);
                this.lp.add(4).writeS32(fakeY);
            }
        }
    });
    send('HOOKED: GetCursorPos @ ' + gcp.addr + ' (via method #' + gcp.via + ')');
}

// 顺手 hook GetCursorInfo, 某些游戏用它代替 GetCursorPos
var gci = resolveExport('user32.dll', 'GetCursorInfo');
if (gci !== null) {
    Interceptor.attach(gci.addr, {
        onEnter: function (args) { this.lp = args[0]; },
        onLeave: function (retval) {
            stats.GetCursorInfo++;
            if (!this.lp.isNull()) {
                // CURSORINFO: DWORD cbSize; DWORD flags; HCURSOR hCursor; POINT ptScreenPos;
                // HCURSOR 是指针, 32 位 = 4 字节, 64 位 = 8 字节
                var offset = 4 + 4 + Process.pointerSize;
                this.lp.add(offset).writeS32(fakeX);
                this.lp.add(offset + 4).writeS32(fakeY);
            }
        }
    });
    send('HOOKED: GetCursorInfo @ ' + gci.addr);
}

// GetMessagePos: 返回 DWORD (LOWORD=x, HIWORD=y), 老 Win32 游戏最常用的取光标方式
var gmp = resolveExport('user32.dll', 'GetMessagePos');
if (gmp !== null) {
    Interceptor.attach(gmp.addr, {
        onLeave: function (retval) {
            stats.GetMessagePos++;
            var packed = (((fakeY & 0xFFFF) << 16) | (fakeX & 0xFFFF)) >>> 0;
            retval.replace(ptr(packed));
        }
    });
    send('HOOKED: GetMessagePos @ ' + gmp.addr);
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


def _pack_lparam(x, y):
    return ((y & 0xFFFF) << 16) | (x & 0xFFFF)


def post_move_and_click(hwnd, screen_x, screen_y):
    """先发 WM_MOUSEMOVE 再发 WM_LBUTTONDOWN/UP, lparam 里塞客户区坐标。
    如果游戏靠 WM_MOUSEMOVE 追踪位置, 这样就能让它"以为"光标在目标位置。"""
    cx, cy = win32gui.ScreenToClient(hwnd, (screen_x, screen_y))
    lp = _pack_lparam(cx, cy)
    win32gui.PostMessage(hwnd, win32con.WM_MOUSEMOVE, 0, lp)
    time.sleep(0.03)
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lp)
    time.sleep(0.05)
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lp)
    return cx, cy


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
        f3 = ttk.LabelFrame(self.root, text="3. 发送点击 (真实鼠标要先挪到远离游戏的位置!)")
        f3.pack(fill='x', **pad)
        r = ttk.Frame(f3); r.pack(fill='x', padx=6, pady=6)
        ttk.Button(r, text="仅点击 (靠 hook 伪造光标)", command=self._click).pack(side='left', padx=4)
        ttk.Button(r, text="假鼠标移动+点击 (塞 lparam)", command=self._click_with_move).pack(side='left', padx=4)
        ttk.Label(f3, text="  两种方式都用上面输入框里的坐标作为目标屏幕坐标",
                  foreground='gray').pack(anchor='w', padx=6)

        # 4. 诊断: 查看 hook 被调用了几次, 判断游戏实际用的是哪个 API
        f5 = ttk.LabelFrame(self.root, text="4. 诊断 (点击后查看计数, 判断游戏调了哪个 API)")
        f5.pack(fill='x', **pad)
        r = ttk.Frame(f5); r.pack(fill='x', padx=6, pady=6)
        ttk.Button(r, text="查询调用计数", command=self._show_stats).pack(side='left', padx=4)
        ttk.Button(r, text="重置计数", command=self._reset_stats).pack(side='left', padx=4)
        ttk.Label(r, text="  建议: 先重置 → 点击 → 查询, 看哪项计数涨了",
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
            self._log(f"已发送仅点击到 HWND={self.hwnd} (依赖 hook 伪造光标)")
        except Exception as e:
            self._log(f"点击失败: {e}")

    def _click_with_move(self):
        if not self.hwnd:
            messagebox.showwarning("", "请先选择窗口"); return
        if not win32gui.IsWindow(self.hwnd):
            messagebox.showerror("", "窗口已失效, 请刷新"); return
        try:
            sx = int(self.ent_x.get()); sy = int(self.ent_y.get())
        except ValueError:
            messagebox.showerror("", "X/Y 必须是整数"); return
        try:
            cx, cy = post_move_and_click(self.hwnd, sx, sy)
            self._log(f"已发送 MouseMove+点击: 屏幕({sx},{sy}) → 客户区({cx},{cy})")
        except Exception as e:
            self._log(f"点击失败: {e}")

    def _show_stats(self):
        if not self.script:
            messagebox.showwarning("", "还未注入"); return
        try:
            s = self.script.exports_sync.stats()
            self._log(f"Hook 调用计数: GetCursorPos={s.get('GetCursorPos')}  "
                      f"GetCursorInfo={s.get('GetCursorInfo')}  "
                      f"GetMessagePos={s.get('GetMessagePos')}")
        except Exception as e:
            self._log(f"查询失败: {e}")

    def _reset_stats(self):
        if not self.script:
            messagebox.showwarning("", "还未注入"); return
        try:
            self.script.exports_sync.resetstats()
            self._log("已重置 hook 调用计数")
        except Exception as e:
            self._log(f"重置失败: {e}")

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
