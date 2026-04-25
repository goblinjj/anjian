#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
截图工具模块

两种模式:
    1. mss: 从屏幕抓取像素, 窗口被遮挡会截到遮挡物。
    2. 窗口模式 (BitBlt): 直接从游戏窗口的 DC 拷贝, 不触发重绘 → 不闪烁,
       即使被其他窗口遮挡也能拿到游戏画面 (经 魔力宝贝 等老游戏验证)。

用法:
    引擎启动时 set_capture_hwnd(hwnd) 绑定游戏窗口,
    之后 take_screenshot(region=...) 会优先用 BitBlt 抓窗口再裁剪 region;
    BitBlt 失败 / 返回黑屏时自动回退到 mss。
    引擎停止时 set_capture_hwnd(None) 解绑。
"""

import mss
import mss.tools
from PIL import Image

try:
    import win32gui
    import win32ui
    import win32con
    _HAS_WIN32 = True
except ImportError:
    _HAS_WIN32 = False


_bound_hwnd = None


def set_capture_hwnd(hwnd):
    """绑定游戏窗口。绑定后 take_screenshot(region=...) 会优先用 BitBlt
    从该窗口抓像素, 即使被遮挡也能截。传 None 解绑, 恢复到 mss 屏幕截图。"""
    global _bound_hwnd
    _bound_hwnd = hwnd if hwnd else None


def get_capture_hwnd():
    return _bound_hwnd


def _capture_window(hwnd):
    """用 BitBlt 从窗口 DC 拷贝整个窗口 (含标题栏), 返回 PIL.Image 或 None。
    BitBlt 不发 WM_PRINT, 不触发游戏重绘, 所以无闪烁;
    被遮挡时通过 DWM 重定向位图通常仍可拿到画面。
    None 表示尺寸异常 / 异常 / 全黑。"""
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

        save_dc.BitBlt((0, 0), (w, h), mfc_dc, (0, 0), win32con.SRCCOPY)

        info = bmp.GetInfo()
        bits = bmp.GetBitmapBits(True)
        img = Image.frombytes(
            'RGB', (info['bmWidth'], info['bmHeight']),
            bits, 'raw', 'BGRX', 0, 1,
        )

        # 黑屏检测: 49 个采样点全部近乎纯黑才判失败, 否则接受
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

    策略:
        - 未绑定窗口 / region=None: 直接 mss。
        - 已绑定窗口: BitBlt 抓整窗口再裁剪 region (无闪烁, 被遮挡也能截);
          BitBlt 失败 / 黑屏自动回退 mss。
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
            crop_l = max(0, crop_l)
            crop_t = max(0, crop_t)
            crop_r = min(win_img.width, crop_r)
            crop_b = min(win_img.height, crop_b)
            if crop_r > crop_l and crop_b > crop_t:
                return win_img.crop((crop_l, crop_t, crop_r, crop_b))
        # BitBlt 失败 / 黑屏 → mss 回退 (会截到遮挡物, 但起码不会崩)
    return _mss_capture(region)
