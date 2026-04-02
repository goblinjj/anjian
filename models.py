#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据模型模块
包含操作步骤和相关数据结构
"""

class ActionStep:
    """操作步骤类"""
    def __init__(self, step_type, **kwargs):
        self.step_type = step_type  # 'mouse_click', 'keyboard_press', 'image_search', 'wait',
                                     # 'if_image', 'for_loop', 'while_image', 'break_loop',
                                     # 'random_delay', 'mouse_scroll'
        self.params = kwargs
        self.enabled = True
        self.description = ""
        self.children = []        # 子步骤（if的true分支，loop的循环体）
        self.else_children = []   # else分支（仅if_image使用）

    def to_dict(self):
        d = {
            'step_type': self.step_type,
            'params': self.params,
            'enabled': self.enabled,
            'description': self.description
        }
        if self.children:
            d['children'] = [c.to_dict() for c in self.children]
        if self.else_children:
            d['else_children'] = [c.to_dict() for c in self.else_children]
        return d

    @classmethod
    def from_dict(cls, data):
        step = cls(data['step_type'], **data['params'])
        step.enabled = data.get('enabled', True)
        step.description = data.get('description', "")
        step.children = [cls.from_dict(c) for c in data.get('children', [])]
        step.else_children = [cls.from_dict(c) for c in data.get('else_children', [])]
        return step
