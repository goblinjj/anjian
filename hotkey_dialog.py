#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
快捷键设置对话框
"""

import tkinter as tk
from tkinter import ttk
import threading
import keyboard


class HotkeySettingsDialog:
    """快捷键设置对话框"""

    def __init__(self, parent, hotkey_manager):
        self.result = None
        self.hotkey_manager = hotkey_manager
        self._recording = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("快捷键设置")
        self.dialog.geometry("380x220")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._create_widgets()
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)
        self.dialog.wait_window()

    def _create_widgets(self):
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="点击「录制」按钮后按下新的快捷键",
                  foreground='gray').pack(anchor=tk.W, pady=(0, 15))

        # 启动快捷键
        start_row = ttk.Frame(main_frame)
        start_row.pack(fill=tk.X, pady=5)
        ttk.Label(start_row, text="启动快捷键:", width=12).pack(side=tk.LEFT)
        self.start_key_var = tk.StringVar(
            value=self.hotkey_manager.global_start_hotkey)
        self.start_key_label = ttk.Label(
            start_row, textvariable=self.start_key_var,
            width=15, relief='sunken', anchor='center')
        self.start_key_label.pack(side=tk.LEFT, padx=5)
        self.start_record_btn = ttk.Button(
            start_row, text="录制",
            command=lambda: self._start_recording('start'))
        self.start_record_btn.pack(side=tk.LEFT, padx=5)

        # 停止快捷键
        stop_row = ttk.Frame(main_frame)
        stop_row.pack(fill=tk.X, pady=5)
        ttk.Label(stop_row, text="停止快捷键:", width=12).pack(side=tk.LEFT)
        self.stop_key_var = tk.StringVar(
            value=self.hotkey_manager.global_stop_hotkey)
        self.stop_key_label = ttk.Label(
            stop_row, textvariable=self.stop_key_var,
            width=15, relief='sunken', anchor='center')
        self.stop_key_label.pack(side=tk.LEFT, padx=5)
        self.stop_record_btn = ttk.Button(
            stop_row, text="录制",
            command=lambda: self._start_recording('stop'))
        self.stop_record_btn.pack(side=tk.LEFT, padx=5)

        # 按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(20, 0))
        ttk.Button(btn_frame, text="保存",
                   command=self._save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消",
                   command=self._on_close).pack(side=tk.RIGHT, padx=5)

    def _start_recording(self, which):
        """开始录制快捷键"""
        if self._recording:
            return
        self._recording = which

        if which == 'start':
            self.start_record_btn.config(text="请按键...", state=tk.DISABLED)
        else:
            self.stop_record_btn.config(text="请按键...", state=tk.DISABLED)

        # 临时取消全局热键避免冲突
        self.hotkey_manager._unregister_hotkeys()

        thread = threading.Thread(
            target=self._record_key, args=(which,), daemon=True)
        thread.start()

    def _record_key(self, which):
        """后台线程录制按键"""
        try:
            key = keyboard.read_hotkey(suppress=False)
            self.dialog.after(0, self._on_key_recorded, which, key)
        except Exception:
            self.dialog.after(0, self._on_record_failed, which)

    def _on_key_recorded(self, which, key):
        """按键录制完成"""
        self._recording = None
        if which == 'start':
            self.start_key_var.set(key)
            self.start_record_btn.config(text="录制", state=tk.NORMAL)
        else:
            self.stop_key_var.set(key)
            self.stop_record_btn.config(text="录制", state=tk.NORMAL)

    def _on_record_failed(self, which):
        """录制失败"""
        self._recording = None
        if which == 'start':
            self.start_record_btn.config(text="录制", state=tk.NORMAL)
        else:
            self.stop_record_btn.config(text="录制", state=tk.NORMAL)

    def _save(self):
        """保存快捷键设置"""
        start_key = self.start_key_var.get().strip()
        stop_key = self.stop_key_var.get().strip()
        if start_key and stop_key:
            self.hotkey_manager.update_hotkeys(start_key, stop_key)
            self.result = (start_key, stop_key)
        else:
            self.hotkey_manager.start_global_hotkey_listener()
        self.dialog.destroy()

    def _on_close(self):
        """关闭对话框时确保热键重新注册"""
        if not self.result:
            self.hotkey_manager.start_global_hotkey_listener()
        self.dialog.destroy()
