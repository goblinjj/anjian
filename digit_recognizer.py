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
        self.templates_gr = {}    # {digit_int: CLAHE-enhanced G-R channel}
        self._clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
        self._load_templates()

    @staticmethod
    def _compute_gr_channel(bgr_image):
        """计算 G-R 通道，突出青色数字、抑制背景干扰"""
        return np.clip(
            bgr_image[:, :, 1].astype(int)
            - bgr_image[:, :, 2].astype(int) + 128,
            0, 255
        ).astype(np.uint8)

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
                    bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
                    gr = self._compute_gr_channel(bgr)
                    # 仅当G-R通道有足够变化时才保存（排除白/黑文字等无色差模板）
                    if np.std(gr) > 5:
                        self.templates_gr[digit] = clahe.apply(gr)
                else:
                    gray = img
                self.templates[digit] = clahe.apply(gray)

    def _pad_image(self, img):
        """添加边距：用边缘颜色填充，防止数字被截断时匹配失败"""
        pad = 4
        bg_val = int(np.median(np.concatenate([
            img[0, :], img[-1, :], img[:, 0], img[:, -1]
        ])))
        return cv2.copyMakeBorder(
            img, pad, pad, pad, pad,
            cv2.BORDER_CONSTANT, value=bg_val)

    def _match_templates(self, padded, templates, confidence):
        """在padded图上匹配所有模板，返回去重后的结果

        Returns:
            list: [(x_position, digit, confidence)] 按x排序
        """
        h, w = padded.shape
        tmpl_widths = [t.shape[1] for t in templates.values()]
        avg_tw = sum(tmpl_widths) / len(tmpl_widths) if tmpl_widths else 10

        all_matches = []
        for digit, tmpl in templates.items():
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

        if not all_matches:
            return []

        # 去重：在每个位置区间内保留最高置信度的匹配
        min_spacing = avg_tw * 0.5
        all_matches.sort(key=lambda m: (-m[2]))
        selected = []
        for x, digit, conf in all_matches:
            if not any(abs(x - sx) < min_spacing for sx, _, _ in selected):
                selected.append((x, digit, conf))
        selected.sort(key=lambda m: m[0])
        return selected

    def _decode_matches(self, selected):
        """将匹配结果解码为数字"""
        if not selected:
            return None, 0.0
        number_str = ''.join(str(d) for _, d, _ in selected)
        avg_conf = sum(c for _, _, c in selected) / len(selected)
        try:
            return int(number_str), avg_conf
        except ValueError:
            return None, 0.0

    def recognize(self, region_image, confidence=0.6, debug_label=''):
        """识别图片区域中的数字

        同时使用灰度匹配和G-R颜色通道匹配（突出青色数字），
        选择识别位数更多或置信度更高的结果。
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

        is_color = len(region_image.shape) == 3

        # --- 方法1: 灰度 + CLAHE ---
        if is_color:
            gray = cv2.cvtColor(region_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = region_image.copy()
        gray = self._clahe.apply(gray)
        padded_gray = self._pad_image(gray)
        selected_gray = self._match_templates(
            padded_gray, self.templates, confidence)
        result_gray, conf_gray = self._decode_matches(selected_gray)

        # --- 方法2: G-R颜色通道 + CLAHE (仅彩色图) ---
        result_gr, conf_gr = None, 0.0
        selected_gr = []
        if is_color and len(self.templates_gr) > 0:
            gr = self._compute_gr_channel(region_image)
            gr = self._clahe.apply(gr)
            padded_gr = self._pad_image(gr)
            selected_gr = self._match_templates(
                padded_gr, self.templates_gr, confidence)
            result_gr, conf_gr = self._decode_matches(selected_gr)

        # --- 选择最佳结果 ---
        # 优先选识别出更多位数的，位数相同选置信度高的
        len_gray = len(str(result_gray)) if result_gray is not None else 0
        len_gr = len(str(result_gr)) if result_gr is not None else 0

        if len_gr > len_gray:
            final, selected = result_gr, selected_gr
            method = 'G-R'
        elif len_gray > len_gr:
            final, selected = result_gray, selected_gray
            method = '灰度'
        elif result_gray is None:
            final, selected = None, []
            method = ''
        elif conf_gr >= conf_gray:
            final, selected = result_gr, selected_gr
            method = 'G-R'
        else:
            final, selected = result_gray, selected_gray
            method = '灰度'

        if debug_label:
            logger.info(
                f'{debug_label} 灰度匹配: '
                f'{[(d, f"{c:.2f}") for _, d, c in selected_gray]} '
                f'→ {result_gray}')
            logger.info(
                f'{debug_label} G-R匹配: '
                f'{[(d, f"{c:.2f}") for _, d, c in selected_gr]} '
                f'→ {result_gr}')
            logger.info(
                f'{debug_label} 最终({method}): {final}')

        return final

    def is_loaded(self):
        """检查模板是否已加载"""
        return len(self.templates) == 10
