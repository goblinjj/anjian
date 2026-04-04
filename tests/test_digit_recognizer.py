#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import unittest
import shutil
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from digit_recognizer import DigitRecognizer


class TestDigitRecognizer(unittest.TestCase):
    def setUp(self):
        """创建测试用的数字模板图片"""
        self.test_dir = os.path.join(os.path.dirname(__file__), 'test_digits')
        os.makedirs(self.test_dir, exist_ok=True)
        for digit in range(10):
            img = Image.new('RGB', (10, 14), color=(0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.text((1, 0), str(digit), fill=(255, 255, 255))
            img.save(os.path.join(self.test_dir, f'{digit}.png'))
        self.recognizer = DigitRecognizer(self.test_dir)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_load_templates(self):
        """模板加载成功"""
        self.assertEqual(len(self.recognizer.templates), 10)
        for i in range(10):
            self.assertIn(i, self.recognizer.templates)

    def test_is_loaded(self):
        """is_loaded 返回 True"""
        self.assertTrue(self.recognizer.is_loaded())

    def test_templates_not_found(self):
        """模板目录不存在时返回空"""
        recognizer = DigitRecognizer('/nonexistent')
        self.assertEqual(len(recognizer.templates), 0)
        self.assertFalse(recognizer.is_loaded())

    def test_recognize_returns_none_for_blank(self):
        """纯黑图片应返回 None (无数字)"""
        blank = np.zeros((14, 30, 3), dtype=np.uint8)
        result = self.recognizer.recognize(blank)
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
