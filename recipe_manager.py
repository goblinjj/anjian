#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配方管理模块
负责配方的增删改查和持久化
"""

import os
import json
import shutil


class RecipeManager:
    """配方管理器"""

    def __init__(self, recipes_dir='recipes'):
        self.recipes_dir = recipes_dir
        os.makedirs(self.recipes_dir, exist_ok=True)

    def list_recipes(self):
        """列出所有配方名称"""
        if not os.path.exists(self.recipes_dir):
            return []
        names = []
        for name in os.listdir(self.recipes_dir):
            recipe_path = os.path.join(self.recipes_dir, name, 'recipe.json')
            if os.path.isfile(recipe_path):
                names.append(name)
        return sorted(names)

    def save_recipe(self, recipe):
        """保存配方

        Args:
            recipe: dict with keys: name, wait_time, organize_interval, materials
                    materials: list of {image_file, quantity}
        """
        name = recipe['name']
        recipe_dir = os.path.join(self.recipes_dir, name)
        os.makedirs(recipe_dir, exist_ok=True)

        recipe_file = os.path.join(recipe_dir, 'recipe.json')
        with open(recipe_file, 'w', encoding='utf-8') as f:
            json.dump(recipe, f, ensure_ascii=False, indent=2)

    def load_recipe(self, name):
        """加载配方

        Args:
            name: 配方名称

        Returns:
            dict: 配方数据
        """
        recipe_file = os.path.join(self.recipes_dir, name, 'recipe.json')
        with open(recipe_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def delete_recipe(self, name):
        """删除配方

        Args:
            name: 配方名称
        """
        recipe_dir = os.path.join(self.recipes_dir, name)
        if os.path.exists(recipe_dir):
            shutil.rmtree(recipe_dir)

    def get_recipe_dir(self, name):
        """获取配方目录路径

        Args:
            name: 配方名称

        Returns:
            str: 配方目录的绝对路径
        """
        return os.path.join(self.recipes_dir, name)

    def rename_recipe(self, old_name, new_name):
        """重命名配方

        Args:
            old_name: 旧名称
            new_name: 新名称
        """
        old_dir = os.path.join(self.recipes_dir, old_name)
        new_dir = os.path.join(self.recipes_dir, new_name)
        if os.path.exists(old_dir):
            os.rename(old_dir, new_dir)
            recipe = self.load_recipe(new_name)
            recipe['name'] = new_name
            self.save_recipe(recipe)
