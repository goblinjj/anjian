#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
背包识别模块
在游戏窗口中定位背包，切割网格，识别物品图标和数量
"""

import cv2
import numpy as np
from PIL import Image
from screenshot_util import take_screenshot


# 背包网格常量
GRID_COLS = 5
GRID_ROWS = 4
GRID_TOTAL = GRID_COLS * GRID_ROWS  # 20


class BackpackSlot:
    """背包格子信息"""
    def __init__(self, grid_x, grid_y, icon_image, quantity):
        self.grid_x = grid_x       # 列索引 0-4
        self.grid_y = grid_y       # 行索引 0-3
        self.icon_image = icon_image  # numpy array, 物品图标区域
        self.quantity = quantity    # int or None


class BackpackReader:
    """背包读取器"""

    def __init__(self, digit_recognizer, settings=None):
        """
        Args:
            digit_recognizer: DigitRecognizer 实例
            settings: dict, 包含背包相关设置:
                - backpack_title_image: 背包标题栏模板图片路径
                - cell_width: 格子宽度 (像素)
                - cell_height: 格子高度 (像素)
                - grid_offset_x: 网格相对于标题栏左侧的X偏移
                - grid_offset_y: 网格相对于标题栏底部的Y偏移
                - digit_region: 数字区域在格子内的相对位置 {x, y, w, h}
                - icon_region: 图标区域在格子内的相对位置 {x, y, w, h}
        """
        self.digit_recognizer = digit_recognizer
        self.settings = settings or {}

    def locate_backpack(self, window_region, confidence=0.7):
        """在窗口截图中定位背包

        Args:
            window_region: (left, top, width, height) 游戏窗口的屏幕区域
            confidence: float 匹配置信度阈值

        Returns:
            tuple: (backpack_x, backpack_y, info) 背包网格左上角的屏幕坐标和诊断信息，
                   或 (None, None, error_msg) 如果未找到
        """
        title_image_path = self.settings.get('backpack_title_image')
        if not title_image_path:
            return (None, None, "未设置背包定位模板，请在「设置」中截取")

        import os
        if not os.path.exists(title_image_path):
            return (None, None, f"模板文件不存在: {title_image_path}")

        # 截取游戏窗口区域
        screenshot = take_screenshot(region=window_region)
        screenshot_np = np.array(screenshot)
        screenshot.close()
        screenshot_bgr = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)

        # 加载背包标题模板
        pil_tmpl = Image.open(title_image_path)
        tmpl = np.array(pil_tmpl)
        pil_tmpl.close()
        if len(tmpl.shape) == 3:
            tmpl = cv2.cvtColor(tmpl, cv2.COLOR_RGB2BGR)

        # 检查模板尺寸是否合理
        if tmpl.shape[0] > screenshot_bgr.shape[0] or tmpl.shape[1] > screenshot_bgr.shape[1]:
            return (None, None,
                    f"模板图片({tmpl.shape[1]}x{tmpl.shape[0]})大于窗口截图"
                    f"({screenshot_bgr.shape[1]}x{screenshot_bgr.shape[0]})，请重新截取")

        # 模板匹配
        result = cv2.matchTemplate(screenshot_bgr, tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val < confidence:
            return (None, None,
                    f"匹配度不足: {max_val:.2f} (需要>={confidence})，"
                    f"请确认背包窗口已打开，或在设置中重新截取模板")

        # 计算网格左上角的屏幕坐标
        tmpl_h = tmpl.shape[0]
        win_left, win_top = window_region[0], window_region[1]
        offset_x = self.settings.get('grid_offset_x', 0)
        offset_y = self.settings.get('grid_offset_y', 0)

        grid_screen_x = win_left + max_loc[0] + offset_x
        grid_screen_y = win_top + max_loc[1] + tmpl_h + offset_y

        return (grid_screen_x, grid_screen_y,
                f"匹配成功: 置信度{max_val:.2f}, 位置({grid_screen_x},{grid_screen_y})")

    def scan_backpack(self, window_region, backpack_origin):
        """扫描背包所有格子

        Args:
            window_region: (left, top, width, height) 游戏窗口区域
            backpack_origin: (x, y) 背包网格左上角的屏幕坐标

        Returns:
            list[BackpackSlot]: 20个格子的信息
        """
        cell_w = self.settings.get('cell_width', 40)
        cell_h = self.settings.get('cell_height', 40)
        origin_x, origin_y = backpack_origin

        # 截取整个背包网格区域
        grid_width = cell_w * GRID_COLS
        grid_height = cell_h * GRID_ROWS
        grid_region = (origin_x, origin_y, grid_width, grid_height)
        screenshot = take_screenshot(region=grid_region)
        grid_image = np.array(screenshot)
        screenshot.close()
        grid_bgr = cv2.cvtColor(grid_image, cv2.COLOR_RGB2BGR)

        # 数字区域在格子内的相对位置
        digit_region = self.settings.get('digit_region', {})
        digit_x = digit_region.get('x', cell_w - 20)
        digit_y = digit_region.get('y', cell_h - 14)
        digit_w = digit_region.get('w', 20)
        digit_h = digit_region.get('h', 14)

        # 图标区域在格子内的相对位置
        icon_region = self.settings.get('icon_region', {})
        icon_x = icon_region.get('x', 2)
        icon_y = icon_region.get('y', 2)
        icon_w = icon_region.get('w', cell_w - 4)
        icon_h = icon_region.get('h', cell_h - 4)

        slots = []
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                x_start = col * cell_w
                y_start = row * cell_h

                # 提取图标区域
                icon_img = grid_bgr[
                    y_start + icon_y : y_start + icon_y + icon_h,
                    x_start + icon_x : x_start + icon_x + icon_w
                ].copy()

                # 提取数字区域并识别
                digit_img = grid_bgr[
                    y_start + digit_y : y_start + digit_y + digit_h,
                    x_start + digit_x : x_start + digit_x + digit_w
                ].copy()
                quantity = self.digit_recognizer.recognize(digit_img)

                slots.append(BackpackSlot(col, row, icon_img, quantity))

        return slots

    def match_item(self, slots, material_image_path, required_quantity, confidence=0.7):
        """在背包中查找匹配的物品格子

        Args:
            slots: list[BackpackSlot] 背包扫描结果
            material_image_path: str 材料图标截图路径
            required_quantity: int 需求数量
            confidence: float 匹配置信度

        Returns:
            BackpackSlot or None: 匹配的格子，优先选择匹配度最高的
        """
        # 加载材料模板
        pil_tmpl = Image.open(material_image_path)
        tmpl = np.array(pil_tmpl)
        pil_tmpl.close()
        if len(tmpl.shape) == 3:
            tmpl = cv2.cvtColor(tmpl, cv2.COLOR_RGB2BGR)

        candidates = []

        for slot in slots:
            if slot.quantity is None:
                continue
            if slot.quantity < required_quantity:
                continue

            # 模板匹配图标
            icon = slot.icon_image
            if icon.shape[0] < tmpl.shape[0] or icon.shape[1] < tmpl.shape[1]:
                continue

            result = cv2.matchTemplate(icon, tmpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)

            if max_val >= confidence:
                candidates.append((slot, max_val))

        if not candidates:
            return None

        # 按匹配度排序，取最高的
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]
