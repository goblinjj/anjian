#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""自定义工具编辑对话框 + 8 种步骤的子编辑器。"""

import os
import time
import tkinter as tk
from tkinter import ttk, messagebox

# 单键 Combobox 候选 (按键 alias 沿用 bg_input._SPECIAL_VK)
_SINGLE_KEY_PRESETS = [
    'enter', 'space', 'tab', 'esc', 'backspace',
    'delete', 'up', 'down', 'left', 'right',
    'home', 'end',
    'f1', 'f2', 'f3', 'f4', 'f5', 'f6',
    'f7', 'f8', 'f9', 'f10', 'f11', 'f12',
]

_MOUSE_TYPE_TITLES = {
    'mouse_move': '鼠标移动',
    'mouse_click': '鼠标左键',
    'mouse_right_click': '鼠标右键',
    'mouse_double_click': '鼠标双击',
}

_IMAGE_ACTION_LABELS = [
    ('click', '左键单击'),
    ('double_click', '左键双击'),
    ('right_click', '右键单击'),
    ('move', '仅移动'),
    ('none', '什么也不做'),
]

_IMAGE_NOT_FOUND_LABELS = [
    ('skip', '跳过本步'),
    ('retry_skip', '重试后跳过本步'),
    ('retry_stop', '重试后停止整个工具'),
]


def step_summary(step):
    """生成 #N 行右半部分的摘要文本 (不含 #N 前缀)。"""
    t = step.get('type')
    if t in _MOUSE_TYPE_TITLES:
        ox = step.get('offset_x', 0)
        oy = step.get('offset_y', 0)
        return f"{_MOUSE_TYPE_TITLES[t]}  偏移({ox}, {oy})"
    if t == 'key_press':
        if step.get('input_mode') == 'text':
            return f"键盘输入  文本: \"{step.get('text', '')}\""
        return f"键盘输入  单键: {step.get('key', '')}"
    if t == 'hotkey':
        return f"组合键    {' + '.join(step.get('keys', []))}"
    if t == 'image_search':
        img = os.path.basename(step.get('image_path', '')) or '?'
        on_found = dict(_IMAGE_ACTION_LABELS).get(
            step.get('on_found', 'click'), '?')
        on_nf = dict(_IMAGE_NOT_FOUND_LABELS).get(
            step.get('on_not_found', 'skip'), '?')
        ox = step.get('offset_x', 0)
        oy = step.get('offset_y', 0)
        return f"图片查询  {img}  找到→{on_found} 偏移({ox},{oy})  未找到→{on_nf}"
    if t == 'wait':
        return f"等待      {step.get('ms', 500)} ms"
    return f"<未知步骤 {t}>"


class MouseStepDialog:
    """鼠标移动 / 左键 / 右键 / 双击 共享的偏移编辑对话框。"""

    def __init__(self, parent, step_type, initial=None):
        self.result = None
        self._step_type = step_type
        title = _MOUSE_TYPE_TITLES.get(step_type, '鼠标动作')
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"编辑[{title}]")
        self.dialog.geometry("320x140")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        initial = initial or {}
        frame = ttk.Frame(self.dialog, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        row = ttk.Frame(frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="X 偏移:", width=8).pack(side=tk.LEFT)
        self.x_var = tk.IntVar(value=initial.get('offset_x', 0))
        ttk.Spinbox(row, from_=-2000, to=2000, increment=10,
                    textvariable=self.x_var, width=8).pack(side=tk.LEFT)

        row2 = ttk.Frame(frame)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="Y 偏移:", width=8).pack(side=tk.LEFT)
        self.y_var = tk.IntVar(value=initial.get('offset_y', 0))
        ttk.Spinbox(row2, from_=-2000, to=2000, increment=10,
                    textvariable=self.y_var, width=8).pack(side=tk.LEFT)

        ttk.Label(frame, text="(相对游戏窗口中心, 正X右/正Y下)",
                  foreground='gray').pack(anchor=tk.W, pady=(4, 0))

        btn_row = ttk.Frame(frame)
        btn_row.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(btn_row, text="确定",
                   command=self._ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_row, text="取消",
                   command=self.dialog.destroy).pack(side=tk.RIGHT)

        self.dialog.wait_window()

    def _ok(self):
        self.result = {
            'type': self._step_type,
            'offset_x': self.x_var.get(),
            'offset_y': self.y_var.get(),
        }
        self.dialog.destroy()


