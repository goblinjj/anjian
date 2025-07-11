#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文件操作模块
负责配置文件的加载和保存
"""

import json
import os
import time
from tkinter import filedialog, messagebox
from models import ActionStep

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, gui_instance):
        self.gui = gui_instance
        self.current_config_file = None
    
    def new_config(self):
        """新建配置"""
        if self.gui.steps:
            result = messagebox.askyesnocancel("新建配置", "当前配置未保存，是否保存？")
            if result is True:
                if not self.save_config():
                    return
            elif result is None:
                return
        
        self.gui.steps = []
        self.current_config_file = None
        self.gui.refresh_step_list()
        self.gui.update_status("已创建新配置")
    
    def open_config(self):
        """打开配置文件"""
        filename = filedialog.askopenfilename(
            title="打开配置文件",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        
        if filename:
            try:
                self.load_from_file(filename)
                self.current_config_file = filename
                self.gui.update_status(f"已加载配置: {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("错误", f"加载配置失败: {str(e)}")
    
    def save_config(self):
        """保存配置"""
        if self.current_config_file:
            try:
                self.save_to_file(self.current_config_file)
                self.gui.update_status(f"已保存配置: {os.path.basename(self.current_config_file)}")
                return True
            except Exception as e:
                messagebox.showerror("错误", f"保存配置失败: {str(e)}")
                return False
        else:
            return self.save_as_config()
    
    def save_as_config(self):
        """另存为配置"""
        filename = filedialog.asksaveasfilename(
            title="保存配置文件",
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        
        if filename:
            try:
                self.save_to_file(filename)
                self.current_config_file = filename
                self.gui.update_status(f"已保存配置: {os.path.basename(filename)}")
                return True
            except Exception as e:
                messagebox.showerror("错误", f"保存配置失败: {str(e)}")
                return False
        return False
    
    def save_to_file(self, filename):
        """保存到文件"""
        config = {
            "version": "1.0",
            "steps": [step.to_dict() for step in self.gui.steps]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    def load_from_file(self, filename):
        """从文件加载"""
        with open(filename, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        self.gui.steps = []
        for step_data in config.get('steps', []):
            step = ActionStep.from_dict(step_data)
            self.gui.steps.append(step)
        
        self.gui.refresh_step_list()
    
    def load_default_config(self):
        """加载默认配置"""
        default_config_path = "default.json"
        
        if os.path.exists(default_config_path):
            # 如果default.json存在，加载它
            try:
                self.load_from_file(default_config_path)
                self.current_config_file = default_config_path
                self.gui.update_status(f"已加载默认配置: {default_config_path}")
                return
            except Exception as e:
                messagebox.showerror("错误", f"加载默认配置失败: {str(e)}")
                # 如果加载失败，继续创建空配置
        
        # 如果default.json不存在或加载失败，创建空配置
        self.gui.steps = []
        self.gui.refresh_step_list()
        
        # 创建一个空的default.json文件
        try:
            self.create_empty_default_config(default_config_path)
            self.current_config_file = default_config_path
            self.gui.update_status(f"已创建空的默认配置: {default_config_path}")
        except Exception as e:
            messagebox.showerror("错误", f"创建默认配置失败: {str(e)}")
            self.gui.update_status("使用空配置启动")
    
    def create_empty_default_config(self, filename):
        """创建空的默认配置文件"""
        empty_config = {
            "version": "1.0",
            "created_time": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "description": "默认配置文件",
            "steps": []
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(empty_config, f, ensure_ascii=False, indent=2)
    
    def export_config(self):
        """导出配置"""
        if not self.gui.steps:
            messagebox.showwarning("警告", "没有可导出的步骤")
            return
        
        filename = filedialog.asksaveasfilename(
            title="导出配置",
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        
        if filename:
            try:
                self.save_to_file(filename)
                messagebox.showinfo("成功", f"配置已导出到: {filename}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {str(e)}")
    
    def import_config(self):
        """导入配置"""
        filename = filedialog.askopenfilename(
            title="导入配置",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        
        if filename:
            try:
                self.load_from_file(filename)
                messagebox.showinfo("成功", f"配置已导入: {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("错误", f"导入失败: {str(e)}")
    
    def get_current_file(self):
        """获取当前文件名"""
        return self.current_config_file
    
    def is_modified(self):
        """检查是否已修改"""
        # 这里可以实现更复杂的修改检测逻辑
        return True  # 简化实现，总是返回True
