#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
截图工具模块
使用mss库截图，解决RDP远程桌面下pyautogui截图黑屏的问题
"""

import mss
import mss.tools
from PIL import Image


def take_screenshot(region=None):
    """
    截取屏幕，返回PIL.Image对象

    Args:
        region: 可选，截图区域 (left, top, width, height)

    Returns:
        PIL.Image: 截图的PIL图片对象(RGB模式)
    """
    with mss.mss() as sct:
        if region:
            left, top, width, height = region
            monitor = {"left": left, "top": top, "width": width, "height": height}
        else:
            monitor = sct.monitors[0]  # 全屏（包含所有显示器）

        sct_img = sct.grab(monitor)
        # mss返回BGRA格式，转换为RGB的PIL Image
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        return img
