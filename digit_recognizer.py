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
        self.templates = {}  # {digit_int: numpy_array (binary)}
        self._load_templates()

    def _load_templates(self):
        """加载 0-9 数字模板图片，转为二值化"""
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
                # 二值化：Otsu自动阈值
                _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                self.templates[digit] = binary

    def _binarize(self, gray_image):
        """将灰度图二值化"""
        _, binary = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary

    def recognize(self, region_image, confidence=0.6):
        """识别图片区域中的数字

        从左到右扫描，逐位匹配数字模板。

        Args:
            region_image: numpy array (BGR 或灰度), 包含数字的图片区域
            confidence: 匹配置信度阈值

        Returns:
            int or None: 识别到的数字, 没有识别到返回 None
        """
        if len(self.templates) == 0:
            return None

        # 转为灰度再二值化
        if len(region_image.shape) == 3:
            gray = cv2.cvtColor(region_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = region_image.copy()

        binary = self._binarize(gray)

        digits_found = []  # [(x_position, digit_value, confidence)]
        h, w = binary.shape

        for digit, tmpl in self.templates.items():
            th, tw = tmpl.shape
            if th > h or tw > w:
                continue

            result = cv2.matchTemplate(binary, tmpl, cv2.TM_CCOEFF_NORMED)
            locations = np.where(result >= confidence)

            for idx in range(len(locations[0])):
                pt_x = locations[1][idx]
                pt_y = locations[0][idx]
                match_val = result[pt_y, pt_x]

                # 去重: 如果附近已有更高置信度的识别结果，跳过
                is_duplicate = False
                for i, (existing_x, _, existing_conf) in enumerate(digits_found):
                    if abs(pt_x - existing_x) < tw * 0.6:
                        # 保留置信度更高的
                        if match_val > existing_conf:
                            digits_found[i] = (pt_x, digit, match_val)
                        is_duplicate = True
                        break
                if not is_duplicate:
                    digits_found.append((pt_x, digit, match_val))

        if not digits_found:
            return None

        # 按 x 坐标排序，组合成数字
        digits_found.sort(key=lambda x: x[0])
        number_str = ''.join(str(d) for _, d, _ in digits_found)

        try:
            return int(number_str)
        except ValueError:
            return None

    def is_loaded(self):
        """检查模板是否已加载"""
        return len(self.templates) == 10
