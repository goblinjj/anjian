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
        self.grid_x = grid_x         # 列索引 0-4
        self.grid_y = grid_y         # 行索引 0-3
        self.screen_x = screen_x     # 格子中心的屏幕X坐标
        self.screen_y = screen_y     # 格子中心的屏幕Y坐标
        self.icon_image = icon_image  # numpy array, 格子图像
        self.quantity = quantity      # int or None
        self.is_empty = is_empty     # 是否为空格子


class GridInfo:
    """网格定位结果，包含20个格子的屏幕坐标"""
    def __init__(self, origin_x, origin_y, cell_w, cell_h):
        self.origin_x = origin_x  # 网格左上角屏幕X
        self.origin_y = origin_y  # 网格左上角屏幕Y
        self.cell_w = cell_w
        self.cell_h = cell_h

    def get_cell_center(self, col, row):
        """获取指定格子的屏幕中心坐标"""
        x = self.origin_x + col * self.cell_w + self.cell_w // 2
        y = self.origin_y + row * self.cell_h + self.cell_h // 2
        return (x, y)

    def get_cell_rect(self, col, row):
        """获取指定格子的屏幕区域 (left, top, width, height)"""
        x = self.origin_x + col * self.cell_w
        y = self.origin_y + row * self.cell_h
        return (x, y, self.cell_w, self.cell_h)

    def __str__(self):
        return (f"网格: 起点({self.origin_x},{self.origin_y}), "
                f"格子{self.cell_w}x{self.cell_h}, "
                f"范围({self.origin_x}-{self.origin_x + self.cell_w * GRID_COLS},"
                f"{self.origin_y}-{self.origin_y + self.cell_h * GRID_ROWS})")


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

    def locate_grid(self, window_region):
        """定位背包5x4网格的精确位置

        步骤:
        1. 用标题模板确认制造窗口
        2. 在窗口右半部分搜索空格子
        3. 从空格子位置推算网格起点和格子大小
        4. 返回GridInfo（包含20个格子的坐标）

        Args:
            window_region: (left, top, width, height) 游戏窗口区域

        Returns:
            tuple: (GridInfo, info_str) 或 (None, error_str)
        """
        win_left, win_top, win_width, win_height = window_region

        # ── 步骤1: 标题模板确认窗口 ──
        title_path = self.settings.get('backpack_title_image')
        if not title_path or not os.path.exists(title_path):
            return (None, "未设置背包定位模板，请在「设置」中截取")

        # 截取整个窗口
        screenshot = take_screenshot(region=window_region)
        screen_np = np.array(screenshot)
        screenshot.close()
        screen_bgr = cv2.cvtColor(screen_np, cv2.COLOR_RGB2BGR)

        title_tmpl = self._load_template(title_path)
        if (title_tmpl.shape[0] > screen_bgr.shape[0] or
                title_tmpl.shape[1] > screen_bgr.shape[1]):
            return (None, "背包定位模板大于窗口截图，请重新截取")

        result = cv2.matchTemplate(screen_bgr, title_tmpl, cv2.TM_CCOEFF_NORMED)
        _, title_conf, _, title_loc = cv2.minMaxLoc(result)

        if title_conf < 0.7:
            return (None, f"背包定位匹配度不足: {title_conf:.2f}，"
                          f"请确认制造窗口已打开")

        # ── 步骤2: 空格子模板检测格子大小和位置 ──
        empty_path = self.settings.get('empty_cell_image')
        if not empty_path or not os.path.exists(empty_path):
            # 没有空格子模板，使用标题位置+设置偏移量
            cell_w = self.settings.get('cell_width', 40)
            cell_h = self.settings.get('cell_height', 40)
            offset_x = self.settings.get('grid_offset_x', 0)
            offset_y = self.settings.get('grid_offset_y', 0)
            title_h = title_tmpl.shape[0]
            origin_x = win_left + title_loc[0] + offset_x
            origin_y = win_top + title_loc[1] + title_h + offset_y
            grid = GridInfo(origin_x, origin_y, cell_w, cell_h)
            return (grid, f"标题定位(无空格子模板): {grid}")

        empty_tmpl = self._load_template(empty_path)
        cell_h, cell_w = empty_tmpl.shape[:2]

        if cell_w < 15 or cell_h < 15:
            return (None, f"空格子模板太小({cell_w}x{cell_h})，请重新截取完整格子")

        # 只在窗口右半部分搜索空格子（避免匹配左侧制造栏）
        mid_x = screen_bgr.shape[1] // 2
        right_half = screen_bgr[:, mid_x:]

        if (empty_tmpl.shape[0] > right_half.shape[0] or
                empty_tmpl.shape[1] > right_half.shape[1]):
            return (None, "空格子模板大于搜索区域")

        result = cv2.matchTemplate(right_half, empty_tmpl, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= 0.8)

        if len(locations[0]) == 0:
            # 没有找到空格子（可能全满了），用标题位置回退
            offset_x = self.settings.get('grid_offset_x', 0)
            offset_y = self.settings.get('grid_offset_y', 0)
            title_h = title_tmpl.shape[0]
            origin_x = win_left + title_loc[0] + offset_x
            origin_y = win_top + title_loc[1] + title_h + offset_y
            grid = GridInfo(origin_x, origin_y, cell_w, cell_h)
            return (grid, f"未找到空格子(背包可能全满)，用标题定位: {grid}")

        # ── 步骤3: 从空格子位置推算网格起点 ──
        # 将匹配坐标转换回完整窗口坐标（加上右半偏移）
        points = sorted(zip(
            (locations[1] + mid_x).tolist(),
            locations[0].tolist()
        ))

        # 去重
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
            return (None, "空格子去重后无结果")

        # 找到最左上角的空格子
        min_x = min(c[0] for c in cells)
        min_y = min(c[1] for c in cells)

        # 这个空格子的网格坐标可能是(col, row)中的任意一个
        # 但网格原点 = 空格子位置 - (col * cell_w, row * cell_h)
        # 我们用所有空格子位置，找到能被cell_w/cell_h整除的对齐方式
        # 最简单的方法：原点x = min_x % cell_w 的对齐位置
        # 即从 min_x 向左推到第0列
        origin_x = min_x
        origin_y = min_y

        # 如果有多个空格子，验证它们是否在同一网格上
        if len(cells) >= 2:
            # 所有空格子相对于min位置的偏移应该是cell_w/cell_h的整数倍
            # 用这个验证格子大小是否正确
            x_offsets = sorted(set(c[0] - min_x for c in cells))
            y_offsets = sorted(set(c[1] - min_y for c in cells))

            # 找最小正偏移来确认实际间距
            x_steps = [x for x in x_offsets if x > 0]
            y_steps = [y for y in y_offsets if y > 0]

            if x_steps:
                # 最小x间距应该是cell_w（或cell_w的整数倍）
                min_x_step = min(x_steps)
                # 如果最小间距接近cell_w，确认正确
                if abs(min_x_step - cell_w) <= 3:
                    cell_w = min_x_step  # 微调

            if y_steps:
                min_y_step = min(y_steps)
                if abs(min_y_step - cell_h) <= 3:
                    cell_h = min_y_step

        # 从最左上角空格子反推网格起点（第0列第0行）
        # 空格子到网格起点的距离 = col * cell_w, row * cell_h
        # col = (min_x - origin_x) / cell_w 必须是0-4之间的整数
        # 我们不知道col是多少，但可以用模运算找对齐
        # 网格的x范围应该是 5*cell_w，起点在 min_x 之前的某个对齐位置

        # 方法：在可能的范围内找到最合理的起点
        # 候选起点 = min_x - n * cell_w (n = 0,1,2,3,4)
        # 选择让最多空格子对齐到网格上的起点
        best_origin_x = min_x
        best_origin_y = min_y
        best_score = 0

        for try_col in range(GRID_COLS):
            for try_row in range(GRID_ROWS):
                ox = min_x - try_col * cell_w
                oy = min_y - try_row * cell_h
                # 检查有多少空格子能对齐到这个网格
                score = 0
                for cx, cy in cells:
                    dx = cx - ox
                    dy = cy - oy
                    if dx < 0 or dy < 0:
                        continue
                    col_f = dx / cell_w
                    row_f = dy / cell_h
                    col_i = round(col_f)
                    row_i = round(row_f)
                    if (0 <= col_i < GRID_COLS and 0 <= row_i < GRID_ROWS
                            and abs(col_f - col_i) < 0.15
                            and abs(row_f - row_i) < 0.15):
                        score += 1
                if score > best_score:
                    best_score = score
                    best_origin_x = ox
                    best_origin_y = oy

        # 转换为屏幕坐标
        screen_origin_x = win_left + best_origin_x
        screen_origin_y = win_top + best_origin_y

        grid = GridInfo(screen_origin_x, screen_origin_y, cell_w, cell_h)
        return (grid, f"网格定位成功({len(cells)}个空格子): {grid}")

    def scan_backpack(self, grid_info):
        """扫描背包20个格子

        Args:
            grid_info: GridInfo 网格定位信息

        Returns:
            list[BackpackSlot]: 20个格子的信息
        """
        cell_w = grid_info.cell_w
        cell_h = grid_info.cell_h

        # 截取整个网格区域
        grid_region = (grid_info.origin_x, grid_info.origin_y,
                       cell_w * GRID_COLS, cell_h * GRID_ROWS)
        screenshot = take_screenshot(region=grid_region)
        grid_image = np.array(screenshot)
        screenshot.close()

        if grid_image.size == 0:
            return []

        grid_bgr = cv2.cvtColor(grid_image, cv2.COLOR_RGB2BGR)

        # 加载空格子模板
        empty_tmpl = None
        empty_cell_path = self.settings.get('empty_cell_image')
        if empty_cell_path and os.path.exists(empty_cell_path):
            empty_tmpl = self._load_template(empty_cell_path)

        has_digits = self.digit_recognizer.is_loaded()

        # 数字区域：格子右下角
        digit_rw = 20
        digit_rh = 14
        digit_rx = cell_w - digit_rw
        digit_ry = cell_h - digit_rh

        slots = []
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                x_start = col * cell_w
                y_start = row * cell_h

                # 边界检查
                if (y_start + cell_h > grid_bgr.shape[0] or
                        x_start + cell_w > grid_bgr.shape[1]):
                    continue

                # 提取格子图像
                cell_img = grid_bgr[
                    y_start : y_start + cell_h,
                    x_start : x_start + cell_w
                ].copy()

                # 格子中心屏幕坐标
                center_x, center_y = grid_info.get_cell_center(col, row)

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
                    if (digit_ry >= 0 and digit_rx >= 0
                            and digit_ry + digit_rh <= cell_h
                            and digit_rx + digit_rw <= cell_w):
                        digit_img = cell_img[
                            digit_ry : digit_ry + digit_rh,
                            digit_rx : digit_rx + digit_rw
                        ].copy()
                        quantity = self.digit_recognizer.recognize(digit_img)

                slots.append(BackpackSlot(
                    col, row, center_x, center_y,
                    cell_img, quantity, is_empty))

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
