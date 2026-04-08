#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
全局设置对话框
管理图片模板、数字模板和其他全局设置
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import json


SETTINGS_FILE = 'settings.json'
TEMPLATES_DIR = 'templates'
DIGITS_DIR = os.path.join(TEMPLATES_DIR, 'digits')

# 全局模板项配置
TEMPLATE_ITEMS = [
    ('backpack_title_image', '背包定位', '用于在游戏窗口中定位背包位置'),
    ('empty_cell_image', '空格子', '背包中一个完整空格子，自动检测格子大小'),
    ('execute_button_image', '执行按钮', '制造界面的「执行」按钮'),
    ('completion_image', '制造完成', '制造结束后出现的按钮'),
    ('organize_button_image', '整理背包', '背包界面的「整理」按钮'),
    ('get_material_image', '获取材料', '获取材料时需要点击的目标图片'),
]


def load_settings():
    """加载全局设置"""
    defaults = {
        'backpack_title_image': '',
        'empty_cell_image': '',
        'execute_button_image': '',
        'completion_image': '',
        'organize_button_image': '',
        'get_material_image': '',
        'window_title_keyword': 'QI魔力',
        'cell_width': 40,
        'cell_height': 40,
        'grid_offset_x': 0,
        'grid_offset_y': 0,
        'digit_region': {'x': 20, 'y': 26, 'w': 20, 'h': 14},
        'icon_region': {'x': 2, 'y': 2, 'w': 36, 'h': 36},
        'click_pre_delay': 200,
        'click_interval': 100,
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
            defaults.update(saved)
        except Exception:
            pass
    return defaults


def save_settings(settings):
    """保存全局设置"""
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


class SettingsDialog:
    """全局设置对话框"""

    def __init__(self, parent, screenshot_callback, window_manager=None):
        """
        Args:
            parent: 父窗口
            screenshot_callback: 截图回调函数, 参数为 save_path, 返回 bool
            window_manager: WindowManager 实例（用于测试定位）
        """
        self.result = None
        self.screenshot_callback = screenshot_callback
        self.window_manager = window_manager
        self.settings = load_settings()

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("设置")
        self.dialog.geometry("520x750")
        self.dialog.resizable(False, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._create_widgets()
        self.dialog.wait_window()

    def _create_widgets(self):
        main_frame = ttk.Frame(self.dialog, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 图片模板区
        tmpl_label = ttk.LabelFrame(main_frame, text="图片模板", padding=10)
        tmpl_label.pack(fill=tk.X, pady=(0, 10))

        self.template_status = {}
        for key, name, desc in TEMPLATE_ITEMS:
            row = ttk.Frame(tmpl_label)
            row.pack(fill=tk.X, pady=3)

            ttk.Label(row, text=f"{name}:", width=10).pack(side=tk.LEFT)

            path = self.settings.get(key, '')
            has_file = bool(path) and os.path.exists(path)
            status_text = "已设置 ✓" if has_file else "未设置 ✗"
            status_label = ttk.Label(row, text=status_text, width=10)
            status_label.pack(side=tk.LEFT, padx=5)
            self.template_status[key] = status_label

            btn_text = "重新截图" if has_file else "截图"
            btn = ttk.Button(row, text=btn_text, width=8,
                           command=lambda k=key, n=name: self._capture_template(k, n))
            btn.pack(side=tk.LEFT, padx=5)

            ttk.Label(row, text=desc, foreground='gray').pack(side=tk.LEFT, padx=5)

        # 数字模板区
        digit_label = ttk.LabelFrame(main_frame, text="数字模板", padding=10)
        digit_label.pack(fill=tk.X, pady=(0, 10))

        digit_row = ttk.Frame(digit_label)
        digit_row.pack(fill=tk.X)
        ttk.Label(digit_row, text="0-9模板:", width=10).pack(side=tk.LEFT)

        digits_exist = all(
            os.path.exists(os.path.join(DIGITS_DIR, f'{d}.png')) for d in range(10)
        )
        digit_status = "已设置 ✓" if digits_exist else "未设置 ✗"
        self.digit_status_label = ttk.Label(digit_row, text=digit_status, width=10)
        self.digit_status_label.pack(side=tk.LEFT, padx=5)

        ttk.Button(digit_row, text="截取数字", width=8,
                  command=self._capture_digits).pack(side=tk.LEFT, padx=5)
        ttk.Label(digit_row, text="逐个截取0-9数字", foreground='gray').pack(side=tk.LEFT, padx=5)

        # 网格定位区
        grid_label = ttk.LabelFrame(main_frame, text="网格定位 (相对于背包定位模板)", padding=10)
        grid_label.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(grid_label, text="调整偏移量使红色网格线对齐背包格子边界",
                  foreground='gray').pack(anchor=tk.W, pady=(0, 5))

        offset_row = ttk.Frame(grid_label)
        offset_row.pack(fill=tk.X, pady=3)
        ttk.Label(offset_row, text="X偏移:").pack(side=tk.LEFT)
        self.offset_x_var = tk.IntVar(value=self.settings.get('grid_offset_x', 0))
        ttk.Spinbox(offset_row, from_=-200, to=200,
                    textvariable=self.offset_x_var, width=6).pack(side=tk.LEFT, padx=5)
        ttk.Label(offset_row, text="Y偏移:").pack(side=tk.LEFT, padx=(10, 0))
        self.offset_y_var = tk.IntVar(value=self.settings.get('grid_offset_y', 0))
        ttk.Spinbox(offset_row, from_=-200, to=200,
                    textvariable=self.offset_y_var, width=6).pack(side=tk.LEFT, padx=5)

        ttk.Button(offset_row, text="测试定位", width=8,
                  command=self._test_grid).pack(side=tk.LEFT, padx=15)

        self.grid_test_label = ttk.Label(grid_label, text="", foreground='gray')
        self.grid_test_label.pack(anchor=tk.W, pady=3)

        # 数字区域调节
        digit_area = ttk.LabelFrame(main_frame, text="数字识别区域 (格子内相对位置)", padding=10)
        digit_area.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(digit_area, text="调整使蓝色框精确框住数字区域",
                  foreground='gray').pack(anchor=tk.W, pady=(0, 5))

        dr = self.settings.get('digit_region', {})
        digit_row1 = ttk.Frame(digit_area)
        digit_row1.pack(fill=tk.X, pady=2)
        ttk.Label(digit_row1, text="X:").pack(side=tk.LEFT)
        self.digit_x_var = tk.IntVar(value=dr.get('x', 16))
        ttk.Spinbox(digit_row1, from_=0, to=100,
                    textvariable=self.digit_x_var, width=4).pack(side=tk.LEFT, padx=3)
        ttk.Label(digit_row1, text="Y:").pack(side=tk.LEFT, padx=(8, 0))
        self.digit_y_var = tk.IntVar(value=dr.get('y', 42))
        ttk.Spinbox(digit_row1, from_=0, to=100,
                    textvariable=self.digit_y_var, width=4).pack(side=tk.LEFT, padx=3)
        ttk.Label(digit_row1, text="宽:").pack(side=tk.LEFT, padx=(8, 0))
        self.digit_w_var = tk.IntVar(value=dr.get('w', 30))
        ttk.Spinbox(digit_row1, from_=5, to=100,
                    textvariable=self.digit_w_var, width=4).pack(side=tk.LEFT, padx=3)
        ttk.Label(digit_row1, text="高:").pack(side=tk.LEFT, padx=(8, 0))
        self.digit_h_var = tk.IntVar(value=dr.get('h', 20))
        ttk.Spinbox(digit_row1, from_=5, to=100,
                    textvariable=self.digit_h_var, width=4).pack(side=tk.LEFT, padx=3)

        ttk.Button(digit_row1, text="测试数字", width=8,
                  command=self._test_digit).pack(side=tk.LEFT, padx=10)

        self.digit_test_label = ttk.Label(digit_area, text="", foreground='gray')
        self.digit_test_label.pack(anchor=tk.W, pady=2)

        # 其他设置区
        other_label = ttk.LabelFrame(main_frame, text="其他设置", padding=10)
        other_label.pack(fill=tk.X, pady=(0, 10))

        # 点击延迟
        click_row = ttk.Frame(other_label)
        click_row.pack(fill=tk.X, pady=3)
        ttk.Label(click_row, text="点击前延迟:", width=14).pack(side=tk.LEFT)
        self.click_pre_var = tk.IntVar(value=self.settings.get('click_pre_delay', 200))
        ttk.Spinbox(click_row, from_=0, to=2000, increment=50,
                    textvariable=self.click_pre_var, width=6).pack(side=tk.LEFT, padx=5)
        ttk.Label(click_row, text="ms").pack(side=tk.LEFT)
        ttk.Label(click_row, text="双击间隔:", width=10).pack(side=tk.LEFT, padx=(10, 0))
        self.click_int_var = tk.IntVar(value=self.settings.get('click_interval', 100))
        ttk.Spinbox(click_row, from_=0, to=2000, increment=50,
                    textvariable=self.click_int_var, width=6).pack(side=tk.LEFT, padx=5)
        ttk.Label(click_row, text="ms (移动→等待→单击→间隔→单击)", foreground='gray').pack(side=tk.LEFT)

        # 窗口标题关键字
        title_row = ttk.Frame(other_label)
        title_row.pack(fill=tk.X, pady=3)
        ttk.Label(title_row, text="窗口标题关键字:", width=14).pack(side=tk.LEFT)
        self.title_var = tk.StringVar(value=self.settings.get('window_title_keyword', 'QI魔力'))
        ttk.Entry(title_row, textvariable=self.title_var, width=20).pack(side=tk.LEFT, padx=5)

        # 格子尺寸（有空格子模板时自动获取）
        size_row = ttk.Frame(other_label)
        size_row.pack(fill=tk.X, pady=3)
        ttk.Label(size_row, text="格子宽度:", width=14).pack(side=tk.LEFT)
        self.cell_w_var = tk.IntVar(value=self.settings.get('cell_width', 40))
        ttk.Spinbox(size_row, from_=20, to=100, textvariable=self.cell_w_var, width=6).pack(side=tk.LEFT, padx=5)
        ttk.Label(size_row, text="高度:").pack(side=tk.LEFT, padx=(10, 0))
        self.cell_h_var = tk.IntVar(value=self.settings.get('cell_height', 40))
        ttk.Spinbox(size_row, from_=20, to=100, textvariable=self.cell_h_var, width=6).pack(side=tk.LEFT, padx=5)
        ttk.Label(size_row, text="(有空格子模板时自动检测)", foreground='gray').pack(side=tk.LEFT, padx=5)

        # 按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(15, 0))
        ttk.Button(btn_frame, text="保存", command=self._save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)

    def _capture_template(self, key, name):
        """截取模板图片"""
        os.makedirs(TEMPLATES_DIR, exist_ok=True)
        filename = key.replace('_image', '') + '.png'
        save_path = os.path.join(TEMPLATES_DIR, filename)

        self.dialog.grab_release()
        self.dialog.withdraw()
        success = self.screenshot_callback(save_path)
        self.dialog.deiconify()
        self.dialog.grab_set()

        if success and os.path.exists(save_path):
            self.settings[key] = save_path
            self.template_status[key].config(text="已设置 ✓")

    def _capture_digits(self):
        """逐个截取0-9数字模板"""
        os.makedirs(DIGITS_DIR, exist_ok=True)

        self.dialog.grab_release()
        self.dialog.withdraw()
        for digit in range(10):
            save_path = os.path.join(DIGITS_DIR, f'{digit}.png')
            messagebox.showinfo("截取数字", f"请准备截取数字 {digit}\n点击确定后开始框选")
            success = self.screenshot_callback(save_path)
            if not success:
                self.dialog.deiconify()
                self.dialog.grab_set()
                return
        self.dialog.deiconify()
        self.dialog.grab_set()

        digits_exist = all(
            os.path.exists(os.path.join(DIGITS_DIR, f'{d}.png')) for d in range(10)
        )
        if digits_exist:
            self.digit_status_label.config(text="已设置 ✓")

    def _test_grid(self):
        """测试网格定位，生成带网格线的截图"""
        if not self.window_manager or not self.window_manager.is_window_valid():
            self.grid_test_label.config(
                text="请先绑定游戏窗口", foreground='red')
            return

        # 用当前界面上的值（不需要先保存）
        self.settings['grid_offset_x'] = self.offset_x_var.get()
        self.settings['grid_offset_y'] = self.offset_y_var.get()
        self.settings['cell_width'] = self.cell_w_var.get()
        self.settings['cell_height'] = self.cell_h_var.get()

        self.grid_test_label.config(text="正在测试...", foreground='orange')
        self.dialog.update()

        try:
            from backpack_reader import BackpackReader
            from digit_recognizer import DigitRecognizer

            reader = BackpackReader(
                DigitRecognizer('templates/digits'), self.settings)

            window_rect = self.window_manager.get_window_rect()
            if not window_rect:
                self.grid_test_label.config(
                    text="无法获取窗口坐标", foreground='red')
                return

            save_path, info = reader.test_grid_overlay(window_rect)
            if save_path:
                self.grid_test_label.config(
                    text=f"已保存到 {save_path}，请查看红色网格线是否对齐",
                    foreground='green')
            else:
                self.grid_test_label.config(text=info, foreground='red')

        except Exception as e:
            self.grid_test_label.config(
                text=f"测试出错: {str(e)}", foreground='red')

    def _test_digit(self):
        """测试数字区域，在格子上画出数字区域框"""
        if not self.window_manager or not self.window_manager.is_window_valid():
            self.digit_test_label.config(
                text="请先绑定游戏窗口", foreground='red')
            return

        # 用当前界面值
        self.settings['grid_offset_x'] = self.offset_x_var.get()
        self.settings['grid_offset_y'] = self.offset_y_var.get()
        self.settings['cell_width'] = self.cell_w_var.get()
        self.settings['cell_height'] = self.cell_h_var.get()
        self.settings['digit_region'] = {
            'x': self.digit_x_var.get(),
            'y': self.digit_y_var.get(),
            'w': self.digit_w_var.get(),
            'h': self.digit_h_var.get(),
        }

        self.digit_test_label.config(text="正在测试...", foreground='orange')
        self.dialog.update()

        try:
            from backpack_reader import BackpackReader
            from digit_recognizer import DigitRecognizer
            import cv2
            import numpy as np

            reader = BackpackReader(
                DigitRecognizer('templates/digits'), self.settings)

            window_rect = self.window_manager.get_window_rect()
            if not window_rect:
                self.digit_test_label.config(
                    text="无法获取窗口坐标", foreground='red')
                return

            grid, info = reader.locate_grid(window_rect)
            if not grid:
                self.digit_test_label.config(text=info, foreground='red')
                return

            # 截取网格区域
            from screenshot_util import take_screenshot
            grid_region = (grid.origin_x, grid.origin_y,
                           grid.cell_w * 5, grid.cell_h * 4)
            screenshot = take_screenshot(region=grid_region)
            grid_img = np.array(screenshot)
            screenshot.close()
            overlay = cv2.cvtColor(grid_img, cv2.COLOR_RGB2BGR)

            dr = self.settings['digit_region']
            dx, dy, dw, dh = dr['x'], dr['y'], dr['w'], dr['h']

            # 在每个格子上画数字区域（蓝色框）和格子边界（红色）
            for row in range(4):
                for col in range(5):
                    x0 = col * grid.cell_w
                    y0 = row * grid.cell_h
                    # 格子边界
                    cv2.rectangle(overlay,
                                  (x0, y0),
                                  (x0 + grid.cell_w, y0 + grid.cell_h),
                                  (0, 0, 255), 1)
                    # 数字区域
                    cv2.rectangle(overlay,
                                  (x0 + dx, y0 + dy),
                                  (x0 + dx + dw, y0 + dy + dh),
                                  (255, 0, 0), 1)

            debug_dir = 'debug'
            os.makedirs(debug_dir, exist_ok=True)
            save_path = os.path.join(debug_dir, 'digit_test.png')
            cv2.imwrite(save_path, overlay)

            self.digit_test_label.config(
                text=f"已保存到 {save_path}，蓝框=数字区域",
                foreground='green')

        except Exception as e:
            self.digit_test_label.config(
                text=f"测试出错: {str(e)}", foreground='red')

    def _save(self):
        """保存设置"""
        self.settings['window_title_keyword'] = self.title_var.get()
        self.settings['grid_offset_x'] = self.offset_x_var.get()
        self.settings['grid_offset_y'] = self.offset_y_var.get()
        self.settings['cell_width'] = self.cell_w_var.get()
        self.settings['cell_height'] = self.cell_h_var.get()
        self.settings['digit_region'] = {
            'x': self.digit_x_var.get(),
            'y': self.digit_y_var.get(),
            'w': self.digit_w_var.get(),
            'h': self.digit_h_var.get(),
        }
        self.settings['click_pre_delay'] = self.click_pre_var.get()
        self.settings['click_interval'] = self.click_int_var.get()
        save_settings(self.settings)
        self.result = self.settings
        self.dialog.destroy()
