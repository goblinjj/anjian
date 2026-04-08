#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
魔力宝贝制造助手 - 主界面
"""

import tkinter as tk
from tkinter import ttk, messagebox
import time
import os

from recipe_manager import RecipeManager
from recipe_dialog import RecipeDialog
from settings_dialog import SettingsDialog, load_settings
from window_manager import WindowManager
from backpack_reader import BackpackReader
from digit_recognizer import DigitRecognizer
from craft_engine import CraftEngine
from hotkey_manager import HotkeyManager
from hotkey_dialog import HotkeySettingsDialog
from tool_dialog import (AutoEncounterDialog, LoopHealingDialog,
                         load_tool_config)
from tool_scripts import AutoEncounterEngine, LoopHealingEngine, GetMaterialEngine
from screenshot_util import take_screenshot


# 工具描述信息
TOOL_INFO = {
    'auto_encounter': {
        'name': '自动遇敌',
        'desc': '在绑定窗口中心的两个自定义偏移点之间循环点击，用于自动遇敌。\n'
                '流程: 点1点击 → 点2点击 → 循环',
    },
    'loop_healing': {
        'name': '循环医疗',
        'desc': '循环查找并点击治疗技能，然后按偏移列表依次点击队员位置进行治疗。\n'
                '流程: 点击技能 → 定位队员 → 依次点击偏移位置 → 循环',
    },
    'get_material': {
        'name': '获取材料',
        'desc': '按快捷键执行一次获取材料操作（全局，可与其他功能同时使用）。\n'
                '流程: 双击当前位置 → 查找并点击材料图片 → Ctrl+E 打开背包',
    },
}


class CraftAssistantGUI:
    """魔力宝贝制造助手主界面"""

    def __init__(self, root):
        self.root = root
        self.root.title("魔力宝贝制造助手")
        self.root.geometry("900x600")
        self.root.minsize(800, 500)

        self.is_running = False
        self.selected_recipe = None
        self._selected_type = None      # 'recipe' / 'tool' / None
        self._selected_tool_id = None   # 'auto_encounter' / 'loop_healing'
        self._tool_stop_callback = None
        self._active_tool_engine = None
        self._in_mini_mode = False
        self._saved_geometry = None

        # 初始化管理器
        self.settings = load_settings()
        self.recipe_manager = RecipeManager('recipes')
        self.window_manager = WindowManager()
        self.digit_recognizer = DigitRecognizer('templates/digits')
        self.backpack_reader = BackpackReader(
            self.digit_recognizer, self.settings, self._log_message)
        self.craft_engine = CraftEngine(
            self.window_manager, self.backpack_reader, self._log_message
        )
        self.hotkey_manager = HotkeyManager(self)
        self.get_material_engine = GetMaterialEngine(
            self.window_manager, self._log_message)

        # 创建界面
        self._create_widgets()

        # 加载列表
        self._refresh_tree()

        # 启动热键
        self.hotkey_manager.start_global_hotkey_listener()

        # 窗口关闭处理
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_widgets(self):
        # ── 主内容区 ──
        self._main_frame = ttk.Frame(self.root)
        self._main_frame.pack(fill=tk.BOTH, expand=True)

        # 顶部: 窗口绑定 + 设置
        top_frame = ttk.Frame(self._main_frame, padding=5)
        top_frame.pack(fill=tk.X)

        ttk.Label(top_frame, text="游戏窗口:").pack(side=tk.LEFT)
        self.bind_label = ttk.Label(top_frame, text="未绑定", foreground='red')
        self.bind_label.pack(side=tk.LEFT, padx=10)
        ttk.Button(top_frame, text="点击选择窗口",
                  command=self._pick_window).pack(side=tk.LEFT, padx=5)

        ttk.Button(top_frame, text="设置",
                  command=self._open_settings).pack(side=tk.RIGHT, padx=5)
        ttk.Button(top_frame, text="快捷键",
                  command=self._open_hotkey_settings).pack(side=tk.RIGHT, padx=5)

        ttk.Separator(self._main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X)

        # 主体区域
        body = ttk.PanedWindow(self._main_frame, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ── 左侧: 分类列表 (Treeview) ──
        left_frame = ttk.Frame(body, width=200)
        body.add(left_frame, weight=1)

        self.tree = ttk.Treeview(left_frame, show='tree', selectmode='browse')
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind('<<TreeviewSelect>>', self._on_tree_select)

        # 分类根节点
        self._recipe_node = self.tree.insert(
            '', 'end', text='  配方', open=True, tags=('category',))
        self._tool_node = self.tree.insert(
            '', 'end', text='  工具', open=True, tags=('category',))

        # 固定的工具子项
        self.tree.insert(self._tool_node, 'end', text='自动遇敌',
                         values=('auto_encounter',), tags=('tool',))
        self.tree.insert(self._tool_node, 'end', text='循环医疗',
                         values=('loop_healing',), tags=('tool',))
        self.tree.insert(self._tool_node, 'end', text='获取材料',
                         values=('get_material',), tags=('tool',))

        # 分类样式
        self.tree.tag_configure('category', font=('', 10, 'bold'))

        # 按钮行
        btn_row = ttk.Frame(left_frame)
        btn_row.pack(fill=tk.X, pady=5)
        self.new_btn = ttk.Button(
            btn_row, text="新建配方", width=8, command=self._new_recipe)
        self.new_btn.pack(side=tk.LEFT, padx=2)
        self.edit_btn = ttk.Button(
            btn_row, text="编辑", width=6, command=self._on_edit)
        self.edit_btn.pack(side=tk.LEFT, padx=2)
        self.delete_btn = ttk.Button(
            btn_row, text="删除", width=6, command=self._delete_recipe,
            state=tk.DISABLED)
        self.delete_btn.pack(side=tk.LEFT, padx=2)

        # ── 右侧: 信息 + 控制 ──
        right_frame = ttk.Frame(body)
        body.add(right_frame, weight=3)

        # 信息区
        self.info_frame = ttk.LabelFrame(right_frame, text="详情", padding=10)
        self.info_frame.pack(fill=tk.X, pady=(0, 10))

        self.info_label = ttk.Label(
            self.info_frame, text="请选择配方或工具", foreground='gray')
        self.info_label.pack(anchor=tk.W)

        # 控制按钮
        ctrl_frame = ttk.Frame(right_frame)
        ctrl_frame.pack(fill=tk.X, pady=5)

        self.start_btn = ttk.Button(
            ctrl_frame, text="开始", command=self._on_start)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(
            ctrl_frame, text="停止", command=self._on_stop, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.stats_label = ttk.Label(ctrl_frame, text="")
        self.stats_label.pack(side=tk.RIGHT, padx=10)

        # 日志区
        log_frame = ttk.LabelFrame(right_frame, text="运行日志", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(
            log_frame, height=15, state=tk.DISABLED, wrap=tk.WORD)
        log_scrollbar = ttk.Scrollbar(
            log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 状态栏
        status_frame = ttk.Frame(self._main_frame, padding=3)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Separator(self._main_frame, orient=tk.HORIZONTAL).pack(
            fill=tk.X, side=tk.BOTTOM)

        self.status_label = ttk.Label(status_frame, text="就绪")
        self.status_label.pack(side=tk.LEFT)

        hotkey_text = self.hotkey_manager.get_status_text()
        self.hotkey_label = ttk.Label(
            status_frame, text=f"热键: {hotkey_text}")
        self.hotkey_label.pack(side=tk.RIGHT)

        # ── 迷你模式区（初始隐藏）──
        self._mini_frame = ttk.Frame(self.root, padding=10)

        self._mini_task_label = ttk.Label(
            self._mini_frame, text="", font=('', 11, 'bold'))
        self._mini_task_label.pack(anchor=tk.W, pady=(0, 5))

        self._mini_step_label = ttk.Label(
            self._mini_frame, text="准备中...", foreground='gray',
            wraplength=350)
        self._mini_step_label.pack(anchor=tk.W, pady=(0, 5))

        self._mini_stats_label = ttk.Label(self._mini_frame, text="")
        self._mini_stats_label.pack(anchor=tk.W, pady=(0, 8))

        mini_btn_frame = ttk.Frame(self._mini_frame)
        mini_btn_frame.pack(fill=tk.X)

        self._mini_stop_btn = ttk.Button(
            mini_btn_frame, text="停止", command=self._mini_stop)
        self._mini_stop_btn.pack(side=tk.LEFT)

        self._mini_hotkey_label = ttk.Label(
            mini_btn_frame,
            text=f"停止热键: {self.hotkey_manager.global_stop_hotkey}",
            foreground='gray')
        self._mini_hotkey_label.pack(side=tk.RIGHT)

    # ── 分类列表 ──

    def _refresh_tree(self):
        """刷新配方子项"""
        # 清除旧配方节点
        for child in self.tree.get_children(self._recipe_node):
            self.tree.delete(child)
        # 重新插入
        for name in self.recipe_manager.list_recipes():
            self.tree.insert(
                self._recipe_node, 'end', text=name, tags=('recipe',))

    def _on_tree_select(self, event):
        """树列表选中事件"""
        sel = self.tree.selection()
        if not sel:
            return
        item = sel[0]

        # 点击分类根节点
        if item in (self._recipe_node, self._tool_node):
            self._selected_type = None
            self._selected_tool_id = None
            self.selected_recipe = None
            self._update_buttons()
            self.info_frame.config(text="详情")
            self.info_label.config(
                text="请选择配方或工具", foreground='gray')
            return

        parent = self.tree.parent(item)

        if parent == self._recipe_node:
            # 选中配方
            name = self.tree.item(item, 'text')
            self._selected_type = 'recipe'
            self._selected_tool_id = None
            try:
                self.selected_recipe = self.recipe_manager.load_recipe(name)
                self._show_recipe_info(self.selected_recipe)
            except Exception as e:
                self.selected_recipe = None
                self.info_label.config(text=f"加载失败: {e}")
            self._update_buttons()

        elif parent == self._tool_node:
            # 选中工具
            values = self.tree.item(item, 'values')
            tool_id = values[0] if values else ''
            self._selected_type = 'tool'
            self._selected_tool_id = tool_id
            self.selected_recipe = None
            self._show_tool_info(tool_id)
            self._update_buttons()

    def _update_buttons(self):
        """根据选中类型更新按钮状态"""
        if self._selected_type == 'recipe':
            self.edit_btn.config(text="编辑", state=tk.NORMAL)
            self.delete_btn.config(state=tk.NORMAL)
            self.start_btn.config(text="开始制造")
            self.info_frame.config(text="当前配方")
        elif self._selected_type == 'tool':
            self.edit_btn.config(text="配置", state=tk.NORMAL)
            self.delete_btn.config(state=tk.DISABLED)
            if self._selected_tool_id == 'get_material':
                self.start_btn.config(text="执行一次")
            else:
                self.start_btn.config(text="开始执行")
            self.info_frame.config(text="当前工具")
        else:
            self.edit_btn.config(text="编辑", state=tk.DISABLED)
            self.delete_btn.config(state=tk.DISABLED)
            self.start_btn.config(text="开始")

    def _on_edit(self):
        """编辑/配置按钮"""
        if self._selected_type == 'recipe':
            self._edit_recipe()
        elif self._selected_type == 'tool':
            self._configure_tool()

    def _on_start(self):
        """统一开始按钮"""
        if self._selected_type == 'recipe':
            self.start_craft()
        elif self._selected_type == 'tool':
            self._start_selected_tool()

    def _on_stop(self):
        """统一停止按钮"""
        if self.is_running:
            self.stop_craft()
        elif self._active_tool_engine:
            self._stop_tool()

    # 供 HotkeyManager 调用的通用启动
    def start_selected(self):
        """热键触发：启动当前选中项"""
        self._on_start()

    # ── 显示信息 ──

    def _show_recipe_info(self, recipe):
        """显示配方详情"""
        lines = [f"配方: {recipe['name']}"]
        for i, mat in enumerate(recipe.get('materials', [])):
            lines.append(
                f"  材料{i+1}: {mat['image_file']} x{mat['quantity']}")
        lines.append(f"等待时间: {recipe.get('wait_time', 3.0)} 秒")
        self.info_label.config(text='\n'.join(lines), foreground='black')

    def _show_tool_info(self, tool_id):
        """显示工具详情及已保存的配置"""
        info = TOOL_INFO.get(tool_id, {})
        config = load_tool_config()
        lines = [f"工具: {info.get('name', tool_id)}",
                 info.get('desc', '')]

        if tool_id == 'auto_encounter':
            cfg = config.get('auto_encounter', {})
            p1x = cfg.get('point1_x', -200)
            p1y = cfg.get('point1_y', 200)
            p2x = cfg.get('point2_x', 200)
            p2y = cfg.get('point2_y', -200)
            delay = cfg.get('click_delay', 500)
            lines.append(f"\n点1偏移: ({p1x}, {p1y})")
            lines.append(f"点2偏移: ({p2x}, {p2y})")
            lines.append(f"点击延迟: {delay}ms")

        elif tool_id == 'loop_healing':
            cfg = config.get('loop_healing', {})
            skill = cfg.get('skill_image', '')
            member = cfg.get('member_image', '')
            steps = cfg.get('steps', [])
            skill_ok = bool(skill) and os.path.exists(skill)
            member_ok = bool(member) and os.path.exists(member)
            lines.append(f"\n治疗技能: {'已设置' if skill_ok else '未设置'}")
            lines.append(f"队员定位: {'已设置' if member_ok else '未设置'}")
            # 显示步骤摘要
            skill_count = sum(1 for s in steps if s['type'] == 'skill')
            member_count = sum(1 for s in steps if s['type'] == 'member')
            delay_count = sum(1 for s in steps if s['type'] == 'delay')
            summary = f"技能x{skill_count}, 队员x{member_count}"
            if delay_count:
                summary += f", 延迟x{delay_count}"
            lines.append(f"执行步骤: {len(steps)} 个 ({summary})")
            if not (skill_ok and member_ok and steps):
                lines.append("\n(需先点击「配置」截取图片并添加步骤)")

        elif tool_id == 'get_material':
            mat = self.settings.get('get_material_image', '')
            mat_ok = bool(mat) and os.path.exists(mat)
            hotkey = self.hotkey_manager.get_material_hotkey
            lines.append(f"\n材料图片: {'已设置' if mat_ok else '未设置'}")
            lines.append(f"触发快捷键: {hotkey}")
            if not mat_ok:
                lines.append("\n(需先在「设置」中截取获取材料图片)")

        self.info_label.config(text='\n'.join(lines), foreground='black')

    # ── 窗口绑定 ──

    def _pick_window(self):
        """选择游戏窗口"""
        self.bind_label.config(text="请点击游戏窗口...", foreground='orange')
        self.root.iconify()

        def on_picked(hwnd, title):
            self.root.after(0, self._on_window_picked, hwnd, title)

        self.window_manager.start_pick_window(on_picked)

    def _on_window_picked(self, hwnd, title):
        """窗口选择完成回调"""
        self.root.deiconify()
        if hwnd:
            self.bind_label.config(
                text=f"已绑定: {title} (0x{hwnd:X})",
                foreground='green')
        else:
            self.bind_label.config(text="绑定失败", foreground='red')

    # ── 配方管理 ──

    def _new_recipe(self):
        """新建配方"""
        dialog = RecipeDialog(
            self.root, self.recipe_manager, self._screenshot_region)
        if dialog.result:
            self._refresh_tree()

    def _edit_recipe(self):
        """编辑配方"""
        if not self.selected_recipe:
            messagebox.showinfo("提示", "请先选择一个配方")
            return
        dialog = RecipeDialog(self.root, self.recipe_manager,
                              self._screenshot_region, self.selected_recipe)
        if dialog.result:
            self.selected_recipe = dialog.result
            self._refresh_tree()
            self._show_recipe_info(self.selected_recipe)

    def _delete_recipe(self):
        """删除配方"""
        if not self.selected_recipe:
            messagebox.showinfo("提示", "请先选择一个配方")
            return
        name = self.selected_recipe['name']
        if messagebox.askyesno("确认", f"确定删除配方「{name}」？"):
            self.recipe_manager.delete_recipe(name)
            self.selected_recipe = None
            self._selected_type = None
            self.info_frame.config(text="详情")
            self.info_label.config(
                text="请选择配方或工具", foreground='gray')
            self._update_buttons()
            self._refresh_tree()

    # ── 制造控制 ──

    def start_craft(self):
        """开始制造"""
        if self.is_running or self._active_tool_engine:
            return
        if not self.selected_recipe:
            messagebox.showwarning("提示", "请先选择一个配方")
            return
        if not self.window_manager.is_window_valid():
            messagebox.showwarning("提示", "请先绑定游戏窗口")
            return

        self.is_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_label.config(text="制造中...")

        self._enter_mini_mode(f"制造: {self.selected_recipe['name']}")

        engine_settings = dict(self.settings)
        recipe_dir = self.recipe_manager.get_recipe_dir(
            self.selected_recipe['name'])
        engine_settings['recipe_dir'] = recipe_dir

        self.craft_engine.start(self.selected_recipe, engine_settings)
        self._update_stats()

    def stop_craft(self):
        """停止制造"""
        self.craft_engine.stop()
        self.is_running = False
        self._exit_mini_mode()

    def _update_stats(self):
        """定时更新统计信息"""
        if self.craft_engine.is_running:
            stats_text = (
                f"成功: {self.craft_engine.success_count} 次 | "
                f"失败: {self.craft_engine.fail_count} 次")
            self.stats_label.config(text=stats_text)
            if self._in_mini_mode:
                self._mini_stats_label.config(text=stats_text)
            self.root.after(1000, self._update_stats)
        else:
            self.is_running = False
            stats_text = (
                f"完成 - 成功: {self.craft_engine.success_count} 次 | "
                f"失败: {self.craft_engine.fail_count} 次")
            self.stats_label.config(text=stats_text)
            self._exit_mini_mode()

    # ── 工具脚本 ──

    def _configure_tool(self):
        """打开工具配置对话框"""
        if not self._selected_tool_id:
            return
        if self._selected_tool_id == 'auto_encounter':
            dialog = AutoEncounterDialog(self.root)
            if dialog.result:
                self._show_tool_info('auto_encounter')
        elif self._selected_tool_id == 'loop_healing':
            dialog = LoopHealingDialog(self.root, self._screenshot_region)
            if dialog.result:
                self._show_tool_info('loop_healing')
        elif self._selected_tool_id == 'get_material':
            self._open_settings()
            self._show_tool_info('get_material')

    def _start_selected_tool(self):
        """启动当前选中的工具"""
        if not self.window_manager.is_window_valid():
            messagebox.showwarning("提示", "请先绑定游戏窗口")
            return

        # 获取材料是全局功能，不受其他任务影响
        if self._selected_tool_id == 'get_material':
            self._trigger_get_material()
            return

        if self.is_running or self._active_tool_engine:
            messagebox.showwarning("提示", "请先停止当前任务")
            return

        if self._selected_tool_id == 'auto_encounter':
            self._start_auto_encounter()
        elif self._selected_tool_id == 'loop_healing':
            self._start_loop_healing()

    def _start_auto_encounter(self):
        """启动自动遇敌（直接使用已保存配置）"""
        config = load_tool_config().get('auto_encounter', {})

        engine = AutoEncounterEngine(self.window_manager, self._log_message)
        engine.start(
            point1_x=config.get('point1_x', -200),
            point1_y=config.get('point1_y', 200),
            point2_x=config.get('point2_x', 200),
            point2_y=config.get('point2_y', -200),
            click_delay=config.get('click_delay', 500),
        )
        self._active_tool_engine = engine
        self._tool_stop_callback = self._stop_tool
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self._enter_mini_mode("工具: 自动遇敌")
        self._monitor_tool_engine()

    def _start_loop_healing(self):
        """启动循环医疗（已配置则直接启动，否则打开配置）"""
        config = load_tool_config().get('loop_healing', {})
        skill = config.get('skill_image', '')
        member = config.get('member_image', '')
        steps = config.get('steps', [])

        # 检查配置是否完整
        if (not skill or not os.path.exists(skill)
                or not member or not os.path.exists(member)
                or not steps):
            dialog = LoopHealingDialog(self.root, self._screenshot_region)
            if not dialog.result:
                return
            skill = dialog.result['skill_image']
            member = dialog.result['member_image']
            steps = dialog.result['steps']
            self._show_tool_info('loop_healing')

        engine = LoopHealingEngine(self.window_manager, self._log_message)
        engine.start(skill, member, steps)
        self._active_tool_engine = engine
        self._tool_stop_callback = self._stop_tool
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self._enter_mini_mode("工具: 循环医疗")
        self._monitor_tool_engine()

    def _stop_tool(self):
        """停止工具脚本"""
        if self._active_tool_engine:
            self._active_tool_engine.stop()
            self._active_tool_engine = None
        self._tool_stop_callback = None
        self._exit_mini_mode()

    def _monitor_tool_engine(self):
        """监控工具脚本引擎状态"""
        if self._active_tool_engine and self._active_tool_engine.is_running:
            self.root.after(500, self._monitor_tool_engine)
        else:
            self._active_tool_engine = None
            self._tool_stop_callback = None
            self._exit_mini_mode()

    def _trigger_get_material(self):
        """快捷键触发获取材料（全局，不受其他功能运行状态影响）"""
        mat_img = self.settings.get('get_material_image', '')
        if not mat_img or not os.path.exists(mat_img):
            self._log_message("获取材料: 未配置材料图片，请在「设置」中截取")
            return
        self.get_material_engine.execute(mat_img)

    # ── 迷你模式 ──

    def _enter_mini_mode(self, task_name):
        """进入迷你模式"""
        if self._in_mini_mode:
            return
        self._in_mini_mode = True
        self._saved_geometry = self.root.geometry()

        self._main_frame.pack_forget()
        self._mini_frame.pack(fill=tk.BOTH, expand=True)

        self._mini_task_label.config(text=task_name)
        self._mini_step_label.config(text="准备中...")
        self._mini_stats_label.config(text="")
        self._mini_hotkey_label.config(
            text=f"停止热键: {self.hotkey_manager.global_stop_hotkey}")

        self.root.minsize(300, 100)
        self.root.geometry("400x140")
        self.root.attributes('-topmost', True)

    def _exit_mini_mode(self):
        """退出迷你模式"""
        if not self._in_mini_mode:
            return
        self._in_mini_mode = False

        self.root.attributes('-topmost', False)
        self._mini_frame.pack_forget()
        self._main_frame.pack(fill=tk.BOTH, expand=True)

        self.root.minsize(800, 500)
        if self._saved_geometry:
            self.root.geometry(self._saved_geometry)

        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_label.config(text="就绪")

    def _mini_stop(self):
        """迷你模式停止按钮"""
        if self.is_running:
            self.stop_craft()
        elif self._active_tool_engine:
            self._stop_tool()

    # ── 快捷键设置 ──

    def _open_hotkey_settings(self):
        """打开快捷键设置对话框"""
        dialog = HotkeySettingsDialog(self.root, self.hotkey_manager)
        if dialog.result:
            hotkey_text = self.hotkey_manager.get_status_text()
            self.hotkey_label.config(text=f"热键: {hotkey_text}")

    # ── 设置 ──

    def _open_settings(self):
        """打开设置对话框"""
        dialog = SettingsDialog(
            self.root, self._screenshot_region, self.window_manager)
        if dialog.result:
            self.settings = dialog.result
            self.digit_recognizer = DigitRecognizer('templates/digits')
            self.backpack_reader = BackpackReader(
                self.digit_recognizer, self.settings, self._log_message)
            self.craft_engine = CraftEngine(
                self.window_manager, self.backpack_reader, self._log_message)

    # ── 截图工具 ──

    def _screenshot_region(self, save_path):
        """截图并保存到指定路径"""
        try:
            self.root.iconify()
            self.root.update()
            import time as _time
            _time.sleep(0.3)

            screenshot = take_screenshot()

            overlay = tk.Toplevel(self.root)
            overlay.attributes('-fullscreen', True)
            overlay.attributes('-topmost', True)
            overlay.configure(cursor='cross')
            from PIL import ImageTk
            bg_photo = ImageTk.PhotoImage(screenshot)

            canvas = tk.Canvas(overlay, highlightthickness=0)
            canvas.pack(fill=tk.BOTH, expand=True)
            canvas.create_image(0, 0, anchor=tk.NW, image=bg_photo)

            state = {'start': None, 'rect_id': None, 'success': False}

            def on_press(event):
                state['start'] = (event.x, event.y)

            def on_drag(event):
                if state['start'] is None:
                    return
                if state['rect_id']:
                    canvas.delete(state['rect_id'])
                x0, y0 = state['start']
                state['rect_id'] = canvas.create_rectangle(
                    x0, y0, event.x, event.y, outline='red', width=2)

            def on_release(event):
                if state['start'] is None:
                    return
                x0, y0 = state['start']
                x1, y1 = event.x, event.y
                left = min(x0, x1)
                top = min(y0, y1)
                width = abs(x1 - x0)
                height = abs(y1 - y0)
                if width > 5 and height > 5:
                    cropped = screenshot.crop(
                        (left, top, left + width, top + height))
                    save_dir = os.path.dirname(save_path)
                    if save_dir:
                        os.makedirs(save_dir, exist_ok=True)
                    cropped.save(save_path)
                    cropped.close()
                    state['success'] = True
                overlay.destroy()

            def on_escape(event):
                overlay.destroy()

            canvas.bind('<ButtonPress-1>', on_press)
            canvas.bind('<B1-Motion>', on_drag)
            canvas.bind('<ButtonRelease-1>', on_release)
            overlay.bind('<Escape>', on_escape)

            overlay.wait_window()
            screenshot.close()
            self.root.deiconify()
            return state['success']

        except Exception as e:
            print(f"截图失败: {e}")
            self.root.deiconify()
            return False

    # ── 日志 ──

    def _log_message(self, message):
        """添加日志消息 (线程安全)"""
        timestamp = time.strftime('%H:%M:%S')
        self.root.after(0, self._append_log, f"[{timestamp}] {message}")

    def _append_log(self, text):
        """向日志文本框追加内容，同时更新迷你模式步骤"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, text + '\n')
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

        if self._in_mini_mode:
            step_text = text
            if text.startswith('[') and '] ' in text:
                step_text = text.split('] ', 1)[1]
            self._mini_step_label.config(text=step_text)

    # ── 清理 ──

    def _on_close(self):
        """窗口关闭"""
        if self.is_running:
            self.craft_engine.stop()
        if self._active_tool_engine:
            self._active_tool_engine.stop()
        self.hotkey_manager.cleanup()
        self.root.destroy()
