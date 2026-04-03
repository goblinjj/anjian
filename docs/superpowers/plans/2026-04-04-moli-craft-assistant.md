# 魔力宝贝制造助手 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the generic automation tool into a dedicated 魔力宝贝 crafting assistant with backpack item/quantity recognition, recipe management, and automated crafting loops.

**Architecture:** Bottom-up build: data layer (recipe_manager) → recognition modules (digit_recognizer, backpack_reader) → window management (window_manager) → crafting engine (craft_engine) → UI layer (settings_dialog, recipe_dialog, main_gui). Old generic modules are removed. screenshot_util.py is reused as-is.

**Tech Stack:** Python 3.11, tkinter, OpenCV, pyautogui, mss, pywin32 (win32gui/win32api), keyboard, Pillow, numpy

---

## File Structure

```
项目根目录/
├── start_gui.py          # 入口 (修改: 更新依赖检查和标题)
├── main_gui.py           # 主界面 (重写)
├── recipe_manager.py     # 配方管理 (新建)
├── recipe_dialog.py      # 配方编辑对话框 (新建)
├── settings_dialog.py    # 全局设置对话框 (新建)
├── digit_recognizer.py   # 数字识别 (新建)
├── backpack_reader.py    # 背包识别 (新建)
├── craft_engine.py       # 制造引擎 (新建)
├── window_manager.py     # 窗口管理 (新建)
├── screenshot_util.py    # 截图工具 (复用, 不修改)
├── hotkey_manager.py     # 热键管理 (修改: 移除旧依赖)
├── build_exe.py          # 打包脚本 (修改: 更新模块列表和名称)
├── requirements.txt      # 依赖 (修改: 添加pywin32)
├── settings.json         # 全局设置 (运行时生成)
├── templates/            # 全局图片模板 (用户截图后生成)
│   ├── backpack_title.png
│   ├── execute_button.png
│   ├── completion.png
│   ├── organize_button.png
│   └── digits/
│       ├── 0.png ~ 9.png
├── recipes/              # 配方数据 (用户创建后生成)
│   └── {配方名}/
│       ├── recipe.json
│       └── material_N.png
└── tests/                # 单元测试
    ├── test_recipe_manager.py
    └── test_digit_recognizer.py
```

---

### Task 1: 清理旧模块，更新依赖

**Files:**
- Delete: `models.py`, `execution_engine.py`, `ui_editors.py`, `dialogs.py`, `file_manager.py`, `default.json`
- Modify: `requirements.txt`
- Modify: `hotkey_manager.py`

- [ ] **Step 1: 删除旧模块文件**

```bash
cd /Volumes/T7/work/anjian
rm models.py execution_engine.py ui_editors.py dialogs.py file_manager.py default.json
```

- [ ] **Step 2: 更新 requirements.txt，添加 pywin32**

```
opencv-python>=4.8.0
pyautogui>=0.9.54
numpy>=1.24.0
Pillow>=10.0.0
keyboard>=0.13.5
mss>=9.0.0
pyinstaller>=5.13.0
pywin32>=306
```

移除 `requests>=2.31.0`（不再需要）。

- [ ] **Step 3: 简化 hotkey_manager.py，移除 dialogs 依赖**

