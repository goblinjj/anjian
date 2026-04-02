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
from screenshot_util import take_screenshot

class EditPageManager:
    """编辑页面管理器"""
    
    def __init__(self, notebook, gui_instance):
        self.notebook = notebook
        self.gui = gui_instance
        self.create_pages()
    
    # 步骤类型到notebook tab索引的映射
    STEP_TYPE_TAB_INDEX = {
        'mouse_click': 0,
        'keyboard_press': 1,
        'image_search': 2,
        'wait': 3,
        'if_image': 4,
        'for_loop': 5,
        'while_image': 6,
        'break_loop': 7,
        'random_delay': 8,
        'mouse_scroll': 9,
    }

    def create_pages(self):
        """创建所有编辑页面"""
        self.create_mouse_click_page()
        self.create_keyboard_press_page()
        self.create_image_search_page()
        self.create_wait_page()
        self.create_if_image_page()
        self.create_for_loop_page()
        self.create_while_image_page()
        self.create_break_loop_page()
        self.create_random_delay_page()
        self.create_mouse_scroll_page()
        # 保存所有tab引用，用于动态显示
        self._all_tabs = []
        for i in range(self.notebook.index("end")):
            tab_id = self.notebook.tabs()[i]
            tab_text = self.notebook.tab(tab_id, "text")
            self._all_tabs.append((tab_id, tab_text))

    def show_tab_for_step_type(self, step_type):
        """只显示对应步骤类型的tab，隐藏其他tab"""
        target_index = self.STEP_TYPE_TAB_INDEX.get(step_type, 0)
        # 先恢复所有tab
        for tab_id, tab_text in self._all_tabs:
            try:
                self.notebook.add(tab_id, text=tab_text)
            except Exception:
                pass
        # 隐藏不相关的tab
        for i, (tab_id, tab_text) in enumerate(self._all_tabs):
            if i != target_index:
                self.notebook.hide(tab_id)
        # 选中目标tab
        target_tab_id = self._all_tabs[target_index][0]
        self.notebook.select(target_tab_id)
    
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
        ttk.Radiobutton(wait_frame, text="双击", variable=self.gui.after_found_var, value="double_click").grid(row=2, column=1, sticky=tk.W, padx=5)

        # 排除区域设置
        exclude_frame = ttk.LabelFrame(frame, text="排除区域设置")
        exclude_frame.grid(row=4, column=0, columnspan=4, sticky=(tk.W, tk.E), padx=5, pady=5)

        self.gui.exclude_enabled_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(exclude_frame, text="启用排除区域", variable=self.gui.exclude_enabled_var).grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)

        # 排除列表
        ttk.Label(exclude_frame, text="排除图片列表:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.gui.exclude_listbox = tk.Listbox(exclude_frame, height=4, width=50)
        self.gui.exclude_listbox.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E), padx=5, pady=2)

        # 排除列表操作按钮
        exc_btn_frame = ttk.Frame(exclude_frame)
        exc_btn_frame.grid(row=3, column=0, columnspan=4, sticky=tk.W, padx=5, pady=2)
        ttk.Button(exc_btn_frame, text="添加排除图片", command=self._add_exclude_image).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(exc_btn_frame, text="截图获取", command=self._screenshot_exclude_image).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(exc_btn_frame, text="删除选中", command=self._remove_exclude_image).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(exc_btn_frame, text="排除半径(px):").pack(side=tk.LEFT, padx=(5, 2))
        self.gui.exclude_radius_var = tk.StringVar(value="50")
        ttk.Entry(exc_btn_frame, textvariable=self.gui.exclude_radius_var, width=6).pack(side=tk.LEFT)

        # 内部存储排除项数据: list of {"image_path": str, "radius": int}
        self.gui._exclude_items_data = []

    def _add_exclude_image(self):
        """添加排除图片"""
        filename = filedialog.askopenfilename(
            title="选择排除图片",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )
        if filename:
            try:
                radius = int(self.gui.exclude_radius_var.get())
            except ValueError:
                radius = 50
            self.gui._exclude_items_data.append({"image_path": filename, "radius": radius})
            self._refresh_exclude_listbox()

    def _screenshot_exclude_image(self):
        """截图获取排除图片"""
        messagebox.showinfo("截图获取", "请在3秒后进行截图选择...")
        def do_screenshot():
            try:
                time.sleep(3)
                screenshot = take_screenshot()
                self.gui.root.after(0, lambda: self._show_screenshot_for_exclude(screenshot))
            except Exception as e:
                self.gui.root.after(0, lambda: messagebox.showerror("错误", f"截图失败: {str(e)}"))
        import threading
        threading.Thread(target=do_screenshot, daemon=True).start()

    def _show_screenshot_for_exclude(self, screenshot):
        """显示截图对话框用于排除图片"""
        from dialogs import ScreenshotDialog
        dialog = ScreenshotDialog(self.gui.root, screenshot, "search_image")
        if dialog.result:
            try:
                radius = int(self.gui.exclude_radius_var.get())
            except ValueError:
                radius = 50
            self.gui._exclude_items_data.append({"image_path": dialog.result, "radius": radius})
            self._refresh_exclude_listbox()
            self.gui.update_status(f"已添加排除图片: {dialog.result}")

    def _remove_exclude_image(self):
        """删除选中的排除图片"""
        selection = self.gui.exclude_listbox.curselection()
        if selection:
            index = selection[0]
            if 0 <= index < len(self.gui._exclude_items_data):
                del self.gui._exclude_items_data[index]
                self._refresh_exclude_listbox()

    def _refresh_exclude_listbox(self):
        """刷新排除图片列表显示"""
        self.gui.exclude_listbox.delete(0, tk.END)
        for i, item in enumerate(self.gui._exclude_items_data):
            name = os.path.basename(item["image_path"])
            self.gui.exclude_listbox.insert(tk.END, f"{i+1}. {name}  半径:{item['radius']}px")

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

        ttk.Label(image_wait_frame, text="超时时间(秒):").grid(row=1, column=0, padx=5, pady=5)
        self.gui.wait_timeout_var = tk.StringVar(value="10")
        ttk.Entry(image_wait_frame, textvariable=self.gui.wait_timeout_var, width=10).grid(row=1, column=1, padx=5, pady=5)

    def create_if_image_page(self):
        """创建条件判断编辑页面"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="条件判断")

        # 说明
        ttk.Label(frame, text="如果在屏幕上找到指定图片，则执行子步骤；否则执行\"否则\"分支的步骤。",
                  wraplength=450).grid(row=0, column=0, columnspan=4, sticky=tk.W, padx=5, pady=5)

        # 图片选择
        ttk.Label(frame, text="目标图片:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.gui.if_image_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.gui.if_image_var, width=40).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(frame, text="选择图片", command=lambda: self._select_image_file(self.gui.if_image_var)).grid(row=1, column=2, padx=5, pady=5)
        ttk.Button(frame, text="截图获取", command=lambda: self._screenshot_get_image(self.gui.if_image_var)).grid(row=1, column=3, padx=5, pady=5)

        # 搜索参数
        param_frame = ttk.LabelFrame(frame, text="搜索参数")
        param_frame.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E), padx=5, pady=5)

        ttk.Label(param_frame, text="匹配度:").grid(row=0, column=0, padx=5, pady=5)
        self.gui.if_confidence_var = tk.StringVar(value="0.8")
        ttk.Entry(param_frame, textvariable=self.gui.if_confidence_var, width=10).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(param_frame, text="检测超时(秒):").grid(row=0, column=2, padx=5, pady=5)
        self.gui.if_timeout_var = tk.StringVar(value="3")
        ttk.Entry(param_frame, textvariable=self.gui.if_timeout_var, width=10).grid(row=0, column=3, padx=5, pady=5)

        # 提示
        ttk.Label(frame, text="提示: 添加此步骤后，使用\"添加子步骤\"按钮添加满足条件时执行的步骤，\n"
                              "使用\"添加到否则\"按钮添加不满足条件时执行的步骤。",
                  wraplength=450, foreground="gray").grid(row=3, column=0, columnspan=4, sticky=tk.W, padx=5, pady=10)

    def create_for_loop_page(self):
        """创建循环(N次)编辑页面"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="循环(N次)")

        ttk.Label(frame, text="重复执行子步骤指定的次数。",
                  wraplength=450).grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)

        param_frame = ttk.LabelFrame(frame, text="循环设置")
        param_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)

        ttk.Label(param_frame, text="重复次数:").grid(row=0, column=0, padx=5, pady=5)
        self.gui.loop_count_var = tk.StringVar(value="3")
        spinbox = ttk.Spinbox(param_frame, from_=1, to=9999, textvariable=self.gui.loop_count_var, width=10)
        spinbox.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(frame, text="提示: 添加此步骤后，使用\"添加子步骤\"按钮添加循环体中的步骤。",
                  wraplength=450, foreground="gray").grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=5, pady=10)

    def create_while_image_page(self):
        """创建条件循环编辑页面"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="条件循环")

        ttk.Label(frame, text="当图片存在（或不存在）时，持续循环执行子步骤。",
                  wraplength=450).grid(row=0, column=0, columnspan=4, sticky=tk.W, padx=5, pady=5)

        # 图片选择
        ttk.Label(frame, text="目标图片:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.gui.while_image_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.gui.while_image_var, width=40).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(frame, text="选择图片", command=lambda: self._select_image_file(self.gui.while_image_var)).grid(row=1, column=2, padx=5, pady=5)
        ttk.Button(frame, text="截图获取", command=lambda: self._screenshot_get_image(self.gui.while_image_var)).grid(row=1, column=3, padx=5, pady=5)

        # 参数
        param_frame = ttk.LabelFrame(frame, text="循环参数")
        param_frame.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E), padx=5, pady=5)

        ttk.Label(param_frame, text="匹配度:").grid(row=0, column=0, padx=5, pady=5)
        self.gui.while_confidence_var = tk.StringVar(value="0.8")
        ttk.Entry(param_frame, textvariable=self.gui.while_confidence_var, width=10).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(param_frame, text="循环条件:").grid(row=1, column=0, padx=5, pady=5)
        self.gui.while_condition_var = tk.StringVar(value="exists")
        ttk.Radiobutton(param_frame, text="图片存在时继续", variable=self.gui.while_condition_var, value="exists").grid(row=1, column=1, sticky=tk.W, padx=5)
        ttk.Radiobutton(param_frame, text="图片不存在时继续", variable=self.gui.while_condition_var, value="not_exists").grid(row=1, column=2, sticky=tk.W, padx=5)

        ttk.Label(param_frame, text="最大循环次数:").grid(row=2, column=0, padx=5, pady=5)
        self.gui.while_max_iter_var = tk.StringVar(value="100")
        ttk.Entry(param_frame, textvariable=self.gui.while_max_iter_var, width=10).grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(frame, text="提示: 添加此步骤后，使用\"添加子步骤\"按钮添加循环体中的步骤。",
                  wraplength=450, foreground="gray").grid(row=3, column=0, columnspan=4, sticky=tk.W, padx=5, pady=10)

    def create_break_loop_page(self):
        """创建跳出循环编辑页面"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="跳出循环")

        ttk.Label(frame, text="跳出循环", font=("Arial", 14, "bold")).grid(row=0, column=0, sticky=tk.W, padx=5, pady=10)
        ttk.Label(frame, text="执行到此步骤时，将立即跳出最近的循环（循环N次 或 条件循环）。\n\n"
                              "通常与\"条件判断\"配合使用，例如：\n"
                              "  循环(100次)\n"
                              "    条件判断(如果找到某图片)\n"
                              "      跳出循环\n",
                  wraplength=450).grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)

    def create_random_delay_page(self):
        """创建随机延迟编辑页面"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="随机延迟")

        ttk.Label(frame, text="在指定的最小和最大时间之间随机等待。",
                  wraplength=450).grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)

        param_frame = ttk.LabelFrame(frame, text="延迟设置")
        param_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)

        ttk.Label(param_frame, text="最小时间(秒):").grid(row=0, column=0, padx=5, pady=5)
        self.gui.random_min_var = tk.StringVar(value="0.5")
        ttk.Entry(param_frame, textvariable=self.gui.random_min_var, width=10).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(param_frame, text="最大时间(秒):").grid(row=0, column=2, padx=5, pady=5)
        self.gui.random_max_var = tk.StringVar(value="2.0")
        ttk.Entry(param_frame, textvariable=self.gui.random_max_var, width=10).grid(row=0, column=3, padx=5, pady=5)

    def create_mouse_scroll_page(self):
        """创建鼠标滚轮编辑页面"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="鼠标滚轮")

        ttk.Label(frame, text="在指定位置滚动鼠标滚轮。",
                  wraplength=450).grid(row=0, column=0, columnspan=4, sticky=tk.W, padx=5, pady=5)

        # 坐标
        coord_frame = ttk.LabelFrame(frame, text="坐标设置")
        coord_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), padx=5, pady=5)

        ttk.Label(coord_frame, text="X坐标:").grid(row=0, column=0, padx=5, pady=5)
        self.gui.scroll_x_var = tk.StringVar(value="0")
        ttk.Entry(coord_frame, textvariable=self.gui.scroll_x_var, width=10).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(coord_frame, text="Y坐标:").grid(row=0, column=2, padx=5, pady=5)
        self.gui.scroll_y_var = tk.StringVar(value="0")
        ttk.Entry(coord_frame, textvariable=self.gui.scroll_y_var, width=10).grid(row=0, column=3, padx=5, pady=5)

        ttk.Button(coord_frame, text="获取当前鼠标位置", command=self._get_scroll_mouse_pos).grid(row=0, column=4, padx=5, pady=5)

        # 滚动量
        scroll_frame = ttk.LabelFrame(frame, text="滚动设置")
        scroll_frame.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E), padx=5, pady=5)

        ttk.Label(scroll_frame, text="滚动量:").grid(row=0, column=0, padx=5, pady=5)
        self.gui.scroll_clicks_var = tk.StringVar(value="3")
        ttk.Entry(scroll_frame, textvariable=self.gui.scroll_clicks_var, width=10).grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(scroll_frame, text="正数=向上, 负数=向下").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)

    def _select_image_file(self, string_var):
        """通用图片文件选择"""
        filename = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )
        if filename:
            string_var.set(filename)

    def _screenshot_get_image(self, string_var):
        """通用截图获取图片"""
        messagebox.showinfo("截图获取", "请在3秒后进行截图选择...")
        def do_screenshot():
            try:
                time.sleep(3)
                screenshot = take_screenshot()
                self.gui.root.after(0, lambda: self._show_screenshot_for_var(screenshot, string_var))
            except Exception as e:
                self.gui.root.after(0, lambda: messagebox.showerror("错误", f"截图失败: {str(e)}"))
        threading.Thread(target=do_screenshot, daemon=True).start()

    def _show_screenshot_for_var(self, screenshot, string_var):
        """显示截图对话框并将结果设置到指定变量"""
        dialog = ScreenshotDialog(self.gui.root, screenshot, "search_image")
        if dialog.result:
            string_var.set(dialog.result)
            self.gui.update_status(f"已保存截图: {dialog.result}")

    def _get_scroll_mouse_pos(self):
        """获取当前鼠标位置用于滚轮"""
        x, y = pyautogui.position()
        self.gui.scroll_x_var.set(str(x))
        self.gui.scroll_y_var.set(str(y))


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
            screenshot = take_screenshot()
            
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
            screenshot = take_screenshot()
            
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
            screenshot = take_screenshot()
            
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
