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
    ('execute_button_image', '执行按钮', '制造界面的「执行」按钮'),
    ('completion_image', '制造完成', '制造结束后出现的按钮'),
    ('organize_button_image', '整理背包', '背包界面的「整理」按钮'),
]


def load_settings():
    """加载全局设置"""
    defaults = {
        'backpack_title_image': '',
        'execute_button_image': '',
        'completion_image': '',
        'organize_button_image': '',
        'window_title_keyword': 'QI魔力',
        'cell_width': 40,
        'cell_height': 40,
        'grid_offset_x': 0,
        'grid_offset_y': 0,
        'digit_region': {'x': 20, 'y': 26, 'w': 20, 'h': 14},
        'icon_region': {'x': 2, 'y': 2, 'w': 36, 'h': 36},
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

    def __init__(self, parent, screenshot_callback):
        """
        Args:
            parent: 父窗口
            screenshot_callback: 截图回调函数, 参数为 save_path, 返回 bool
        """
        self.result = None
        self.screenshot_callback = screenshot_callback
        self.settings = load_settings()

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("设置")
        self.dialog.geometry("500x550")
        self.dialog.resizable(False, False)
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

        # 其他设置区
        other_label = ttk.LabelFrame(main_frame, text="其他设置", padding=10)
        other_label.pack(fill=tk.X, pady=(0, 10))

        # 窗口标题关键字
        title_row = ttk.Frame(other_label)
        title_row.pack(fill=tk.X, pady=3)
        ttk.Label(title_row, text="窗口标题关键字:", width=14).pack(side=tk.LEFT)
        self.title_var = tk.StringVar(value=self.settings.get('window_title_keyword', 'QI魔力'))
        ttk.Entry(title_row, textvariable=self.title_var, width=20).pack(side=tk.LEFT, padx=5)

        # 格子尺寸
        size_row = ttk.Frame(other_label)
        size_row.pack(fill=tk.X, pady=3)
        ttk.Label(size_row, text="格子宽度:", width=14).pack(side=tk.LEFT)
        self.cell_w_var = tk.IntVar(value=self.settings.get('cell_width', 40))
        ttk.Spinbox(size_row, from_=20, to=100, textvariable=self.cell_w_var, width=6).pack(side=tk.LEFT, padx=5)
        ttk.Label(size_row, text="高度:").pack(side=tk.LEFT, padx=(10, 0))
        self.cell_h_var = tk.IntVar(value=self.settings.get('cell_height', 40))
        ttk.Spinbox(size_row, from_=20, to=100, textvariable=self.cell_h_var, width=6).pack(side=tk.LEFT, padx=5)

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

        self.dialog.withdraw()
        success = self.screenshot_callback(save_path)
        self.dialog.deiconify()

        if success and os.path.exists(save_path):
            self.settings[key] = save_path
            self.template_status[key].config(text="已设置 ✓")

    def _capture_digits(self):
        """逐个截取0-9数字模板"""
        os.makedirs(DIGITS_DIR, exist_ok=True)

        self.dialog.withdraw()
        for digit in range(10):
            save_path = os.path.join(DIGITS_DIR, f'{digit}.png')
            messagebox.showinfo("截取数字", f"请准备截取数字 {digit}\n点击确定后开始框选")
            success = self.screenshot_callback(save_path)
            if not success:
                self.dialog.deiconify()
                return
        self.dialog.deiconify()

        digits_exist = all(
            os.path.exists(os.path.join(DIGITS_DIR, f'{d}.png')) for d in range(10)
        )
        if digits_exist:
            self.digit_status_label.config(text="已设置 ✓")

    def _save(self):
        """保存设置"""
        self.settings['window_title_keyword'] = self.title_var.get()
        self.settings['cell_width'] = self.cell_w_var.get()
        self.settings['cell_height'] = self.cell_h_var.get()
        save_settings(self.settings)
        self.result = self.settings
        self.dialog.destroy()
