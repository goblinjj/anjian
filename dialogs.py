#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
对话框模块
包含各种对话框类
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
import keyboard
import pyautogui
from PIL import Image, ImageTk
import cv2
import numpy as np
import os

class StepTypeDialog:
    """步骤类型选择对话框"""
    def __init__(self, parent):
        self.parent = parent
        self.result = None
        self.create_dialog()
    
    def create_dialog(self):
        """创建对话框"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("选择步骤类型")
        self.dialog.geometry("300x250")  # 增加高度从200到250
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # 居中显示
        self.dialog.geometry("+%d+%d" % (self.parent.winfo_rootx() + 50, self.parent.winfo_rooty() + 50))
        
        # 主框架
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        ttk.Label(main_frame, text="请选择要添加的步骤类型:", font=("Arial", 12)).pack(pady=(0, 20))
        
        # 步骤类型选择
        self.step_type_var = tk.StringVar(value="mouse_click")
        
        types = [
            ("mouse_click", "鼠标点击"),
            ("keyboard_press", "键盘按键"),
            ("image_search", "图片搜索"),
            ("wait", "等待")
        ]
        
        for value, text in types:
            ttk.Radiobutton(main_frame, text=text, variable=self.step_type_var, value=value).pack(anchor=tk.W, pady=2)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side=tk.BOTTOM, pady=(20, 0))
        
        ttk.Button(button_frame, text="确定", command=self.ok_clicked).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="取消", command=self.cancel_clicked).pack(side=tk.LEFT)
    
    def ok_clicked(self):
        """确定按钮点击"""
        self.result = self.step_type_var.get()
        self.dialog.destroy()
    
    def cancel_clicked(self):
        """取消按钮点击"""
        self.result = None
        self.dialog.destroy()

class ScreenshotDialog:
    """截图选择对话框"""
    def __init__(self, parent, screenshot, dialog_type):
        self.parent = parent
        self.screenshot = screenshot
        self.dialog_type = dialog_type  # 'position', 'image', 'search_image', 'region'
        self.result = None
        self.create_dialog()
    
    def create_dialog(self):
        """创建对话框"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("截图选择")
        self.dialog.state('zoomed')  # 最大化窗口
        self.dialog.attributes('-topmost', True)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # 创建画布
        self.canvas = tk.Canvas(self.dialog, bg='black')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # 显示截图
        self.display_screenshot()
        
        # 绑定事件
        if self.dialog_type == 'position':
            self.canvas.bind('<Button-1>', self.on_position_click)
        elif self.dialog_type in ['image', 'search_image']:
            self.canvas.bind('<Button-1>', self.start_selection)
            self.canvas.bind('<B1-Motion>', self.update_selection)
            self.canvas.bind('<ButtonRelease-1>', self.end_selection)
        elif self.dialog_type == 'region':
            self.canvas.bind('<Button-1>', self.start_region_selection)
            self.canvas.bind('<B1-Motion>', self.update_region_selection)
            self.canvas.bind('<ButtonRelease-1>', self.end_region_selection)
        
        # 键盘事件
        self.dialog.bind('<Escape>', lambda e: self.dialog.destroy())
        self.dialog.focus_set()
        
        # 选择变量
        self.start_x = None
        self.start_y = None
        self.selection_rect = None
    
    def display_screenshot(self):
        """显示截图"""
        # 获取屏幕尺寸
        screen_width = self.screenshot.width
        screen_height = self.screenshot.height
        
        # 计算缩放比例
        canvas_width = self.dialog.winfo_screenwidth()
        canvas_height = self.dialog.winfo_screenheight()
        
        scale_x = canvas_width / screen_width
        scale_y = canvas_height / screen_height
        self.scale = min(scale_x, scale_y, 1.0)  # 不放大，只缩小
        
        # 调整图片大小
        new_width = int(screen_width * self.scale)
        new_height = int(screen_height * self.scale)
        
        resized_screenshot = self.screenshot.resize((new_width, new_height), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(resized_screenshot)
        
        # 在画布上显示图片
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
    
    def on_position_click(self, event):
        """位置点击事件"""
        # 转换坐标
        x = int(event.x / self.scale)
        y = int(event.y / self.scale)
        
        self.result = (x, y)
        self.dialog.destroy()
    
    def start_selection(self, event):
        """开始选择区域"""
        self.start_x = event.x
        self.start_y = event.y
        
        # 删除之前的选择框
        if self.selection_rect:
            self.canvas.delete(self.selection_rect)
    
    def update_selection(self, event):
        """更新选择区域"""
        if self.start_x is not None and self.start_y is not None:
            # 删除之前的选择框
            if self.selection_rect:
                self.canvas.delete(self.selection_rect)
            
            # 绘制新的选择框
            self.selection_rect = self.canvas.create_rectangle(
                self.start_x, self.start_y, event.x, event.y,
                outline='red', width=2
            )
    
    def end_selection(self, event):
        """结束选择"""
        if self.start_x is not None and self.start_y is not None:
            # 计算选择区域
            x1 = min(self.start_x, event.x)
            y1 = min(self.start_y, event.y)
            x2 = max(self.start_x, event.x)
            y2 = max(self.start_y, event.y)
            
            # 转换为原始坐标
            x1 = int(x1 / self.scale)
            y1 = int(y1 / self.scale)
            x2 = int(x2 / self.scale)
            y2 = int(y2 / self.scale)
            
            # 裁剪图片
            if x2 > x1 and y2 > y1:
                cropped = self.screenshot.crop((x1, y1, x2, y2))
                
                # 让用户选择保存位置
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                default_filename = f"screenshot_{timestamp}.png"
                
                # 暂时隐藏对话框
                self.dialog.withdraw()
                
                # 打开文件保存对话框
                filename = filedialog.asksaveasfilename(
                    title="保存截图",
                    defaultextension=".png",
                    filetypes=[("PNG files", "*.png"), ("All files", "*.*")],
                    initialfile=default_filename
                )
                
                if filename:
                    try:
                        cropped.save(filename)
                        self.result = filename
                        messagebox.showinfo("保存成功", f"截图已保存到: {filename}")
                    except Exception as e:
                        messagebox.showerror("保存失败", f"保存截图时出错: {str(e)}")
                        self.result = None
                else:
                    self.result = None
                
                self.dialog.destroy()
    
    def start_region_selection(self, event):
        """开始选择区域"""
        self.start_x = event.x
        self.start_y = event.y
        
        # 删除之前的选择框
        if self.selection_rect:
            self.canvas.delete(self.selection_rect)
    
    def update_region_selection(self, event):
        """更新区域选择"""
        if self.start_x is not None and self.start_y is not None:
            # 删除之前的选择框
            if self.selection_rect:
                self.canvas.delete(self.selection_rect)
            
            # 绘制新的选择框
            self.selection_rect = self.canvas.create_rectangle(
                self.start_x, self.start_y, event.x, event.y,
                outline='red', width=2
            )
    
    def end_region_selection(self, event):
        """结束区域选择"""
        if self.start_x is not None and self.start_y is not None:
            # 计算选择区域
            x1 = min(self.start_x, event.x)
            y1 = min(self.start_y, event.y)
            x2 = max(self.start_x, event.x)
            y2 = max(self.start_y, event.y)
            
            # 转换为原始坐标
            x1 = int(x1 / self.scale)
            y1 = int(y1 / self.scale)
            x2 = int(x2 / self.scale)
            y2 = int(y2 / self.scale)
            
            self.result = (x1, y1, x2, y2)
            self.dialog.destroy()

class HotkeySettingsDialog:
    """快捷键设置对话框"""
    def __init__(self, parent, current_start_key, current_stop_key):
        self.parent = parent
        self.current_start_key = current_start_key
        self.current_stop_key = current_stop_key
        self.result = None
        self.create_dialog()
    
    def create_dialog(self):
        """创建对话框"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("快捷键设置")
        self.dialog.geometry("400x500")
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # 居中显示
        self.dialog.geometry("+%d+%d" % (self.parent.winfo_rootx() + 50, self.parent.winfo_rooty() + 50))
        
        # 主框架
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="设置全局快捷键", font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 说明
        info_label = ttk.Label(main_frame, text="设置启动和停止自动化脚本的全局快捷键", font=("Arial", 10))
        info_label.pack(pady=(0, 20))
        
        # 启动快捷键设置
        start_frame = ttk.LabelFrame(main_frame, text="启动快捷键", padding="10")
        start_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(start_frame, text="当前启动快捷键:").pack(anchor=tk.W)
        self.start_key_var = tk.StringVar(value=self.current_start_key)
        
        start_key_frame = ttk.Frame(start_frame)
        start_key_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.start_key_entry = ttk.Entry(start_key_frame, textvariable=self.start_key_var, width=20)
        self.start_key_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(start_key_frame, text="检测按键", command=self.detect_start_key).pack(side=tk.LEFT)
        
        # 停止快捷键设置
        stop_frame = ttk.LabelFrame(main_frame, text="停止快捷键", padding="10")
        stop_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(stop_frame, text="当前停止快捷键:").pack(anchor=tk.W)
        self.stop_key_var = tk.StringVar(value=self.current_stop_key)
        
        stop_key_frame = ttk.Frame(stop_frame)
        stop_key_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.stop_key_entry = ttk.Entry(stop_key_frame, textvariable=self.stop_key_var, width=20)
        self.stop_key_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(stop_key_frame, text="检测按键", command=self.detect_stop_key).pack(side=tk.LEFT)
        
        # 常用快捷键选择
        common_frame = ttk.LabelFrame(main_frame, text="常用快捷键", padding="10")
        common_frame.pack(fill=tk.X, pady=(0, 20))
        
        common_keys = ["`", "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12", "esc", "space", "ctrl+shift+s", "ctrl+shift+q"]
        
        row = 0
        col = 0
        for key in common_keys:
            btn = ttk.Button(common_frame, text=key, width=8, 
                           command=lambda k=key: self.set_start_key(k))
            btn.grid(row=row, column=col, padx=2, pady=2)
            col += 1
            if col > 5:
                col = 0
                row += 1
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side=tk.BOTTOM, pady=(20, 0))
        
        ttk.Button(button_frame, text="确定", command=self.ok_clicked).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="取消", command=self.cancel_clicked).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="恢复默认", command=self.restore_defaults).pack(side=tk.LEFT)
    
    def detect_start_key(self):
        """检测启动快捷键"""
        self.detect_key("start")
    
    def detect_stop_key(self):
        """检测停止快捷键"""
        self.detect_key("stop")
    
    def detect_key(self, key_type):
        """检测按键"""
        # 创建检测窗口
        detect_window = tk.Toplevel(self.dialog)
        detect_window.title("按键检测")
        detect_window.geometry("300x150")
        detect_window.resizable(False, False)
        detect_window.transient(self.dialog)
        detect_window.grab_set()
        
        # 居中显示
        detect_window.geometry("+%d+%d" % (self.dialog.winfo_rootx() + 50, self.dialog.winfo_rooty() + 50))
        
        # 提示信息
        info_frame = ttk.Frame(detect_window, padding="20")
        info_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(info_frame, text=f"请按下要设置的{key_type}键", font=("Arial", 12)).pack(pady=(20, 10))
        ttk.Label(info_frame, text="(按ESC键取消)", font=("Arial", 10)).pack(pady=(0, 20))
        
        # 检测按键
        detected_key = None
        
        def on_key_event(event):
            nonlocal detected_key
            key_name = event.name
            
            if key_name == "esc":
                detect_window.destroy()
                return
            
            # 处理特殊按键
            if key_name == "space":
                key_name = "space"
            elif key_name == "grave":  # 反引号
                key_name = "`"
            elif key_name.startswith("f") and key_name[1:].isdigit():  # 功能键
                key_name = key_name
            
            detected_key = key_name
            detect_window.destroy()
        
        # 开始监听
        keyboard.on_press(on_key_event)
        
        # 等待窗口关闭
        self.dialog.wait_window(detect_window)
        
        # 停止监听
        keyboard.unhook_all()
        
        # 设置检测到的按键
        if detected_key:
            if key_type == "start":
                self.start_key_var.set(detected_key)
            else:
                self.stop_key_var.set(detected_key)
    
    def set_start_key(self, key):
        """设置启动快捷键"""
        self.start_key_var.set(key)
    
    def restore_defaults(self):
        """恢复默认设置"""
        self.start_key_var.set("`")
        self.stop_key_var.set("esc")
    
    def ok_clicked(self):
        """确定按钮点击"""
        start_key = self.start_key_var.get().strip()
        stop_key = self.stop_key_var.get().strip()
        
        if not start_key or not stop_key:
            messagebox.showwarning("警告", "请设置启动和停止快捷键")
            return
        
        if start_key == stop_key:
            messagebox.showwarning("警告", "启动和停止快捷键不能相同")
            return
        
        self.result = (start_key, stop_key)
        self.dialog.destroy()
    
    def cancel_clicked(self):
        """取消按钮点击"""
        self.result = None
        self.dialog.destroy()