class KeyPressStepDialog:
    """键盘输入: 单键 或 ASCII 文本串。"""

    def __init__(self, parent, initial=None):
        self.result = None
        initial = initial or {}
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("编辑[键盘输入]")
        self.dialog.geometry("420x260")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        frame = ttk.Frame(self.dialog, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        # 模式切换
        mode_row = ttk.Frame(frame)
        mode_row.pack(fill=tk.X)
        ttk.Label(mode_row, text="模式:").pack(side=tk.LEFT)
        self.mode_var = tk.StringVar(
            value=initial.get('input_mode', 'single'))
        ttk.Radiobutton(mode_row, text="单键", value='single',
                        variable=self.mode_var,
                        command=self._refresh_mode).pack(side=tk.LEFT, padx=8)
        ttk.Radiobutton(mode_row, text="文本串", value='text',
                        variable=self.mode_var,
                        command=self._refresh_mode).pack(side=tk.LEFT)

        # 单键面板
        self.single_frame = ttk.LabelFrame(frame, text="单键", padding=8)
        ttk.Label(self.single_frame, text="按键:").pack(side=tk.LEFT)
        self.key_var = tk.StringVar(value=initial.get('key', 'enter'))
        ttk.Combobox(self.single_frame, textvariable=self.key_var,
                     values=_SINGLE_KEY_PRESETS, width=14).pack(
            side=tk.LEFT, padx=5)

        # 文本面板
        self.text_frame = ttk.LabelFrame(frame, text="文本串", padding=8)
        text_row = ttk.Frame(self.text_frame)
        text_row.pack(fill=tk.X)
        ttk.Label(text_row, text="文本:").pack(side=tk.LEFT)
        self.text_var = tk.StringVar(value=initial.get('text', ''))
        ttk.Entry(text_row, textvariable=self.text_var, width=30).pack(
            side=tk.LEFT, padx=5)
        ttk.Label(self.text_frame, text="仅 ASCII (不支持中文/大写)",
                  foreground='gray').pack(anchor=tk.W, pady=(4, 0))
        interval_row = ttk.Frame(self.text_frame)
        interval_row.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(interval_row, text="字间隔:").pack(side=tk.LEFT)
        self.interval_var = tk.IntVar(
            value=initial.get('char_interval_ms', 30))
        ttk.Spinbox(interval_row, from_=10, to=500, increment=10,
                    textvariable=self.interval_var, width=8).pack(
            side=tk.LEFT, padx=5)
        ttk.Label(interval_row, text="ms").pack(side=tk.LEFT)

        btn_row = ttk.Frame(frame)
        btn_row.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))
        ttk.Button(btn_row, text="确定",
                   command=self._ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_row, text="取消",
                   command=self.dialog.destroy).pack(side=tk.RIGHT)

        self._refresh_mode()
        self.dialog.wait_window()

    def _refresh_mode(self):
        if self.mode_var.get() == 'single':
            self.text_frame.pack_forget()
            self.single_frame.pack(fill=tk.X, pady=8)
        else:
            self.single_frame.pack_forget()
            self.text_frame.pack(fill=tk.X, pady=8)

    def _ok(self):
        mode = self.mode_var.get()
        if mode == 'single':
            key = self.key_var.get().strip()
            if not key:
                messagebox.showwarning("提示", "请填写按键名",
                                       parent=self.dialog)
                return
            self.result = {'type': 'key_press',
                           'input_mode': 'single', 'key': key}
        else:
            text = self.text_var.get()
            if not text:
                messagebox.showwarning("提示", "文本不能为空",
                                       parent=self.dialog)
                return
            for ch in text:
                if ord(ch) > 127:
                    messagebox.showwarning(
                        "提示", f"文本含非 ASCII 字符: {ch}",
                        parent=self.dialog)
                    return
                if 'A' <= ch <= 'Z':
                    messagebox.showwarning(
                        "提示", f"暂不支持大写字母: {ch} (请改用小写)",
                        parent=self.dialog)
                    return
            self.result = {
                'type': 'key_press', 'input_mode': 'text',
                'text': text, 'char_interval_ms': self.interval_var.get()}
        self.dialog.destroy()


