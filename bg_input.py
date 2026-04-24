#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
后台输入 —— 用 Windows 消息 (PostMessage) 向游戏窗口发鼠标/键盘, 不抢真实鼠标。

原理 (已对 魔力宝贝 验证):
    游戏通过 WM_MOUSEMOVE 消息的 lParam 追踪内部"当前光标位置",
    WM_LBUTTONDOWN 时使用这个位置。PostMessage 序列 MOVE→DOWN→UP
    就能让游戏响应点击, 而真实鼠标完全不动。

接口约定:
    - 传入的是 *屏幕坐标* (和现在 pyautogui 调用一致),
      内部用 ScreenToClient 转成客户区坐标再塞进 lParam。
    - 所有函数第一个参数是绑定的游戏窗口 HWND。
"""
import time
import ctypes
import ctypes.wintypes

user32 = ctypes.windll.user32

WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
MK_LBUTTON = 0x0001
MAPVK_VK_TO_VSC = 0

user32.PostMessageW.argtypes = [
    ctypes.wintypes.HWND, ctypes.wintypes.UINT,
    ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM,
]
user32.PostMessageW.restype = ctypes.wintypes.BOOL

user32.ScreenToClient.argtypes = [
    ctypes.wintypes.HWND, ctypes.POINTER(ctypes.wintypes.POINT),
]
user32.ScreenToClient.restype = ctypes.wintypes.BOOL

user32.MapVirtualKeyW.argtypes = [ctypes.wintypes.UINT, ctypes.wintypes.UINT]
user32.MapVirtualKeyW.restype = ctypes.wintypes.UINT


_SPECIAL_VK = {
    'ctrl': 0x11, 'control': 0x11,
    'shift': 0x10,
    'alt': 0x12, 'menu': 0x12,
    'win': 0x5B,
    'esc': 0x1B, 'escape': 0x1B,
    'enter': 0x0D, 'return': 0x0D,
    'tab': 0x09, 'space': 0x20,
    'backspace': 0x08,
    'delete': 0x2E, 'del': 0x2E,
    'home': 0x24, 'end': 0x23,
    'up': 0x26, 'down': 0x28, 'left': 0x25, 'right': 0x27,
}


def _vk_of(key):
    k = key.lower()
    if k in _SPECIAL_VK:
        return _SPECIAL_VK[k]
    if len(k) == 1:
        c = k.upper()
        if 'A' <= c <= 'Z' or '0' <= c <= '9':
            return ord(c)
    if k.startswith('f') and k[1:].isdigit():
        n = int(k[1:])
        if 1 <= n <= 24:
            return 0x70 + n - 1
    raise ValueError(f"unknown key: {key}")


def _screen_to_client(hwnd, sx, sy):
    pt = ctypes.wintypes.POINT(int(sx), int(sy))
    user32.ScreenToClient(hwnd, ctypes.byref(pt))
    return pt.x, pt.y


def _pack_lparam(x, y):
    return ((y & 0xFFFF) << 16) | (x & 0xFFFF)


def _post(hwnd, msg, wparam, lparam):
    # PostMessage lparam 必须是有符号 LPARAM, 负客户区坐标要保留低 32 位
    user32.PostMessageW(hwnd, msg, wparam, ctypes.c_long(lparam & 0xFFFFFFFF).value)


def _key_lparam_down(vk, repeat=1):
    scan = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)
    return (repeat & 0xFFFF) | ((scan & 0xFF) << 16)


def _key_lparam_up(vk, repeat=1):
    scan = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)
    # bit30 = previous state (1 = was down), bit31 = transition (1 = being released)
    return (repeat & 0xFFFF) | ((scan & 0xFF) << 16) | (3 << 30)


# ---------- 鼠标 ----------

def post_move(hwnd, screen_x, screen_y):
    """仅更新游戏内部光标位置 (不产生点击)。"""
    cx, cy = _screen_to_client(hwnd, screen_x, screen_y)
    _post(hwnd, WM_MOUSEMOVE, 0, _pack_lparam(cx, cy))


def post_click(hwnd, screen_x, screen_y, pre_delay=0.0, hold_time=0.05):
    """左键单击 (MOVE → 前置延迟 → DOWN → 持续时间 → UP)。"""
    cx, cy = _screen_to_client(hwnd, screen_x, screen_y)
    lp = _pack_lparam(cx, cy)
    _post(hwnd, WM_MOUSEMOVE, 0, lp)
    if pre_delay > 0:
        time.sleep(pre_delay)
    _post(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lp)
    time.sleep(hold_time)
    _post(hwnd, WM_LBUTTONUP, 0, lp)


def post_long_press(hwnd, screen_x, screen_y, pre_delay=0.0, hold_time=0.5):
    """左键长按, 用于"整理背包"这类需要按住的按钮。"""
    post_click(hwnd, screen_x, screen_y, pre_delay=pre_delay, hold_time=hold_time)


def post_double_click(hwnd, screen_x, screen_y, pre_delay=0.0, interval=0.1):
    """左键双击。"""
    cx, cy = _screen_to_client(hwnd, screen_x, screen_y)
    lp = _pack_lparam(cx, cy)
    _post(hwnd, WM_MOUSEMOVE, 0, lp)
    if pre_delay > 0:
        time.sleep(pre_delay)
    for i in range(2):
        _post(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lp)
        time.sleep(0.05)
        _post(hwnd, WM_LBUTTONUP, 0, lp)
        if i == 0:
            time.sleep(interval)


# ---------- 键盘 ----------

def post_key(hwnd, key, hold_time=0.03):
    """单键按下+抬起 (key 可以是 'e', 'escape', 'f1' 等)。"""
    vk = _vk_of(key) if isinstance(key, str) else int(key)
    _post(hwnd, WM_KEYDOWN, vk, _key_lparam_down(vk))
    time.sleep(hold_time)
    _post(hwnd, WM_KEYUP, vk, _key_lparam_up(vk))


def post_hotkey(hwnd, *keys, hold_time=0.05):
    """组合键, 如 post_hotkey(hwnd, 'ctrl', 'e')。
    按下顺序压下, 逆序抬起, 模拟真实按键。"""
    vks = [_vk_of(k) for k in keys]
    for vk in vks:
        _post(hwnd, WM_KEYDOWN, vk, _key_lparam_down(vk))
        time.sleep(0.02)
    time.sleep(hold_time)
    for vk in reversed(vks):
        _post(hwnd, WM_KEYUP, vk, _key_lparam_up(vk))
        time.sleep(0.02)
