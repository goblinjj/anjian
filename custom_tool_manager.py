#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""自定义工具管理: 一个工具 = 一个 JSON + 一个同名子目录 (放图片模板)。"""

import json
import os
import re
import shutil

CUSTOM_TOOLS_DIR = 'custom_tools'

# Windows 文件名非法字符
_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class CustomToolManager:
    def __init__(self, tools_dir=CUSTOM_TOOLS_DIR):
        self.tools_dir = tools_dir
        os.makedirs(self.tools_dir, exist_ok=True)

    @staticmethod
    def sanitize_name(name):
        """去掉非法字符并 trim, 返回安全名 (空字符串表示无效)。"""
        if not name:
            return ''
        cleaned = _INVALID_CHARS.sub('', name).strip().rstrip('. ')
        return cleaned

    def _json_path(self, name):
        return os.path.join(self.tools_dir, f'{name}.json')

    def img_dir(self, name):
        """该工具的图片模板专属子目录 (相对路径, 与 image_path 字段对齐)。"""
        return os.path.join(self.tools_dir, name)

    def list_tools(self):
        """返回工具名列表 (按字母排序), 仅扫描根目录下的 .json 文件。"""
        if not os.path.isdir(self.tools_dir):
            return []
        names = []
        for f in os.listdir(self.tools_dir):
            if f.endswith('.json'):
                names.append(f[:-5])
        names.sort()
        return names

    def exists(self, name):
        return os.path.isfile(self._json_path(name))

    def load(self, name):
        """加载工具数据。文件不存在抛 FileNotFoundError。"""
        with open(self._json_path(name), 'r', encoding='utf-8') as f:
            return json.load(f)

    def save(self, tool_data, original_name=None):
        """保存工具。

        Args:
            tool_data: dict, 必须含 name / mode / steps
            original_name: 编辑模式下的原工具名; 改名时用来搬目录 + 重写 image_path
        Raises:
            ValueError: 名字非法 / 重名冲突
        """
        new_name = self.sanitize_name(tool_data.get('name', ''))
        if not new_name:
            raise ValueError('工具名不能为空且不能全是非法字符')
        if not tool_data.get('steps'):
            raise ValueError('至少要有一个步骤')

        # 重名冲突: 新名 != 原名 且新名已存在
        if new_name != (original_name or '') and self.exists(new_name):
            raise ValueError(f'已存在同名工具: {new_name}')

        # 改名: 搬目录 + 重写 image_path 字段
        if original_name and original_name != new_name:
            old_dir = self.img_dir(original_name)
            new_dir = self.img_dir(new_name)
            if os.path.isdir(old_dir):
                os.rename(old_dir, new_dir)
            for step in tool_data.get('steps', []):
                if step.get('type') == 'image_search':
                    p = step.get('image_path', '')
                    if p.startswith(old_dir + os.sep) or p.startswith(old_dir + '/'):
                        step['image_path'] = new_dir + p[len(old_dir):]
            old_json = self._json_path(original_name)
            if os.path.isfile(old_json):
                os.remove(old_json)

        tool_data['name'] = new_name
        tool_data.setdefault('version', '1.0')
        with open(self._json_path(new_name), 'w', encoding='utf-8') as f:
            json.dump(tool_data, f, ensure_ascii=False, indent=2)
        return new_name

    def delete(self, name):
        """删工具 JSON + 图片子目录。"""
        json_path = self._json_path(name)
        if os.path.isfile(json_path):
            os.remove(json_path)
        sub_dir = self.img_dir(name)
        if os.path.isdir(sub_dir):
            shutil.rmtree(sub_dir, ignore_errors=True)