class HotkeyStepDialog:
    """组合键, 输入框 + 录制按钮 (复用 keyboard.read_hotkey)。"""

    def __init__(self, parent, initial=None):
        self.result = None
        initial = initial or {}
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("编辑[组合键]")
        self.dialog.geometry("380x150")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        frame = ttk.Frame(self.dialog, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        row = ttk.Frame(frame)
        row.pack(fill=tk.X)
        ttk.Label(row, text="组合键:").pack(side=tk.LEFT)
        keys_init = '+'.join(initial.get('keys', []))
        self.combo_var = tk.StringVar(value=keys_init)
        ttk.Entry(row, textvariable=self.combo_var, width=20).pack(
            side=tk.LEFT, padx=5)
        self.record_btn = ttk.Button(row, text="录制", width=6,
                                     command=self._start_record)
        self.record_btn.pack(side=tk.LEFT, padx=5)

        ttk.Label(frame, text="例: ctrl+c / alt+f4 / ctrl+shift+s",
                  foreground='gray').pack(anchor=tk.W, pady=(8, 0))

        btn_row = ttk.Frame(frame)
        btn_row.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(btn_row, text="确定",
                   command=self._ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_row, text="取消",
                   command=self.dialog.destroy).pack(side=tk.RIGHT)

        self._recording = False
        self.dialog.wait_window()

    def _start_record(self):
        if self._recording:
            return
        self._recording = True
        self.record_btn.config(text="按键中...", state=tk.DISABLED)
        import threading
        threading.Thread(target=self._record_thread, daemon=True).start()

    def _record_thread(self):
        try:
            import keyboard
            key = keyboard.read_hotkey(suppress=False)
            self.dialog.after(0, self._on_recorded, key)
        except Exception:
            self.dialog.after(0, self._on_record_failed)

    def _on_recorded(self, key):
        self._recording = False
        self.combo_var.set(key)
        self.record_btn.config(text="录制", state=tk.NORMAL)

    def _on_record_failed(self):
        self._recording = False
        self.record_btn.config(text="录制", state=tk.NORMAL)

    def _ok(self):
        raw = self.combo_var.get().strip().lower()
        if not raw:
            messagebox.showwarning("提示", "组合键不能为空",
                                   parent=self.dialog)
            return
        keys = [k.strip() for k in raw.split('+') if k.strip()]
        if len(keys) < 2:
            messagebox.showwarning(
                "提示", "组合键至少要有 2 个键 (单键请用'键盘输入'步骤)",
                parent=self.dialog)
            return
        # 校验每个键能被 bg_input 识别
        import bg_input
        for k in keys:
            try:
                bg_input._vk_of(k)
            except ValueError:
                messagebox.showwarning(
                    "提示", f"无法识别的按键: {k}", parent=self.dialog)
                return
        self.result = {'type': 'hotkey', 'keys': keys}
        self.dialog.destroy()


class ImageSearchStepDialog:
    """图片查询: 图片模板 + 找到后动作 + 找不到处理。

    Args:
        screenshot_callback(save_path) -> bool: 截图回调, 复用 main_gui 的
        image_dir: 该工具的图片专属子目录 (相对路径)
        on_image_added(path): 父对话框收集本次会话新增的图片路径以便取消时清理
    """

    def __init__(self, parent, screenshot_callback, image_dir,
                 on_image_added=None, initial=None):
        self.result = None
        self._screenshot_cb = screenshot_callback
        self._image_dir = os.path.abspath(image_dir)
        self._on_image_added = on_image_added or (lambda p: None)
        initial = initial or {}

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("编辑[图片查询]")
        self.dialog.geometry("520x440")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        main = ttk.Frame(self.dialog, padding=12)
        main.pack(fill=tk.BOTH, expand=True)

        # 图片模板
        img_frame = ttk.LabelFrame(main, text="图片模板", padding=8)
        img_frame.pack(fill=tk.X, pady=(0, 8))
        self._image_path = initial.get('image_path', '')
        self.img_status = ttk.Label(
            img_frame, text=self._format_img_status())
        self.img_status.pack(side=tk.LEFT)
        ttk.Button(img_frame, text="截图", width=6,
                   command=self._capture).pack(side=tk.RIGHT, padx=2)

        # 找到后
        found_frame = ttk.LabelFrame(main, text="找到后动作", padding=8)
        found_frame.pack(fill=tk.X, pady=(0, 8))
        action_row = ttk.Frame(found_frame)
        action_row.pack(fill=tk.X)
        ttk.Label(action_row, text="动作:").pack(side=tk.LEFT)
        self.action_var = tk.StringVar(
            value=dict(_IMAGE_ACTION_LABELS).get(
                initial.get('on_found', 'click'), '左键单击'))
        ttk.Combobox(action_row, textvariable=self.action_var,
                     values=[label for _, label in _IMAGE_ACTION_LABELS],
                     state='readonly', width=12).pack(side=tk.LEFT, padx=5)
        offset_row = ttk.Frame(found_frame)
        offset_row.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(offset_row, text="偏移 X:").pack(side=tk.LEFT)
        self.ox_var = tk.IntVar(value=initial.get('offset_x', 0))
        ttk.Spinbox(offset_row, from_=-1000, to=1000, increment=5,
                    textvariable=self.ox_var, width=7).pack(
            side=tk.LEFT, padx=5)
        ttk.Label(offset_row, text="Y:").pack(side=tk.LEFT, padx=(10, 0))
        self.oy_var = tk.IntVar(value=initial.get('offset_y', 0))
        ttk.Spinbox(offset_row, from_=-1000, to=1000, increment=5,
                    textvariable=self.oy_var, width=7).pack(
            side=tk.LEFT, padx=5)
        ttk.Label(offset_row, text="(相对匹配中心)",
                  foreground='gray').pack(side=tk.LEFT, padx=5)

        # 找不到
        nf_frame = ttk.LabelFrame(main, text="找不到时", padding=8)
        nf_frame.pack(fill=tk.X, pady=(0, 8))
        nf_row = ttk.Frame(nf_frame)
        nf_row.pack(fill=tk.X)
        ttk.Label(nf_row, text="处理:").pack(side=tk.LEFT)
        self.nf_var = tk.StringVar(
            value=dict(_IMAGE_NOT_FOUND_LABELS).get(
                initial.get('on_not_found', 'skip'), '跳过本步'))
        ttk.Combobox(nf_row, textvariable=self.nf_var,
                     values=[label for _, label in _IMAGE_NOT_FOUND_LABELS],
                     state='readonly', width=20).pack(side=tk.LEFT, padx=5)

        retry_row = ttk.Frame(nf_frame)
        retry_row.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(retry_row, text="重试时长:").pack(side=tk.LEFT)
        self.retry_var = tk.DoubleVar(
            value=initial.get('retry_seconds', 3.0))
        ttk.Spinbox(retry_row, from_=0.5, to=30.0, increment=0.5,
                    textvariable=self.retry_var, width=7).pack(
            side=tk.LEFT, padx=5)
        ttk.Label(retry_row, text="秒").pack(side=tk.LEFT)
        ttk.Label(retry_row, text="匹配阈值:").pack(side=tk.LEFT, padx=(15, 0))
        self.threshold_var = tk.DoubleVar(
            value=initial.get('threshold', 0.7))
        ttk.Spinbox(retry_row, from_=0.5, to=0.95, increment=0.05,
                    textvariable=self.threshold_var, width=6).pack(
            side=tk.LEFT, padx=5)

        # 按钮
        btn_row = ttk.Frame(main)
        btn_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(btn_row, text="确定",
                   command=self._ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_row, text="取消",
                   command=self.dialog.destroy).pack(side=tk.RIGHT)

        self.dialog.wait_window()

    def _format_img_status(self):
        if self._image_path and os.path.exists(self._image_path):
            return f"已设置 ✓  {os.path.basename(self._image_path)}"
        return "未设置 ✗"

    def _capture(self):
        os.makedirs(self._image_dir, exist_ok=True)
        save_path = os.path.join(
            self._image_dir, f"img_{int(time.time()*1000)}.png")
        self.dialog.grab_release()
        self.dialog.withdraw()
        ok = self._screenshot_cb(save_path)
        self.dialog.deiconify()
        self.dialog.grab_set()
        if ok and os.path.exists(save_path):
            self._image_path = save_path
            self._on_image_added(save_path)
            self.img_status.config(text=self._format_img_status())

    def _ok(self):
        if not self._image_path or not os.path.exists(self._image_path):
            messagebox.showwarning("提示", "请先截图设置图片模板",
                                   parent=self.dialog)
            return
        # 中文 label → 英文 enum 反查
        action_label_to_id = {label: id_ for id_, label in _IMAGE_ACTION_LABELS}
        nf_label_to_id = {label: id_ for id_, label in _IMAGE_NOT_FOUND_LABELS}
        self.result = {
            'type': 'image_search',
            'image_path': self._image_path,
            'offset_x': self.ox_var.get(),
            'offset_y': self.oy_var.get(),
            'on_found': action_label_to_id.get(self.action_var.get(), 'click'),
            'on_not_found': nf_label_to_id.get(self.nf_var.get(), 'skip'),
            'retry_seconds': float(self.retry_var.get()),
            'threshold': float(self.threshold_var.get()),
        }
        self.dialog.destroy()


class WaitStepDialog:
    def __init__(self, parent, initial=None):
        self.result = None
        initial = initial or {}
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("编辑[等待]")
        self.dialog.geometry("280x110")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        frame = ttk.Frame(self.dialog, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        row = ttk.Frame(frame)
        row.pack(fill=tk.X)
        ttk.Label(row, text="等待时间:").pack(side=tk.LEFT)
        self.ms_var = tk.IntVar(value=initial.get('ms', 500))
        ttk.Spinbox(row, from_=50, to=30000, increment=50,
                    textvariable=self.ms_var, width=8).pack(
            side=tk.LEFT, padx=5)
        ttk.Label(row, text="ms (50 ~ 30000)").pack(side=tk.LEFT)

        btn_row = ttk.Frame(frame)
        btn_row.pack(fill=tk.X, pady=(15, 0))
        ttk.Button(btn_row, text="确定",
                   command=self._ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_row, text="取消",
                   command=self.dialog.destroy).pack(side=tk.RIGHT)

        self.dialog.wait_window()

    def _ok(self):
        self.result = {'type': 'wait', 'ms': self.ms_var.get()}
        self.dialog.destroy()


class CustomToolDialog:
    """自定义工具的新建/编辑对话框。

    Args:
        parent: 主窗口
        manager: CustomToolManager
        screenshot_callback(path) -> bool: 截图回调
        original_name: 编辑模式下的原工具名; 新建时为 None
    Result:
        self.result: 保存后的工具名 (str), 或 None (取消)
    """

    def __init__(self, parent, manager, screenshot_callback,
                 original_name=None):
        self.result = None
        self._manager = manager
        self._screenshot_cb = screenshot_callback
        self._original_name = original_name
        # 取消时要清理的本次会话新截图
        self._pending_images = []

        # 加载初始数据
        if original_name:
            self._data = manager.load(original_name)
        else:
            self._data = {
                'version': '1.0', 'name': '', 'mode': 'loop',
                'description': '', 'steps': []
            }

        self.dialog = tk.Toplevel(parent)
        title = f"编辑自定义工具: {original_name}" if original_name \
            else "新建自定义工具"
        self.dialog.title(title)
        self.dialog.geometry("580x640")
        self.dialog.minsize(500, 500)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.protocol("WM_DELETE_WINDOW", self._cancel)

        self._create_widgets()
        self._refresh_step_list()
        self.dialog.wait_window()

    def _create_widgets(self):
        main = ttk.Frame(self.dialog, padding=12)
        main.pack(fill=tk.BOTH, expand=True)

        # 基本信息
        info = ttk.LabelFrame(main, text="基本信息", padding=8)
        info.pack(fill=tk.X, pady=(0, 8))

        n_row = ttk.Frame(info)
        n_row.pack(fill=tk.X, pady=2)
        ttk.Label(n_row, text="名称:", width=8).pack(side=tk.LEFT)
        self.name_var = tk.StringVar(value=self._data.get('name', ''))
        ttk.Entry(n_row, textvariable=self.name_var, width=30).pack(
            side=tk.LEFT, padx=5)

        m_row = ttk.Frame(info)
        m_row.pack(fill=tk.X, pady=2)
        ttk.Label(m_row, text="模式:", width=8).pack(side=tk.LEFT)
        self.mode_var = tk.StringVar(value=self._data.get('mode', 'loop'))
        ttk.Radiobutton(m_row, text="循环", value='loop',
                        variable=self.mode_var).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(m_row, text="单次", value='once',
                        variable=self.mode_var).pack(side=tk.LEFT)

        d_row = ttk.Frame(info)
        d_row.pack(fill=tk.X, pady=2)
        ttk.Label(d_row, text="说明:", width=8).pack(side=tk.LEFT)
        self.desc_var = tk.StringVar(
            value=self._data.get('description', ''))
        ttk.Entry(d_row, textvariable=self.desc_var, width=40).pack(
            side=tk.LEFT, padx=5)

        # 步骤序列
        step_frame = ttk.LabelFrame(
            main, text="步骤序列 (按顺序执行)", padding=8)
        step_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        list_frame = ttk.Frame(step_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.step_tree = ttk.Treeview(
            list_frame, show='tree', selectmode='extended', height=14)
        scroll = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self.step_tree.yview)
        self.step_tree.configure(yscrollcommand=scroll.set)
        self.step_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.step_tree.bind('<Double-1>', lambda e: self._edit_step())

        # 操作按钮行
        op_row = ttk.Frame(step_frame)
        op_row.pack(fill=tk.X, pady=(6, 0))

        # 添加菜单
        self._add_mb = ttk.Menubutton(op_row, text="+ 添加步骤", width=12)
        menu = tk.Menu(self._add_mb, tearoff=0)
        for label, st_type in [
            ('鼠标移动', 'mouse_move'),
            ('鼠标左键', 'mouse_click'),
            ('鼠标右键', 'mouse_right_click'),
            ('鼠标双击', 'mouse_double_click'),
            ('键盘输入', 'key_press'),
            ('组合键', 'hotkey'),
            ('图片查询', 'image_search'),
            ('等待', 'wait'),
        ]:
            menu.add_command(
                label=label,
                command=lambda t=st_type: self._add_step(t))
        self._add_mb['menu'] = menu
        self._add_mb.pack(side=tk.LEFT, padx=2)

        ttk.Button(op_row, text="编辑", width=6,
                   command=self._edit_step).pack(side=tk.LEFT, padx=2)
        ttk.Button(op_row, text="删除", width=6,
                   command=self._delete_step).pack(side=tk.LEFT, padx=2)
        ttk.Button(op_row, text="上移", width=6,
                   command=self._move_up).pack(side=tk.LEFT, padx=2)
        ttk.Button(op_row, text="下移", width=6,
                   command=self._move_down).pack(side=tk.LEFT, padx=2)
        ttk.Button(op_row, text="复制", width=6,
                   command=self._duplicate_step).pack(side=tk.LEFT, padx=2)

        # 底部确定/取消
        bottom = ttk.Frame(main)
        bottom.pack(fill=tk.X)
        ttk.Button(bottom, text="确定",
                   command=self._save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(bottom, text="取消",
                   command=self._cancel).pack(side=tk.RIGHT)

    def _refresh_step_list(self):
        prev_indices = sorted(
            self.step_tree.index(it) for it in self.step_tree.selection())
        for child in self.step_tree.get_children():
            self.step_tree.delete(child)
        for i, step in enumerate(self._data['steps']):
            text = f"#{i+1}  {step_summary(step)}"
            self.step_tree.insert('', 'end', iid=str(i), text=text)
        # 恢复选中
        all_iids = self.step_tree.get_children()
        valid_indices = [i for i in prev_indices if i < len(all_iids)]
        if valid_indices:
            self.step_tree.selection_set([all_iids[i] for i in valid_indices])

    def _selected_indices(self):
        """返回选中行的索引列表 (升序)。"""
        return sorted(self.step_tree.index(it)
                      for it in self.step_tree.selection())

    def _img_dir(self):
        """该工具图片专属子目录 (用当前编辑器里的名字, 截图实时落到这里)。

        新建工具时, 名字可能还没填; 用临时目录避免空名问题。
        """
        name = self._manager.sanitize_name(self.name_var.get())
        if not name:
            return os.path.join(self._manager.tools_dir, '_unnamed_temp')
        return self._manager.img_dir(name)

    def _add_step(self, step_type):
        # 计算插入位置
        sel = self._selected_indices()
        insert_at = (sel[-1] + 1) if sel else len(self._data['steps'])

        new_step = self._open_step_dialog(step_type, initial=None)
        if not new_step:
            return
        self._data['steps'].insert(insert_at, new_step)
        self._refresh_step_list()
        # 选中新行
        all_iids = self.step_tree.get_children()
        if insert_at < len(all_iids):
            self.step_tree.selection_set(all_iids[insert_at])

    def _open_step_dialog(self, step_type, initial):
        """根据类型派发到子对话框, 返回 step dict 或 None。"""
        if step_type in _MOUSE_TYPE_TITLES:
            d = MouseStepDialog(self.dialog, step_type, initial)
            return d.result
        if step_type == 'key_press':
            d = KeyPressStepDialog(self.dialog, initial)
            return d.result
        if step_type == 'hotkey':
            d = HotkeyStepDialog(self.dialog, initial)
            return d.result
        if step_type == 'image_search':
            d = ImageSearchStepDialog(
                self.dialog, self._screenshot_cb,
                self._img_dir(), self._pending_images.append, initial)
            return d.result
        if step_type == 'wait':
            d = WaitStepDialog(self.dialog, initial)
            return d.result
        return None

    def _edit_step(self):
        sel = self._selected_indices()
        if len(sel) != 1:
            return  # 多选时编辑禁用
        idx = sel[0]
        step = self._data['steps'][idx]
        new_step = self._open_step_dialog(step['type'], initial=step)
        if not new_step:
            return
        self._data['steps'][idx] = new_step
        self._refresh_step_list()
        all_iids = self.step_tree.get_children()
        self.step_tree.selection_set(all_iids[idx])

    def _delete_step(self):
        sel = self._selected_indices()
        if not sel:
            return
        # 倒序删, 避免索引漂移
        for i in reversed(sel):
            self._data['steps'].pop(i)
        self._refresh_step_list()

    def _move_up(self):
        sel = self._selected_indices()
        if not sel or sel[0] == 0:
            return
        is_contiguous = (sel[-1] - sel[0] + 1) == len(sel)
        steps = self._data['steps']
        if is_contiguous:
            block = steps[sel[0]:sel[-1]+1]
            del steps[sel[0]:sel[-1]+1]
            steps.insert(sel[0]-1, block[0])
            for k, st in enumerate(block[1:], start=1):
                steps.insert(sel[0]-1+k, st)
            new_sel = [i-1 for i in sel]
        else:
            i = sel[0]
            steps[i-1], steps[i] = steps[i], steps[i-1]
            new_sel = [i-1]
        self._refresh_step_list()
        all_iids = self.step_tree.get_children()
        self.step_tree.selection_set([all_iids[i] for i in new_sel])

    def _move_down(self):
        sel = self._selected_indices()
        if not sel or sel[-1] == len(self._data['steps']) - 1:
            return
        is_contiguous = (sel[-1] - sel[0] + 1) == len(sel)
        steps = self._data['steps']
        if is_contiguous:
            block = steps[sel[0]:sel[-1]+1]
            del steps[sel[0]:sel[-1]+1]
            steps.insert(sel[0]+1, block[0])
            for k, st in enumerate(block[1:], start=1):
                steps.insert(sel[0]+1+k, st)
            new_sel = [i+1 for i in sel]
        else:
            i = sel[0]
            steps[i], steps[i+1] = steps[i+1], steps[i]
            new_sel = [i+1]
        self._refresh_step_list()
        all_iids = self.step_tree.get_children()
        self.step_tree.selection_set([all_iids[i] for i in new_sel])

    def _duplicate_step(self):
        sel = self._selected_indices()
        if not sel:
            return
        import copy
        steps = self._data['steps']
        clones = [copy.deepcopy(steps[i]) for i in sel]
        insert_at = sel[-1] + 1
        for k, c in enumerate(clones):
            steps.insert(insert_at + k, c)
        self._refresh_step_list()
        all_iids = self.step_tree.get_children()
        new_indices = list(range(insert_at, insert_at + len(clones)))
        self.step_tree.selection_set([all_iids[i] for i in new_indices])

    def _save(self):
        name = self._manager.sanitize_name(self.name_var.get())
        if not name:
            messagebox.showwarning(
                "提示", "请填写有效的名称 (不能为空且不能全是非法字符)",
                parent=self.dialog)
            return
        if not self._data['steps']:
            messagebox.showwarning(
                "提示", "至少要添加一个步骤", parent=self.dialog)
            return

        # 处理"新建工具时图片落在 _unnamed_temp"的搬迁
        temp_dir = os.path.join(self._manager.tools_dir, '_unnamed_temp')
        target_dir = self._manager.img_dir(name)
        if (not self._original_name and os.path.isdir(temp_dir)
                and os.path.exists(temp_dir)):
            os.makedirs(target_dir, exist_ok=True)
            for fname in os.listdir(temp_dir):
                src = os.path.join(temp_dir, fname)
                dst = os.path.join(target_dir, fname)
                if os.path.isfile(src):
                    os.replace(src, dst)
                    # 同步改写 image_path 字段 (注意比较绝对路径)
                    abs_src = os.path.abspath(src)
                    for step in self._data['steps']:
                        if (step.get('type') == 'image_search'
                                and os.path.abspath(
                                    step.get('image_path', '')) == abs_src):
                            step['image_path'] = dst
            try:
                os.rmdir(temp_dir)
            except OSError:
                pass

        self._data['name'] = name
        self._data['mode'] = self.mode_var.get()
        self._data['description'] = self.desc_var.get()

        try:
            saved_name = self._manager.save(
                self._data, original_name=self._original_name)
        except ValueError as e:
            messagebox.showwarning("提示", str(e), parent=self.dialog)
            return

        self.result = saved_name
        self.dialog.destroy()

    def _cancel(self):
        # 删本次会话新增、但用户取消的截图
        for p in self._pending_images:
            if os.path.isfile(p):
                try:
                    os.remove(p)
                except OSError:
                    pass
        # 清理 _unnamed_temp 目录
        temp_dir = os.path.join(self._manager.tools_dir, '_unnamed_temp')
        if os.path.isdir(temp_dir):
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        self.dialog.destroy()
