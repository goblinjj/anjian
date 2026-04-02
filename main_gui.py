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

# 容器类型步骤（可以包含子步骤）
CONTAINER_STEP_TYPES = {'if_image', 'for_loop', 'while_image'}

class AutomationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("按键小精灵 v2.0")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)

        # 设置最小窗口大小
        self.root.minsize(1000, 700)

        # 数据存储
        self.steps = []
        self.is_running = False

        # 树形步骤映射
        self._item_to_step = {}         # Treeview item ID → ActionStep
        self._item_to_parent_list = {}  # Treeview item ID → 所属的父列表
        self._branch_label_items = set()  # 分支标签节点集合（不可编辑）
        self._branch_label_to_list = {}   # 分支标签 item ID → 对应的子步骤列表引用
        self._editing_step = None         # 当前正在编辑的步骤引用
        self._editing_parent_list = None  # 当前编辑步骤所在的列表引用

        # 配置pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1

        # 初始化管理器
        self.config_manager = ConfigManager(self)
        self.hotkey_manager = HotkeyManager(self)
        self.automation_runner = AutomationRunner(self._thread_safe_status)

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

        self.execution_mode_var = tk.StringVar(value="单次执行")
        self.execution_mode_combo = ttk.Combobox(toolbar, textvariable=self.execution_mode_var,
                                                values=["单次执行", "循环执行"], state="readonly", width=10)
        self.execution_mode_combo.pack(side=tk.LEFT, padx=(0, 10))

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

        self.step_tree.column("#0", width=100)
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

        # 步骤操作按钮 - 第一行
        button_frame1 = ttk.Frame(left_frame)
        button_frame1.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

        ttk.Button(button_frame1, text="添加步骤", command=self.add_step).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame1, text="编辑步骤", command=self.edit_step).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame1, text="删除步骤", command=self.delete_step).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame1, text="上移", command=self.move_step_up).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame1, text="下移", command=self.move_step_down).pack(side=tk.LEFT)

        # 步骤操作按钮 - 第二行（子步骤管理）
        button_frame2 = ttk.Frame(left_frame)
        button_frame2.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(5, 0))

        self.add_child_btn = ttk.Button(button_frame2, text="添加子步骤", command=self.add_child_step)
        self.add_child_btn.pack(side=tk.LEFT, padx=(0, 5))
        self.add_else_btn = ttk.Button(button_frame2, text="添加到否则", command=self.add_else_step)
        self.add_else_btn.pack(side=tk.LEFT, padx=(0, 5))

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

    # ==================== 步骤列表相关方法 ====================

    def refresh_step_list(self):
        """刷新步骤列表（支持树形结构）"""
        # 清空映射
        self._item_to_step.clear()
        self._item_to_parent_list.clear()
        self._branch_label_items.clear()
        self._branch_label_to_list.clear()

        # 清空Treeview
        for item in self.step_tree.get_children():
            self.step_tree.delete(item)

        # 递归插入步骤
        self._insert_steps_recursive(self.steps, parent_item="", prefix="")

    def _insert_steps_recursive(self, step_list, parent_item, prefix):
        """递归插入步骤到Treeview"""
        for i, step in enumerate(step_list):
            step_num = f"{prefix}{i + 1}"
            step_type_name = self.get_step_type_name(step.step_type)
            description = step.description or self.get_default_description(step)
            if not step.enabled:
                description = f"[已禁用] {description}"

            item = self.step_tree.insert(parent_item, "end", text=f"步骤 {step_num}",
                                         values=(step_type_name, description))

            # 记录映射
            self._item_to_step[item] = step
            self._item_to_parent_list[item] = step_list

            # 容器类型：插入子步骤
            if step.step_type == 'if_image':
                # 满足条件分支
                true_label = self.step_tree.insert(item, "end", text="[满足条件时]",
                                                   values=("", ""))
                self._branch_label_items.add(true_label)
                self._branch_label_to_list[true_label] = step.children
                self._insert_steps_recursive(step.children, true_label, f"{step_num}.")

                # 不满足条件分支
                else_label = self.step_tree.insert(item, "end", text="[不满足时]",
                                                   values=("", ""))
                self._branch_label_items.add(else_label)
                self._branch_label_to_list[else_label] = step.else_children
                self._insert_steps_recursive(step.else_children, else_label, f"{step_num}.")

                # 展开if节点
                self.step_tree.item(item, open=True)

            elif step.step_type in ('for_loop', 'while_image'):
                self._insert_steps_recursive(step.children, item, f"{step_num}.")
                self.step_tree.item(item, open=True)

    def _get_selected_step_info(self):
        """获取当前选中步骤的信息，返回 (step, parent_list, index) 或 None"""
        selection = self.step_tree.selection()
        if not selection:
            return None
        item = selection[0]
        if item in self._branch_label_items:
            return None
        step = self._item_to_step.get(item)
        parent_list = self._item_to_parent_list.get(item)
        if step is None or parent_list is None:
            return None
        try:
            index = parent_list.index(step)
        except ValueError:
            return None
        return step, parent_list, index

    def get_step_type_name(self, step_type):
        """获取步骤类型名称"""
        type_names = {
            "mouse_click": "鼠标点击",
            "keyboard_press": "键盘按键",
            "image_search": "图片搜索",
            "wait": "等待",
            "if_image": "条件判断",
            "for_loop": "循环(N次)",
            "while_image": "条件循环",
            "break_loop": "跳出循环",
            "random_delay": "随机延迟",
            "mouse_scroll": "鼠标滚轮",
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
        elif step.step_type == "if_image":
            img = os.path.basename(step.params.get('image_path', ''))
            return f"如果找到 {img}"
        elif step.step_type == "for_loop":
            return f"循环 {step.params.get('count', 1)} 次"
        elif step.step_type == "while_image":
            cond = "存在" if step.params.get('condition', 'exists') == 'exists' else "不存在"
            img = os.path.basename(step.params.get('image_path', ''))
            return f"当 {img} {cond} 时循环"
        elif step.step_type == "break_loop":
            return "跳出当前循环"
        elif step.step_type == "random_delay":
            return f"随机等待 {step.params.get('min_time', 0.5)}-{step.params.get('max_time', 2.0)} 秒"
        elif step.step_type == "mouse_scroll":
            clicks = step.params.get('clicks', 3)
            direction = "向上" if clicks > 0 else "向下"
            return f"滚轮{direction} {abs(clicks)} 格"
        return "未知步骤"

    # ==================== 事件处理方法 ====================

    def on_step_select(self, event):
        """步骤选择事件"""
        info = self._get_selected_step_info()
        if info:
            step, parent_list, index = info
            self.load_step_to_editor(step)

    def on_step_double_click(self, event):
        """步骤双击事件"""
        self.edit_step()

    def load_step_to_editor(self, step):
        """加载步骤到编辑器"""
        # 清空所有输入
        self.clear_editor()

        # 动态显示对应tab
        if hasattr(self, 'edit_page_manager') and hasattr(self.edit_page_manager, 'show_tab_for_step_type'):
            self.edit_page_manager.show_tab_for_step_type(step.step_type)

        # 根据步骤类型加载数据
        if step.step_type == "mouse_click":
            self.mouse_button_var.set(step.params.get('button', 'left'))
            self.mouse_x_var.set(str(step.params.get('x', 0)))
            self.mouse_y_var.set(str(step.params.get('y', 0)))
            self.click_count_var.set(str(step.params.get('click_count', 1)))
            self.click_interval_var.set(str(step.params.get('click_interval', 0.1)))

        elif step.step_type == "keyboard_press":
            self.key_var.set(step.params.get('key', ''))
            self.key_type_var.set(step.params.get('key_type', 'single'))
            self.text_var.set(step.params.get('text', ''))
            self.key_duration_var.set(str(step.params.get('duration', 0.05)))

        elif step.step_type == "image_search":
            self.search_image_var.set(step.params.get('image_path', ''))
            self.confidence_var.set(str(step.params.get('confidence', 0.8)))
            self.search_offset_x_var.set(str(step.params.get('offset_x', 0)))
            self.search_offset_y_var.set(str(step.params.get('offset_y', 0)))
            self.search_timeout_var.set(str(step.params.get('timeout', 5)))
            self.after_found_var.set(step.params.get('action', 'none'))
            self.search_region_var.set(step.params.get('search_region', 'full'))
            self.region_x1_var.set(str(step.params.get('region_x1', 0)))
            self.region_y1_var.set(str(step.params.get('region_y1', 0)))
            self.region_x2_var.set(str(step.params.get('region_x2', 100)))
            self.region_y2_var.set(str(step.params.get('region_y2', 100)))
            self.save_region_var.set(step.params.get('save_region', False))
            self.use_saved_region_var.set(step.params.get('use_saved_region', False))
            self.on_search_region_change()
            # 排除区域
            if hasattr(self, 'exclude_enabled_var'):
                self.exclude_enabled_var.set(step.params.get('exclude_enabled', False))
                self._exclude_items_data = list(step.params.get('exclude_items', []))
                self.edit_page_manager._refresh_exclude_listbox()

        elif step.step_type == "wait":
            self.wait_type_var.set(step.params.get('wait_type', 'time'))
            self.wait_time_var.set(str(step.params.get('time', 1.0)))
            self.wait_image_var.set(step.params.get('wait_image', ''))
            if hasattr(self, 'wait_timeout_var'):
                self.wait_timeout_var.set(str(step.params.get('timeout', 10)))

        elif step.step_type == "if_image":
            self.if_image_var.set(step.params.get('image_path', ''))
            self.if_confidence_var.set(str(step.params.get('confidence', 0.8)))
            self.if_timeout_var.set(str(step.params.get('timeout', 3)))

        elif step.step_type == "for_loop":
            self.loop_count_var.set(str(step.params.get('count', 3)))

        elif step.step_type == "while_image":
            self.while_image_var.set(step.params.get('image_path', ''))
            self.while_confidence_var.set(str(step.params.get('confidence', 0.8)))
            self.while_condition_var.set(step.params.get('condition', 'exists'))
            self.while_max_iter_var.set(str(step.params.get('max_iterations', 100)))

        elif step.step_type == "break_loop":
            pass  # 无参数

        elif step.step_type == "random_delay":
            self.random_min_var.set(str(step.params.get('min_time', 0.5)))
            self.random_max_var.set(str(step.params.get('max_time', 2.0)))

        elif step.step_type == "mouse_scroll":
            self.scroll_x_var.set(str(step.params.get('x', 0)))
            self.scroll_y_var.set(str(step.params.get('y', 0)))
            self.scroll_clicks_var.set(str(step.params.get('clicks', 3)))

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
            self.key_type_var.set("single")
            self.text_var.set("")
            self.key_duration_var.set("0.05")
            self.search_image_var.set("")
            self.confidence_var.set("0.8")
            self.search_offset_x_var.set("0")
            self.search_offset_y_var.set("0")
            self.search_timeout_var.set("5")
            self.after_found_var.set("none")
            self.search_region_var.set("full")
            self.region_x1_var.set("0")
            self.region_y1_var.set("0")
            self.region_x2_var.set("100")
            self.region_y2_var.set("100")
            self.save_region_var.set(False)
            self.use_saved_region_var.set(False)
        if hasattr(self, 'exclude_enabled_var'):
            self.exclude_enabled_var.set(False)
            self._exclude_items_data = []
            if hasattr(self, 'edit_page_manager') and hasattr(self.edit_page_manager, '_refresh_exclude_listbox'):
                self.edit_page_manager._refresh_exclude_listbox()
        if hasattr(self, 'mouse_button_var'):
            self.wait_time_var.set("1.0")
            self.wait_type_var.set("time")
            self.wait_image_var.set("")
            if hasattr(self, 'wait_timeout_var'):
                self.wait_timeout_var.set("10")
        # 新步骤类型变量
        if hasattr(self, 'if_image_var'):
            self.if_image_var.set("")
            self.if_confidence_var.set("0.8")
            self.if_timeout_var.set("3")
        if hasattr(self, 'loop_count_var'):
            self.loop_count_var.set("3")
        if hasattr(self, 'while_image_var'):
            self.while_image_var.set("")
            self.while_confidence_var.set("0.8")
            self.while_condition_var.set("exists")
            self.while_max_iter_var.set("100")
        if hasattr(self, 'random_min_var'):
            self.random_min_var.set("0.5")
            self.random_max_var.set("2.0")
        if hasattr(self, 'scroll_x_var'):
            self.scroll_x_var.set("0")
            self.scroll_y_var.set("0")
            self.scroll_clicks_var.set("3")
        # 通用
        if hasattr(self, 'description_var'):
            self.description_var.set("")
            self.enabled_var.set(True)

    # ==================== 工具方法 ====================

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
            self.search_image_var.set(filename)

    def screenshot_get_search_image(self):
        """通过截图获取搜索图片"""
        self.screenshot_manager.screenshot_get_search_image()

    def on_search_region_change(self):
        """处理搜索区域选择变化"""
        if self.search_region_var.get() == "region":
            self.region_frame.grid()
        else:
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
        """更新状态（主线程调用）"""
        self.status_var.set(message)

    def _thread_safe_status(self, message):
        """线程安全的状态更新（供子线程回调使用）"""
        self.root.after(0, lambda: self.status_var.set(message))

    # ==================== 步骤操作方法 ====================

    def _determine_target_list(self):
        """确定新步骤应添加到哪个列表。

        - 如果选中的是分支标签（[满足条件时]/[不满足时]），添加到对应分支
        - 否则添加到顶层列表

        返回 (target_list, description_suffix)
        """
        selection = self.step_tree.selection()
        if selection:
            item = selection[0]
            # 如果选中的是分支标签
            if item in self._branch_label_items:
                target_list = self._branch_label_to_list.get(item)
                if target_list is not None:
                    return target_list, " (到分支)"
        return self.steps, ""

    def add_step(self):
        """添加步骤"""
        dialog = StepTypeDialog(self.root)
        self.root.wait_window(dialog.dialog)
        if dialog.result:
            step_type = dialog.result
            step = ActionStep(step_type)
            target_list, suffix = self._determine_target_list()
            target_list.append(step)
            self.refresh_step_list()
            self.update_status(f"已添加 {self.get_step_type_name(step_type)} 步骤{suffix}")

    def add_child_step(self):
        """添加子步骤到容器步骤的children"""
        info = self._get_selected_step_info()
        if not info:
            messagebox.showwarning("提示", "请先选择一个容器步骤（条件判断/循环）")
            return
        step, parent_list, index = info
        if step.step_type not in CONTAINER_STEP_TYPES:
            messagebox.showwarning("提示", "只有条件判断、循环类步骤才能添加子步骤")
            return

        dialog = StepTypeDialog(self.root)
        self.root.wait_window(dialog.dialog)
        if dialog.result:
            child = ActionStep(dialog.result)
            step.children.append(child)
            self.refresh_step_list()
            self.update_status(f"已添加子步骤 {self.get_step_type_name(dialog.result)}")

    def add_else_step(self):
        """添加步骤到if_image的else_children"""
        info = self._get_selected_step_info()
        if not info:
            messagebox.showwarning("提示", "请先选择一个条件判断步骤")
            return
        step, parent_list, index = info
        if step.step_type != 'if_image':
            messagebox.showwarning("提示", "只有条件判断步骤才能添加\"否则\"分支")
            return

        dialog = StepTypeDialog(self.root)
        self.root.wait_window(dialog.dialog)
        if dialog.result:
            child = ActionStep(dialog.result)
            step.else_children.append(child)
            self.refresh_step_list()
            self.update_status(f"已添加否则分支步骤 {self.get_step_type_name(dialog.result)}")

    def edit_step(self):
        """编辑步骤"""
        info = self._get_selected_step_info()
        if info:
            step, parent_list, index = info
            self._editing_step = step
            self._editing_parent_list = parent_list
            self.load_step_to_editor(step)

    def delete_step(self):
        """删除步骤"""
        info = self._get_selected_step_info()
        if info:
            step, parent_list, index = info
            desc = step.description or self.get_default_description(step)
            if messagebox.askyesno("确认删除", f"确定要删除步骤「{desc}」吗？"):
                parent_list.remove(step)
                self.refresh_step_list()
                self.update_status("已删除步骤")

    def move_step_up(self):
        """上移步骤"""
        info = self._get_selected_step_info()
        if info:
            step, parent_list, index = info
            if index > 0:
                parent_list[index], parent_list[index - 1] = parent_list[index - 1], parent_list[index]
                self.refresh_step_list()
                self.update_status("步骤已上移")

    def move_step_down(self):
        """下移步骤"""
        info = self._get_selected_step_info()
        if info:
            step, parent_list, index = info
            if index < len(parent_list) - 1:
                parent_list[index], parent_list[index + 1] = parent_list[index + 1], parent_list[index]
                self.refresh_step_list()
                self.update_status("步骤已下移")

    def test_current_step(self):
        """测试当前步骤"""
        step = self.get_current_step_from_editor()
        if step:
            self.automation_runner.test_single_step(step)

    def save_current_step(self):
        """保存当前步骤"""
        new_step = self.get_current_step_from_editor()
        if not new_step:
            return

        info = self._get_selected_step_info()
        if info:
            old_step, parent_list, index = info
            # 保留子步骤（仅当新旧都是容器类型时）
            if old_step.step_type in CONTAINER_STEP_TYPES and new_step.step_type in CONTAINER_STEP_TYPES:
                new_step.children = old_step.children
                new_step.else_children = old_step.else_children
            parent_list[index] = new_step
            self.refresh_step_list()
            self.update_status("已保存步骤")

    def cancel_edit(self):
        """取消编辑"""
        self.clear_editor()
        self.update_status("已取消编辑")

    def get_current_step_from_editor(self):
        """从编辑器获取当前步骤"""
        # 通过当前可见的tab确定步骤类型
        current_tab_id = self.edit_notebook.select()
        if not current_tab_id:
            return None

        # 查找当前tab对应的步骤类型
        current_tab_index = None
        if hasattr(self, 'edit_page_manager') and hasattr(self.edit_page_manager, '_all_tabs'):
            for i, (tab_id, tab_text) in enumerate(self.edit_page_manager._all_tabs):
                if tab_id == current_tab_id:
                    current_tab_index = i
                    break

        if current_tab_index is None:
            # 回退：使用notebook的index方法
            current_tab_index = self.edit_notebook.index(current_tab_id)

        if current_tab_index == 0:  # 鼠标点击
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

        elif current_tab_index == 1:  # 键盘按键
            key = self.key_var.get()
            key_type = self.key_type_var.get()
            text = self.text_var.get()

            if key_type == 'text':
                if not text:
                    messagebox.showerror("错误", "请输入文本")
                    return None
            elif not key:
                messagebox.showerror("错误", "请输入按键")
                return None

            try:
                duration = float(self.key_duration_var.get())
                step = ActionStep("keyboard_press", key=key, key_type=key_type,
                                text=text, duration=duration)
                step.description = self.description_var.get()
                step.enabled = self.enabled_var.get()
                return step
            except ValueError:
                messagebox.showerror("错误", "请输入有效的持续时间")
                return None

        elif current_tab_index == 2:  # 图片搜索
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

                search_region = self.search_region_var.get()
                region_x1 = int(self.region_x1_var.get()) if self.region_x1_var.get() else 0
                region_y1 = int(self.region_y1_var.get()) if self.region_y1_var.get() else 0
                region_x2 = int(self.region_x2_var.get()) if self.region_x2_var.get() else 100
                region_y2 = int(self.region_y2_var.get()) if self.region_y2_var.get() else 100
                save_region = self.save_region_var.get()
                use_saved_region = self.use_saved_region_var.get()

                # 排除区域参数
                exclude_enabled = self.exclude_enabled_var.get() if hasattr(self, 'exclude_enabled_var') else False
                exclude_items = list(self._exclude_items_data) if hasattr(self, '_exclude_items_data') else []

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
                                use_saved_region=use_saved_region,
                                exclude_enabled=exclude_enabled,
                                exclude_items=exclude_items)
                step.description = self.description_var.get()
                step.enabled = self.enabled_var.get()
                return step
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数值")
                return None

        elif current_tab_index == 3:  # 等待
            try:
                wait_type = self.wait_type_var.get()
                wait_time = float(self.wait_time_var.get())
                wait_image = self.wait_image_var.get()
                wait_timeout = float(self.wait_timeout_var.get()) if hasattr(self, 'wait_timeout_var') and self.wait_timeout_var.get() else 10.0

                if wait_type == 'image' and not wait_image:
                    messagebox.showerror("错误", "请选择等待图片")
                    return None

                step = ActionStep("wait", wait_type=wait_type, time=wait_time,
                                wait_image=wait_image, timeout=wait_timeout)
                step.description = self.description_var.get()
                step.enabled = self.enabled_var.get()
                return step
            except ValueError:
                messagebox.showerror("错误", "请输入有效的等待时间")
                return None

        elif current_tab_index == 4:  # 条件判断
            image_path = self.if_image_var.get()
            if not image_path:
                messagebox.showerror("错误", "请选择条件判断的目标图片")
                return None
            try:
                confidence = float(self.if_confidence_var.get())
                timeout = float(self.if_timeout_var.get())
                step = ActionStep("if_image", image_path=image_path,
                                confidence=confidence, timeout=timeout)
                step.description = self.description_var.get()
                step.enabled = self.enabled_var.get()
                return step
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数值")
                return None

        elif current_tab_index == 5:  # 循环(N次)
            try:
                count = int(self.loop_count_var.get())
                if count < 1:
                    messagebox.showerror("错误", "循环次数必须大于0")
                    return None
                step = ActionStep("for_loop", count=count)
                step.description = self.description_var.get()
                step.enabled = self.enabled_var.get()
                return step
            except ValueError:
                messagebox.showerror("错误", "请输入有效的循环次数")
                return None

        elif current_tab_index == 6:  # 条件循环
            image_path = self.while_image_var.get()
            if not image_path:
                messagebox.showerror("错误", "请选择条件循环的目标图片")
                return None
            try:
                confidence = float(self.while_confidence_var.get())
                condition = self.while_condition_var.get()
                max_iterations = int(self.while_max_iter_var.get())
                step = ActionStep("while_image", image_path=image_path,
                                confidence=confidence, condition=condition,
                                max_iterations=max_iterations)
                step.description = self.description_var.get()
                step.enabled = self.enabled_var.get()
                return step
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数值")
                return None

        elif current_tab_index == 7:  # 跳出循环
            step = ActionStep("break_loop")
            step.description = self.description_var.get()
            step.enabled = self.enabled_var.get()
            return step

        elif current_tab_index == 8:  # 随机延迟
            try:
                min_time = float(self.random_min_var.get())
                max_time = float(self.random_max_var.get())
                if min_time > max_time:
                    messagebox.showerror("错误", "最小时间不能大于最大时间")
                    return None
                step = ActionStep("random_delay", min_time=min_time, max_time=max_time)
                step.description = self.description_var.get()
                step.enabled = self.enabled_var.get()
                return step
            except ValueError:
                messagebox.showerror("错误", "请输入有效的时间")
                return None

        elif current_tab_index == 9:  # 鼠标滚轮
            try:
                x = int(self.scroll_x_var.get())
                y = int(self.scroll_y_var.get())
                clicks = int(self.scroll_clicks_var.get())
                step = ActionStep("mouse_scroll", x=x, y=y, clicks=clicks)
                step.description = self.description_var.get()
                step.enabled = self.enabled_var.get()
                return step
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数值")
                return None

        return None

    # ==================== 执行相关方法 ====================

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
            self.automation_runner.start_execution(self.steps, loop_mode=False)
            self.update_status("开始单次执行...")
        else:
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
            self.is_running = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)

            if self.execution_mode_var.get() == "单次执行":
                self.update_status("单次执行完成")
            else:
                self.update_status("循环执行已停止")
        elif self.is_running:
            self.root.after(100, self.check_execution_status)

    def show_help(self):
        """显示帮助"""
        help_text = """
按键小精灵 v2.0

基本操作：
1. 鼠标点击：模拟鼠标左键、右键点击
2. 键盘按键：模拟键盘按键和文本输入
3. 图片搜索：在屏幕上搜索指定图片并执行动作
4. 等待：等待指定时间或图片出现

流程控制：
5. 条件判断：如果找到图片则执行子步骤，否则执行否则分支
6. 循环(N次)：重复执行子步骤指定次数
7. 条件循环：当图片存在/不存在时持续循环
8. 跳出循环：立即跳出最近的循环

高级操作：
9. 随机延迟：在指定范围内随机等待
10. 鼠标滚轮：在指定位置滚动鼠标

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
