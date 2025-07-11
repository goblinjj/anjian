#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据模型模块
包含操作步骤和相关数据结构
"""

class ActionStep:
    """操作步骤类"""
    def __init__(self, step_type, **kwargs):
        self.step_type = step_type  # 'mouse_click', 'keyboard_press', 'image_search', 'wait'
        self.params = kwargs
        self.enabled = True
        self.description = ""
    
    def to_dict(self):
        return {
            'step_type': self.step_type,
            'params': self.params,
            'enabled': self.enabled,
            'description': self.description
        }
    
    @classmethod
    def from_dict(cls, data):
        step = cls(data['step_type'], **data['params'])
        step.enabled = data.get('enabled', True)
        step.description = data.get('description', "")
        return step
