#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
快捷键管理模块
负责全局快捷键监听和管理
"""

import json
import os
import keyboard
from dialogs import HotkeySettingsDialog

HOTKEY_CONFIG_FILE = "hotkey_config.json"


class HotkeyManager:
    """快捷键管理器"""

    def __init__(self, gui_instance):
        self.gui = gui_instance
        self.global_start_hotkey = "`"  # 默认启动快捷键
        self.global_stop_hotkey = "esc"  # 默认停止快捷键
        self._start_hook = None
        self._stop_hook = None
        self.is_listening = False
        self._load_hotkey_config()

    def _load_hotkey_config(self):
        """从配置文件加载快捷键设置"""
        try:
            if os.path.exists(HOTKEY_CONFIG_FILE):
                with open(HOTKEY_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self.global_start_hotkey = config.get("start_hotkey", "`")
                self.global_stop_hotkey = config.get("stop_hotkey", "esc")
        except Exception:
            pass

    def _save_hotkey_config(self):
        """保存快捷键设置到配置文件"""
        config = {
            "start_hotkey": self.global_start_hotkey,
            "stop_hotkey": self.global_stop_hotkey
        }
        try:
            with open(HOTKEY_CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def setup_hotkeys(self):
        """设置窗口内快捷键"""
        self.gui.root.bind('<Control-n>', lambda e: self.gui.config_manager.new_config())
        self.gui.root.bind('<Control-o>', lambda e: self.gui.config_manager.open_config())
        self.gui.root.bind('<Control-s>', lambda e: self.gui.config_manager.save_config())
        self.gui.root.bind('<F5>', lambda e: self.gui.start_execution())
        self.gui.root.bind('<F6>', lambda e: self.gui.stop_execution())
        self.gui.root.bind('<Delete>', lambda e: self.gui.delete_step())
        self.gui.root.focus_set()

    def start_global_hotkey_listener(self):
        """注册全局快捷键（基于回调，无需轮询线程）"""
        self._unregister_hotkeys()
        try:
            self._start_hook = keyboard.add_hotkey(
                self.global_start_hotkey, self.hotkey_start_execution, suppress=False
            )
            self._stop_hook = keyboard.add_hotkey(
                self.global_stop_hotkey, self.hotkey_stop_execution, suppress=False
            )
            self.is_listening = True
        except Exception as e:
            print(f"注册全局快捷键失败: {e}")

    def _unregister_hotkeys(self):
        """取消注册全局快捷键"""
        if self._start_hook is not None:
            try:
                keyboard.remove_hotkey(self._start_hook)
            except Exception:
                pass
            self._start_hook = None
        if self._stop_hook is not None:
            try:
                keyboard.remove_hotkey(self._stop_hook)
            except Exception:
                pass
            self._stop_hook = None
        self.is_listening = False

    def hotkey_start_execution(self):
        """快捷键启动执行"""
        if self.gui.is_running:
            return
        self.gui.root.after(0, self.gui.start_execution)

    def hotkey_stop_execution(self):
        """快捷键停止执行"""
        if self.gui.is_running:
            self.gui.root.after(0, self.gui.stop_execution)

    def show_hotkey_settings(self):
        """显示快捷键设置对话框"""
        dialog = HotkeySettingsDialog(self.gui.root, self.global_start_hotkey, self.global_stop_hotkey)
        if dialog.result:
            start_key, stop_key = dialog.result
            self.update_global_hotkeys(start_key, stop_key)

    def update_global_hotkeys(self, start_key, stop_key):
        """更新全局快捷键"""
        self.global_start_hotkey = start_key
        self.global_stop_hotkey = stop_key

        # 更新状态显示
        if hasattr(self.gui, 'hotkey_status_label'):
            self.gui.hotkey_status_label.config(text=f"启动:{start_key} 停止:{stop_key}")

        # 保存并重新注册
        self._save_hotkey_config()
        self.start_global_hotkey_listener()

    def cleanup_hotkeys(self):
        """清理快捷键"""
        self._unregister_hotkeys()

    def get_hotkey_status(self):
        """获取快捷键状态"""
        return f"启动:{self.global_start_hotkey} 停止:{self.global_stop_hotkey}"

    def is_hotkey_enabled(self):
        """检查快捷键是否启用"""
        return self.is_listening

    def enable_hotkeys(self):
        """启用快捷键"""
        if not self.is_listening:
            self.start_global_hotkey_listener()

    def disable_hotkeys(self):
        """禁用快捷键"""
        self._unregister_hotkeys()