移除 `from dialogs import HotkeySettingsDialog` 导入和 `show_hotkey_settings` 中对它的调用。热键设置将在新的全局设置对话框中处理。

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
快捷键管理模块
负责全局快捷键监听和管理
"""

import json
import os
import keyboard

HOTKEY_CONFIG_FILE = "hotkey_config.json"


class HotkeyManager:
    """快捷键管理器"""

    def __init__(self, gui_instance):
        self.gui = gui_instance
        self.global_start_hotkey = "`"
        self.global_stop_hotkey = "esc"
        self._start_hook = None
        self._stop_hook = None
        self.is_listening = False
        self._load_hotkey_config()

    def _load_hotkey_config(self):
        """从配置文件加载快捷键设置"""
        try:
            if os.path.exists(HOTKEY_CONFIG_FILE):
                with open(HOTKEY_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self.global_start_hotkey = config.get("start_hotkey", "`")
                self.global_stop_hotkey = config.get("stop_hotkey", "esc")
        except Exception:
            pass

    def _save_hotkey_config(self):
        """保存快捷键设置到配置文件"""
        config = {
            "start_hotkey": self.global_start_hotkey,
            "stop_hotkey": self.global_stop_hotkey
        }
        try:
            with open(HOTKEY_CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def start_global_hotkey_listener(self):
        """注册全局快捷键"""
        self._unregister_hotkeys()
        try:
            self._start_hook = keyboard.add_hotkey(
                self.global_start_hotkey, self._on_start_hotkey, suppress=False
            )
            self._stop_hook = keyboard.add_hotkey(
                self.global_stop_hotkey, self._on_stop_hotkey, suppress=False
            )
            self.is_listening = True
        except Exception as e:
            print(f"注册全局快捷键失败: {e}")

    def _unregister_hotkeys(self):
        """取消注册全局快捷键"""
        if self._start_hook is not None:
            try:
                keyboard.remove_hotkey(self._start_hook)
            except Exception:
                pass
            self._start_hook = None
        if self._stop_hook is not None:
            try:
                keyboard.remove_hotkey(self._stop_hook)
            except Exception:
                pass
            self._stop_hook = None
        self.is_listening = False

    def _on_start_hotkey(self):
        """快捷键启动执行"""
        if self.gui.is_running:
            return
        self.gui.root.after(0, self.gui.start_craft)

    def _on_stop_hotkey(self):
        """快捷键停止执行"""
        if self.gui.is_running:
            self.gui.root.after(0, self.gui.stop_craft)

    def update_hotkeys(self, start_key, stop_key):
        """更新全局快捷键"""
        self.global_start_hotkey = start_key
        self.global_stop_hotkey = stop_key
        self._save_hotkey_config()
        self.start_global_hotkey_listener()

    def cleanup(self):
        """清理快捷键"""
        self._unregister_hotkeys()

    def get_status_text(self):
        """获取快捷键状态文本"""
        return f"启动:{self.global_start_hotkey} 停止:{self.global_stop_hotkey}"
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "移除旧通用模块，简化hotkey_manager，添加pywin32依赖"
```

---

### Task 2: 创建 recipe_manager.py — 配方数据管理

**Files:**
- Create: `recipe_manager.py`
- Create: `tests/test_recipe_manager.py`

- [ ] **Step 1: 编写 recipe_manager 测试**

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /Volumes/T7/work/anjian
python -m pytest tests/test_recipe_manager.py -v
```

预期: FAIL — `ModuleNotFoundError: No module named 'recipe_manager'`

- [ ] **Step 3: 实现 recipe_manager.py**

```python
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
            # 更新 recipe.json 中的名称
            recipe = self.load_recipe(new_name)
            recipe['name'] = new_name
            self.save_recipe(recipe)
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_recipe_manager.py -v
```

预期: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add recipe_manager.py tests/test_recipe_manager.py
git commit -m "新增配方管理模块，支持配方CRUD和持久化"
```

---

### Task 3: 创建 digit_recognizer.py — 数字识别

**Files:**
- Create: `digit_recognizer.py`
- Create: `tests/test_digit_recognizer.py`

- [ ] **Step 1: 编写 digit_recognizer 测试**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import unittest
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from digit_recognizer import DigitRecognizer


class TestDigitRecognizer(unittest.TestCase):
    def setUp(self):
        """创建测试用的数字模板图片"""
        self.test_dir = os.path.join(os.path.dirname(__file__), 'test_digits')
        os.makedirs(self.test_dir, exist_ok=True)
        # 创建简单的 10x14 数字模板图片 (白色数字，黑色背景)
        for digit in range(10):
            img = Image.new('RGB', (10, 14), color=(0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.text((1, 0), str(digit), fill=(255, 255, 255))
            img.save(os.path.join(self.test_dir, f'{digit}.png'))
        self.recognizer = DigitRecognizer(self.test_dir)

    def tearDown(self):
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_load_templates(self):
        """模板加载成功"""
        self.assertEqual(len(self.recognizer.templates), 10)
        for i in range(10):
            self.assertIn(i, self.recognizer.templates)

    def test_templates_not_found(self):
        """模板目录不存在时返回空"""
        recognizer = DigitRecognizer('/nonexistent')
        self.assertEqual(len(recognizer.templates), 0)

    def test_recognize_returns_none_for_blank(self):
        """纯黑图片应返回 None (无数字)"""
        blank = np.zeros((14, 30, 3), dtype=np.uint8)
        result = self.recognizer.recognize(blank)
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest tests/test_digit_recognizer.py -v
```

预期: FAIL — `ModuleNotFoundError: No module named 'digit_recognizer'`

- [ ] **Step 3: 实现 digit_recognizer.py**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数字识别模块
使用0-9模板匹配识别背包物品数量
"""

import os
import cv2
import numpy as np
from PIL import Image


