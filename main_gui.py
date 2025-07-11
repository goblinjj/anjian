#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
主GUI模块
整合所有模块，创建主界面
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import threading
import time
import pyautogui
from models import ActionStep
from dialogs import StepTypeDialog, ScreenshotDialog
from execution_engine import AutomationRunner
from ui_editors import EditPageManager, ScreenshotManager
from file_manager import ConfigManager
from hotkey_manager import HotkeyManager

# 禁用pyautogui的故障保护
pyautogui.FAILSAFE = False

class AutomationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("按键小精灵 v1.0")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)
        
        # 设置最小窗口大小
        self.root.minsize(1000, 700)
        
        # 数据存储
        self.steps = []
        self.is_running = False
        
        # 配置pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1
        
        # 初始化管理器
        self.config_manager = ConfigManager(self)
        self.hotkey_manager = HotkeyManager(self)
        self.automation_runner = AutomationRunner(self.update_status)
        
        # 创建界面
        self.create_widgets()
        
        # 初始化编辑器和截图管理器
        self.edit_page_manager = EditPageManager(self.edit_notebook, self)
        self.screenshot_manager = ScreenshotManager(self)
        
        # 加载默认配置
        self.config_manager.load_default_config()
        
        # 设置快捷键
        self.hotkey_manager.setup_hotkeys()
        
        # 启动全局快捷键监听
        self.hotkey_manager.start_global_hotkey_listener()
        
        # 设置窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_widgets(self):
        """创建GUI组件"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # 创建顶部工具栏
        self.create_toolbar(main_frame)
        
        # 创建主要内容区域
        self.create_main_content(main_frame)
        
        # 创建底部状态栏
        self.create_status_bar(main_frame)
    
    def create_toolbar(self, parent):
        """创建工具栏"""
        toolbar = ttk.Frame(parent)
        toolbar.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 文件操作按钮
        ttk.Button(toolbar, text="新建", command=self.config_manager.new_config).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="打开", command=self.config_manager.open_config).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="保存", command=self.config_manager.save_config).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="另存为", command=self.config_manager.save_as_config).pack(side=tk.LEFT, padx=(0, 10))
        
        # 分隔线
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # 执行模式选择
        ttk.Label(toolbar, text="执行模式:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.execution_mode_var = tk.StringVar(value="single")
        self.execution_mode_combo = ttk.Combobox(toolbar, textvariable=self.execution_mode_var, 
                                                values=["单次执行", "循环执行"], state="readonly", width=10)
        self.execution_mode_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        # 设置默认值
        self.execution_mode_combo.set("单次执行")
        
        # 执行控制按钮
        self.start_button = ttk.Button(toolbar, text="开始执行", command=self.start_execution)
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_button = ttk.Button(toolbar, text="停止执行", command=self.stop_execution, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # 分隔线
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=(10, 10))
        
        # 快捷键设置按钮
        ttk.Button(toolbar, text="快捷键设置", command=self.hotkey_manager.show_hotkey_settings).pack(side=tk.LEFT, padx=(0, 10))
        
        # 快捷键状态显示
        self.hotkey_status_label = ttk.Label(toolbar, text=self.hotkey_manager.get_hotkey_status())
        self.hotkey_status_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # 帮助按钮
        ttk.Button(toolbar, text="帮助", command=self.show_help).pack(side=tk.RIGHT)
    
    def create_main_content(self, parent):
        """创建主要内容区域"""
        # 创建左侧步骤列表
        self.create_step_list(parent)
        
        # 创建右侧编辑面板
        self.create_edit_panel(parent)
    
    def create_step_list(self, parent):
        """创建步骤列表"""
        # 左侧框架
        left_frame = ttk.Frame(parent)
        left_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(1, weight=1)
        
        # 步骤列表标题
        ttk.Label(left_frame, text="操作步骤列表", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        # 步骤列表
        list_frame = ttk.Frame(left_frame)
        list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # 创建Treeview
        self.step_tree = ttk.Treeview(list_frame, columns=("type", "description"), show="tree headings")
        self.step_tree.heading("#0", text="步骤")
        self.step_tree.heading("type", text="类型")
        self.step_tree.heading("description", text="描述")
        
        self.step_tree.column("#0", width=60)
        self.step_tree.column("type", width=100)
        self.step_tree.column("description", width=200)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.step_tree.yview)
        self.step_tree.configure(yscrollcommand=scrollbar.set)
        
        self.step_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 绑定事件
        self.step_tree.bind("<<TreeviewSelect>>", self.on_step_select)
        self.step_tree.bind("<Double-1>", self.on_step_double_click)
        
        # 步骤操作按钮
        button_frame = ttk.Frame(left_frame)
        button_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        ttk.Button(button_frame, text="添加步骤", command=self.add_step).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="编辑步骤", command=self.edit_step).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="删除步骤", command=self.delete_step).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="上移", command=self.move_step_up).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="下移", command=self.move_step_down).pack(side=tk.LEFT)
    
    def create_edit_panel(self, parent):
        """创建编辑面板"""
        # 右侧框架
        right_frame = ttk.Frame(parent)
        right_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=1)
        
        # 编辑面板标题
        ttk.Label(right_frame, text="步骤编辑", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        # 创建Notebook用于不同类型的编辑
        self.edit_notebook = ttk.Notebook(right_frame)
        self.edit_notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 预览和测试区域
        self.create_preview_area(right_frame)
    
    def create_preview_area(self, parent):
        """创建预览和测试区域"""
        # 预览框架
        preview_frame = ttk.LabelFrame(parent, text="步骤预览")
        preview_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        preview_frame.columnconfigure(1, weight=1)
        
        # 描述
        ttk.Label(preview_frame, text="描述:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.description_var = tk.StringVar()
        ttk.Entry(preview_frame, textvariable=self.description_var, width=50).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # 启用/禁用
        self.enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(preview_frame, text="启用此步骤", variable=self.enabled_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        # 测试按钮
        button_frame = ttk.Frame(preview_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=5)
        
        ttk.Button(button_frame, text="测试此步骤", command=self.test_current_step).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="保存步骤", command=self.save_current_step).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=self.cancel_edit).pack(side=tk.LEFT, padx=5)
    
    def create_status_bar(self, parent):
        """创建状态栏"""
        self.status_frame = ttk.Frame(parent)
        self.status_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(self.status_frame, textvariable=self.status_var).pack(side=tk.LEFT)
        
        # 执行状态
        self.execution_status_var = tk.StringVar(value="")
        ttk.Label(self.status_frame, textvariable=self.execution_status_var).pack(side=tk.RIGHT)
    
    # 步骤列表相关方法
    def refresh_step_list(self):
        """刷新步骤列表"""
        # 清空现有项目
        for item in self.step_tree.get_children():
            self.step_tree.delete(item)
        
        # 添加步骤
        for i, step in enumerate(self.steps):
            step_num = f"步骤 {i+1}"
            step_type = self.get_step_type_name(step.step_type)
            description = step.description or self.get_default_description(step)
            
            # 添加项目
            item = self.step_tree.insert("", "end", text=step_num, values=(step_type, description))
            
            # 如果步骤被禁用，改变颜色
            if not step.enabled:
                self.step_tree.set(item, "description", f"[已禁用] {description}")
    
    def get_step_type_name(self, step_type):
        """获取步骤类型名称"""
        type_names = {
            "mouse_click": "鼠标点击",
            "keyboard_press": "键盘按键",
            "image_search": "图片搜索",
            "wait": "等待"
        }
        return type_names.get(step_type, step_type)
    
    def get_default_description(self, step):
        """获取默认描述"""
        if step.step_type == "mouse_click":
            return f"点击位置 ({step.params.get('x', 0)}, {step.params.get('y', 0)})"
        elif step.step_type == "keyboard_press":
            return f"按键 {step.params.get('key', '')}"
        elif step.step_type == "image_search":
            return f"搜索图片 {step.params.get('image_path', '')}"
        elif step.step_type == "wait":
            return f"等待 {step.params.get('time', 1)} 秒"
        return "未知步骤"
    
    # 事件处理方法
    def on_step_select(self, event):
        """步骤选择事件"""
        selection = self.step_tree.selection()
        if selection:
            item = selection[0]
            index = self.step_tree.index(item)
            if 0 <= index < len(self.steps):
                self.load_step_to_editor(self.steps[index])
    
    def on_step_double_click(self, event):
        """步骤双击事件"""
        self.edit_step()
    
    def load_step_to_editor(self, step):
        """加载步骤到编辑器"""
        # 清空所有输入
        self.clear_editor()
        
        # 根据步骤类型加载数据
        if step.step_type == "mouse_click":
            self.edit_notebook.select(0)  # 选择鼠标点击标签页
            self.mouse_button_var.set(step.params.get('button', 'left'))
            self.mouse_x_var.set(str(step.params.get('x', 0)))
            self.mouse_y_var.set(str(step.params.get('y', 0)))
            self.click_count_var.set(str(step.params.get('click_count', 1)))
            self.click_interval_var.set(str(step.params.get('click_interval', 0.1)))
            
        elif step.step_type == "keyboard_press":
            self.edit_notebook.select(1)  # 选择键盘按键标签页
            self.key_var.set(step.params.get('key', ''))
            self.key_duration_var.set(str(step.params.get('duration', 0.05)))
            
        elif step.step_type == "image_search":
            self.edit_notebook.select(2)  # 选择图片搜索标签页
            self.search_image_var.set(step.params.get('image_path', ''))
            self.confidence_var.set(str(step.params.get('confidence', 0.8)))
            self.search_offset_x_var.set(str(step.params.get('offset_x', 0)))
            self.search_offset_y_var.set(str(step.params.get('offset_y', 0)))
            self.after_found_var.set(step.params.get('action', 'none'))
            
            # 加载区域相关参数
            self.search_region_var.set(step.params.get('search_region', 'full'))
            self.region_x1_var.set(str(step.params.get('region_x1', 0)))
            self.region_y1_var.set(str(step.params.get('region_y1', 0)))
            self.region_x2_var.set(str(step.params.get('region_x2', 100)))
            self.region_y2_var.set(str(step.params.get('region_y2', 100)))
            self.save_region_var.set(step.params.get('save_region', False))
            self.use_saved_region_var.set(step.params.get('use_saved_region', False))
            
            # 根据区域设置显示/隐藏区域框架
            self.on_search_region_change()
            
        elif step.step_type == "wait":
            self.edit_notebook.select(3)  # 选择等待标签页
            self.wait_time_var.set(str(step.params.get('time', 1.0)))
        
        # 加载通用属性
        self.description_var.set(step.description)
        self.enabled_var.set(step.enabled)
    
    def clear_editor(self):
        """清空编辑器"""
        # 清空所有变量
        if hasattr(self, 'mouse_button_var'):
            self.mouse_button_var.set("left")
            self.mouse_x_var.set("")
            self.mouse_y_var.set("")
            self.click_count_var.set("1")
            self.click_interval_var.set("0.1")
            self.key_var.set("")
            self.key_duration_var.set("0.05")
            self.search_image_var.set("")
            self.confidence_var.set("0.8")
            self.search_offset_x_var.set("0")
            self.search_offset_y_var.set("0")
            self.after_found_var.set("none")
            self.search_region_var.set("full")
            self.region_x1_var.set("0")
            self.region_y1_var.set("0")
            self.region_x2_var.set("100")
            self.region_y2_var.set("100")
            self.save_region_var.set(False)
            self.use_saved_region_var.set(False)
            self.wait_time_var.set("1.0")
            self.description_var.set("")
            self.enabled_var.set(True)
    
    # 工具方法
    def get_current_mouse_pos(self):
        """获取当前鼠标位置"""
        x, y = pyautogui.position()
        self.mouse_x_var.set(str(x))
        self.mouse_y_var.set(str(y))
        self.update_status(f"获取鼠标位置: ({x}, {y})")
    
    def select_search_image(self):
        """选择搜索图片文件"""
        filename = filedialog.askopenfilename(
            title="选择搜索图片文件",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp *.gif"), ("所有文件", "*.*")]
        )
        if filename:
            # 只使用文件名，不使用完整路径
            basename = os.path.basename(filename)
            self.search_image_var.set(basename)

    def screenshot_get_search_image(self):
        """通过截图获取搜索图片"""
        self.screenshot_manager.screenshot_get_search_image()
    
    def on_search_region_change(self):
        """处理搜索区域选择变化"""
        if self.search_region_var.get() == "region":
            # 显示区域设置框架
            self.region_frame.grid()
        else:
            # 隐藏区域设置框架
            self.region_frame.grid_remove()
    
    def screenshot_select_region(self):
        """通过截图选择搜索区域"""
        self.screenshot_manager.screenshot_select_region()
    
    def select_wait_image(self):
        """选择等待图片文件"""
        filename = filedialog.askopenfilename(
            title="选择等待图片文件",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp *.gif"), ("所有文件", "*.*")]
        )
        if filename:
            self.wait_image_var.set(filename)
    
    def screenshot_select_position(self):
        """通过截图选择位置"""
        self.screenshot_manager.screenshot_select_position()
    
    def show_screenshot_dialog(self, screenshot, dialog_type):
        """显示截图选择对话框"""
        self.screenshot_manager.show_screenshot_dialog(screenshot, dialog_type)
    
    def update_status(self, message):
        """更新状态"""
        self.status_var.set(message)
    
    def update_execution_mode(self):
        """更新执行模式显示"""
        selected_value = self.execution_mode_combo.get()
        
        if selected_value == "single":
            self.execution_mode_combo.set("单次执行")
            self.execution_mode_var.set("single")
        elif selected_value == "loop":
            self.execution_mode_combo.set("循环执行")
            self.execution_mode_var.set("loop")
        elif selected_value == "单次执行":
            self.execution_mode_var.set("single")
        elif selected_value == "循环执行":
            self.execution_mode_var.set("loop")
    
    # 步骤操作方法
    def add_step(self):
        """添加步骤"""
        dialog = StepTypeDialog(self.root)
        self.root.wait_window(dialog.dialog)  # 等待对话框关闭
        if dialog.result:
            step_type = dialog.result
            step = ActionStep(step_type)
            self.steps.append(step)
            self.refresh_step_list()
            self.update_status(f"已添加 {self.get_step_type_name(step_type)} 步骤")
    
    def edit_step(self):
        """编辑步骤"""
        selection = self.step_tree.selection()
        if selection:
            item = selection[0]
            index = self.step_tree.index(item)
            if 0 <= index < len(self.steps):
                self.load_step_to_editor(self.steps[index])
    
    def delete_step(self):
        """删除步骤"""
        selection = self.step_tree.selection()
        if selection:
            item = selection[0]
            index = self.step_tree.index(item)
            if 0 <= index < len(self.steps):
                if messagebox.askyesno("确认删除", f"确定要删除步骤 {index + 1} 吗？"):
                    del self.steps[index]
                    self.refresh_step_list()
                    self.update_status(f"已删除步骤 {index + 1}")
    
    def move_step_up(self):
        """上移步骤"""
        selection = self.step_tree.selection()
        if selection:
            item = selection[0]
            index = self.step_tree.index(item)
            if 0 < index < len(self.steps):
                # 交换位置
                self.steps[index], self.steps[index - 1] = self.steps[index - 1], self.steps[index]
                self.refresh_step_list()
                # 重新选择移动后的项目
                new_item = self.step_tree.get_children()[index - 1]
                self.step_tree.selection_set(new_item)
                self.update_status(f"步骤 {index + 1} 已上移")
    
    def move_step_down(self):
        """下移步骤"""
        selection = self.step_tree.selection()
        if selection:
            item = selection[0]
            index = self.step_tree.index(item)
            if 0 <= index < len(self.steps) - 1:
                # 交换位置
                self.steps[index], self.steps[index + 1] = self.steps[index + 1], self.steps[index]
                self.refresh_step_list()
                # 重新选择移动后的项目
                new_item = self.step_tree.get_children()[index + 1]
                self.step_tree.selection_set(new_item)
                self.update_status(f"步骤 {index + 1} 已下移")
    
    def test_current_step(self):
        """测试当前步骤"""
        step = self.get_current_step_from_editor()
        if step:
            self.automation_runner.test_single_step(step)
    
    def save_current_step(self):
        """保存当前步骤"""
        step = self.get_current_step_from_editor()
        if step:
            selection = self.step_tree.selection()
            if selection:
                item = selection[0]
                index = self.step_tree.index(item)
                if 0 <= index < len(self.steps):
                    self.steps[index] = step
                    self.refresh_step_list()
                    self.update_status(f"已保存步骤 {index + 1}")
    
    def cancel_edit(self):
        """取消编辑"""
        self.clear_editor()
        self.update_status("已取消编辑")
    
    def get_current_step_from_editor(self):
        """从编辑器获取当前步骤"""
        current_tab = self.edit_notebook.index(self.edit_notebook.select())
        
        if current_tab == 0:  # 鼠标点击
            try:
                x = int(self.mouse_x_var.get())
                y = int(self.mouse_y_var.get())
                button = self.mouse_button_var.get()
                click_count = int(self.click_count_var.get())
                click_interval = float(self.click_interval_var.get())
                
                step = ActionStep("mouse_click", x=x, y=y, button=button, 
                                click_count=click_count, click_interval=click_interval)
                step.description = self.description_var.get()
                step.enabled = self.enabled_var.get()
                return step
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数值")
                return None
        
        elif current_tab == 1:  # 键盘按键
            key = self.key_var.get()
            if not key:
                messagebox.showerror("错误", "请输入按键")
                return None
            
            try:
                duration = float(self.key_duration_var.get())
                step = ActionStep("keyboard_press", key=key, duration=duration)
                step.description = self.description_var.get()
                step.enabled = self.enabled_var.get()
                return step
            except ValueError:
                messagebox.showerror("错误", "请输入有效的持续时间")
                return None
        
        elif current_tab == 2:  # 图片搜索
            image_path = self.search_image_var.get()
            if not image_path:
                messagebox.showerror("错误", "请选择搜索图片")
                return None
            
            try:
                confidence = float(self.confidence_var.get())
                offset_x = int(self.search_offset_x_var.get())
                offset_y = int(self.search_offset_y_var.get())
                timeout = float(self.search_timeout_var.get())
                action = self.after_found_var.get()
                
                # 区域相关参数
                search_region = self.search_region_var.get()
                region_x1 = int(self.region_x1_var.get()) if self.region_x1_var.get() else 0
                region_y1 = int(self.region_y1_var.get()) if self.region_y1_var.get() else 0
                region_x2 = int(self.region_x2_var.get()) if self.region_x2_var.get() else 100
                region_y2 = int(self.region_y2_var.get()) if self.region_y2_var.get() else 100
                save_region = self.save_region_var.get()
                use_saved_region = self.use_saved_region_var.get()
                
                step = ActionStep("image_search", 
                                image_path=image_path, 
                                confidence=confidence,
                                offset_x=offset_x, 
                                offset_y=offset_y, 
                                timeout=timeout, 
                                action=action,
                                search_region=search_region,
                                region_x1=region_x1,
                                region_y1=region_y1,
                                region_x2=region_x2,
                                region_y2=region_y2,
                                save_region=save_region,
                                use_saved_region=use_saved_region)
                step.description = self.description_var.get()
                step.enabled = self.enabled_var.get()
                return step
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数值")
                return None
        
        elif current_tab == 3:  # 等待
            try:
                wait_time = float(self.wait_time_var.get())
                step = ActionStep("wait", time=wait_time)
                step.description = self.description_var.get()
                step.enabled = self.enabled_var.get()
                return step
            except ValueError:
                messagebox.showerror("错误", "请输入有效的等待时间")
                return None
        
        return None
    
    # 执行相关方法
    def start_execution(self):
        """开始执行"""
        if self.is_running:
            return
        
        if not self.steps:
            messagebox.showwarning("警告", "没有可执行的步骤")
            return
        
        self.is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        # 根据执行模式启动执行
        if self.execution_mode_var.get() == "单次执行":
            # 单次执行
            self.automation_runner.start_execution(self.steps, loop_mode=False)
            self.update_status("开始单次执行...")
        else:
            # 循环执行
            self.automation_runner.start_execution(self.steps, loop_mode=True, loop_interval=0.5)
            self.update_status("开始循环执行... (按ESC键停止)")
        
        # 启动状态检查
        self.check_execution_status()
    
    def stop_execution(self):
        """停止执行"""
        if not self.is_running:
            return
        
        self.automation_runner.stop_execution()
        self.is_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.update_status("已停止执行")
    
    def check_execution_status(self):
        """检查执行状态"""
        if self.is_running and not self.automation_runner.is_running():
            # 执行已完成，重置状态
            self.is_running = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            
            # 根据执行模式显示不同的完成信息
            if self.execution_mode_var.get() == "单次执行":
                self.update_status("单次执行完成")
            else:
                self.update_status("循环执行已停止")
        elif self.is_running:
            # 继续检查
            self.root.after(100, self.check_execution_status)
    
    def show_help(self):
        """显示帮助"""
        help_text = """
游戏自动化脚本 GUI 编辑器 v1.0

功能说明：
1. 鼠标点击：模拟鼠标左键、右键点击
2. 键盘按键：模拟键盘按键和文本输入
3. 图片搜索：在屏幕上搜索指定图片并执行动作
4. 等待：等待指定时间或图片出现

快捷键：
- Ctrl+N：新建配置
- Ctrl+O：打开配置
- Ctrl+S：保存配置
- F5：开始执行
- F6：停止执行
- Delete：删除选中步骤

全局快捷键：
- `（反引号）：启动执行
- Esc：停止执行
"""
        messagebox.showinfo("帮助", help_text)
    
    def on_closing(self):
        """窗口关闭事件"""
        self.hotkey_manager.cleanup_hotkeys()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = AutomationGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
