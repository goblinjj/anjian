#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数字识别模块
使用0-9模板匹配识别背包物品数量
"""

import os
import cv2
import numpy as np
from PIL import Image


class DigitRecognizer:
    """数字识别器 — 模板匹配方式"""

    def __init__(self, templates_dir='templates/digits'):
        self.templates_dir = templates_dir
        self.templates = {}  # {digit_int: numpy_array}
        self._load_templates()

    def _load_templates(self):
        """加载 0-9 数字模板图片"""
        if not os.path.exists(self.templates_dir):
            return
        for digit in range(10):
            path = os.path.join(self.templates_dir, f'{digit}.png')
            if os.path.exists(path):
                pil_img = Image.open(path)
                img = np.array(pil_img)
                pil_img.close()
                if len(img.shape) == 3:
                    img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
                self.templates[digit] = img

    def recognize(self, region_image, confidence=0.7):
        """识别图片区域中的数字

        从左到右扫描，逐位匹配数字模板。

        Args:
            region_image: numpy array (BGR 或 RGB 或 灰度), 包含数字的图片区域
            confidence: 匹配置信度阈值

        Returns:
            int or None: 识别到的数字 (1-80), 没有识别到返回 None
        """
        if len(self.templates) == 0:
            return None

        # 转为灰度
        if len(region_image.shape) == 3:
            gray = cv2.cvtColor(region_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = region_image.copy()

        digits_found = []  # [(x_position, digit_value)]
        h, w = gray.shape

        for digit, tmpl in self.templates.items():
            th, tw = tmpl.shape
            if th > h or tw > w:
                continue

            result = cv2.matchTemplate(gray, tmpl, cv2.TM_CCOEFF_NORMED)
            locations = np.where(result >= confidence)

            for pt_x in locations[1]:
                # 去重: 如果附近已有识别结果，跳过
                is_duplicate = False
                for existing_x, _ in digits_found:
                    if abs(pt_x - existing_x) < tw * 0.5:
                        is_duplicate = True
                        break
                if not is_duplicate:
                    digits_found.append((pt_x, digit))

        if not digits_found:
            return None

        # 按 x 坐标排序，组合成数字
        digits_found.sort(key=lambda x: x[0])
        number_str = ''.join(str(d) for _, d in digits_found)

        try:
            return int(number_str)
        except ValueError:
            return None

    def is_loaded(self):
        """检查模板是否已加载"""
        return len(self.templates) == 10
