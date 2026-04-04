#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
背包识别模块
在游戏窗口中定位背包，切割网格，识别物品图标和数量
"""

import os
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
    def __init__(self, grid_x, grid_y, icon_image, quantity, is_empty=False):
        self.grid_x = grid_x       # 列索引 0-4
        self.grid_y = grid_y       # 行索引 0-3
        self.icon_image = icon_image  # numpy array, 物品图标区域
        self.quantity = quantity    # int or None
        self.is_empty = is_empty   # 是否为空格子


class BackpackReader:
    """背包读取器"""

    def __init__(self, digit_recognizer, settings=None):
        self.digit_recognizer = digit_recognizer
        self.settings = settings or {}

    def _load_template(self, path):
        """加载模板图片，返回BGR格式numpy数组"""
        pil_img = Image.open(path)
        img = np.array(pil_img)
        pil_img.close()
        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        return img

    def locate_backpack(self, window_region, confidence=0.7):
        """在窗口截图中定位背包

        Returns:
            tuple: (backpack_x, backpack_y, info) 或 (None, None, error_msg)
        """
        title_image_path = self.settings.get('backpack_title_image')
        if not title_image_path:
            return (None, None, "未设置背包定位模板，请在「设置」中截取")

        if not os.path.exists(title_image_path):
            return (None, None, f"模板文件不存在: {title_image_path}")

        # 截取游戏窗口区域
        screenshot = take_screenshot(region=window_region)
        screenshot_np = np.array(screenshot)
        screenshot.close()
        screenshot_bgr = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)

        tmpl = self._load_template(title_image_path)

        if tmpl.shape[0] > screenshot_bgr.shape[0] or tmpl.shape[1] > screenshot_bgr.shape[1]:
            return (None, None,
                    f"模板图片({tmpl.shape[1]}x{tmpl.shape[0]})大于窗口截图"
                    f"({screenshot_bgr.shape[1]}x{screenshot_bgr.shape[0]})，请重新截取")

        result = cv2.matchTemplate(screenshot_bgr, tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val < confidence:
            return (None, None,
                    f"匹配度不足: {max_val:.2f} (需要>={confidence})，"
                    f"请确认背包窗口已打开，或在设置中重新截取模板")

        tmpl_h = tmpl.shape[0]
        win_left, win_top = window_region[0], window_region[1]
        offset_x = self.settings.get('grid_offset_x', 0)
        offset_y = self.settings.get('grid_offset_y', 0)

        grid_screen_x = win_left + max_loc[0] + offset_x
        grid_screen_y = win_top + max_loc[1] + tmpl_h + offset_y

        return (grid_screen_x, grid_screen_y,
                f"标题定位成功: 置信度{max_val:.2f}, 位置({grid_screen_x},{grid_screen_y})")

    def detect_grid(self, window_region, confidence=0.8):
        """使用空格子模板自动检测网格布局

        模板的宽高即为格子尺寸，通过匹配找到空格子位置确定网格起点。

        Args:
            window_region: (left, top, width, height) 游戏窗口区域
            confidence: 匹配置信度

        Returns:
            dict: {'origin': (x,y), 'cell_width': w, 'cell_height': h, ...}
            或 None
        """
        empty_cell_path = self.settings.get('empty_cell_image')
        if not empty_cell_path or not os.path.exists(empty_cell_path):
            return None

        tmpl = self._load_template(empty_cell_path)
        cell_h, cell_w = tmpl.shape[:2]

        # 模板太小说明截取有误
        if cell_w < 15 or cell_h < 15:
            return None

        screenshot = take_screenshot(region=window_region)
        screen_np = np.array(screenshot)
        screenshot.close()
        screen_bgr = cv2.cvtColor(screen_np, cv2.COLOR_RGB2BGR)

        if cell_h > screen_bgr.shape[0] or cell_w > screen_bgr.shape[1]:
            return None

        result = cv2.matchTemplate(screen_bgr, tmpl, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= confidence)

        if len(locations[0]) == 0:
            return None

        # 去重：合并相邻匹配点（距离小于格子尺寸一半的视为同一格子）
        points = sorted(zip(locations[1].tolist(), locations[0].tolist()))
        cells = []
        for x, y in points:
            is_dup = False
            for cx, cy in cells:
                if abs(x - cx) < cell_w * 0.5 and abs(y - cy) < cell_h * 0.5:
                    is_dup = True
                    break
            if not is_dup:
                cells.append((x, y))

        if not cells:
            return None

        # 最左上角的空格子位置即为网格起点（不做反推，避免负坐标）
        min_x = min(c[0] for c in cells)
        min_y = min(c[1] for c in cells)

        win_left, win_top = window_region[0], window_region[1]

        return {
            'origin': (win_left + min_x, win_top + min_y),
            'cell_width': cell_w,
            'cell_height': cell_h,
            'empty_count': len(cells),
            'info': f"网格检测: 格子{cell_w}x{cell_h}, {len(cells)}个空格子, "
                    f"起点({win_left + min_x},{win_top + min_y})"
        }

    def scan_backpack(self, window_region, backpack_origin,
                      cell_w=None, cell_h=None):
        """扫描背包所有格子

        Args:
            window_region: (left, top, width, height) 游戏窗口区域
            backpack_origin: (x, y) 背包网格左上角的屏幕坐标
            cell_w: 格子宽度（优先于settings）
            cell_h: 格子高度（优先于settings）

        Returns:
            list[BackpackSlot]: 20个格子的信息
        """
        cell_w = cell_w or self.settings.get('cell_width', 40)
        cell_h = cell_h or self.settings.get('cell_height', 40)
        origin_x, origin_y = backpack_origin

        # 截取整个背包网格区域
        grid_width = cell_w * GRID_COLS
        grid_height = cell_h * GRID_ROWS
        grid_region = (origin_x, origin_y, grid_width, grid_height)
        screenshot = take_screenshot(region=grid_region)
        grid_image = np.array(screenshot)
        screenshot.close()
        grid_bgr = cv2.cvtColor(grid_image, cv2.COLOR_RGB2BGR)

        # 加载空格子模板（用于判断格子是否为空）
        empty_tmpl = None
        empty_cell_path = self.settings.get('empty_cell_image')
        if empty_cell_path and os.path.exists(empty_cell_path):
            empty_tmpl = self._load_template(empty_cell_path)

        # 数字识别是否可用
        has_digits = self.digit_recognizer.is_loaded()

        # 数字区域在格子内的相对位置
        digit_region = self.settings.get('digit_region', {})
        digit_rx = digit_region.get('x', cell_w - 20)
        digit_ry = digit_region.get('y', cell_h - 14)
        digit_rw = digit_region.get('w', 20)
        digit_rh = digit_region.get('h', 14)

        slots = []
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                x_start = col * cell_w
                y_start = row * cell_h

                # 提取整个格子区域作为图标
                cell_img = grid_bgr[
                    y_start : y_start + cell_h,
                    x_start : x_start + cell_w
                ].copy()

                # 判断是否为空格子
                is_empty = False
                if empty_tmpl is not None:
                    eh, ew = empty_tmpl.shape[:2]
                    if cell_img.shape[0] >= eh and cell_img.shape[1] >= ew:
                        match_result = cv2.matchTemplate(
                            cell_img, empty_tmpl, cv2.TM_CCOEFF_NORMED)
                        _, mv, _, _ = cv2.minMaxLoc(match_result)
                        is_empty = mv >= 0.85

                # 数字识别
                quantity = None
                if has_digits and not is_empty:
                    digit_img = grid_bgr[
                        y_start + digit_ry : y_start + digit_ry + digit_rh,
                        x_start + digit_rx : x_start + digit_rx + digit_rw
                    ].copy()
                    quantity = self.digit_recognizer.recognize(digit_img)

                slots.append(BackpackSlot(col, row, cell_img, quantity, is_empty))

        return slots

    def match_item(self, slots, material_image_path, required_quantity,
                   confidence=0.6):
        """在背包中查找匹配的物品格子

        图标匹配 + 数量检查：只返回数量 >= required_quantity 的格子。

        Args:
            slots: list[BackpackSlot] 背包扫描结果
            material_image_path: str 材料图标截图路径
            required_quantity: int 需求数量
            confidence: float 匹配置信度

        Returns:
            tuple: (BackpackSlot, info_str) 或 (None, error_str)
        """
        pil_tmpl = Image.open(material_image_path)
        tmpl = np.array(pil_tmpl)
        pil_tmpl.close()
        if len(tmpl.shape) == 3:
            tmpl = cv2.cvtColor(tmpl, cv2.COLOR_RGB2BGR)

        candidates = []
        icon_matched_but_insufficient = []  # 图标匹配但数量不足

        for slot in slots:
            # 跳过空格子
            if slot.is_empty:
                continue

            # 模板匹配图标
            icon = slot.icon_image
            if icon.shape[0] < tmpl.shape[0] or icon.shape[1] < tmpl.shape[1]:
                continue

            result = cv2.matchTemplate(icon, tmpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)

            if max_val >= confidence:
                # 图标匹配成功，检查数量
                if slot.quantity is None:
                    icon_matched_but_insufficient.append(
                        (slot, max_val, "数量未识别"))
                elif slot.quantity < required_quantity:
                    icon_matched_but_insufficient.append(
                        (slot, max_val, f"数量{slot.quantity}<{required_quantity}"))
                else:
                    candidates.append((slot, max_val))

        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            slot = candidates[0][0]
            return (slot,
                    f"格子({slot.grid_x},{slot.grid_y}) "
                    f"数量:{slot.quantity} 匹配度:{candidates[0][1]:.2f}")

        # 没有满足数量要求的
        if icon_matched_but_insufficient:
            details = "; ".join(
                f"({s.grid_x},{s.grid_y}):{reason}"
                for s, _, reason in icon_matched_but_insufficient
            )
            return (None, f"找到图标但数量不足: {details}")

        return (None, "未找到匹配的图标")