class DigitRecognizer:
    """数字识别器 — 模板匹配方式"""

    def __init__(self, templates_dir='templates/digits'):
        self.templates_dir = templates_dir
        self.templates = {}  # {digit_int: numpy_array}
        self._load_templates()

    def _load_templates(self):
        """加载 0-9 数字模板图片"""
        if not os.path.exists(self.templates_dir):
            return
        for digit in range(10):
            path = os.path.join(self.templates_dir, f'{digit}.png')
            if os.path.exists(path):
                pil_img = Image.open(path)
                img = np.array(pil_img)
                pil_img.close()
                if len(img.shape) == 3:
                    img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
                self.templates[digit] = img

    def recognize(self, region_image, confidence=0.7):
        """识别图片区域中的数字

        从左到右扫描，逐位匹配数字模板。

        Args:
            region_image: numpy array (BGR 或 RGB 或 灰度), 包含数字的图片区域
            confidence: 匹配置信度阈值

        Returns:
            int or None: 识别到的数字 (1-80), 没有识别到返回 None
        """
        if len(self.templates) == 0:
            return None

        # 转为灰度
        if len(region_image.shape) == 3:
            gray = cv2.cvtColor(region_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = region_image.copy()

        digits_found = []  # [(x_position, digit_value)]
        h, w = gray.shape

        for digit, tmpl in self.templates.items():
            th, tw = tmpl.shape
            if th > h or tw > w:
                continue

            result = cv2.matchTemplate(gray, tmpl, cv2.TM_CCOEFF_NORMED)
            locations = np.where(result >= confidence)

            for pt_x in locations[1]:
                # 去重: 如果附近已有识别结果，跳过
                is_duplicate = False
                for existing_x, _ in digits_found:
                    if abs(pt_x - existing_x) < tw * 0.5:
                        is_duplicate = True
                        break
                if not is_duplicate:
                    digits_found.append((pt_x, digit))

        if not digits_found:
            return None

        # 按 x 坐标排序，组合成数字
        digits_found.sort(key=lambda x: x[0])
        number_str = ''.join(str(d) for _, d in digits_found)

        try:
            return int(number_str)
        except ValueError:
            return None

    def is_loaded(self):
        """检查模板是否已加载"""
        return len(self.templates) == 10
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_digit_recognizer.py -v
```

预期: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add digit_recognizer.py tests/test_digit_recognizer.py
git commit -m "新增数字识别模块，使用0-9模板匹配识别物品数量"
```

---

### Task 4: 创建 window_manager.py — 窗口管理

**Files:**
- Create: `window_manager.py`

此模块依赖 win32gui/win32api，仅在 Windows 上可运行，不写自动化测试。

- [ ] **Step 1: 实现 window_manager.py**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
窗口管理模块
负责游戏窗口的选择和坐标管理
"""

import ctypes
import ctypes.wintypes
import threading
import time


# Windows API 常量
WH_MOUSE_LL = 14
WM_LBUTTONDOWN = 0x0201
GWL_EXSTYLE = -20
WS_EX_TOPMOST = 0x0008
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040
IDC_CROSS = 32515

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


class WindowManager:
    """窗口管理器"""

    def __init__(self):
        self.hwnd = None  # 绑定的窗口句柄
        self.window_title = ""  # 窗口标题

    def start_pick_window(self, callback):
        """启动窗口选择模式

        在后台线程中运行，用户点击任意窗口后回调。

        Args:
            callback: 回调函数，参数为 (hwnd, title) 或 (None, None) 表示取消
        """
        thread = threading.Thread(target=self._pick_window_thread, args=(callback,), daemon=True)
        thread.start()

    def _pick_window_thread(self, callback):
        """窗口选择线程"""
        # 设置十字光标
        cross_cursor = user32.LoadCursorW(0, IDC_CROSS)
        old_cursor = user32.SetCursor(cross_cursor)

        picked_hwnd = [None]

        # 低级鼠标钩子回调
        HOOKPROC = ctypes.CFUNCTYPE(ctypes.c_long, ctypes.c_int,
                                     ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM)

        def mouse_proc(nCode, wParam, lParam):
            if nCode >= 0 and wParam == WM_LBUTTONDOWN:
                # 获取鼠标位置
                pt = ctypes.wintypes.POINT()
                user32.GetCursorPos(ctypes.byref(pt))
                # 获取该位置的窗口
                hwnd = user32.WindowFromPoint(pt)
                # 获取顶层父窗口
                root_hwnd = user32.GetAncestor(hwnd, 2)  # GA_ROOT = 2
                if root_hwnd:
                    picked_hwnd[0] = root_hwnd
                else:
                    picked_hwnd[0] = hwnd
                # 退出消息循环
                user32.PostQuitMessage(0)
                return 1  # 拦截点击
            return user32.CallNextHookEx(None, nCode, wParam, lParam)

        proc = HOOKPROC(mouse_proc)
        hook = user32.SetWindowsHookExW(WH_MOUSE_LL, proc, kernel32.GetModuleHandleW(None), 0)

        if not hook:
            callback(None, None)
            return

        # 消息循环
        msg = ctypes.wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        user32.UnhookWindowsHookEx(hook)

        hwnd = picked_hwnd[0]
        if hwnd:
            title = self._get_window_title(hwnd)
            self.hwnd = hwnd
            self.window_title = title
            callback(hwnd, title)
        else:
            callback(None, None)

    def _get_window_title(self, hwnd):
        """获取窗口标题"""
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return ""
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value

    def get_window_rect(self):
        """获取绑定窗口的屏幕坐标

        Returns:
            tuple: (left, top, width, height) 或 None
        """
        if not self.hwnd:
            return None
        rect = ctypes.wintypes.RECT()
        if user32.GetWindowRect(self.hwnd, ctypes.byref(rect)):
            return (rect.left, rect.top,
                    rect.right - rect.left, rect.bottom - rect.top)
        return None

    def is_window_valid(self):
        """检查绑定的窗口是否仍然有效"""
        if not self.hwnd:
            return False
        return bool(user32.IsWindow(self.hwnd))

    def grid_to_screen(self, grid_x, grid_y, backpack_origin, cell_width, cell_height):
        """将背包网格坐标转换为屏幕坐标（格子中心点）

        Args:
            grid_x: 列索引 (0-4)
            grid_y: 行索引 (0-3)
            backpack_origin: 背包网格左上角的屏幕坐标 (x, y)
            cell_width: 格子宽度
            cell_height: 格子高度

        Returns:
            tuple: (screen_x, screen_y) 格子中心的屏幕坐标
        """
        origin_x, origin_y = backpack_origin
        screen_x = origin_x + grid_x * cell_width + cell_width // 2
        screen_y = origin_y + grid_y * cell_height + cell_height // 2
        return (screen_x, screen_y)

    def get_bind_info(self):
        """获取绑定信息的显示文本"""
        if not self.hwnd:
            return "未绑定"
        if not self.is_window_valid():
            return "窗口已失效"
        return f"已绑定: {self.window_title} (句柄:0x{self.hwnd:X})"
```

- [ ] **Step 2: Commit**

```bash
git add window_manager.py
git commit -m "新增窗口管理模块，支持点击选择绑定游戏窗口"
```

---

### Task 5: 创建 backpack_reader.py — 背包识别

**Files:**
- Create: `backpack_reader.py`

- [ ] **Step 1: 实现 backpack_reader.py**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
背包识别模块
在游戏窗口中定位背包，切割网格，识别物品图标和数量
"""

import cv2
import numpy as np
from PIL import Image
from screenshot_util import take_screenshot


# 背包网格常量 (像素值需根据实际游戏界面调整)
GRID_COLS = 5
GRID_ROWS = 4
GRID_TOTAL = GRID_COLS * GRID_ROWS  # 20


class BackpackSlot:
    """背包格子信息"""
    def __init__(self, grid_x, grid_y, icon_image, quantity):
        self.grid_x = grid_x       # 列索引 0-4
        self.grid_y = grid_y       # 行索引 0-3
        self.icon_image = icon_image  # numpy array, 物品图标区域
        self.quantity = quantity    # int or None


class BackpackReader:
    """背包读取器"""

    def __init__(self, digit_recognizer, settings=None):
        """
        Args:
            digit_recognizer: DigitRecognizer 实例
            settings: dict, 包含背包相关设置:
                - backpack_title_image: 背包标题栏模板图片路径
                - cell_width: 格子宽度 (像素)
                - cell_height: 格子高度 (像素)
                - grid_offset_x: 网格相对于标题栏左侧的X偏移
                - grid_offset_y: 网格相对于标题栏底部的Y偏移
                - digit_region: 数字区域在格子内的相对位置 (x, y, w, h)
                - icon_region: 图标区域在格子内的相对位置 (x, y, w, h)
        """
        self.digit_recognizer = digit_recognizer
        self.settings = settings or {}

    def locate_backpack(self, window_region):
        """在窗口截图中定位背包

        Args:
            window_region: (left, top, width, height) 游戏窗口的屏幕区域

        Returns:
            tuple: (backpack_x, backpack_y) 背包网格左上角的屏幕坐标，
                   或 None 如果未找到
        """
        title_image_path = self.settings.get('backpack_title_image')
        if not title_image_path:
            return None

        # 截取游戏窗口区域
        screenshot = take_screenshot(region=window_region)
        screenshot_np = np.array(screenshot)
        screenshot.close()
        screenshot_bgr = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)

        # 加载背包标题模板
        pil_tmpl = Image.open(title_image_path)
        tmpl = np.array(pil_tmpl)
        pil_tmpl.close()
        if len(tmpl.shape) == 3:
            tmpl = cv2.cvtColor(tmpl, cv2.COLOR_RGB2BGR)

        # 模板匹配
        result = cv2.matchTemplate(screenshot_bgr, tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val < 0.7:
            return None

        # 计算网格左上角的屏幕坐标
        tmpl_h = tmpl.shape[0]
        win_left, win_top = window_region[0], window_region[1]
        offset_x = self.settings.get('grid_offset_x', 0)
        offset_y = self.settings.get('grid_offset_y', 0)

        grid_screen_x = win_left + max_loc[0] + offset_x
        grid_screen_y = win_top + max_loc[1] + tmpl_h + offset_y

        return (grid_screen_x, grid_screen_y)

    def scan_backpack(self, window_region, backpack_origin):
        """扫描背包所有格子

        Args:
            window_region: (left, top, width, height) 游戏窗口区域
            backpack_origin: (x, y) 背包网格左上角的屏幕坐标

        Returns:
            list[BackpackSlot]: 20个格子的信息
        """
        cell_w = self.settings.get('cell_width', 40)
        cell_h = self.settings.get('cell_height', 40)
        origin_x, origin_y = backpack_origin

        # 截取整个背包网格区域
        grid_width = cell_w * GRID_COLS
        grid_height = cell_h * GRID_ROWS
        grid_region = (origin_x, origin_y, grid_width, grid_height)
        screenshot = take_screenshot(region=grid_region)
        grid_image = np.array(screenshot)
        screenshot.close()
        grid_bgr = cv2.cvtColor(grid_image, cv2.COLOR_RGB2BGR)

        # 数字区域在格子内的相对位置
        digit_region = self.settings.get('digit_region', {})
        digit_x = digit_region.get('x', cell_w - 20)
        digit_y = digit_region.get('y', cell_h - 14)
        digit_w = digit_region.get('w', 20)
        digit_h = digit_region.get('h', 14)

        # 图标区域在格子内的相对位置
        icon_region = self.settings.get('icon_region', {})
        icon_x = icon_region.get('x', 2)
        icon_y = icon_region.get('y', 2)
        icon_w = icon_region.get('w', cell_w - 4)
        icon_h = icon_region.get('h', cell_h - 4)

        slots = []
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                x_start = col * cell_w
                y_start = row * cell_h

                # 提取图标区域
                icon_img = grid_bgr[
                    y_start + icon_y : y_start + icon_y + icon_h,
                    x_start + icon_x : x_start + icon_x + icon_w
                ].copy()

                # 提取数字区域并识别
                digit_img = grid_bgr[
                    y_start + digit_y : y_start + digit_y + digit_h,
                    x_start + digit_x : x_start + digit_x + digit_w
                ].copy()
                quantity = self.digit_recognizer.recognize(digit_img)

                slots.append(BackpackSlot(col, row, icon_img, quantity))

        return slots

    def match_item(self, slots, material_image_path, required_quantity, confidence=0.7):
        """在背包中查找匹配的物品格子

        Args:
            slots: list[BackpackSlot] 背包扫描结果
            material_image_path: str 材料图标截图路径
            required_quantity: int 需求数量
            confidence: float 匹配置信度

        Returns:
            BackpackSlot or None: 匹配的格子，优先选择数量最接近需求的
        """
        # 加载材料模板
        pil_tmpl = Image.open(material_image_path)
        tmpl = np.array(pil_tmpl)
        pil_tmpl.close()
        if len(tmpl.shape) == 3:
            tmpl = cv2.cvtColor(tmpl, cv2.COLOR_RGB2BGR)

        candidates = []

        for slot in slots:
            if slot.quantity is None:
                continue
            if slot.quantity < required_quantity:
                continue

            # 模板匹配图标
            icon = slot.icon_image
            if icon.shape[0] < tmpl.shape[0] or icon.shape[1] < tmpl.shape[1]:
                continue

            result = cv2.matchTemplate(icon, tmpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)

            if max_val >= confidence:
                candidates.append((slot, max_val))

        if not candidates:
            return None

        # 按匹配度排序，取最高的
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]
```

- [ ] **Step 2: Commit**

```bash
git add backpack_reader.py
git commit -m "新增背包识别模块，支持网格切割、物品图标匹配和数量识别"
```

---

### Task 6: 创建 craft_engine.py — 制造引擎

**Files:**
- Create: `craft_engine.py`

- [ ] **Step 1: 实现 craft_engine.py**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
制造引擎模块
负责自动制造循环的核心逻辑
"""

import time
import threading
import pyautogui
import cv2
import numpy as np
from PIL import Image
from screenshot_util import take_screenshot


class CraftEngine:
    """制造引擎"""

    def __init__(self, window_manager, backpack_reader, status_callback=None):
        """
        Args:
            window_manager: WindowManager 实例
            backpack_reader: BackpackReader 实例
            status_callback: 状态回调函数 (message: str)
        """
        self.window_manager = window_manager
        self.backpack_reader = backpack_reader
        self.status_callback = status_callback
        self.should_stop = False
        self.is_running = False
        self.craft_count = 0
        self.success_count = 0
        self.fail_count = 0
        self._thread = None

    def start(self, recipe, settings):
        """启动制造循环

        Args:
            recipe: dict 配方数据
            settings: dict 全局设置 (模板图片路径等)
        """
        if self.is_running:
            return
        self.should_stop = False
        self.is_running = True
        self.craft_count = 0
        self.success_count = 0
        self.fail_count = 0
        self._thread = threading.Thread(
            target=self._craft_loop, args=(recipe, settings), daemon=True
        )
        self._thread.start()

    def stop(self):
        """停止制造"""
        self.should_stop = True

    def _log(self, message):
        """输出日志"""
        if self.status_callback:
            self.status_callback(message)

    def _check_stop(self):
        """检查是否应该停止"""
        return self.should_stop

    def _craft_loop(self, recipe, settings):
        """制造主循环"""
        try:
            materials = recipe['materials']
            wait_time = recipe.get('wait_time', 3.0)
            organize_interval = recipe.get('organize_interval', 0)

            execute_button_path = settings.get('execute_button_image')
            completion_image_path = settings.get('completion_image')
            organize_button_path = settings.get('organize_button_image')

            while not self._check_stop():
                # 1. 检查窗口有效性
                if not self.window_manager.is_window_valid():
                    self._log("错误: 游戏窗口已失效")
                    break

                # 2. 获取窗口坐标
                window_rect = self.window_manager.get_window_rect()
                if not window_rect:
                    self._log("错误: 无法获取窗口坐标")
                    break

                # 3. 定位背包
                self._log("扫描背包...")
                backpack_origin = self.backpack_reader.locate_backpack(window_rect)
                if not backpack_origin:
                    self._log("错误: 无法定位背包窗口")
                    break

                # 4. 扫描背包格子
                slots = self.backpack_reader.scan_backpack(window_rect, backpack_origin)
                items_with_qty = sum(1 for s in slots if s.quantity is not None)
                self._log(f"扫描完成，发现 {items_with_qty} 种有数量的物品")

                if self._check_stop():
                    break

                # 5. 匹配每种材料
                matched_slots = []
                all_matched = True
                recipe_dir = settings.get('recipe_dir', '')

                for i, mat in enumerate(materials):
                    import os
                    mat_image_path = os.path.join(recipe_dir, mat['image_file'])
                    required_qty = mat['quantity']

                    slot = self.backpack_reader.match_item(
                        slots, mat_image_path, required_qty
                    )

                    if slot is None:
                        self._log(f"材料不足: 第{i+1}种材料 (需要 {required_qty} 个)")
                        all_matched = False
                        break

                    matched_slots.append(slot)
                    self._log(f"材料{i+1} 匹配成功: 格子({slot.grid_x},{slot.grid_y}) 数量:{slot.quantity}")

                if not all_matched:
                    self._log("材料不足，暂停等待...")
                    # 等待用户补充材料或停止
                    while not self._check_stop():
                        time.sleep(1)
                    break

                if self._check_stop():
                    break

                # 6. 点击匹配到的格子
                cell_w = self.backpack_reader.settings.get('cell_width', 40)
                cell_h = self.backpack_reader.settings.get('cell_height', 40)

                for slot in matched_slots:
                    if self._check_stop():
                        break
                    screen_x, screen_y = self.window_manager.grid_to_screen(
                        slot.grid_x, slot.grid_y, backpack_origin, cell_w, cell_h
                    )
                    pyautogui.click(screen_x, screen_y)
                    time.sleep(0.3)

                if self._check_stop():
                    break

                # 7. 点击执行按钮
                self._log("点击执行...")
                if execute_button_path:
                    self._click_template(execute_button_path, window_rect)
                time.sleep(0.5)

                # 8. 等待制造完成
                self._log(f"等待制造完成 (最长 {wait_time} 秒)...")
                if completion_image_path:
                    completed = self._wait_for_template(
                        completion_image_path, window_rect, timeout=wait_time + 30
                    )
                    if completed and not self._check_stop():
                        # 9. 点击完成按钮
                        self._log("制造完成，点击确认...")
                        self._click_template(completion_image_path, window_rect)
                        self.success_count += 1
                    else:
                        self.fail_count += 1
                else:
                    time.sleep(wait_time)
                    self.success_count += 1

                self.craft_count += 1
                self._log(f"第 {self.craft_count} 次制造完成 (成功:{self.success_count} 失败:{self.fail_count})")

                if self._check_stop():
                    break

                # 10. 整理背包
                if organize_interval > 0 and self.craft_count % organize_interval == 0:
                    if organize_button_path:
                        self._log("整理背包...")
                        self._click_template(organize_button_path, window_rect)
                        time.sleep(1.0)

                # 短暂间隔再开始下一轮
                time.sleep(0.5)

        except Exception as e:
            self._log(f"制造出错: {str(e)}")
        finally:
            self.is_running = False
            self._log("制造已停止")

    def _click_template(self, template_path, window_rect):
        """在窗口中查找模板并点击

        Args:
            template_path: 模板图片路径
            window_rect: (left, top, width, height)
        """
        screenshot = take_screenshot(region=window_rect)
        screen_np = np.array(screenshot)
        screenshot.close()
        screen_bgr = cv2.cvtColor(screen_np, cv2.COLOR_RGB2BGR)

        pil_tmpl = Image.open(template_path)
        tmpl = np.array(pil_tmpl)
        pil_tmpl.close()
        if len(tmpl.shape) == 3:
            tmpl = cv2.cvtColor(tmpl, cv2.COLOR_RGB2BGR)

        result = cv2.matchTemplate(screen_bgr, tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= 0.7:
            th, tw = tmpl.shape[:2]
            click_x = window_rect[0] + max_loc[0] + tw // 2
            click_y = window_rect[1] + max_loc[1] + th // 2
            pyautogui.click(click_x, click_y)
            return True
        return False

    def _wait_for_template(self, template_path, window_rect, timeout=30):
        """等待模板出现

        Args:
            template_path: 模板图片路径
            window_rect: 窗口区域
            timeout: 超时秒数

        Returns:
            bool: 是否在超时前找到
        """
        pil_tmpl = Image.open(template_path)
        tmpl = np.array(pil_tmpl)
        pil_tmpl.close()
        if len(tmpl.shape) == 3:
            tmpl = cv2.cvtColor(tmpl, cv2.COLOR_RGB2BGR)

        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._check_stop():
                return False

            screenshot = take_screenshot(region=window_rect)
            screen_np = np.array(screenshot)
            screenshot.close()
            screen_bgr = cv2.cvtColor(screen_np, cv2.COLOR_RGB2BGR)

            result = cv2.matchTemplate(screen_bgr, tmpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)

            if max_val >= 0.7:
                return True

            time.sleep(0.5)

        return False
```

