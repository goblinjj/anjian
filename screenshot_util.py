#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
截图工具模块

两种模式:
    1. 普通模式 (mss): 从屏幕抓取像素, 窗口被遮挡会截到遮挡物。
    2. 窗口模式 (PrintWindow): 让游戏自己把画面重绘到离屏 DC, 窗口被遮挡也能截。

用法:
    引擎启动时调用 set_capture_hwnd(hwnd) 绑定游戏窗口,
    之后 take_screenshot(region=...) 会优先用 PrintWindow,
    失败或黑屏时自动回退到 mss。
    引擎停止时 set_capture_hwnd(None) 解绑。
"""

import ctypes
import ctypes.wintypes

import mss
import mss.tools
from PIL import Image

try:
    import win32gui
    import win32ui
    _HAS_WIN32 = True
except ImportError:
    _HAS_WIN32 = False


PW_RENDERFULLCONTENT = 2

_bound_hwnd = None

_user32 = ctypes.windll.user32
_user32.PrintWindow.argtypes = [
    ctypes.wintypes.HWND, ctypes.wintypes.HDC, ctypes.wintypes.UINT,
]
_user32.PrintWindow.restype = ctypes.wintypes.BOOL


def set_capture_hwnd(hwnd):
    """绑定游戏窗口。绑定后 take_screenshot(region=...) 会优先用 PrintWindow
    从该窗口抓像素, 即使被遮挡也能截。传 None 解绑, 恢复到 mss 屏幕截图。"""
    global _bound_hwnd
    _bound_hwnd = hwnd if hwnd else None


def get_capture_hwnd():
    return _bound_hwnd


def _capture_window(hwnd):
    """用 PrintWindow 抓整个窗口 (含标题栏), 返回 PIL.Image 或 None。
    None 表示失败或画面全黑 (DWM/串流抽风)。"""
    if not _HAS_WIN32 or not hwnd:
        return None

    hwnd_dc = None
    mfc_dc = None
    save_dc = None
    bmp = None
    try:
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        w, h = right - left, bottom - top
        if w <= 0 or h <= 0:
            return None

        hwnd_dc = win32gui.GetWindowDC(hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()
        bmp = win32ui.CreateBitmap()
        bmp.CreateCompatibleBitmap(mfc_dc, w, h)
        save_dc.SelectObject(bmp)

        ok = _user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), PW_RENDERFULLCONTENT)
        if not ok:
            return None

        info = bmp.GetInfo()
        bits = bmp.GetBitmapBits(True)
        img = Image.frombytes(
            'RGB', (info['bmWidth'], info['bmHeight']),
            bits, 'raw', 'BGRX', 0, 1,
        )

        # 黑屏检测: 等距采样几十个点, 全部近乎纯黑才判失败, 否则接受
        sample = [
            img.getpixel((img.width * i // 8, img.height * j // 8))
            for i in range(1, 8) for j in range(1, 8)
        ]
        if all(max(p[:3]) < 3 for p in sample):
            return None
        return img
    except Exception:
        return None
    finally:
        try:
            if bmp is not None:
                win32gui.DeleteObject(bmp.GetHandle())
        except Exception:
            pass
        try:
            if save_dc is not None:
                save_dc.DeleteDC()
        except Exception:
            pass
        try:
            if mfc_dc is not None:
                mfc_dc.DeleteDC()
        except Exception:
            pass
        try:
            if hwnd_dc:
                win32gui.ReleaseDC(hwnd, hwnd_dc)
        except Exception:
            pass


def _mss_capture(region):
    with mss.mss() as sct:
        if region:
            left, top, width, height = region
            monitor = {"left": left, "top": top, "width": width, "height": height}
        else:
            monitor = sct.monitors[0]
        sct_img = sct.grab(monitor)
        return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")


def take_screenshot(region=None):
    """
    截图, 返回 PIL.Image (RGB)。

    Args:
        region: 可选 (left, top, width, height) 屏幕坐标区域。

    如果通过 set_capture_hwnd() 绑定了窗口且 region 不为空,
    会先尝试 PrintWindow 抓整窗口再裁剪 region;
    PrintWindow 失败或黑屏时回退到 mss。
    """
    hwnd = _bound_hwnd
    if region is not None and hwnd and _HAS_WIN32:
        win_img = _capture_window(hwnd)
        if win_img is not None:
            try:
                win_left, win_top, _, _ = win32gui.GetWindowRect(hwnd)
            except Exception:
                return _mss_capture(region)
            r_left, r_top, r_w, r_h = region
            crop_l = r_left - win_left
            crop_t = r_top - win_top
            crop_r = crop_l + r_w
            crop_b = crop_t + r_h
            # 边界钳制
            crop_l = max(0, crop_l)
            crop_t = max(0, crop_t)
            crop_r = min(win_img.width, crop_r)
            crop_b = min(win_img.height, crop_b)
            if crop_r > crop_l and crop_b > crop_t:
                return win_img.crop((crop_l, crop_t, crop_r, crop_b))
        # PrintWindow 不可用/失败/黑屏, 回退 mss
    return _mss_capture(region)
