#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
窗口管理模块
负责游戏窗口的选择和坐标管理
"""

import ctypes
import ctypes.wintypes
import threading


# Windows API 常量
WH_MOUSE_LL = 14
WM_LBUTTONDOWN = 0x0201
IDC_CROSS = 32515

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


class WindowManager:
    """窗口管理器"""

    def __init__(self):
        self.hwnd = None  # 绑定的窗口句柄
        self.window_title = ""  # 窗口标题

    def start_pick_window(self, callback):
        """启动窗口选择模式

        在后台线程中运行，用户点击任意窗口后回调。

        Args:
            callback: 回调函数，参数为 (hwnd, title) 或 (None, None) 表示取消
        """
        thread = threading.Thread(target=self._pick_window_thread, args=(callback,), daemon=True)
        thread.start()

    def _pick_window_thread(self, callback):
        """窗口选择线程"""
        picked_hwnd = [None]

        HOOKPROC = ctypes.CFUNCTYPE(ctypes.c_long, ctypes.c_int,
                                     ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM)

        def mouse_proc(nCode, wParam, lParam):
            if nCode >= 0 and wParam == WM_LBUTTONDOWN:
                pt = ctypes.wintypes.POINT()
                user32.GetCursorPos(ctypes.byref(pt))
                hwnd = user32.WindowFromPoint(pt)
                # 获取顶层父窗口
                root_hwnd = user32.GetAncestor(hwnd, 2)  # GA_ROOT = 2
                if root_hwnd:
                    picked_hwnd[0] = root_hwnd
                else:
                    picked_hwnd[0] = hwnd
                user32.PostQuitMessage(0)
                return 1  # 拦截点击
            return user32.CallNextHookEx(None, nCode, wParam, lParam)

        proc = HOOKPROC(mouse_proc)
        hook = user32.SetWindowsHookExW(WH_MOUSE_LL, proc, kernel32.GetModuleHandleW(None), 0)

        if not hook:
            callback(None, None)
            return

        msg = ctypes.wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        user32.UnhookWindowsHookEx(hook)

        hwnd = picked_hwnd[0]
        if hwnd:
            title = self._get_window_title(hwnd)
            self.hwnd = hwnd
            self.window_title = title
            callback(hwnd, title)
        else:
            callback(None, None)

    def _get_window_title(self, hwnd):
        """获取窗口标题"""
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return ""
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value

    def get_window_rect(self):
        """获取绑定窗口的屏幕坐标

        Returns:
            tuple: (left, top, width, height) 或 None
        """
        if not self.hwnd:
            return None
        rect = ctypes.wintypes.RECT()
        if user32.GetWindowRect(self.hwnd, ctypes.byref(rect)):
            return (rect.left, rect.top,
                    rect.right - rect.left, rect.bottom - rect.top)
        return None

    def is_window_valid(self):
        """检查绑定的窗口是否仍然有效"""
        if not self.hwnd:
            return False
        return bool(user32.IsWindow(self.hwnd))

    def grid_to_screen(self, grid_x, grid_y, backpack_origin, cell_width, cell_height):
        """将背包网格坐标转换为屏幕坐标（格子中心点）

        Args:
            grid_x: 列索引 (0-4)
            grid_y: 行索引 (0-3)
            backpack_origin: 背包网格左上角的屏幕坐标 (x, y)
            cell_width: 格子宽度
            cell_height: 格子高度

        Returns:
            tuple: (screen_x, screen_y) 格子中心的屏幕坐标
        """
        origin_x, origin_y = backpack_origin
        screen_x = origin_x + grid_x * cell_width + cell_width // 2
        screen_y = origin_y + grid_y * cell_height + cell_height // 2
        return (screen_x, screen_y)

    def get_bind_info(self):
        """获取绑定信息的显示文本"""
        if not self.hwnd:
            return "未绑定"
        if not self.is_window_valid():
            return "窗口已失效"
        return f"已绑定: {self.window_title} (句柄:0x{self.hwnd:X})"
