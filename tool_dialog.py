#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
工具脚本配置对话框
仅负责配置参数，引擎由主界面管理
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import json

TOOL_CONFIG_FILE = 'tool_config.json'
TOOLS_DIR = 'tools'


def load_tool_config():
    """加载工具脚本配置"""
    defaults = {
        'auto_encounter': {
            'offset': 200,
        },
        'loop_healing': {
            'skill_image': '',
            'member_image': '',
            'offsets': [],
        }
    }
    if os.path.exists(TOOL_CONFIG_FILE):
        try:
            with open(TOOL_CONFIG_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
            for key in defaults:
                if key in saved:
                    defaults[key].update(saved[key])
        except Exception:
            pass
    return defaults


def save_tool_config(config):
    """保存工具脚本配置"""
    with open(TOOL_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


class AutoEncounterDialog:
    """自动遇敌配置对话框

    result: {'offset': int} 或 None（取消）
    """

    def __init__(self, parent):
        self.result = None
        self.config = load_tool_config()['auto_encounter']

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("自动遇敌 - 配置")
        self.dialog.geometry("420x220")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._create_widgets()
        self.dialog.wait_window()

    def _create_widgets(self):
        main = ttk.Frame(self.dialog, padding=15)
        main.pack(fill=tk.BOTH, expand=True)

        # 说明
        desc = ttk.LabelFrame(main, text="说明", padding=10)
        desc.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(desc, wraplength=370,
                  text="根据绑定窗口的中心位置，在左下和右上两个偏移点之间\n"
                       "循环移动鼠标并点击，用于自动遇敌。\n"
                       "流程: 左下点击→右上点击→循环"
                  ).pack(anchor=tk.W)

        # 参数
        params = ttk.LabelFrame(main, text="参数设置", padding=10)
        params.pack(fill=tk.X, pady=(0, 10))

        row = ttk.Frame(params)
        row.pack(fill=tk.X, pady=3)
        ttk.Label(row, text="偏移距离:", width=10).pack(side=tk.LEFT)
        self.offset_var = tk.IntVar(value=self.config.get('offset', 200))
        ttk.Spinbox(row, from_=50, to=500, increment=10,
                    textvariable=self.offset_var, width=8).pack(side=tk.LEFT, padx=5)
        ttk.Label(row, text="像素 (从中心向左下/右上偏移)",
                  foreground='gray').pack(side=tk.LEFT, padx=5)

        # 按钮
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(btn_frame, text="确定",
                   command=self._start).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消",
                   command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)

    def _start(self):
        offset = self.offset_var.get()

        # 保存配置
        config = load_tool_config()
        config['auto_encounter']['offset'] = offset
        save_tool_config(config)

        self.result = {'offset': offset}
        self.dialog.destroy()


class LoopHealingDialog:
    """循环医疗配置对话框

    result: {'skill_image': str, 'member_image': str, 'offsets': list} 或 None
    """

    def __init__(self, parent, screenshot_callback):
        self.result = None
        self.screenshot_callback = screenshot_callback
        self.config = load_tool_config()['loop_healing']

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("循环医疗 - 配置")
        self.dialog.geometry("520x480")
        self.dialog.resizable(False, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._create_widgets()
        self._load_offsets()
        self.dialog.wait_window()

    def _create_widgets(self):
        main = ttk.Frame(self.dialog, padding=15)
        main.pack(fill=tk.BOTH, expand=True)

        # 图片模板
        img_frame = ttk.LabelFrame(main, text="图片模板", padding=10)
        img_frame.pack(fill=tk.X, pady=(0, 10))

        # 治疗技能
        skill_row = ttk.Frame(img_frame)
        skill_row.pack(fill=tk.X, pady=3)
        ttk.Label(skill_row, text="治疗技能:", width=10).pack(side=tk.LEFT)
        skill_path = self.config.get('skill_image', '')
        has_skill = bool(skill_path) and os.path.exists(skill_path)
        self.skill_status = ttk.Label(
            skill_row, text="已设置 ✓" if has_skill else "未设置 ✗", width=10)
        self.skill_status.pack(side=tk.LEFT, padx=5)
        ttk.Button(skill_row, text="截图", width=6,
                   command=self._capture_skill).pack(side=tk.LEFT, padx=5)
        ttk.Label(skill_row, text="治疗技能的图标",
                  foreground='gray').pack(side=tk.LEFT, padx=5)

        # 队员定位
        member_row = ttk.Frame(img_frame)
        member_row.pack(fill=tk.X, pady=3)
        ttk.Label(member_row, text="队员定位:", width=10).pack(side=tk.LEFT)
        member_path = self.config.get('member_image', '')
        has_member = bool(member_path) and os.path.exists(member_path)
        self.member_status = ttk.Label(
            member_row, text="已设置 ✓" if has_member else "未设置 ✗", width=10)
        self.member_status.pack(side=tk.LEFT, padx=5)
        ttk.Button(member_row, text="截图", width=6,
                   command=self._capture_member).pack(side=tk.LEFT, padx=5)
        ttk.Label(member_row, text="选择治疗队员界面的定位图片",
                  foreground='gray').pack(side=tk.LEFT, padx=5)

        # 偏移点击列表
        offset_frame = ttk.LabelFrame(
            main, text="偏移点击列表 (相对于队员定位图片的中心位置)", padding=10)
        offset_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        ttk.Label(offset_frame,
                  text="找到队员后，依次在以下偏移位置点击，每次点击后等待指定延迟",
                  foreground='gray').pack(anchor=tk.W, pady=(0, 5))

        # 表头
        header = ttk.Frame(offset_frame)
        header.pack(fill=tk.X)
        ttk.Label(header, text="  X偏移", width=10).pack(side=tk.LEFT)
        ttk.Label(header, text="Y偏移", width=10).pack(side=tk.LEFT)
        ttk.Label(header, text="延迟(ms)", width=10).pack(side=tk.LEFT)

        # 滚动列表
        list_frame = ttk.Frame(offset_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.offset_canvas = tk.Canvas(list_frame, height=130)
        self.offset_scrollbar = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self.offset_canvas.yview)
        self.offset_inner = ttk.Frame(self.offset_canvas)

        self.offset_inner.bind(
            '<Configure>',
            lambda e: self.offset_canvas.configure(
                scrollregion=self.offset_canvas.bbox('all')))
        self.offset_canvas.create_window(
            (0, 0), window=self.offset_inner, anchor=tk.NW)
        self.offset_canvas.configure(
            yscrollcommand=self.offset_scrollbar.set)

        self.offset_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.offset_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.offset_rows = []

        # 添加/删除按钮
        btn_row = ttk.Frame(offset_frame)
        btn_row.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(btn_row, text="添加偏移", width=8,
                   command=self._add_offset).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="删除最后一个", width=10,
                   command=self._remove_offset).pack(side=tk.LEFT, padx=2)

        # 底部按钮
        bottom = ttk.Frame(main)
        bottom.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(bottom, text="确定",
                   command=self._start).pack(side=tk.RIGHT, padx=5)
        ttk.Button(bottom, text="取消",
                   command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)

    def _add_offset(self, x=0, y=0, delay=500):
        """添加一个偏移行"""
        row = ttk.Frame(self.offset_inner)
        row.pack(fill=tk.X, pady=1)

        x_var = tk.IntVar(value=x)
        y_var = tk.IntVar(value=y)
        delay_var = tk.IntVar(value=delay)

        ttk.Spinbox(row, from_=-1000, to=1000,
                    textvariable=x_var, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Spinbox(row, from_=-1000, to=1000,
                    textvariable=y_var, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Spinbox(row, from_=0, to=10000, increment=100,
                    textvariable=delay_var, width=8).pack(side=tk.LEFT, padx=2)

        idx = len(self.offset_rows) + 1
        ttk.Label(row, text=f"#{idx}", foreground='gray').pack(side=tk.LEFT, padx=5)

        self.offset_rows.append((row, x_var, y_var, delay_var))
        self.offset_inner.update_idletasks()
        self.offset_canvas.configure(
            scrollregion=self.offset_canvas.bbox('all'))

    def _remove_offset(self):
        """删除最后一个偏移行"""
        if self.offset_rows:
            row, _, _, _ = self.offset_rows.pop()
            row.destroy()
            self.offset_inner.update_idletasks()
            self.offset_canvas.configure(
                scrollregion=self.offset_canvas.bbox('all'))

    def _load_offsets(self):
        """从配置加载偏移列表"""
        offsets = self.config.get('offsets', [])
        if not offsets:
            self._add_offset(0, 0, 500)
        else:
            for off in offsets:
                self._add_offset(
                    off.get('offset_x', 0),
                    off.get('offset_y', 0),
                    off.get('delay_ms', 500))

    def _get_offsets(self):
        """获取当前偏移列表"""
        result = []
        for _, x_var, y_var, delay_var in self.offset_rows:
            result.append({
                'offset_x': x_var.get(),
                'offset_y': y_var.get(),
                'delay_ms': delay_var.get(),
            })
        return result

    def _capture_skill(self):
        """截取治疗技能图片"""
        os.makedirs(TOOLS_DIR, exist_ok=True)
        save_path = os.path.join(TOOLS_DIR, 'healing_skill.png')
        self.dialog.grab_release()
        self.dialog.withdraw()
        success = self.screenshot_callback(save_path)
        self.dialog.deiconify()
        self.dialog.grab_set()
        if success and os.path.exists(save_path):
            self.config['skill_image'] = save_path
            self.skill_status.config(text="已设置 ✓")

    def _capture_member(self):
        """截取队员定位图片"""
        os.makedirs(TOOLS_DIR, exist_ok=True)
        save_path = os.path.join(TOOLS_DIR, 'healing_member.png')
        self.dialog.grab_release()
        self.dialog.withdraw()
        success = self.screenshot_callback(save_path)
        self.dialog.deiconify()
        self.dialog.grab_set()
        if success and os.path.exists(save_path):
            self.config['member_image'] = save_path
            self.member_status.config(text="已设置 ✓")

    def _start(self):
        skill_path = self.config.get('skill_image', '')
        member_path = self.config.get('member_image', '')

        if not skill_path or not os.path.exists(skill_path):
            messagebox.showwarning("提示", "请先截取治疗技能图片", parent=self.dialog)
            return
        if not member_path or not os.path.exists(member_path):
            messagebox.showwarning("提示", "请先截取队员定位图片", parent=self.dialog)
            return

        offsets = self._get_offsets()
        if not offsets:
            messagebox.showwarning("提示", "请至少添加一个偏移点击位置", parent=self.dialog)
            return

        # 保存配置
        config = load_tool_config()
        config['loop_healing'] = {
            'skill_image': skill_path,
            'member_image': member_path,
            'offsets': offsets,
        }
        save_tool_config(config)

        self.result = {
            'skill_image': skill_path,
            'member_image': member_path,
            'offsets': offsets,
        }
        self.dialog.destroy()
