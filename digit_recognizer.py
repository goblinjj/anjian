#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数字识别模块
使用0-9模板匹配识别背包物品数量
"""

import os
import logging
import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger('digit_recognizer')


class DigitRecognizer:
    """数字识别器 — 模板匹配方式"""

    def __init__(self, templates_dir='templates/digits'):
        self.templates_dir = templates_dir
        self.templates = {}       # {digit_int: CLAHE-enhanced gray numpy_array}
        self._clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
        self._load_templates()

    def _load_templates(self):
        """加载 0-9 数字模板图片，同时生成CLAHE增强版本"""
        if not os.path.exists(self.templates_dir):
            return
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
        for digit in range(10):
            path = os.path.join(self.templates_dir, f'{digit}.png')
            if os.path.exists(path):
                pil_img = Image.open(path)
                img = np.array(pil_img)
                pil_img.close()
                if len(img.shape) == 3:
                    img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
                self.templates[digit] = clahe.apply(img)

    def recognize(self, region_image, confidence=0.6, debug_label=''):
        """识别图片区域中的数字

        在灰度图上用模板匹配，从左到右逐位识别。
        自动添加边距防止边缘数字被截断。

        Args:
            region_image: numpy array (BGR 或灰度), 包含数字的图片区域
            confidence: 匹配置信度阈值
            debug_label: 调试标签，用于日志输出

        Returns:
            int or None: 识别到的数字, 没有识别到返回 None
        """
        if len(self.templates) == 0:
            return None

        # 转为灰度 + CLAHE增强对比度
        if len(region_image.shape) == 3:
            gray = cv2.cvtColor(region_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = region_image.copy()
        gray = self._clahe.apply(gray)

        # 添加边距：用边缘颜色填充，防止数字被截断时匹配失败
        pad = 4
        bg_val = int(np.median(np.concatenate([
            gray[0, :], gray[-1, :], gray[:, 0], gray[:, -1]
        ])))
        padded = cv2.copyMakeBorder(
            gray, pad, pad, pad, pad,
            cv2.BORDER_CONSTANT, value=bg_val)

        h, w = padded.shape

        # 获取模板典型宽度（用于去重间距）
        tmpl_widths = [t.shape[1] for t in self.templates.values()]
        avg_tw = sum(tmpl_widths) / len(tmpl_widths) if tmpl_widths else 10

        # 在灰度图上匹配每个数字模板
        all_matches = []  # [(x_position, digit, confidence)]

        for digit, tmpl in self.templates.items():
            th, tw = tmpl.shape
            if th > h or tw > w:
                continue

            result = cv2.matchTemplate(padded, tmpl, cv2.TM_CCOEFF_NORMED)
            locations = np.where(result >= confidence)

            for idx in range(len(locations[0])):
                pt_x = locations[1][idx]
                pt_y = locations[0][idx]
                match_val = result[pt_y, pt_x]
                all_matches.append((pt_x, digit, float(match_val)))

        if debug_label:
            match_summary = [(x, d, f'{c:.2f}') for x, d, c in all_matches]
            logger.info(f'{debug_label} 原始匹配({len(all_matches)}个): '
                        f'{match_summary}')

        if not all_matches:
            if debug_label:
                logger.info(f'{debug_label} 无匹配 (阈值={confidence})')
            return None

        # 去重：按x排序后，在每个位置区间内保留最高置信度的匹配
        # 最小间距 = 模板宽度的50%
        min_spacing = avg_tw * 0.5
        all_matches.sort(key=lambda m: (-m[2]))  # 按置信度降序

        selected = []  # [(x_position, digit, confidence)]
        for x, digit, conf in all_matches:
            conflict = False
            for sx, _, _ in selected:
                if abs(x - sx) < min_spacing:
                    conflict = True
                    break
            if not conflict:
                selected.append((x, digit, conf))

        # 按x坐标排序
        selected.sort(key=lambda m: m[0])

        if debug_label:
            logger.info(f'{debug_label} 去重后: '
                        f'{[(x, d, f"{c:.2f}") for x, d, c in selected]}')

        # 组合成数字
        number_str = ''.join(str(d) for _, d, _ in selected)
        if debug_label:
            logger.info(f'{debug_label} 识别结果: {number_str}')

        try:
            return int(number_str)
        except ValueError:
            return None

    def is_loaded(self):
        """检查模板是否已加载"""
        return len(self.templates) == 10
