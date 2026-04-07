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
            'steps': [],
        }
    }
    if os.path.exists(TOOL_CONFIG_FILE):
        try:
            with open(TOOL_CONFIG_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
            for key in defaults:
                if key in saved:
                    defaults[key].update(saved[key])
            # 向后兼容: 旧版 offsets 格式转换为 steps
            lh = defaults['loop_healing']
            if 'offsets' in lh and not lh.get('steps'):
                steps = [{'type': 'skill'}]
                for off in lh['offsets']:
                    steps.append({
                        'type': 'member',
                        'offset_x': off.get('offset_x', 0),
                        'offset_y': off.get('offset_y', 0),
                    })
                lh['steps'] = steps
            lh.pop('offsets', None)
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

        desc = ttk.LabelFrame(main, text="说明", padding=10)
        desc.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(desc, wraplength=370,
                  text="根据绑定窗口的中心位置，在左下和右上两个偏移点之间\n"
                       "循环移动鼠标并点击，用于自动遇敌。\n"
                       "流程: 左下点击 → 右上点击 → 循环"
                  ).pack(anchor=tk.W)

        params = ttk.LabelFrame(main, text="参数设置", padding=10)
        params.pack(fill=tk.X, pady=(0, 10))

        row = ttk.Frame(params)
        row.pack(fill=tk.X, pady=3)
        ttk.Label(row, text="偏移距离:", width=10).pack(side=tk.LEFT)
        self.offset_var = tk.IntVar(value=self.config.get('offset', 200))
        ttk.Spinbox(row, from_=50, to=500, increment=10,
                    textvariable=self.offset_var, width=8).pack(
            side=tk.LEFT, padx=5)
        ttk.Label(row, text="像素 (从中心向左下/右上偏移)",
                  foreground='gray').pack(side=tk.LEFT, padx=5)

        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(btn_frame, text="确定",
                   command=self._save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消",
                   command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)

    def _save(self):
        offset = self.offset_var.get()
        config = load_tool_config()
        config['auto_encounter']['offset'] = offset
        save_tool_config(config)
        self.result = {'offset': offset}
        self.dialog.destroy()


class LoopHealingDialog:
    """循环医疗配置对话框

    步骤可自由组合: 治疗技能 / 队员定位(X偏移, Y偏移)
    result: {'skill_image':str, 'member_image':str, 'steps':list} 或 None
    """

    def __init__(self, parent, screenshot_callback):
        self.result = None
        self.screenshot_callback = screenshot_callback
        self.config = load_tool_config()['loop_healing']
        self.steps = list(self.config.get('steps', []))

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("循环医疗 - 配置")
        self.dialog.geometry("480x560")
        self.dialog.resizable(False, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._create_widgets()
        self._refresh_step_list()
        self.dialog.wait_window()

    def _create_widgets(self):
        main = ttk.Frame(self.dialog, padding=15)
        main.pack(fill=tk.BOTH, expand=True)

        # ── 图片模板 ──
        img_frame = ttk.LabelFrame(main, text="图片模板", padding=10)
        img_frame.pack(fill=tk.X, pady=(0, 10))

        skill_row = ttk.Frame(img_frame)
        skill_row.pack(fill=tk.X, pady=3)
        ttk.Label(skill_row, text="治疗技能:", width=10).pack(side=tk.LEFT)
        skill_path = self.config.get('skill_image', '')
        has_skill = bool(skill_path) and os.path.exists(skill_path)
        self.skill_status = ttk.Label(
            skill_row, text="已设置 ✓" if has_skill else "未设置 ✗",
            width=10)
        self.skill_status.pack(side=tk.LEFT, padx=5)
        ttk.Button(skill_row, text="截图", width=6,
                   command=self._capture_skill).pack(side=tk.LEFT, padx=5)

        member_row = ttk.Frame(img_frame)
        member_row.pack(fill=tk.X, pady=3)
        ttk.Label(member_row, text="队员定位:", width=10).pack(side=tk.LEFT)
        member_path = self.config.get('member_image', '')
        has_member = bool(member_path) and os.path.exists(member_path)
        self.member_status = ttk.Label(
            member_row, text="已设置 ✓" if has_member else "未设置 ✗",
            width=10)
        self.member_status.pack(side=tk.LEFT, padx=5)
        ttk.Button(member_row, text="截图", width=6,
                   command=self._capture_member).pack(side=tk.LEFT, padx=5)

        # ── 步骤序列 ──
        step_frame = ttk.LabelFrame(
            main, text="执行步骤 (每轮循环按顺序执行，点击前自动200ms延迟)",
            padding=10)
        step_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        ttk.Label(step_frame,
                  text="自由组合步骤，例如: 技能→队员1→队员2→延迟500ms→技能→队员3",
                  foreground='gray').pack(anchor=tk.W, pady=(0, 5))

        # 步骤列表 (Treeview)
        list_frame = ttk.Frame(step_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.step_tree = ttk.Treeview(
            list_frame, show='tree', height=8, selectmode='browse')
        step_scroll = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self.step_tree.yview)
        self.step_tree.configure(yscrollcommand=step_scroll.set)
        self.step_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        step_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.step_tree.bind('<Double-1>', lambda e: self._edit_step())

        # 操作按钮
        btn_row1 = ttk.Frame(step_frame)
        btn_row1.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(btn_row1, text="+ 技能", width=7,
                   command=self._add_skill_step).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row1, text="+ 队员", width=7,
                   command=self._add_member_step).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row1, text="+ 延迟", width=7,
                   command=self._add_delay_step).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row1, text="编辑", width=5,
                   command=self._edit_step).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row1, text="删除", width=5,
                   command=self._delete_step).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row1, text="上移", width=5,
                   command=self._move_up).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row1, text="下移", width=5,
                   command=self._move_down).pack(side=tk.LEFT, padx=2)

        # ── 底部按钮 ──
        bottom = ttk.Frame(main)
        bottom.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(bottom, text="确定",
                   command=self._save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(bottom, text="取消",
                   command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)

    # ── 步骤管理 ──

    def _refresh_step_list(self):
        """刷新步骤列表显示"""
        # 记住当前选中
        sel = self.step_tree.selection()
        sel_idx = None
        if sel:
            sel_idx = self.step_tree.index(sel[0])

        for child in self.step_tree.get_children():
            self.step_tree.delete(child)

        for i, step in enumerate(self.steps):
            if step['type'] == 'skill':
                text = f"#{i+1}  治疗技能"
            elif step['type'] == 'member':
                ox = step.get('offset_x', 0)
                oy = step.get('offset_y', 0)
                text = f"#{i+1}  队员定位 (X:{ox}, Y:{oy})"
            elif step['type'] == 'delay':
                ms = step.get('delay_ms', 500)
                text = f"#{i+1}  延迟 {ms}ms"
            self.step_tree.insert('', 'end', text=text)

        # 恢复选中
        children = self.step_tree.get_children()
        if sel_idx is not None and children:
            idx = min(sel_idx, len(children) - 1)
            self.step_tree.selection_set(children[idx])

    def _get_selected_index(self):
        """获取当前选中步骤的索引"""
        sel = self.step_tree.selection()
        if not sel:
            return None
        return self.step_tree.index(sel[0])

    def _add_skill_step(self):
        """添加治疗技能步骤"""
        self.steps.append({'type': 'skill'})
        self._refresh_step_list()

    def _add_member_step(self):
        """添加队员定位步骤（弹出输入偏移值）"""
        popup = tk.Toplevel(self.dialog)
        popup.title("添加队员定位步骤")
        popup.geometry("300x100")
        popup.resizable(False, False)
        popup.transient(self.dialog)
        popup.grab_set()

        frame = ttk.Frame(popup, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        row = ttk.Frame(frame)
        row.pack(fill=tk.X)
        ttk.Label(row, text="X偏移:").pack(side=tk.LEFT)
        x_var = tk.IntVar(value=0)
        ttk.Spinbox(row, from_=-1000, to=1000,
                     textvariable=x_var, width=7).pack(side=tk.LEFT, padx=5)
        ttk.Label(row, text="Y偏移:").pack(side=tk.LEFT, padx=(10, 0))
        y_var = tk.IntVar(value=0)
        ttk.Spinbox(row, from_=-1000, to=1000,
                     textvariable=y_var, width=7).pack(side=tk.LEFT, padx=5)

        added = [False]

        def on_ok():
            added[0] = True
            popup.destroy()

        btn_row = ttk.Frame(frame)
        btn_row.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(btn_row, text="添加", command=on_ok).pack(
            side=tk.RIGHT, padx=5)
        ttk.Button(btn_row, text="取消", command=popup.destroy).pack(
            side=tk.RIGHT)

        popup.wait_window()

        if added[0]:
            self.steps.append({
                'type': 'member',
                'offset_x': x_var.get(),
                'offset_y': y_var.get(),
            })
            self._refresh_step_list()

    def _add_delay_step(self):
        """添加延迟步骤（弹出输入延迟时间）"""
        popup = tk.Toplevel(self.dialog)
        popup.title("添加延迟步骤")
        popup.geometry("250x90")
        popup.resizable(False, False)
        popup.transient(self.dialog)
        popup.grab_set()

        frame = ttk.Frame(popup, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        row = ttk.Frame(frame)
        row.pack(fill=tk.X)
        ttk.Label(row, text="延迟时间:").pack(side=tk.LEFT)
        ms_var = tk.IntVar(value=500)
        ttk.Spinbox(row, from_=50, to=30000, increment=100,
                     textvariable=ms_var, width=8).pack(side=tk.LEFT, padx=5)
        ttk.Label(row, text="ms").pack(side=tk.LEFT)

        added = [False]

        def on_ok():
            added[0] = True
            popup.destroy()

        btn_row = ttk.Frame(frame)
        btn_row.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(btn_row, text="添加", command=on_ok).pack(
            side=tk.RIGHT, padx=5)
        ttk.Button(btn_row, text="取消", command=popup.destroy).pack(
            side=tk.RIGHT)

        popup.wait_window()

        if added[0]:
            self.steps.append({'type': 'delay', 'delay_ms': ms_var.get()})
            self._refresh_step_list()

    def _edit_step(self):
        """编辑选中步骤（双击或点击编辑按钮）"""
        idx = self._get_selected_index()
        if idx is None:
            return
        step = self.steps[idx]

        if step['type'] == 'skill':
            # 技能步骤无参数可编辑
            return

        popup = tk.Toplevel(self.dialog)
        popup.resizable(False, False)
        popup.transient(self.dialog)
        popup.grab_set()

        frame = ttk.Frame(popup, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        saved = [False]

        def on_ok():
            saved[0] = True
            popup.destroy()

        if step['type'] == 'member':
            popup.title("编辑队员定位步骤")
            popup.geometry("300x100")
            row = ttk.Frame(frame)
            row.pack(fill=tk.X)
            ttk.Label(row, text="X偏移:").pack(side=tk.LEFT)
            x_var = tk.IntVar(value=step.get('offset_x', 0))
            ttk.Spinbox(row, from_=-1000, to=1000,
                         textvariable=x_var, width=7).pack(
                side=tk.LEFT, padx=5)
            ttk.Label(row, text="Y偏移:").pack(side=tk.LEFT, padx=(10, 0))
            y_var = tk.IntVar(value=step.get('offset_y', 0))
            ttk.Spinbox(row, from_=-1000, to=1000,
                         textvariable=y_var, width=7).pack(
                side=tk.LEFT, padx=5)

            btn_row = ttk.Frame(frame)
            btn_row.pack(fill=tk.X, pady=(10, 0))
            ttk.Button(btn_row, text="确定", command=on_ok).pack(
                side=tk.RIGHT, padx=5)
            ttk.Button(btn_row, text="取消",
                       command=popup.destroy).pack(side=tk.RIGHT)

            popup.wait_window()
            if saved[0]:
                step['offset_x'] = x_var.get()
                step['offset_y'] = y_var.get()
                self._refresh_step_list()

        elif step['type'] == 'delay':
            popup.title("编辑延迟步骤")
            popup.geometry("250x90")
            row = ttk.Frame(frame)
            row.pack(fill=tk.X)
            ttk.Label(row, text="延迟时间:").pack(side=tk.LEFT)
            ms_var = tk.IntVar(value=step.get('delay_ms', 500))
            ttk.Spinbox(row, from_=50, to=30000, increment=100,
                         textvariable=ms_var, width=8).pack(
                side=tk.LEFT, padx=5)
            ttk.Label(row, text="ms").pack(side=tk.LEFT)

            btn_row = ttk.Frame(frame)
            btn_row.pack(fill=tk.X, pady=(10, 0))
            ttk.Button(btn_row, text="确定", command=on_ok).pack(
                side=tk.RIGHT, padx=5)
            ttk.Button(btn_row, text="取消",
                       command=popup.destroy).pack(side=tk.RIGHT)

            popup.wait_window()
            if saved[0]:
                step['delay_ms'] = ms_var.get()
                self._refresh_step_list()

    def _delete_step(self):
        """删除选中步骤"""
        idx = self._get_selected_index()
        if idx is not None:
            self.steps.pop(idx)
            self._refresh_step_list()

    def _move_up(self):
        """上移选中步骤"""
        idx = self._get_selected_index()
        if idx is not None and idx > 0:
            self.steps[idx], self.steps[idx - 1] = (
                self.steps[idx - 1], self.steps[idx])
            self._refresh_step_list()
            children = self.step_tree.get_children()
            self.step_tree.selection_set(children[idx - 1])

    def _move_down(self):
        """下移选中步骤"""
        idx = self._get_selected_index()
        if idx is not None and idx < len(self.steps) - 1:
            self.steps[idx], self.steps[idx + 1] = (
                self.steps[idx + 1], self.steps[idx])
            self._refresh_step_list()
            children = self.step_tree.get_children()
            self.step_tree.selection_set(children[idx + 1])

    # ── 截图 ──

    def _capture_skill(self):
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

    # ── 保存 ──

    def _save(self):
        skill_path = self.config.get('skill_image', '')
        member_path = self.config.get('member_image', '')

        if not skill_path or not os.path.exists(skill_path):
            messagebox.showwarning(
                "提示", "请先截取治疗技能图片", parent=self.dialog)
            return
        if not member_path or not os.path.exists(member_path):
            messagebox.showwarning(
                "提示", "请先截取队员定位图片", parent=self.dialog)
            return
        if not self.steps:
            messagebox.showwarning(
                "提示", "请至少添加一个执行步骤", parent=self.dialog)
            return

        config = load_tool_config()
        config['loop_healing'] = {
            'skill_image': skill_path,
            'member_image': member_path,
            'steps': self.steps,
        }
        save_tool_config(config)

        self.result = config['loop_healing']
        self.dialog.destroy()