- [ ] **Step 2: Commit**

```bash
git add craft_engine.py
git commit -m "新增制造引擎模块，实现自动制造循环核心逻辑"
```

---

### Task 7: 创建 settings_dialog.py — 全局设置对话框

**Files:**
- Create: `settings_dialog.py`

- [ ] **Step 1: 实现 settings_dialog.py**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
全局设置对话框
管理图片模板、数字模板和其他全局设置
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import json


SETTINGS_FILE = 'settings.json'
TEMPLATES_DIR = 'templates'
DIGITS_DIR = os.path.join(TEMPLATES_DIR, 'digits')

# 全局模板项配置
TEMPLATE_ITEMS = [
    ('backpack_title_image', '背包定位', '用于在游戏窗口中定位背包位置'),
    ('execute_button_image', '执行按钮', '制造界面的「执行」按钮'),
    ('completion_image', '制造完成', '制造结束后出现的按钮'),
    ('organize_button_image', '整理背包', '背包界面的「整理」按钮'),
]


def load_settings():
    """加载全局设置"""
    defaults = {
        'backpack_title_image': '',
        'execute_button_image': '',
        'completion_image': '',
        'organize_button_image': '',
        'window_title_keyword': 'QI魔力',
        'cell_width': 40,
        'cell_height': 40,
        'grid_offset_x': 0,
        'grid_offset_y': 0,
        'digit_region': {'x': 20, 'y': 26, 'w': 20, 'h': 14},
        'icon_region': {'x': 2, 'y': 2, 'w': 36, 'h': 36},
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
            defaults.update(saved)
        except Exception:
            pass
    return defaults


def save_settings(settings):
    """保存全局设置"""
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


class SettingsDialog:
    """全局设置对话框"""

    def __init__(self, parent, screenshot_callback):
        """
        Args:
            parent: 父窗口
            screenshot_callback: 截图回调函数, 参数为 save_path, 返回 bool
        """
        self.result = None
        self.screenshot_callback = screenshot_callback
        self.settings = load_settings()

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("设置")
        self.dialog.geometry("500x550")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._create_widgets()
        self.dialog.wait_window()

    def _create_widgets(self):
        main_frame = ttk.Frame(self.dialog, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 图片模板区
        tmpl_label = ttk.LabelFrame(main_frame, text="图片模板", padding=10)
        tmpl_label.pack(fill=tk.X, pady=(0, 10))

        self.template_status = {}
        for key, name, desc in TEMPLATE_ITEMS:
            row = ttk.Frame(tmpl_label)
            row.pack(fill=tk.X, pady=3)

            ttk.Label(row, text=f"{name}:", width=10).pack(side=tk.LEFT)

            path = self.settings.get(key, '')
            has_file = bool(path) and os.path.exists(path)
            status_text = "已设置 ✓" if has_file else "未设置 ✗"
            status_label = ttk.Label(row, text=status_text, width=10)
            status_label.pack(side=tk.LEFT, padx=5)
            self.template_status[key] = status_label

            btn_text = "重新截图" if has_file else "截图"
            btn = ttk.Button(row, text=btn_text, width=8,
                           command=lambda k=key, n=name: self._capture_template(k, n))
            btn.pack(side=tk.LEFT, padx=5)

            ttk.Label(row, text=desc, foreground='gray').pack(side=tk.LEFT, padx=5)

        # 数字模板区
        digit_label = ttk.LabelFrame(main_frame, text="数字模板", padding=10)
        digit_label.pack(fill=tk.X, pady=(0, 10))

        digit_row = ttk.Frame(digit_label)
        digit_row.pack(fill=tk.X)
        ttk.Label(digit_row, text="0-9模板:", width=10).pack(side=tk.LEFT)

        digits_exist = all(
            os.path.exists(os.path.join(DIGITS_DIR, f'{d}.png')) for d in range(10)
        )
        digit_status = "已设置 ✓" if digits_exist else "未设置 ✗"
        self.digit_status_label = ttk.Label(digit_row, text=digit_status, width=10)
        self.digit_status_label.pack(side=tk.LEFT, padx=5)

        ttk.Button(digit_row, text="截取数字", width=8,
                  command=self._capture_digits).pack(side=tk.LEFT, padx=5)
        ttk.Label(digit_row, text="逐个截取0-9数字", foreground='gray').pack(side=tk.LEFT, padx=5)

        # 其他设置区
        other_label = ttk.LabelFrame(main_frame, text="其他设置", padding=10)
        other_label.pack(fill=tk.X, pady=(0, 10))

        # 窗口标题关键字
        title_row = ttk.Frame(other_label)
        title_row.pack(fill=tk.X, pady=3)
        ttk.Label(title_row, text="窗口标题关键字:", width=14).pack(side=tk.LEFT)
        self.title_var = tk.StringVar(value=self.settings.get('window_title_keyword', 'QI魔力'))
        ttk.Entry(title_row, textvariable=self.title_var, width=20).pack(side=tk.LEFT, padx=5)

        # 格子尺寸
        size_row = ttk.Frame(other_label)
        size_row.pack(fill=tk.X, pady=3)
        ttk.Label(size_row, text="格子宽度:", width=14).pack(side=tk.LEFT)
        self.cell_w_var = tk.IntVar(value=self.settings.get('cell_width', 40))
        ttk.Spinbox(size_row, from_=20, to=100, textvariable=self.cell_w_var, width=6).pack(side=tk.LEFT, padx=5)
        ttk.Label(size_row, text="高度:").pack(side=tk.LEFT, padx=(10, 0))
        self.cell_h_var = tk.IntVar(value=self.settings.get('cell_height', 40))
        ttk.Spinbox(size_row, from_=20, to=100, textvariable=self.cell_h_var, width=6).pack(side=tk.LEFT, padx=5)

        # 按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(15, 0))
        ttk.Button(btn_frame, text="保存", command=self._save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)

    def _capture_template(self, key, name):
        """截取模板图片"""
        os.makedirs(TEMPLATES_DIR, exist_ok=True)
        filename = key.replace('_image', '') + '.png'
        save_path = os.path.join(TEMPLATES_DIR, filename)

        self.dialog.withdraw()
        success = self.screenshot_callback(save_path)
        self.dialog.deiconify()

        if success and os.path.exists(save_path):
            self.settings[key] = save_path
            self.template_status[key].config(text="已设置 ✓")

    def _capture_digits(self):
        """逐个截取0-9数字模板"""
        os.makedirs(DIGITS_DIR, exist_ok=True)

        self.dialog.withdraw()
        for digit in range(10):
            save_path = os.path.join(DIGITS_DIR, f'{digit}.png')
            messagebox.showinfo("截取数字", f"请准备截取数字 {digit}\n点击确定后开始框选")
            success = self.screenshot_callback(save_path)
            if not success:
                self.dialog.deiconify()
                return
        self.dialog.deiconify()

        digits_exist = all(
            os.path.exists(os.path.join(DIGITS_DIR, f'{d}.png')) for d in range(10)
        )
        if digits_exist:
            self.digit_status_label.config(text="已设置 ✓")

    def _save(self):
        """保存设置"""
        self.settings['window_title_keyword'] = self.title_var.get()
        self.settings['cell_width'] = self.cell_w_var.get()
        self.settings['cell_height'] = self.cell_h_var.get()
        save_settings(self.settings)
        self.result = self.settings
        self.dialog.destroy()
```

- [ ] **Step 2: Commit**

```bash
git add settings_dialog.py
git commit -m "新增全局设置对话框，管理图片模板和参数配置"
```

---

### Task 8: 创建 recipe_dialog.py — 配方编辑对话框

**Files:**
- Create: `recipe_dialog.py`

- [ ] **Step 1: 实现 recipe_dialog.py**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配方编辑对话框
支持配方名称、等待时间、整理频率和材料列表的配置
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
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
        self.materials = []  # [(image_path, quantity)]
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
        qty_spin = ttk.Spinbox(row, from_=1, to=80, textvariable=qty_var, width=5)
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

        self.dialog.withdraw()
        success = self.screenshot_callback(save_path)
        self.dialog.deiconify()

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

            if image_path != target_path:
                import shutil
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
```

- [ ] **Step 2: Commit**

```bash
git add recipe_dialog.py
git commit -m "新增配方编辑对话框，支持材料截图和数量配置"
```

---

### Task 9: 重写 main_gui.py — 主界面

**Files:**
- Rewrite: `main_gui.py`

- [ ] **Step 1: 重写 main_gui.py**

```python
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

        # 初始化管理器
        self.settings = load_settings()
        self.recipe_manager = RecipeManager('recipes')
        self.window_manager = WindowManager()
        self.digit_recognizer = DigitRecognizer('templates/digits')
        self.backpack_reader = BackpackReader(self.digit_recognizer, self.settings)
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
        # 顶部: 窗口绑定 + 设置
        top_frame = ttk.Frame(self.root, padding=5)
        top_frame.pack(fill=tk.X)

        ttk.Label(top_frame, text="游戏窗口:").pack(side=tk.LEFT)
        self.bind_label = ttk.Label(top_frame, text="未绑定", foreground='red')
        self.bind_label.pack(side=tk.LEFT, padx=10)
        ttk.Button(top_frame, text="点击选择窗口",
                  command=self._pick_window).pack(side=tk.LEFT, padx=5)

        ttk.Button(top_frame, text="设置",
                  command=self._open_settings).pack(side=tk.RIGHT, padx=5)

        ttk.Separator(self.root, orient=tk.HORIZONTAL).pack(fill=tk.X)

        # 主体区域
        body = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
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
        status_frame = ttk.Frame(self.root, padding=3)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Separator(self.root, orient=tk.HORIZONTAL).pack(fill=tk.X, side=tk.BOTTOM)

        self.status_label = ttk.Label(status_frame, text="就绪")
        self.status_label.pack(side=tk.LEFT)

        hotkey_text = self.hotkey_manager.get_status_text()
        self.hotkey_label = ttk.Label(status_frame, text=f"热键: {hotkey_text}")
        self.hotkey_label.pack(side=tk.RIGHT)

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
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_label.config(text="已停止")

    def _update_stats(self):
        """定时更新统计信息"""
        if self.craft_engine.is_running:
            self.stats_label.config(
                text=f"成功: {self.craft_engine.success_count} 次 | "
                     f"失败: {self.craft_engine.fail_count} 次"
            )
            self.root.after(1000, self._update_stats)
        else:
            # 制造结束
            self.is_running = False
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.status_label.config(text="就绪")
            self.stats_label.config(
                text=f"完成 - 成功: {self.craft_engine.success_count} 次 | "
                     f"失败: {self.craft_engine.fail_count} 次"
            )

    # ── 设置 ──

    def _open_settings(self):
        """打开设置对话框"""
        dialog = SettingsDialog(self.root, self._screenshot_region)
        if dialog.result:
            self.settings = dialog.result
            # 重新初始化依赖设置的组件
            self.digit_recognizer = DigitRecognizer('templates/digits')
            self.backpack_reader = BackpackReader(self.digit_recognizer, self.settings)
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
            # 创建全屏截图覆盖层
            overlay = tk.Toplevel(self.root)
            overlay.attributes('-fullscreen', True)
            overlay.attributes('-topmost', True)
            overlay.configure(cursor='cross')

            # 截取全屏作为背景
            screenshot = take_screenshot()
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
                    os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else '.', exist_ok=True)
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
            return state['success']

        except Exception as e:
            print(f"截图失败: {e}")
            return False

    # ── 日志 ──

    def _log_message(self, message):
        """添加日志消息 (线程安全)"""
        timestamp = time.strftime('%H:%M:%S')
        self.root.after(0, self._append_log, f"[{timestamp}] {message}")

    def _append_log(self, text):
        """向日志文本框追加内容"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, text + '\n')
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    # ── 清理 ──

    def _on_close(self):
        """窗口关闭"""
        if self.is_running:
            self.craft_engine.stop()
        self.hotkey_manager.cleanup()
        self.root.destroy()
```

- [ ] **Step 2: Commit**

```bash
git add main_gui.py
git commit -m "重写主界面为魔力宝贝制造助手，集成配方管理和制造控制"
```

---

### Task 10: 更新 start_gui.py 和 build_exe.py

**Files:**
- Modify: `start_gui.py`
- Modify: `build_exe.py`

- [ ] **Step 1: 更新 start_gui.py**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
魔力宝贝制造助手 启动脚本
"""

import sys
import os
import tkinter as tk
from tkinter import messagebox


def check_dependencies():
    """检查依赖项"""
    missing_deps = []

    try:
        import cv2
    except ImportError:
        missing_deps.append("opencv-python")

    try:
        import pyautogui
    except ImportError:
        missing_deps.append("pyautogui")

    try:
        import numpy
    except ImportError:
        missing_deps.append("numpy")

    try:
        import PIL
    except ImportError:
        missing_deps.append("Pillow")

    try:
        import keyboard
    except ImportError:
        missing_deps.append("keyboard")

    try:
        import mss
    except ImportError:
        missing_deps.append("mss")

    try:
        import win32gui
    except ImportError:
        missing_deps.append("pywin32")

    if missing_deps:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "依赖项缺失",
            f"缺少以下依赖项:\n{chr(10).join(missing_deps)}\n\n"
            f"请运行以下命令安装:\n"
            f"pip install {' '.join(missing_deps)}"
        )
        return False

    return True


def main():
    """主函数"""
    if not check_dependencies():
        return

    root = None
    try:
        from main_gui import CraftAssistantGUI

        root = tk.Tk()
        app = CraftAssistantGUI(root)
        root.mainloop()

    except Exception as e:
        if root:
            try:
                root.destroy()
            except Exception:
                pass
        error_root = tk.Tk()
        error_root.withdraw()
        messagebox.showerror("启动错误", f"程序启动失败:\n{str(e)}")
        error_root.destroy()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 更新 build_exe.py 中的模块列表和输出名称**

需要修改以下几处:

1. `required_files` 检查列表改为 `['main_gui.py', 'start_gui.py', 'craft_engine.py', 'recipe_manager.py']`
2. `--name` 从 `按键小精灵` 改为 `魔力宝贝制造助手`
3. `--hidden-import` 列表替换为新模块:
   - 移除: `models`, `dialogs`, `execution_engine`, `ui_editors`, `file_manager`
   - 添加: `craft_engine`, `recipe_manager`, `recipe_dialog`, `settings_dialog`, `window_manager`, `backpack_reader`, `digit_recognizer`, `win32gui`, `win32api`
4. `create_spec_file()` 中 `hiddenimports` 做同样更新

- [ ] **Step 3: Commit**

```bash
git add start_gui.py build_exe.py
git commit -m "更新启动脚本和打包脚本，适配魔力宝贝制造助手"
```

---

### Task 11: 端到端验证

- [ ] **Step 1: 确认所有文件存在且无导入错误**

```bash
cd /Volumes/T7/work/anjian
python -c "
import recipe_manager
import digit_recognizer
import settings_dialog
print('所有非Windows模块导入成功')
"
```

注意: `window_manager.py`, `backpack_reader.py`, `craft_engine.py`, `main_gui.py` 依赖 Windows 库 (win32gui/pyautogui)，在 macOS 上无法导入完整功能，需要在 Windows 上测试。

- [ ] **Step 2: 运行单元测试**

```bash
python -m pytest tests/ -v
```

预期: 所有测试 PASS

- [ ] **Step 3: Commit 测试通过状态**

如果有修复，提交修复。

- [ ] **Step 4: 更新 .gitignore**

在 `.gitignore` 中添加:
```
templates/
recipes/
settings.json
hotkey_config.json
.superpowers/
```

- [ ] **Step 5: 最终 Commit**

```bash
git add .gitignore
git commit -m "添加gitignore，排除运行时生成的配置和模板目录"
```

---

## 验收清单

- [ ] 旧通用模块已删除 (models.py, execution_engine.py, ui_editors.py, dialogs.py, file_manager.py)
- [ ] 配方管理: 新建、编辑、删除、保存、加载配方
- [ ] 窗口绑定: 点击选择游戏窗口，获取句柄和坐标
- [ ] 背包识别: 定位背包、切割20格、识别物品图标
- [ ] 数字识别: 0-9模板匹配识别物品数量
- [ ] 制造引擎: 完整制造循环（扫描→匹配→点击→执行→等待→完成→整理）
- [ ] 全局设置: 图片模板管理、数字模板管理、参数配置
- [ ] 热键: 开始/停止全局快捷键
- [ ] 日志: 实时显示制造过程
- [ ] 打包: build_exe.py 可正确打包为 exe
