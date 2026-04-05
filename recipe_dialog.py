#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配方编辑对话框
支持配方名称、等待时间、整理频率和材料列表的配置
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import shutil
from PIL import Image, ImageTk


class RecipeDialog:
    """配方编辑对话框"""

    def __init__(self, parent, recipe_manager, screenshot_callback, recipe=None):
        """
        Args:
            parent: 父窗口
            recipe_manager: RecipeManager 实例
            screenshot_callback: 截图回调函数, 参数为 save_path, 返回 bool
            recipe: 已有配方数据 (编辑模式) 或 None (新建模式)
        """
        self.result = None
        self.recipe_manager = recipe_manager
        self.screenshot_callback = screenshot_callback
        self.recipe = recipe
        self.materials = []  # [{'image_path': str, 'quantity': int} or None(已删除)]
        self.material_widgets = []  # UI 引用
        self.photo_refs = []  # 保持 PhotoImage 引用

        self.is_edit = recipe is not None
        self.old_name = recipe['name'] if self.is_edit else None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("编辑配方" if self.is_edit else "新建配方")
        self.dialog.geometry("550x500")
        self.dialog.resizable(False, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._create_widgets()

        if self.is_edit:
            self._load_recipe(recipe)

        self.dialog.wait_window()

    def _create_widgets(self):
        main_frame = ttk.Frame(self.dialog, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 配方名称
        name_row = ttk.Frame(main_frame)
        name_row.pack(fill=tk.X, pady=5)
        ttk.Label(name_row, text="配方名称:").pack(side=tk.LEFT)
        self.name_var = tk.StringVar()
        ttk.Entry(name_row, textvariable=self.name_var, width=30).pack(side=tk.LEFT, padx=10)

        # 等待时间
        wait_row = ttk.Frame(main_frame)
        wait_row.pack(fill=tk.X, pady=5)
        ttk.Label(wait_row, text="等待时间:").pack(side=tk.LEFT)
        self.wait_var = tk.DoubleVar(value=3.0)
        ttk.Spinbox(wait_row, from_=0.5, to=60.0, increment=0.5,
                    textvariable=self.wait_var, width=8).pack(side=tk.LEFT, padx=10)
        ttk.Label(wait_row, text="秒 (制造后等待)").pack(side=tk.LEFT)

        # 整理频率
        org_row = ttk.Frame(main_frame)
        org_row.pack(fill=tk.X, pady=5)
        ttk.Label(org_row, text="整理背包:").pack(side=tk.LEFT)
        self.org_var = tk.IntVar(value=5)
        ttk.Spinbox(org_row, from_=0, to=100,
                    textvariable=self.org_var, width=8).pack(side=tk.LEFT, padx=10)
        ttk.Label(org_row, text="次制造后整理一次 (0=不整理)").pack(side=tk.LEFT)

        # 材料列表
        mat_label = ttk.LabelFrame(main_frame, text="材料列表", padding=10)
        mat_label.pack(fill=tk.BOTH, expand=True, pady=10)

        # 材料列表滚动区
        canvas = tk.Canvas(mat_label, height=200)
        scrollbar = ttk.Scrollbar(mat_label, orient=tk.VERTICAL, command=canvas.yview)
        self.mat_frame = ttk.Frame(canvas)
        self.mat_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=self.mat_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 添加材料按钮
        ttk.Button(main_frame, text="+ 添加材料", command=self._add_material).pack(anchor=tk.W, pady=5)

        # 保存/取消按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(btn_frame, text="保存", command=self._save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)

    def _add_material(self, image_path='', quantity=1):
        """添加一条材料行"""
        index = len(self.materials)
        self.materials.append({'image_path': image_path, 'quantity': quantity})

        row = ttk.Frame(self.mat_frame)
        row.pack(fill=tk.X, pady=3)

        # 序号
        ttk.Label(row, text=f"{index + 1}", width=3).pack(side=tk.LEFT)

        # 图片预览
        preview_label = ttk.Label(row, text="[无图片]", width=10)
        preview_label.pack(side=tk.LEFT, padx=5)
        if image_path and os.path.exists(image_path):
            self._update_preview(preview_label, image_path)

        # 数量
        qty_var = tk.IntVar(value=quantity)
        ttk.Label(row, text="×").pack(side=tk.LEFT)
        qty_spin = ttk.Spinbox(row, from_=0, to=80, textvariable=qty_var, width=5)
        qty_spin.pack(side=tk.LEFT, padx=5)

        # 截图按钮
        ttk.Button(row, text="截图", width=5,
                  command=lambda i=index, lbl=preview_label: self._capture_material(i, lbl)
                  ).pack(side=tk.LEFT, padx=3)

        # 删除按钮
        ttk.Button(row, text="删", width=3,
                  command=lambda i=index: self._remove_material(i)
                  ).pack(side=tk.LEFT, padx=3)

        self.material_widgets.append({
            'row': row,
            'preview': preview_label,
            'qty_var': qty_var,
            'index': index
        })

    def _update_preview(self, label, image_path):
        """更新图片预览"""
        try:
            img = Image.open(image_path)
            img.thumbnail((32, 32))
            photo = ImageTk.PhotoImage(img)
            label.config(image=photo, text='')
            self.photo_refs.append(photo)  # 防止被GC
            img.close()
        except Exception:
            label.config(text="[错误]")

    def _capture_material(self, index, preview_label):
        """截取材料图片"""
        name = self.name_var.get().strip() or '新配方'
        recipe_dir = self.recipe_manager.get_recipe_dir(name)
        os.makedirs(recipe_dir, exist_ok=True)
        save_path = os.path.join(recipe_dir, f'material_{index + 1}.png')

        self.dialog.grab_release()
        self.dialog.withdraw()
        success = self.screenshot_callback(save_path)
        self.dialog.deiconify()
        self.dialog.grab_set()

        if success and os.path.exists(save_path):
            self.materials[index]['image_path'] = save_path
            self._update_preview(preview_label, save_path)

    def _remove_material(self, index):
        """删除材料行"""
        if index < len(self.material_widgets):
            widget = self.material_widgets[index]
            widget['row'].destroy()
            self.materials[index] = None  # 标记为已删除

    def _load_recipe(self, recipe):
        """加载已有配方到界面"""
        self.name_var.set(recipe['name'])
        self.wait_var.set(recipe.get('wait_time', 3.0))
        self.org_var.set(recipe.get('organize_interval', 5))

        recipe_dir = self.recipe_manager.get_recipe_dir(recipe['name'])
        for mat in recipe.get('materials', []):
            image_path = os.path.join(recipe_dir, mat['image_file'])
            self._add_material(image_path, mat['quantity'])

    def _save(self):
        """保存配方"""
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("提示", "请输入配方名称", parent=self.dialog)
            return

        # 收集有效材料
        valid_materials = []
        for i, mat in enumerate(self.materials):
            if mat is None:  # 已删除
                continue
            widget = self.material_widgets[i]
            quantity = widget['qty_var'].get()
            image_path = mat.get('image_path', '')

            if not image_path or not os.path.exists(image_path):
                messagebox.showwarning("提示", f"第{i+1}种材料缺少图片", parent=self.dialog)
                return

            # 确保图片在配方目录中
            recipe_dir = self.recipe_manager.get_recipe_dir(name)
            os.makedirs(recipe_dir, exist_ok=True)
            image_file = f'material_{len(valid_materials) + 1}.png'
            target_path = os.path.join(recipe_dir, image_file)

            if os.path.abspath(image_path) != os.path.abspath(target_path):
                shutil.copy2(image_path, target_path)

            valid_materials.append({
                'image_file': image_file,
                'quantity': quantity,
            })

        if not valid_materials:
            messagebox.showwarning("提示", "请至少添加一种材料", parent=self.dialog)
            return

        recipe_data = {
            'name': name,
            'wait_time': self.wait_var.get(),
            'organize_interval': self.org_var.get(),
            'materials': valid_materials,
        }

        # 如果是编辑模式且名称改变，删除旧配方
        if self.is_edit and self.old_name and self.old_name != name:
            self.recipe_manager.delete_recipe(self.old_name)

        self.recipe_manager.save_recipe(recipe_data)
        self.result = recipe_data
        self.dialog.destroy()
