#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UI编辑器模块
负责创建和管理编辑页面
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import os
import pyautogui
from dialogs import ScreenshotDialog

class EditPageManager:
    """编辑页面管理器"""
    
    def __init__(self, notebook, gui_instance):
        self.notebook = notebook
        self.gui = gui_instance
        self.create_pages()
    
    def create_pages(self):
        """创建所有编辑页面"""
        self.create_mouse_click_page()
        self.create_keyboard_press_page()
        self.create_image_search_page()
        self.create_wait_page()
    
    def create_mouse_click_page(self):
        """创建鼠标点击编辑页面"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="鼠标点击")
        
        # 点击类型
        ttk.Label(frame, text="点击类型:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.gui.mouse_button_var = tk.StringVar(value="left")
        ttk.Radiobutton(frame, text="左键", variable=self.gui.mouse_button_var, value="left").grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Radiobutton(frame, text="右键", variable=self.gui.mouse_button_var, value="right").grid(row=0, column=2, sticky=tk.W, padx=5)
        
        # 坐标输入
        coord_frame = ttk.LabelFrame(frame, text="坐标设置")
        coord_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        ttk.Label(coord_frame, text="X坐标:").grid(row=0, column=0, padx=5, pady=5)
        self.gui.mouse_x_var = tk.StringVar()
        ttk.Entry(coord_frame, textvariable=self.gui.mouse_x_var, width=10).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(coord_frame, text="Y坐标:").grid(row=0, column=2, padx=5, pady=5)
        self.gui.mouse_y_var = tk.StringVar()
        ttk.Entry(coord_frame, textvariable=self.gui.mouse_y_var, width=10).grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Button(coord_frame, text="获取当前鼠标位置", command=self.gui.get_current_mouse_pos).grid(row=0, column=4, padx=5, pady=5)
        ttk.Button(coord_frame, text="截图选择位置", command=self.gui.screenshot_select_position).grid(row=1, column=0, columnspan=5, pady=5)
        
        # 点击设置
        click_frame = ttk.LabelFrame(frame, text="点击设置")
        click_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        ttk.Label(click_frame, text="点击次数:").grid(row=0, column=0, padx=5, pady=5)
        self.gui.click_count_var = tk.StringVar(value="1")
        ttk.Entry(click_frame, textvariable=self.gui.click_count_var, width=10).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(click_frame, text="点击间隔(秒):").grid(row=0, column=2, padx=5, pady=5)
        self.gui.click_interval_var = tk.StringVar(value="0.1")
        ttk.Entry(click_frame, textvariable=self.gui.click_interval_var, width=10).grid(row=0, column=3, padx=5, pady=5)
    
    def create_keyboard_press_page(self):
        """创建键盘按键编辑页面"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="键盘按键")
        
        # 按键类型
        ttk.Label(frame, text="按键类型:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.gui.key_type_var = tk.StringVar(value="single")
        ttk.Radiobutton(frame, text="单个按键", variable=self.gui.key_type_var, value="single").grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Radiobutton(frame, text="组合按键", variable=self.gui.key_type_var, value="combo").grid(row=0, column=2, sticky=tk.W, padx=5)
        ttk.Radiobutton(frame, text="输入文本", variable=self.gui.key_type_var, value="text").grid(row=0, column=3, sticky=tk.W, padx=5)
        
        # 按键设置
        key_frame = ttk.LabelFrame(frame, text="按键设置")
        key_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        ttk.Label(key_frame, text="按键:").grid(row=0, column=0, padx=5, pady=5)
        self.gui.key_var = tk.StringVar()
        key_combo = ttk.Combobox(key_frame, textvariable=self.gui.key_var, width=20)
        key_combo['values'] = ('a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
                               'space', 'enter', 'tab', 'shift', 'ctrl', 'alt', 'esc', 'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12')
        key_combo.grid(row=0, column=1, padx=5, pady=5)
        
        # 文本输入
        ttk.Label(key_frame, text="文本:").grid(row=1, column=0, padx=5, pady=5)
        self.gui.text_var = tk.StringVar()
        ttk.Entry(key_frame, textvariable=self.gui.text_var, width=30).grid(row=1, column=1, padx=5, pady=5)
        
        # 按键持续时间
        ttk.Label(key_frame, text="持续时间(秒):").grid(row=2, column=0, padx=5, pady=5)
        self.gui.key_duration_var = tk.StringVar(value="0.05")
        ttk.Entry(key_frame, textvariable=self.gui.key_duration_var, width=10).grid(row=2, column=1, padx=5, pady=5)
    
    def create_image_search_page(self):
        """创建图片搜索编辑页面"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="图片搜索")
        
        # 图片选择
        ttk.Label(frame, text="目标图片:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.gui.search_image_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.gui.search_image_var, width=40).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(frame, text="选择图片", command=self.gui.select_search_image).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(frame, text="截图获取", command=self.gui.screenshot_get_search_image).grid(row=0, column=3, padx=5, pady=5)
        
        # 搜索参数
        param_frame = ttk.LabelFrame(frame, text="搜索参数")
        param_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        ttk.Label(param_frame, text="匹配度:").grid(row=0, column=0, padx=5, pady=5)
        self.gui.confidence_var = tk.StringVar(value="0.8")
        ttk.Entry(param_frame, textvariable=self.gui.confidence_var, width=10).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(param_frame, text="搜索区域:").grid(row=1, column=0, padx=5, pady=5)
        self.gui.search_region_var = tk.StringVar(value="full")
        ttk.Radiobutton(param_frame, text="全屏", variable=self.gui.search_region_var, value="full", command=self.gui.on_search_region_change).grid(row=1, column=1, sticky=tk.W, padx=5)
        ttk.Radiobutton(param_frame, text="指定区域", variable=self.gui.search_region_var, value="region", command=self.gui.on_search_region_change).grid(row=1, column=2, sticky=tk.W, padx=5)
        
        # 区域设置框架
        self.gui.region_frame = ttk.LabelFrame(param_frame, text="区域设置")
        self.gui.region_frame.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        ttk.Label(self.gui.region_frame, text="左上角X:").grid(row=0, column=0, padx=5, pady=5)
        self.gui.region_x1_var = tk.StringVar(value="0")
        ttk.Entry(self.gui.region_frame, textvariable=self.gui.region_x1_var, width=10).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(self.gui.region_frame, text="左上角Y:").grid(row=0, column=2, padx=5, pady=5)
        self.gui.region_y1_var = tk.StringVar(value="0")
        ttk.Entry(self.gui.region_frame, textvariable=self.gui.region_y1_var, width=10).grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(self.gui.region_frame, text="右下角X:").grid(row=1, column=0, padx=5, pady=5)
        self.gui.region_x2_var = tk.StringVar(value="100")
        ttk.Entry(self.gui.region_frame, textvariable=self.gui.region_x2_var, width=10).grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(self.gui.region_frame, text="右下角Y:").grid(row=1, column=2, padx=5, pady=5)
        self.gui.region_y2_var = tk.StringVar(value="100")
        ttk.Entry(self.gui.region_frame, textvariable=self.gui.region_y2_var, width=10).grid(row=1, column=3, padx=5, pady=5)
        
        ttk.Button(self.gui.region_frame, text="截图选择区域", command=self.gui.screenshot_select_region).grid(row=2, column=0, columnspan=2, pady=5)
        
        # 区域保存和使用选项
        self.gui.save_region_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.gui.region_frame, text="保存区域供后续步骤使用", variable=self.gui.save_region_var).grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        
        self.gui.use_saved_region_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.gui.region_frame, text="使用之前保存的区域", variable=self.gui.use_saved_region_var).grid(row=3, column=2, columnspan=2, sticky=tk.W, padx=5, pady=2)
        
        # 初始状态隐藏区域设置
        self.gui.region_frame.grid_remove()
        
        # 点击偏移量设置
        offset_frame = ttk.LabelFrame(frame, text="点击偏移量")
        offset_frame.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        ttk.Label(offset_frame, text="X偏移:").grid(row=0, column=0, padx=5, pady=5)
        self.gui.search_offset_x_var = tk.StringVar(value="0")
        ttk.Entry(offset_frame, textvariable=self.gui.search_offset_x_var, width=10).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(offset_frame, text="Y偏移:").grid(row=0, column=2, padx=5, pady=5)
        self.gui.search_offset_y_var = tk.StringVar(value="0")
        ttk.Entry(offset_frame, textvariable=self.gui.search_offset_y_var, width=10).grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(offset_frame, text="说明: 偏移量相对于找到图片的中心位置").grid(row=1, column=0, columnspan=4, padx=5, pady=2, sticky=tk.W)
        
        # 等待设置
        wait_frame = ttk.LabelFrame(frame, text="等待设置")
        wait_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        ttk.Label(wait_frame, text="超时时间(秒):").grid(row=0, column=0, padx=5, pady=5)
        self.gui.search_timeout_var = tk.StringVar(value="5")
        ttk.Entry(wait_frame, textvariable=self.gui.search_timeout_var, width=10).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(wait_frame, text="找到后动作:").grid(row=1, column=0, padx=5, pady=5)
        self.gui.after_found_var = tk.StringVar(value="none")
        ttk.Radiobutton(wait_frame, text="无动作", variable=self.gui.after_found_var, value="none").grid(row=1, column=1, sticky=tk.W, padx=5)
        ttk.Radiobutton(wait_frame, text="左键点击", variable=self.gui.after_found_var, value="left_click").grid(row=1, column=2, sticky=tk.W, padx=5)
        ttk.Radiobutton(wait_frame, text="右键点击", variable=self.gui.after_found_var, value="right_click").grid(row=1, column=3, sticky=tk.W, padx=5)
    
    def create_wait_page(self):
        """创建等待编辑页面"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="等待")
        
        # 等待类型
        ttk.Label(frame, text="等待类型:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.gui.wait_type_var = tk.StringVar(value="time")
        ttk.Radiobutton(frame, text="固定时间", variable=self.gui.wait_type_var, value="time").grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Radiobutton(frame, text="等待图片出现", variable=self.gui.wait_type_var, value="image").grid(row=0, column=2, sticky=tk.W, padx=5)
        ttk.Radiobutton(frame, text="等待按键", variable=self.gui.wait_type_var, value="key").grid(row=0, column=3, sticky=tk.W, padx=5)
        
        # 时间设置
        time_frame = ttk.LabelFrame(frame, text="时间设置")
        time_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        ttk.Label(time_frame, text="等待时间(秒):").grid(row=0, column=0, padx=5, pady=5)
        self.gui.wait_time_var = tk.StringVar(value="1.0")
        ttk.Entry(time_frame, textvariable=self.gui.wait_time_var, width=10).grid(row=0, column=1, padx=5, pady=5)
        
        # 图片等待设置
        image_wait_frame = ttk.LabelFrame(frame, text="图片等待设置")
        image_wait_frame.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        ttk.Label(image_wait_frame, text="等待图片:").grid(row=0, column=0, padx=5, pady=5)
        self.gui.wait_image_var = tk.StringVar()
        ttk.Entry(image_wait_frame, textvariable=self.gui.wait_image_var, width=30).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(image_wait_frame, text="选择", command=self.gui.select_wait_image).grid(row=0, column=2, padx=5, pady=5)

class ScreenshotManager:
    """截图管理器"""
    
    def __init__(self, gui_instance):
        self.gui = gui_instance
    
    def screenshot_select_position(self):
        """通过截图选择位置"""
        messagebox.showinfo("截图选择", "请在3秒后进行截图选择...")
        
        # 给用户3秒准备时间
        threading.Thread(target=self.do_screenshot_position, daemon=True).start()
    
    def do_screenshot_position(self):
        """执行截图选择位置"""
        try:
            time.sleep(3)  # 等待3秒
            
            # 截取全屏
            screenshot = pyautogui.screenshot()
            
            # 显示截图选择对话框
            self.gui.root.after(0, lambda: self.show_screenshot_dialog(screenshot, "position"))
            
        except Exception as e:
            self.gui.root.after(0, lambda: messagebox.showerror("错误", f"截图失败: {str(e)}"))
    
    def screenshot_get_search_image(self):
        """通过截图获取搜索图片"""
        messagebox.showinfo("截图获取", "请在3秒后进行截图选择...")
        
        # 给用户3秒准备时间
        threading.Thread(target=self.do_screenshot_search_image, daemon=True).start()
    
    def do_screenshot_search_image(self):
        """执行截图获取搜索图片"""
        try:
            time.sleep(3)  # 等待3秒
            
            # 截取全屏
            screenshot = pyautogui.screenshot()
            
            # 显示截图选择对话框
            self.gui.root.after(0, lambda: self.show_screenshot_dialog(screenshot, "search_image"))
            
        except Exception as e:
            self.gui.root.after(0, lambda: messagebox.showerror("错误", f"截图失败: {str(e)}"))
    
    def screenshot_select_region(self):
        """通过截图选择搜索区域"""
        messagebox.showinfo("截图选择", "请在3秒后进行截图选择区域...")
        
        # 给用户3秒准备时间
        threading.Thread(target=self.do_screenshot_select_region, daemon=True).start()
    
    def do_screenshot_select_region(self):
        """执行截图选择区域"""
        try:
            time.sleep(3)  # 等待3秒
            
            # 截取全屏
            screenshot = pyautogui.screenshot()
            
            # 显示截图选择对话框
            self.gui.root.after(0, lambda: self.show_screenshot_dialog(screenshot, "region"))
            
        except Exception as e:
            self.gui.root.after(0, lambda: messagebox.showerror("错误", f"截图失败: {str(e)}"))
    
    def show_screenshot_dialog(self, screenshot, dialog_type):
        """显示截图选择对话框"""
        dialog = ScreenshotDialog(self.gui.root, screenshot, dialog_type)
        if dialog.result:
            if dialog_type == "position":
                x, y = dialog.result
                self.gui.mouse_x_var.set(str(x))
                self.gui.mouse_y_var.set(str(y))
                self.gui.update_status(f"已选择位置: ({x}, {y})")
            elif dialog_type in ["image", "search_image"]:
                filename = dialog.result
                if dialog_type == "search_image":
                    self.gui.search_image_var.set(filename)
                self.gui.update_status(f"已保存截图: {filename}")
            elif dialog_type == "region":
                x1, y1, x2, y2 = dialog.result
                self.gui.region_x1_var.set(str(x1))
                self.gui.region_y1_var.set(str(y1))
                self.gui.region_x2_var.set(str(x2))
                self.gui.region_y2_var.set(str(y2))
                self.gui.update_status(f"已选择区域: ({x1}, {y1}) - ({x2}, {y2})")
