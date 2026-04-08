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
        self.get_material_hotkey = "+"
        self._start_hook = None
        self._stop_hook = None
        self._get_material_hook = None
        self.is_listening = False
        self._load_hotkey_config()
        self._load_get_material_hotkey()

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

    def _load_get_material_hotkey(self):
        """从工具配置加载获取材料快捷键"""
        try:
            from tool_dialog import load_tool_config
            cfg = load_tool_config().get('get_material', {})
            self.get_material_hotkey = cfg.get('hotkey', '+')
        except Exception:
            pass

    def _save_hotkey_config(self):
        """保存快捷键设置到配置文件"""
        config = {
            "start_hotkey": self.global_start_hotkey,
            "stop_hotkey": self.global_stop_hotkey,
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
            self._get_material_hook = keyboard.add_hotkey(
                self.get_material_hotkey, self._on_get_material_hotkey,
                suppress=False
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
        if self._get_material_hook is not None:
            try:
                keyboard.remove_hotkey(self._get_material_hook)
            except Exception:
                pass
            self._get_material_hook = None
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

    def _on_get_material_hotkey(self):
        """快捷键触发获取材料（全局，不受其他功能影响）"""
        self.gui.root.after(0, self.gui._trigger_get_material)

    def update_hotkeys(self, start_key, stop_key):
        """更新启动/停止快捷键"""
        self.global_start_hotkey = start_key
        self.global_stop_hotkey = stop_key
        self._save_hotkey_config()
        self.start_global_hotkey_listener()

    def reload_get_material_hotkey(self):
        """从工具配置重新加载获取材料快捷键并重新注册"""
        self._load_get_material_hotkey()
        self.start_global_hotkey_listener()

    def cleanup(self):
        """清理快捷键"""
        self._unregister_hotkeys()

    def get_status_text(self):
        """获取快捷键状态文本"""
        return (f"启动:{self.global_start_hotkey} "
                f"停止:{self.global_stop_hotkey}")
