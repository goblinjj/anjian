#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import shutil
import tempfile
import unittest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from recipe_manager import RecipeManager


class TestRecipeManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.manager = RecipeManager(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_save_and_load_recipe(self):
        recipe = {
            'name': '生命力回复药300',
            'wait_time': 3.0,
            'organize_interval': 5,
            'materials': [
                {'image_file': 'material_1.png', 'quantity': 15},
                {'image_file': 'material_2.png', 'quantity': 5},
            ]
        }
        self.manager.save_recipe(recipe)
        loaded = self.manager.load_recipe('生命力回复药300')
        self.assertEqual(loaded['name'], '生命力回复药300')
        self.assertEqual(loaded['wait_time'], 3.0)
        self.assertEqual(loaded['organize_interval'], 5)
        self.assertEqual(len(loaded['materials']), 2)

    def test_list_recipes(self):
        for name in ['配方A', '配方B']:
            recipe = {
                'name': name,
                'wait_time': 2.0,
                'organize_interval': 3,
                'materials': []
            }
            self.manager.save_recipe(recipe)
        names = self.manager.list_recipes()
        self.assertIn('配方A', names)
        self.assertIn('配方B', names)

    def test_delete_recipe(self):
        recipe = {
            'name': '待删除',
            'wait_time': 1.0,
            'organize_interval': 5,
            'materials': []
        }
        self.manager.save_recipe(recipe)
        self.assertIn('待删除', self.manager.list_recipes())
        self.manager.delete_recipe('待删除')
        self.assertNotIn('待删除', self.manager.list_recipes())

    def test_get_recipe_dir(self):
        recipe = {
            'name': '测试配方',
            'wait_time': 1.0,
            'organize_interval': 5,
            'materials': []
        }
        self.manager.save_recipe(recipe)
        recipe_dir = self.manager.get_recipe_dir('测试配方')
        self.assertTrue(os.path.isdir(recipe_dir))


if __name__ == '__main__':
    unittest.main()
