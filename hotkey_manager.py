#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
快捷键管理模块
负责全局快捷键监听和管理
"""

import json
import os
import keyboard

HOTKEY_CONFIG_FILE = "hotkey_config.json"


class HotkeyManager:
    """快捷键管理器"""

    def __init__(self, gui_instance):
        self.gui = gui_instance
        self.global_start_hotkey = "`"
        self.global_stop_hotkey = "esc"
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

    def start_global_hotkey_listener(self):
        """注册全局快捷键"""
        self._unregister_hotkeys()
        try:
            self._start_hook = keyboard.add_hotkey(
                self.global_start_hotkey, self._on_start_hotkey, suppress=False
            )
            self._stop_hook = keyboard.add_hotkey(
                self.global_stop_hotkey, self._on_stop_hotkey, suppress=False
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

    def _on_start_hotkey(self):
        """快捷键启动执行"""
        if self.gui.is_running or self.gui._tool_stop_callback:
            return
        self.gui.root.after(0, self.gui.start_selected)

    def _on_stop_hotkey(self):
        """快捷键停止执行（制造或工具脚本）"""
        if self.gui._tool_stop_callback:
            self.gui.root.after(0, self.gui._tool_stop_callback)
        elif self.gui.is_running:
            self.gui.root.after(0, self.gui.stop_craft)

    def update_hotkeys(self, start_key, stop_key):
        """更新全局快捷键"""
        self.global_start_hotkey = start_key
        self.global_stop_hotkey = stop_key
        self._save_hotkey_config()
        self.start_global_hotkey_listener()

    def cleanup(self):
        """清理快捷键"""
        self._unregister_hotkeys()

    def get_status_text(self):
        """获取快捷键状态文本"""
        return f"启动:{self.global_start_hotkey} 停止:{self.global_stop_hotkey}"
