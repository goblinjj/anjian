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
from tool_dialog import AutoEncounterDialog, LoopHealingDialog
from tool_scripts import AutoEncounterEngine, LoopHealingEngine
from screenshot_util import take_screenshot


class CraftAssistantGUI:
    """魔力宝贝制造助手主界面"""

    def __init__(self, root):
        self.root = root
        self.root.title("魔力宝贝制造助手")
        self.root.geometry("900x600")
        self.root.minsize(800, 500)

        self.is_running = False
        self.selected_recipe = None
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

        # 创建界面
        self._create_widgets()

        # 加载配方列表
        self._refresh_recipe_list()

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

        # 工具脚本下拉菜单
        tool_menu_btn = ttk.Menubutton(top_frame, text="工具脚本 ▾")
        tool_menu_btn.pack(side=tk.RIGHT, padx=5)
        tool_menu = tk.Menu(tool_menu_btn, tearoff=0)
        tool_menu.add_command(label="自动遇敌", command=self._open_auto_encounter)
        tool_menu.add_command(label="循环医疗", command=self._open_loop_healing)
        tool_menu_btn['menu'] = tool_menu

        ttk.Separator(self._main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X)

        # 主体区域
        body = ttk.PanedWindow(self._main_frame, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 左侧: 配方列表
        left_frame = ttk.Frame(body, width=200)
        body.add(left_frame, weight=1)

        ttk.Label(left_frame, text="配方列表", font=('', 10, 'bold')).pack(anchor=tk.W, pady=(0, 5))

        self.recipe_listbox = tk.Listbox(left_frame, width=20)
        self.recipe_listbox.pack(fill=tk.BOTH, expand=True)
        self.recipe_listbox.bind('<<ListboxSelect>>', self._on_recipe_select)

        btn_row = ttk.Frame(left_frame)
        btn_row.pack(fill=tk.X, pady=5)
        ttk.Button(btn_row, text="新建", width=6,
                  command=self._new_recipe).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="编辑", width=6,
                  command=self._edit_recipe).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="删除", width=6,
                  command=self._delete_recipe).pack(side=tk.LEFT, padx=2)

        # 右侧: 制造控制
        right_frame = ttk.Frame(body)
        body.add(right_frame, weight=3)

        # 配方信息
        info_frame = ttk.LabelFrame(right_frame, text="当前配方", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 10))

        self.recipe_info_label = ttk.Label(info_frame, text="请选择一个配方", foreground='gray')
        self.recipe_info_label.pack(anchor=tk.W)

        # 控制按钮
        ctrl_frame = ttk.Frame(right_frame)
        ctrl_frame.pack(fill=tk.X, pady=5)

        self.start_btn = ttk.Button(ctrl_frame, text="开始制造",
                                    command=self.start_craft)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(ctrl_frame, text="停止",
                                   command=self.stop_craft, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.stats_label = ttk.Label(ctrl_frame, text="")
        self.stats_label.pack(side=tk.RIGHT, padx=10)

        # 日志区
        log_frame = ttk.LabelFrame(right_frame, text="运行日志", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_frame, height=15, state=tk.DISABLED, wrap=tk.WORD)
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 状态栏
        status_frame = ttk.Frame(self._main_frame, padding=3)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Separator(self._main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, side=tk.BOTTOM)

        self.status_label = ttk.Label(status_frame, text="就绪")
        self.status_label.pack(side=tk.LEFT)

        hotkey_text = self.hotkey_manager.get_status_text()
        self.hotkey_label = ttk.Label(status_frame, text=f"热键: {hotkey_text}")
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

        hotkey_text = self.hotkey_manager.get_status_text()
        self._mini_hotkey_label = ttk.Label(
            mini_btn_frame, text=f"停止热键: {self.hotkey_manager.global_stop_hotkey}",
            foreground='gray')
        self._mini_hotkey_label.pack(side=tk.RIGHT)

    # ── 迷你模式 ──

    def _enter_mini_mode(self, task_name):
        """进入迷你模式：缩小窗口只显示当前任务和步骤"""
        if self._in_mini_mode:
            return
        self._in_mini_mode = True
        self._saved_geometry = self.root.geometry()

        # 切换内容
        self._main_frame.pack_forget()
        self._mini_frame.pack(fill=tk.BOTH, expand=True)

        # 更新迷你模式内容
        self._mini_task_label.config(text=task_name)
        self._mini_step_label.config(text="准备中...")
        self._mini_stats_label.config(text="")
        self._mini_hotkey_label.config(
            text=f"停止热键: {self.hotkey_manager.global_stop_hotkey}")

        # 缩小窗口并置顶
        self.root.minsize(300, 100)
        self.root.geometry("400x140")
        self.root.attributes('-topmost', True)

    def _exit_mini_mode(self):
        """退出迷你模式：恢复完整窗口"""
        if not self._in_mini_mode:
            return
        self._in_mini_mode = False

        self.root.attributes('-topmost', False)

        # 切换内容
        self._mini_frame.pack_forget()
        self._main_frame.pack(fill=tk.BOTH, expand=True)

        # 恢复窗口大小
        self.root.minsize(800, 500)
        if self._saved_geometry:
            self.root.geometry(self._saved_geometry)

        # 恢复主界面按钮状态
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_label.config(text="就绪")

    def _mini_stop(self):
        """迷你模式停止按钮"""
        if self.is_running:
            self.stop_craft()
        elif self._active_tool_engine:
            self._stop_tool()

    # ── 窗口绑定 ──

    def _pick_window(self):
        """选择游戏窗口"""
        self.bind_label.config(text="请点击游戏窗口...", foreground='orange')
        self.root.iconify()  # 最小化

        def on_picked(hwnd, title):
            self.root.after(0, self._on_window_picked, hwnd, title)

        self.window_manager.start_pick_window(on_picked)

    def _on_window_picked(self, hwnd, title):
        """窗口选择完成回调"""
        self.root.deiconify()  # 恢复
        if hwnd:
            self.bind_label.config(
                text=f"已绑定: {title} (0x{hwnd:X})",
                foreground='green'
            )
        else:
            self.bind_label.config(text="绑定失败", foreground='red')

    # ── 配方管理 ──

    def _refresh_recipe_list(self):
        """刷新配方列表"""
        self.recipe_listbox.delete(0, tk.END)
        for name in self.recipe_manager.list_recipes():
            self.recipe_listbox.insert(tk.END, name)

    def _on_recipe_select(self, event):
        """配方选中事件"""
        sel = self.recipe_listbox.curselection()
        if not sel:
            return
        name = self.recipe_listbox.get(sel[0])
        try:
            self.selected_recipe = self.recipe_manager.load_recipe(name)
            self._show_recipe_info(self.selected_recipe)
        except Exception as e:
            self.selected_recipe = None
            self.recipe_info_label.config(text=f"加载失败: {e}")

    def _show_recipe_info(self, recipe):
        """显示配方信息"""
        lines = [f"配方: {recipe['name']}"]
        for i, mat in enumerate(recipe.get('materials', [])):
            lines.append(f"  材料{i+1}: {mat['image_file']} ×{mat['quantity']}")
        lines.append(f"等待时间: {recipe.get('wait_time', 3.0)} 秒")
        org = recipe.get('organize_interval', 0)
        if org > 0:
            lines.append(f"整理频率: 每 {org} 次")
        self.recipe_info_label.config(text='\n'.join(lines), foreground='black')

    def _new_recipe(self):
        """新建配方"""
        dialog = RecipeDialog(self.root, self.recipe_manager, self._screenshot_region)
        if dialog.result:
            self._refresh_recipe_list()

    def _edit_recipe(self):
        """编辑配方"""
        if not self.selected_recipe:
            messagebox.showinfo("提示", "请先选择一个配方")
            return
        dialog = RecipeDialog(self.root, self.recipe_manager,
                            self._screenshot_region, self.selected_recipe)
        if dialog.result:
            self.selected_recipe = dialog.result
            self._refresh_recipe_list()
            self._show_recipe_info(self.selected_recipe)

    def _delete_recipe(self):
        """删除配方"""
        sel = self.recipe_listbox.curselection()
        if not sel:
            messagebox.showinfo("提示", "请先选择一个配方")
            return
        name = self.recipe_listbox.get(sel[0])
        if messagebox.askyesno("确认", f"确定删除配方「{name}」？"):
            self.recipe_manager.delete_recipe(name)
            self.selected_recipe = None
            self.recipe_info_label.config(text="请选择一个配方", foreground='gray')
            self._refresh_recipe_list()

    # ── 制造控制 ──

    def start_craft(self):
        """开始制造"""
        if self.is_running:
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

        # 进入迷你模式
        self._enter_mini_mode(f"制造: {self.selected_recipe['name']}")

        # 构造引擎所需的 settings
        engine_settings = dict(self.settings)
        recipe_dir = self.recipe_manager.get_recipe_dir(self.selected_recipe['name'])
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
            stats_text = (f"成功: {self.craft_engine.success_count} 次 | "
                          f"失败: {self.craft_engine.fail_count} 次")
            self.stats_label.config(text=stats_text)
            if self._in_mini_mode:
                self._mini_stats_label.config(text=stats_text)
            self.root.after(1000, self._update_stats)
        else:
            # 制造结束
            self.is_running = False
            stats_text = (f"完成 - 成功: {self.craft_engine.success_count} 次 | "
                          f"失败: {self.craft_engine.fail_count} 次")
            self.stats_label.config(text=stats_text)
            self._exit_mini_mode()

    # ── 工具脚本 ──

    def _open_auto_encounter(self):
        """打开自动遇敌工具"""
        if self.is_running or self._active_tool_engine:
            messagebox.showwarning("提示", "请先停止当前任务")
            return
        if not self.window_manager.is_window_valid():
            messagebox.showwarning("提示", "请先绑定游戏窗口")
            return

        dialog = AutoEncounterDialog(self.root)
        if dialog.result:
            engine = AutoEncounterEngine(
                self.window_manager, self._log_message)
            engine.start(dialog.result['offset'])
            self._active_tool_engine = engine
            self._tool_stop_callback = self._stop_tool
            self._enter_mini_mode("工具: 自动遇敌")
            self._monitor_tool_engine()

    def _open_loop_healing(self):
        """打开循环医疗工具"""
        if self.is_running or self._active_tool_engine:
            messagebox.showwarning("提示", "请先停止当前任务")
            return
        if not self.window_manager.is_window_valid():
            messagebox.showwarning("提示", "请先绑定游戏窗口")
            return

        dialog = LoopHealingDialog(self.root, self._screenshot_region)
        if dialog.result:
            r = dialog.result
            engine = LoopHealingEngine(
                self.window_manager, self._log_message)
            engine.start(r['skill_image'], r['member_image'], r['offsets'])
            self._active_tool_engine = engine
            self._tool_stop_callback = self._stop_tool
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
            # 引擎自然结束
            self._active_tool_engine = None
            self._tool_stop_callback = None
            self._exit_mini_mode()

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
        dialog = SettingsDialog(self.root, self._screenshot_region, self.window_manager)
        if dialog.result:
            self.settings = dialog.result
            # 重新初始化依赖设置的组件
            self.digit_recognizer = DigitRecognizer('templates/digits')
            self.backpack_reader = BackpackReader(
                self.digit_recognizer, self.settings, self._log_message)
            self.craft_engine = CraftEngine(
                self.window_manager, self.backpack_reader, self._log_message
            )

    # ── 截图工具 ──

    def _screenshot_region(self, save_path):
        """截图并保存到指定路径

        弹出全屏覆盖层让用户框选区域。

        Returns:
            bool: 是否成功
        """
        try:
            # 先最小化主窗口，避免遮挡游戏画面
            self.root.iconify()
            self.root.update()
            import time as _time
            _time.sleep(0.3)  # 等待窗口最小化动画完成

            # 截取全屏作为背景（在创建覆盖层之前）
            screenshot = take_screenshot()

            # 创建全屏截图覆盖层
            overlay = tk.Toplevel(self.root)
            overlay.attributes('-fullscreen', True)
            overlay.attributes('-topmost', True)
            overlay.configure(cursor='cross')
            from PIL import ImageTk
            bg_photo = ImageTk.PhotoImage(screenshot)

            canvas = tk.Canvas(overlay, highlightthickness=0)
            canvas.pack(fill=tk.BOTH, expand=True)
            canvas.create_image(0, 0, anchor=tk.NW, image=bg_photo)

            # 框选状态
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
                    x0, y0, event.x, event.y, outline='red', width=2
                )

            def on_release(event):
                if state['start'] is None:
                    return
                x0, y0 = state['start']
                x1, y1 = event.x, event.y
                # 确保合理大小
                left = min(x0, x1)
                top = min(y0, y1)
                width = abs(x1 - x0)
                height = abs(y1 - y0)
                if width > 5 and height > 5:
                    # 从全屏截图中裁剪
                    cropped = screenshot.crop((left, top, left + width, top + height))
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

        # 更新迷你模式步骤显示
        if self._in_mini_mode:
            # 取掉时间戳前缀显示
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
