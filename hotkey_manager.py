#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
快捷键管理模块
负责全局快捷键监听和管理
"""

import threading
import keyboard
from dialogs import HotkeySettingsDialog

class HotkeyManager:
    """快捷键管理器"""
    
    def __init__(self, gui_instance):
        self.gui = gui_instance
        self.global_start_hotkey = "`"  # 默认启动快捷键
        self.global_stop_hotkey = "esc"  # 默认停止快捷键
        self.hotkey_listener_thread = None
        self.hotkey_enabled = True
        self.is_listening = False
    
    def setup_hotkeys(self):
        """设置快捷键"""
        # 窗口内快捷键
        self.gui.root.bind('<Control-n>', lambda e: self.gui.config_manager.new_config())
        self.gui.root.bind('<Control-o>', lambda e: self.gui.config_manager.open_config())
        self.gui.root.bind('<Control-s>', lambda e: self.gui.config_manager.save_config())
        self.gui.root.bind('<F5>', lambda e: self.gui.start_execution())
        self.gui.root.bind('<F6>', lambda e: self.gui.stop_execution())
        self.gui.root.bind('<Delete>', lambda e: self.gui.delete_step())
        self.gui.root.focus_set()  # 使窗口可以接收键盘事件
    
    def start_global_hotkey_listener(self):
        """启动全局快捷键监听"""
        if self.hotkey_listener_thread is None or not self.hotkey_listener_thread.is_alive():
            self.hotkey_listener_thread = threading.Thread(target=self.global_hotkey_listener, daemon=True)
            self.hotkey_listener_thread.start()
    
    def global_hotkey_listener(self):
        """全局快捷键监听线程"""
        try:
            self.is_listening = True
            
            while self.hotkey_enabled:
                try:
                    # 监听启动快捷键
                    if keyboard.is_pressed(self.global_start_hotkey):
                        self.hotkey_start_execution()
                        # 等待按键释放
                        while keyboard.is_pressed(self.global_start_hotkey):
                            if not self.hotkey_enabled:
                                break
                        threading.Event().wait(0.1)
                    
                    # 监听停止快捷键
                    if keyboard.is_pressed(self.global_stop_hotkey):
                        self.hotkey_stop_execution()
                        # 等待按键释放
                        while keyboard.is_pressed(self.global_stop_hotkey):
                            if not self.hotkey_enabled:
                                break
                        threading.Event().wait(0.1)
                    
                    threading.Event().wait(0.05)  # 短暂休眠，避免CPU占用过高
                    
                except Exception as e:
                    print(f"快捷键监听错误: {e}")
                    break
                    
        except Exception as e:
            print(f"全局快捷键监听异常: {e}")
        finally:
            self.is_listening = False
    
    def hotkey_start_execution(self):
        """快捷键启动执行"""
        # 如果正在运行，忽略启动请求
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
        
        # 重启快捷键监听
        self.restart_hotkey_listener()
    
    def restart_hotkey_listener(self):
        """重启快捷键监听"""
        self.cleanup_hotkeys()
        self.start_global_hotkey_listener()
    
    def cleanup_hotkeys(self):
        """清理快捷键"""
        self.hotkey_enabled = False
        
        # 等待监听线程结束
        if self.hotkey_listener_thread and self.hotkey_listener_thread.is_alive():
            self.hotkey_listener_thread.join(timeout=1)
        
        # 清理keyboard模块的钩子
        try:
            keyboard.unhook_all()
        except:
            pass
        
        # 重新启用
        self.hotkey_enabled = True
    
    def get_hotkey_status(self):
        """获取快捷键状态"""
        return f"启动:{self.global_start_hotkey} 停止:{self.global_stop_hotkey}"
    
    def is_hotkey_enabled(self):
        """检查快捷键是否启用"""
        return self.hotkey_enabled
    
    def enable_hotkeys(self):
        """启用快捷键"""
        if not self.hotkey_enabled:
            self.hotkey_enabled = True
            self.start_global_hotkey_listener()
    
    def disable_hotkeys(self):
        """禁用快捷键"""
        self.hotkey_enabled = False
