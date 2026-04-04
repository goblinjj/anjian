#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
背包识别模块
在游戏窗口中定位背包5x4网格，识别物品图标和数量
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
    def __init__(self, grid_x, grid_y, screen_x, screen_y,
                 icon_image, quantity, is_empty=False):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.screen_x = screen_x     # 格子中心屏幕坐标
        self.screen_y = screen_y
        self.icon_image = icon_image  # numpy BGR
        self.quantity = quantity      # int or None
        self.is_empty = is_empty


class GridInfo:
    """网格定位结果"""
    def __init__(self, origin_x, origin_y, cell_w, cell_h):
        self.origin_x = origin_x
        self.origin_y = origin_y
        self.cell_w = cell_w
        self.cell_h = cell_h

    def get_cell_center(self, col, row):
        x = self.origin_x + col * self.cell_w + self.cell_w // 2
        y = self.origin_y + row * self.cell_h + self.cell_h // 2
        return (x, y)

    def __str__(self):
        return (f"起点({self.origin_x},{self.origin_y}), "
                f"格子{self.cell_w}x{self.cell_h}")


class BackpackReader:
    """背包读取器"""

    def __init__(self, digit_recognizer, settings=None):
        self.digit_recognizer = digit_recognizer
        self.settings = settings or {}

    def _load_template(self, path):
        pil_img = Image.open(path)
        img = np.array(pil_img)
        pil_img.close()
        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        return img

    def locate_grid(self, window_region):
        """定位背包网格

        使用"制造"标题模板定位 + 固定偏移量计算网格起点。
        格子大小优先从空格子模板获取，否则用设置值。

        Returns:
            tuple: (GridInfo, info_str) 或 (None, error_str)
        """
        win_left, win_top = window_region[0], window_region[1]

        # 1. 找到标题位置
        title_path = self.settings.get('backpack_title_image')
        if not title_path or not os.path.exists(title_path):
            return (None, "未设置背包定位模板，请在「设置」中截取")

        screenshot = take_screenshot(region=window_region)
        screen_np = np.array(screenshot)
        screenshot.close()
        screen_bgr = cv2.cvtColor(screen_np, cv2.COLOR_RGB2BGR)

        title_tmpl = self._load_template(title_path)
        if (title_tmpl.shape[0] > screen_bgr.shape[0] or
                title_tmpl.shape[1] > screen_bgr.shape[1]):
            return (None, "背包定位模板大于窗口截图，请重新截取")

        result = cv2.matchTemplate(
            screen_bgr, title_tmpl, cv2.TM_CCOEFF_NORMED)
        _, conf, _, title_loc = cv2.minMaxLoc(result)

        if conf < 0.7:
            return (None, f"匹配度不足: {conf:.2f}，请确认制造窗口已打开")

        # 2. 计算网格起点 = 标题位置 + 偏移量
        title_h = title_tmpl.shape[0]
        offset_x = self.settings.get('grid_offset_x', 0)
        offset_y = self.settings.get('grid_offset_y', 0)

        origin_x = win_left + title_loc[0] + offset_x
        origin_y = win_top + title_loc[1] + title_h + offset_y

        # 3. 格子大小：优先从空格子模板获取
        cell_w = self.settings.get('cell_width', 40)
        cell_h = self.settings.get('cell_height', 40)

        empty_path = self.settings.get('empty_cell_image')
        if empty_path and os.path.exists(empty_path):
            empty_tmpl = self._load_template(empty_path)
            eh, ew = empty_tmpl.shape[:2]
            if ew >= 15 and eh >= 15:
                cell_w = ew
                cell_h = eh

        grid = GridInfo(origin_x, origin_y, cell_w, cell_h)
        return (grid, f"网格定位: 置信度{conf:.2f}, {grid}")

    def test_grid_overlay(self, window_region):
        """生成带网格线的测试图片

        在游戏窗口截图上画出5x4网格线，保存到debug/grid_test.png，
        用于验证网格定位是否准确。

        Returns:
            tuple: (save_path, info_str) 或 (None, error_str)
        """
        grid, info = self.locate_grid(window_region)
        if grid is None:
            return (None, info)

        # 截取整个窗口
        screenshot = take_screenshot(region=window_region)
        screen_np = np.array(screenshot)
        screenshot.close()
        overlay = cv2.cvtColor(screen_np, cv2.COLOR_RGB2BGR)

        win_left, win_top = window_region[0], window_region[1]

        # 画5x4网格线（红色）
        for row in range(GRID_ROWS + 1):
            y = grid.origin_y - win_top + row * grid.cell_h
            x1 = grid.origin_x - win_left
            x2 = x1 + GRID_COLS * grid.cell_w
            cv2.line(overlay, (x1, y), (x2, y), (0, 0, 255), 1)

        for col in range(GRID_COLS + 1):
            x = grid.origin_x - win_left + col * grid.cell_w
            y1 = grid.origin_y - win_top
            y2 = y1 + GRID_ROWS * grid.cell_h
            cv2.line(overlay, (x, y1), (x, y2), (0, 0, 255), 1)

        # 在每个格子中心画十字（绿色）
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                cx = grid.origin_x - win_left + col * grid.cell_w + grid.cell_w // 2
                cy = grid.origin_y - win_top + row * grid.cell_h + grid.cell_h // 2
                cv2.drawMarker(overlay, (cx, cy), (0, 255, 0),
                               cv2.MARKER_CROSS, 8, 1)

        debug_dir = 'debug'
        os.makedirs(debug_dir, exist_ok=True)
        save_path = os.path.join(debug_dir, 'grid_test.png')
        cv2.imwrite(save_path, overlay)

        return (save_path, info)

    def scan_backpack(self, grid_info, debug=False):
        """扫描背包20个格子"""
        cell_w = grid_info.cell_w
        cell_h = grid_info.cell_h

        grid_region = (grid_info.origin_x, grid_info.origin_y,
                       cell_w * GRID_COLS, cell_h * GRID_ROWS)
        screenshot = take_screenshot(region=grid_region)
        grid_image = np.array(screenshot)
        screenshot.close()

        if grid_image.size == 0:
            return []

        grid_bgr = cv2.cvtColor(grid_image, cv2.COLOR_RGB2BGR)

        if debug:
            debug_dir = 'debug'
            os.makedirs(debug_dir, exist_ok=True)
            cv2.imwrite(os.path.join(debug_dir, 'grid_full.png'), grid_bgr)

        # 空格子模板
        empty_tmpl = None
        empty_path = self.settings.get('empty_cell_image')
        if empty_path and os.path.exists(empty_path):
            empty_tmpl = self._load_template(empty_path)

        has_digits = self.digit_recognizer.is_loaded()

        # 数字区域：格子底部居中（数字在格子下方中间位置）
        digit_rw = cell_w - 10   # 左右各留5px边距
        digit_rh = 16
        digit_rx = 5
        digit_ry = cell_h - digit_rh - 2  # 底部留2px边距

        slots = []
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                x_start = col * cell_w
                y_start = row * cell_h

                if (y_start + cell_h > grid_bgr.shape[0] or
                        x_start + cell_w > grid_bgr.shape[1]):
                    continue

                cell_img = grid_bgr[
                    y_start : y_start + cell_h,
                    x_start : x_start + cell_w
                ].copy()

                center_x, center_y = grid_info.get_cell_center(col, row)

                # 空格子判断
                is_empty = False
                if empty_tmpl is not None:
                    eh, ew = empty_tmpl.shape[:2]
                    if cell_img.shape[0] >= eh and cell_img.shape[1] >= ew:
                        mr = cv2.matchTemplate(
                            cell_img, empty_tmpl, cv2.TM_CCOEFF_NORMED)
                        _, mv, _, _ = cv2.minMaxLoc(mr)
                        is_empty = mv >= 0.85

                # 数字识别
                quantity = None
                digit_img = None
                if has_digits and not is_empty:
                    if (digit_rx >= 0 and digit_ry >= 0
                            and digit_rx + digit_rw <= cell_w
                            and digit_ry + digit_rh <= cell_h):
                        digit_img = cell_img[
                            digit_ry : digit_ry + digit_rh,
                            digit_rx : digit_rx + digit_rw
                        ].copy()
                        quantity = self.digit_recognizer.recognize(digit_img)

                if debug:
                    name = f'cell_{row}_{col}'
                    cv2.imwrite(
                        os.path.join(debug_dir, f'{name}.png'), cell_img)
                    if digit_img is not None:
                        cv2.imwrite(
                            os.path.join(debug_dir, f'{name}_digit.png'),
                            digit_img)
                        gray = cv2.cvtColor(digit_img, cv2.COLOR_BGR2GRAY)
                        _, binary = cv2.threshold(
                            gray, 0, 255,
                            cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                        cv2.imwrite(
                            os.path.join(debug_dir, f'{name}_binary.png'),
                            binary)

                slots.append(BackpackSlot(
                    col, row, center_x, center_y,
                    cell_img, quantity, is_empty))

        return slots

    def match_item(self, slots, material_image_path, required_quantity,
                   confidence=0.6):
        """在背包中查找匹配的物品格子"""
        pil_tmpl = Image.open(material_image_path)
        tmpl = np.array(pil_tmpl)
        pil_tmpl.close()
        if len(tmpl.shape) == 3:
            tmpl = cv2.cvtColor(tmpl, cv2.COLOR_RGB2BGR)

        candidates = []
        icon_matched_but_insufficient = []

        for slot in slots:
            if slot.is_empty:
                continue

            icon = slot.icon_image
            if icon.shape[0] < tmpl.shape[0] or icon.shape[1] < tmpl.shape[1]:
                continue

            result = cv2.matchTemplate(icon, tmpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)

            if max_val >= confidence:
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

        if icon_matched_but_insufficient:
            details = "; ".join(
                f"({s.grid_x},{s.grid_y}):{reason}"
                for s, _, reason in icon_matched_but_insufficient
            )
            return (None, f"找到图标但数量不足: {details}")

        return (None, "未找到匹配的图标")
