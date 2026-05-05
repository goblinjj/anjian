# 自定义工具 (Custom Tool) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在"魔力宝贝制造助手"中新增"自定义工具"功能, 用户可在 GUI 内编排 8 种动作步骤的任意组合, 保存后挂在左侧树新增的"自定义"分类下, 支持循环 / 单次两种运行模式。

**Architecture:** 数据层 (`custom_tool_manager.py`) + 执行引擎 (`custom_tool_engine.py`) + UI (`custom_tool_dialog.py` 含主对话框 + 5 种步骤子对话框) 三层分离, 仿现有 `recipe_manager.py` / `LoopHealingEngine` / `LoopHealingDialog` 的模式。底层 `bg_input.py` 增加 `post_right_click` / `post_text` 两个能力。`main_gui.py` 仅做"接线": 在树里加新分类, 在按钮回调里加 `'custom'` 分支。

**Tech Stack:** Python 3.11, tkinter / ttk, OpenCV 模板匹配, Win32 PostMessage (`bg_input`), JSON 配置。

**Spec:** `docs/superpowers/specs/2026-05-05-custom-tool-design.md`

**Testing strategy:** 用户明确"这次不需要测试", GitHub Actions 编译后在 Windows 手动验证。每个任务以 `python start_gui.py` 冒烟 (导入不报错 / GUI 能起) + commit 收尾。

---

## Task 1: bg_input.py — 新增 post_right_click 与 post_text

**Files:**
- Modify: `bg_input.py` (在文件末尾追加)

- [ ] **Step 1: 在 bg_input.py 顶部常量区添加右键消息常量**

在 `MK_LBUTTON = 0x0001` 那一行之后插入:

```python
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
MK_RBUTTON = 0x0002
```

- [ ] **Step 2: 在文件末尾追加 post_right_click 函数**

```python
def post_right_click(hwnd, screen_x, screen_y, pre_delay=0.0, hold_time=0.05):
    """右键单击 (MOVE → 前置延迟 → R-DOWN → 持续时间 → R-UP)。"""
    cx, cy = _screen_to_client(hwnd, screen_x, screen_y)
    lp = _pack_lparam(cx, cy)
    _post(hwnd, WM_MOUSEMOVE, 0, lp)
    if pre_delay > 0:
        time.sleep(pre_delay)
    _post(hwnd, WM_RBUTTONDOWN, MK_RBUTTON, lp)
    time.sleep(hold_time)
    _post(hwnd, WM_RBUTTONUP, 0, lp)
```

- [ ] **Step 3: 在 post_right_click 之后追加 post_text 函数**

```python
def post_text(hwnd, text, char_interval=0.03):
    """逐字符 post_key, 仅 ASCII 小写字母 / 数字 / 空格。

    上层 (CustomToolDialog) 已经校验过非 ASCII / 大写字母, 这里只做兜底:
    无法映射的字符直接跳过, 不抛异常打断序列。
    """
    for c in text:
        try:
            post_key(hwnd, c)
        except ValueError:
            continue
        time.sleep(char_interval)
```

- [ ] **Step 4: 冒烟检查 — import bg_input 不报错**

Run: `python -c "import bg_input; print(bg_input.post_right_click, bg_input.post_text)"`
Expected: 打印两个函数引用, 无 ImportError / SyntaxError。

- [ ] **Step 5: Commit**

```bash
git add bg_input.py
git commit -m "bg_input: 新增右键单击 + 文本逐字符输入"
```

---

## Task 2: custom_tool_manager.py — 自定义工具的 CRUD

**Files:**
- Create: `custom_tool_manager.py`
- Create: `custom_tools/` 目录 (空目录, 由代码 `os.makedirs(exist_ok=True)` 创建)

- [ ] **Step 1: 创建 custom_tool_manager.py 文件头与类骨架**

```python
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
```

- [ ] **Step 2: 添加 _sanitize_name 与 _json_path / _img_dir 辅助**

在类内部追加:

```python
    @staticmethod
    def sanitize_name(name):
        """去掉非法字符并 trim, 返回安全名 (空字符串表示无效)。"""
        if not name:
            return ''
        cleaned = _INVALID_CHARS.sub('', name).strip()
        return cleaned

    def _json_path(self, name):
        return os.path.join(self.tools_dir, f'{name}.json')

    def img_dir(self, name):
        """该工具的图片模板专属子目录 (相对路径, 与 image_path 字段对齐)。"""
        return os.path.join(self.tools_dir, name)
```

- [ ] **Step 3: 添加 list_tools 方法**

```python
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
```

- [ ] **Step 4: 添加 exists / load 方法**

```python
    def exists(self, name):
        return os.path.isfile(self._json_path(name))

    def load(self, name):
        """加载工具数据。文件不存在抛 FileNotFoundError。"""
        with open(self._json_path(name), 'r', encoding='utf-8') as f:
            return json.load(f)
```

- [ ] **Step 5: 添加 save 方法 (含重命名时的目录搬迁)**

```python
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
                        step['image_path'] = p.replace(old_dir, new_dir, 1)
            old_json = self._json_path(original_name)
            if os.path.isfile(old_json):
                os.remove(old_json)

        tool_data['name'] = new_name
        tool_data.setdefault('version', '1.0')
        with open(self._json_path(new_name), 'w', encoding='utf-8') as f:
            json.dump(tool_data, f, ensure_ascii=False, indent=2)
        return new_name
```

- [ ] **Step 6: 添加 delete 方法 (同时删图片子目录)**

```python
    def delete(self, name):
        """删工具 JSON + 图片子目录。"""
        json_path = self._json_path(name)
        if os.path.isfile(json_path):
            os.remove(json_path)
        sub_dir = self.img_dir(name)
        if os.path.isdir(sub_dir):
            shutil.rmtree(sub_dir, ignore_errors=True)
```

- [ ] **Step 7: 冒烟检查 — 创建+列表+读取+删除一遍**

Run:
```bash
python -c "
from custom_tool_manager import CustomToolManager
m = CustomToolManager('/tmp/_test_ct')
m.save({'name': 'test', 'mode': 'once', 'steps': [{'type':'wait','ms':100}]})
assert 'test' in m.list_tools()
data = m.load('test')
assert data['mode'] == 'once'
m.delete('test')
assert not m.exists('test')
print('ok')
"
```
Expected: 输出 `ok`, 无异常。完成后 `rm -rf /tmp/_test_ct`。

- [ ] **Step 8: Commit**

```bash
git add custom_tool_manager.py
git commit -m "custom_tool: 新增 CustomToolManager (CRUD + 改名搬目录)"
```

---

## Task 3: custom_tool_engine.py — 执行引擎

**Files:**
- Create: `custom_tool_engine.py`

- [ ] **Step 1: 创建文件头 + 类骨架 + 线程入口**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""自定义工具执行引擎。

线程模型/重试模式仿 LoopHealingEngine: daemon thread + should_stop 旗标,
分片睡眠及时响应停止, 每步实时 get_window_rect 容忍窗口移动。
"""

import time
import threading
import cv2
import numpy as np
from PIL import Image

import bg_input
import screenshot_util
from screenshot_util import take_screenshot


class CustomToolEngine:
    def __init__(self, window_manager, status_callback=None):
        self.window_manager = window_manager
        self.status_callback = status_callback
        self.should_stop = False
        self.is_running = False
        self._thread = None

    def start(self, tool_data):
        if self.is_running:
            return
        self.should_stop = False
        self.is_running = True
        self._thread = threading.Thread(
            target=self._run, args=(tool_data,), daemon=True)
        self._thread.start()

    def stop(self):
        self.should_stop = True

    def _log(self, message):
        if self.status_callback:
            self.status_callback(message)
```

- [ ] **Step 2: 添加 _run 主流程 (mode 分支)**

在类末尾追加:

```python
    def _run(self, tool_data):
        screenshot_util.set_capture_hwnd(self.window_manager.hwnd)
        try:
            if not self.window_manager.is_window_valid():
                self._log("错误: 未绑定游戏窗口")
                return
            mode = tool_data.get('mode', 'loop')
            steps = tool_data.get('steps', [])
            name = tool_data.get('name', '?')
            self._log(f"启动自定义工具: {name} (模式={mode}, 步骤={len(steps)})")

            if mode == 'once':
                self._execute_steps(steps)
            else:
                count = 0
                while not self.should_stop:
                    count += 1
                    self._log(f"[第{count}轮]")
                    if not self._execute_steps(steps):
                        break
        except Exception as e:
            self._log(f"自定义工具出错: {e}")
        finally:
            screenshot_util.set_capture_hwnd(None)
            self.is_running = False
            self._log("自定义工具已停止")
```

- [ ] **Step 3: 添加 _execute_steps + 总分发 _execute_one**

```python
    def _execute_steps(self, steps):
        for i, step in enumerate(steps):
            if self.should_stop:
                return False
            ok = self._execute_one(i, step)
            if not ok:
                return False
        return True

    def _execute_one(self, idx, step):
        t = step.get('type')
        if t == 'mouse_move':
            return self._do_mouse(idx, step, 'move')
        if t == 'mouse_click':
            return self._do_mouse(idx, step, 'click')
        if t == 'mouse_right_click':
            return self._do_mouse(idx, step, 'right_click')
        if t == 'mouse_double_click':
            return self._do_mouse(idx, step, 'double_click')
        if t == 'key_press':
            return self._do_key_press(idx, step)
        if t == 'hotkey':
            return self._do_hotkey(idx, step)
        if t == 'image_search':
            return self._do_image_search(idx, step)
        if t == 'wait':
            return self._do_wait(idx, step)
        self._log(f"  步骤{idx+1}: 未知类型 {t}, 跳过")
        return True
```

- [ ] **Step 4: 添加 _resolve_offset 与鼠标动作 _do_mouse**

```python
    def _resolve_offset(self, offset_x, offset_y):
        rect = self.window_manager.get_window_rect()
        if not rect:
            return None
        cx = rect[0] + rect[2] // 2
        cy = rect[1] + rect[3] // 2
        return cx + offset_x, cy + offset_y

    def _do_mouse(self, idx, step, action):
        target = self._resolve_offset(
            step.get('offset_x', 0), step.get('offset_y', 0))
        if not target:
            self._log(f"  步骤{idx+1}: 无法获取窗口坐标")
            return False
        x, y = target
        hwnd = self.window_manager.hwnd
        if action == 'move':
            bg_input.post_move(hwnd, x, y)
        elif action == 'click':
            bg_input.post_click(hwnd, x, y)
        elif action == 'right_click':
            bg_input.post_right_click(hwnd, x, y)
        elif action == 'double_click':
            bg_input.post_double_click(hwnd, x, y)
        self._log(f"  步骤{idx+1}: {action} ({x},{y})")
        return True
```

- [ ] **Step 5: 添加 _do_key_press / _do_hotkey**

```python
    def _do_key_press(self, idx, step):
        hwnd = self.window_manager.hwnd
        mode = step.get('input_mode', 'single')
        if mode == 'single':
            key = step.get('key', '')
            if not key:
                self._log(f"  步骤{idx+1}: 单键为空, 跳过")
                return True
            bg_input.post_key(hwnd, key)
            self._log(f"  步骤{idx+1}: 按键 {key}")
        else:
            text = step.get('text', '')
            interval = step.get('char_interval_ms', 30) / 1000.0
            bg_input.post_text(hwnd, text, char_interval=interval)
            self._log(f"  步骤{idx+1}: 输入文本 \"{text}\"")
        return True

    def _do_hotkey(self, idx, step):
        keys = step.get('keys', [])
        if not keys:
            self._log(f"  步骤{idx+1}: 组合键为空, 跳过")
            return True
        bg_input.post_hotkey(self.window_manager.hwnd, *keys)
        self._log(f"  步骤{idx+1}: 组合键 {'+'.join(keys)}")
        return True
```

- [ ] **Step 6: 添加 _do_wait (分片以响应停止)**

```python
    def _do_wait(self, idx, step):
        ms = step.get('ms', 500)
        self._log(f"  步骤{idx+1}: 等待 {ms}ms")
        deadline = time.time() + ms / 1000.0
        while time.time() < deadline:
            if self.should_stop:
                return False
            time.sleep(0.05)
        return True
```

- [ ] **Step 7: 添加 _find_template 模板匹配辅助**

```python
    def _find_template(self, template_path, window_rect, threshold):
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

        if max_val >= threshold:
            th, tw = tmpl.shape[:2]
            cx = window_rect[0] + max_loc[0] + tw // 2
            cy = window_rect[1] + max_loc[1] + th // 2
            return (cx, cy, max_val)
        return None
```

- [ ] **Step 8: 添加 _do_image_search (含 retry 流程)**

```python
    _IMAGE_ACTION_MAP = {
        'click': bg_input.post_click,
        'double_click': bg_input.post_double_click,
        'right_click': bg_input.post_right_click,
        'move': bg_input.post_move,
    }

    def _apply_image_action(self, target_x, target_y, on_found):
        if on_found == 'none':
            return
        fn = self._IMAGE_ACTION_MAP.get(on_found)
        if fn:
            fn(self.window_manager.hwnd, target_x, target_y)

    def _do_image_search(self, idx, step):
        path = step.get('image_path', '')
        if not path:
            self._log(f"  步骤{idx+1}: image_search 无图片路径, 跳过")
            return True
        threshold = step.get('threshold', 0.7)
        on_found = step.get('on_found', 'click')
        on_not_found = step.get('on_not_found', 'skip')
        retry_seconds = step.get('retry_seconds', 3.0)
        ox = step.get('offset_x', 0)
        oy = step.get('offset_y', 0)

        rect = self.window_manager.get_window_rect()
        if not rect:
            self._log(f"  步骤{idx+1}: 无法获取窗口坐标")
            return False

        pos = self._find_template(path, rect, threshold)
        if pos:
            tx, ty = pos[0] + ox, pos[1] + oy
            self._apply_image_action(tx, ty, on_found)
            self._log(f"  步骤{idx+1}: 图片找到 → {on_found} ({tx},{ty})")
            return True

        if on_not_found == 'skip':
            self._log(f"  步骤{idx+1}: 图片未找到, 直接跳过")
            return True

        # retry_skip / retry_stop
        self._log(f"  步骤{idx+1}: 未找到, 重试 {retry_seconds:.1f}秒...")
        deadline = time.time() + retry_seconds
        while not self.should_stop and time.time() < deadline:
            time.sleep(0.5)
            rect = self.window_manager.get_window_rect()
            if not rect:
                return False
            pos = self._find_template(path, rect, threshold)
            if pos:
                tx, ty = pos[0] + ox, pos[1] + oy
                self._apply_image_action(tx, ty, on_found)
                self._log(f"  步骤{idx+1}: 重试找到 → {on_found} ({tx},{ty})")
                return True

        if self.should_stop:
            return False
        if on_not_found == 'retry_stop':
            self._log(f"  步骤{idx+1}: 重试超时, 停止整个工具")
            return False
        self._log(f"  步骤{idx+1}: 重试超时, 跳过本步")
        return True
```

- [ ] **Step 9: 冒烟检查 — 模块导入正常**

Run: `python -c "from custom_tool_engine import CustomToolEngine; print(CustomToolEngine)"`
Expected: 打印 `<class 'custom_tool_engine.CustomToolEngine'>`, 无 ImportError。

- [ ] **Step 10: Commit**

```bash
git add custom_tool_engine.py
git commit -m "custom_tool: 新增 CustomToolEngine (8 种步骤分发 + 图片重试)"
```

---

## Task 4: custom_tool_dialog.py — 5 种步骤的子对话框

**Files:**
- Create: `custom_tool_dialog.py`

- [ ] **Step 1: 创建文件头 + 公共导入 + 步骤展示文本辅助**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""自定义工具编辑对话框 + 8 种步骤的子编辑器。"""

import os
import time
import tkinter as tk
from tkinter import ttk, messagebox

# 单键 Combobox 候选 (按键 alias 沿用 bg_input._SPECIAL_VK)
_SINGLE_KEY_PRESETS = [
    'enter', 'space', 'tab', 'esc', 'backspace',
    'delete', 'up', 'down', 'left', 'right',
    'home', 'end',
    'f1', 'f2', 'f3', 'f4', 'f5', 'f6',
    'f7', 'f8', 'f9', 'f10', 'f11', 'f12',
]

_MOUSE_TYPE_TITLES = {
    'mouse_move': '鼠标移动',
    'mouse_click': '鼠标左键',
    'mouse_right_click': '鼠标右键',
    'mouse_double_click': '鼠标双击',
}

_IMAGE_ACTION_LABELS = [
    ('click', '左键单击'),
    ('double_click', '左键双击'),
    ('right_click', '右键单击'),
    ('move', '仅移动'),
    ('none', '什么也不做'),
]

_IMAGE_NOT_FOUND_LABELS = [
    ('skip', '跳过本步'),
    ('retry_skip', '重试后跳过本步'),
    ('retry_stop', '重试后停止整个工具'),
]


def step_summary(step):
    """生成 #N 行右半部分的摘要文本 (不含 #N 前缀)。"""
    t = step.get('type')
    if t in _MOUSE_TYPE_TITLES:
        ox = step.get('offset_x', 0)
        oy = step.get('offset_y', 0)
        return f"{_MOUSE_TYPE_TITLES[t]:<6}  偏移({ox}, {oy})"
    if t == 'key_press':
        if step.get('input_mode') == 'text':
            return f"键盘输入  文本: \"{step.get('text', '')}\""
        return f"键盘输入  单键: {step.get('key', '')}"
    if t == 'hotkey':
        return f"组合键    {' + '.join(step.get('keys', []))}"
    if t == 'image_search':
        img = os.path.basename(step.get('image_path', '')) or '?'
        on_found = dict(_IMAGE_ACTION_LABELS).get(
            step.get('on_found', 'click'), '?')
        on_nf = dict(_IMAGE_NOT_FOUND_LABELS).get(
            step.get('on_not_found', 'skip'), '?')
        ox = step.get('offset_x', 0)
        oy = step.get('offset_y', 0)
        return f"图片查询  {img}  找到→{on_found} 偏移({ox},{oy})  未找到→{on_nf}"
    if t == 'wait':
        return f"等待      {step.get('ms', 500)} ms"
    return f"<未知步骤 {t}>"
```

- [ ] **Step 2: 添加 MouseStepDialog (4 种鼠标类型共享)**

在文件末尾追加:

```python
class MouseStepDialog:
    """鼠标移动 / 左键 / 右键 / 双击 共享的偏移编辑对话框。"""

    def __init__(self, parent, step_type, initial=None):
        self.result = None
        self._step_type = step_type
        title = _MOUSE_TYPE_TITLES.get(step_type, '鼠标动作')
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"编辑[{title}]")
        self.dialog.geometry("320x140")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        initial = initial or {}
        frame = ttk.Frame(self.dialog, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        row = ttk.Frame(frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="X 偏移:", width=8).pack(side=tk.LEFT)
        self.x_var = tk.IntVar(value=initial.get('offset_x', 0))
        ttk.Spinbox(row, from_=-2000, to=2000, increment=10,
                    textvariable=self.x_var, width=8).pack(side=tk.LEFT)

        row2 = ttk.Frame(frame)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="Y 偏移:", width=8).pack(side=tk.LEFT)
        self.y_var = tk.IntVar(value=initial.get('offset_y', 0))
        ttk.Spinbox(row2, from_=-2000, to=2000, increment=10,
                    textvariable=self.y_var, width=8).pack(side=tk.LEFT)

        ttk.Label(frame, text="(相对游戏窗口中心, 正X右/正Y下)",
                  foreground='gray').pack(anchor=tk.W, pady=(4, 0))

        btn_row = ttk.Frame(frame)
        btn_row.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(btn_row, text="确定",
                   command=self._ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_row, text="取消",
                   command=self.dialog.destroy).pack(side=tk.RIGHT)

        self.dialog.wait_window()

    def _ok(self):
        self.result = {
            'type': self._step_type,
            'offset_x': self.x_var.get(),
            'offset_y': self.y_var.get(),
        }
        self.dialog.destroy()
```

- [ ] **Step 3: 添加 KeyPressStepDialog (单键 / 文本切换)**

```python
class KeyPressStepDialog:
    """键盘输入: 单键 或 ASCII 文本串。"""

    def __init__(self, parent, initial=None):
        self.result = None
        initial = initial or {}
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("编辑[键盘输入]")
        self.dialog.geometry("420x260")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        frame = ttk.Frame(self.dialog, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        # 模式切换
        mode_row = ttk.Frame(frame)
        mode_row.pack(fill=tk.X)
        ttk.Label(mode_row, text="模式:").pack(side=tk.LEFT)
        self.mode_var = tk.StringVar(
            value=initial.get('input_mode', 'single'))
        ttk.Radiobutton(mode_row, text="单键", value='single',
                        variable=self.mode_var,
                        command=self._refresh_mode).pack(side=tk.LEFT, padx=8)
        ttk.Radiobutton(mode_row, text="文本串", value='text',
                        variable=self.mode_var,
                        command=self._refresh_mode).pack(side=tk.LEFT)

        # 单键面板
        self.single_frame = ttk.LabelFrame(frame, text="单键", padding=8)
        ttk.Label(self.single_frame, text="按键:").pack(side=tk.LEFT)
        self.key_var = tk.StringVar(value=initial.get('key', 'enter'))
        ttk.Combobox(self.single_frame, textvariable=self.key_var,
                     values=_SINGLE_KEY_PRESETS, width=14).pack(
            side=tk.LEFT, padx=5)

        # 文本面板
        self.text_frame = ttk.LabelFrame(frame, text="文本串", padding=8)
        text_row = ttk.Frame(self.text_frame)
        text_row.pack(fill=tk.X)
        ttk.Label(text_row, text="文本:").pack(side=tk.LEFT)
        self.text_var = tk.StringVar(value=initial.get('text', ''))
        ttk.Entry(text_row, textvariable=self.text_var, width=30).pack(
            side=tk.LEFT, padx=5)
        ttk.Label(self.text_frame, text="仅 ASCII (不支持中文/大写)",
                  foreground='gray').pack(anchor=tk.W, pady=(4, 0))
        interval_row = ttk.Frame(self.text_frame)
        interval_row.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(interval_row, text="字间隔:").pack(side=tk.LEFT)
        self.interval_var = tk.IntVar(
            value=initial.get('char_interval_ms', 30))
        ttk.Spinbox(interval_row, from_=10, to=500, increment=10,
                    textvariable=self.interval_var, width=8).pack(
            side=tk.LEFT, padx=5)
        ttk.Label(interval_row, text="ms").pack(side=tk.LEFT)

        btn_row = ttk.Frame(frame)
        btn_row.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))
        ttk.Button(btn_row, text="确定",
                   command=self._ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_row, text="取消",
                   command=self.dialog.destroy).pack(side=tk.RIGHT)

        self._refresh_mode()
        self.dialog.wait_window()

    def _refresh_mode(self):
        if self.mode_var.get() == 'single':
            self.text_frame.pack_forget()
            self.single_frame.pack(fill=tk.X, pady=8)
        else:
            self.single_frame.pack_forget()
            self.text_frame.pack(fill=tk.X, pady=8)

    def _ok(self):
        mode = self.mode_var.get()
        if mode == 'single':
            key = self.key_var.get().strip()
            if not key:
                messagebox.showwarning("提示", "请填写按键名",
                                       parent=self.dialog)
                return
            self.result = {'type': 'key_press',
                           'input_mode': 'single', 'key': key}
        else:
            text = self.text_var.get()
            if not text:
                messagebox.showwarning("提示", "文本不能为空",
                                       parent=self.dialog)
                return
            for ch in text:
                if ord(ch) > 127:
                    messagebox.showwarning(
                        "提示", f"文本含非 ASCII 字符: {ch}",
                        parent=self.dialog)
                    return
                if 'A' <= ch <= 'Z':
                    messagebox.showwarning(
                        "提示", f"暂不支持大写字母: {ch} (请改用小写)",
                        parent=self.dialog)
                    return
            self.result = {
                'type': 'key_press', 'input_mode': 'text',
                'text': text, 'char_interval_ms': self.interval_var.get()}
        self.dialog.destroy()
```

- [ ] **Step 4: 添加 HotkeyStepDialog (含录制按钮)**

```python
class HotkeyStepDialog:
    """组合键, 输入框 + 录制按钮 (复用 keyboard.read_hotkey)。"""

    def __init__(self, parent, initial=None):
        self.result = None
        initial = initial or {}
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("编辑[组合键]")
        self.dialog.geometry("380x150")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        frame = ttk.Frame(self.dialog, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        row = ttk.Frame(frame)
        row.pack(fill=tk.X)
        ttk.Label(row, text="组合键:").pack(side=tk.LEFT)
        keys_init = '+'.join(initial.get('keys', []))
        self.combo_var = tk.StringVar(value=keys_init)
        ttk.Entry(row, textvariable=self.combo_var, width=20).pack(
            side=tk.LEFT, padx=5)
        self.record_btn = ttk.Button(row, text="录制", width=6,
                                     command=self._start_record)
        self.record_btn.pack(side=tk.LEFT, padx=5)

        ttk.Label(frame, text="例: ctrl+c / alt+f4 / ctrl+shift+s",
                  foreground='gray').pack(anchor=tk.W, pady=(8, 0))

        btn_row = ttk.Frame(frame)
        btn_row.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(btn_row, text="确定",
                   command=self._ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_row, text="取消",
                   command=self.dialog.destroy).pack(side=tk.RIGHT)

        self._recording = False
        self.dialog.wait_window()

    def _start_record(self):
        if self._recording:
            return
        self._recording = True
        self.record_btn.config(text="按键中...", state=tk.DISABLED)
        import threading
        threading.Thread(target=self._record_thread, daemon=True).start()

    def _record_thread(self):
        try:
            import keyboard
            key = keyboard.read_hotkey(suppress=False)
            self.dialog.after(0, self._on_recorded, key)
        except Exception:
            self.dialog.after(0, self._on_record_failed)

    def _on_recorded(self, key):
        self._recording = False
        self.combo_var.set(key)
        self.record_btn.config(text="录制", state=tk.NORMAL)

    def _on_record_failed(self):
        self._recording = False
        self.record_btn.config(text="录制", state=tk.NORMAL)

    def _ok(self):
        raw = self.combo_var.get().strip().lower()
        if not raw:
            messagebox.showwarning("提示", "组合键不能为空",
                                   parent=self.dialog)
            return
        keys = [k.strip() for k in raw.split('+') if k.strip()]
        if len(keys) < 2:
            messagebox.showwarning(
                "提示", "组合键至少要有 2 个键 (单键请用'键盘输入'步骤)",
                parent=self.dialog)
            return
        # 校验每个键能被 bg_input 识别
        import bg_input
        for k in keys:
            try:
                bg_input._vk_of(k)
            except ValueError:
                messagebox.showwarning(
                    "提示", f"无法识别的按键: {k}", parent=self.dialog)
                return
        self.result = {'type': 'hotkey', 'keys': keys}
        self.dialog.destroy()
```

- [ ] **Step 5: 添加 ImageSearchStepDialog (三段式)**

```python
class ImageSearchStepDialog:
    """图片查询: 图片模板 + 找到后动作 + 找不到处理。

    Args:
        screenshot_callback(save_path) -> bool: 截图回调, 复用 main_gui 的
        image_dir: 该工具的图片专属子目录 (相对路径)
        on_image_added(path): 父对话框收集本次会话新增的图片路径以便取消时清理
    """

    def __init__(self, parent, screenshot_callback, image_dir,
                 on_image_added=None, initial=None):
        self.result = None
        self._screenshot_cb = screenshot_callback
        self._image_dir = image_dir
        self._on_image_added = on_image_added or (lambda p: None)
        initial = initial or {}

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("编辑[图片查询]")
        self.dialog.geometry("520x440")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        main = ttk.Frame(self.dialog, padding=12)
        main.pack(fill=tk.BOTH, expand=True)

        # 图片模板
        img_frame = ttk.LabelFrame(main, text="图片模板", padding=8)
        img_frame.pack(fill=tk.X, pady=(0, 8))
        self._image_path = initial.get('image_path', '')
        self.img_status = ttk.Label(
            img_frame, text=self._format_img_status())
        self.img_status.pack(side=tk.LEFT)
        ttk.Button(img_frame, text="截图", width=6,
                   command=self._capture).pack(side=tk.RIGHT, padx=2)

        # 找到后
        found_frame = ttk.LabelFrame(main, text="找到后动作", padding=8)
        found_frame.pack(fill=tk.X, pady=(0, 8))
        action_row = ttk.Frame(found_frame)
        action_row.pack(fill=tk.X)
        ttk.Label(action_row, text="动作:").pack(side=tk.LEFT)
        self.action_var = tk.StringVar(
            value=dict(_IMAGE_ACTION_LABELS).get(
                initial.get('on_found', 'click'), '左键单击'))
        ttk.Combobox(action_row, textvariable=self.action_var,
                     values=[label for _, label in _IMAGE_ACTION_LABELS],
                     state='readonly', width=12).pack(side=tk.LEFT, padx=5)
        offset_row = ttk.Frame(found_frame)
        offset_row.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(offset_row, text="偏移 X:").pack(side=tk.LEFT)
        self.ox_var = tk.IntVar(value=initial.get('offset_x', 0))
        ttk.Spinbox(offset_row, from_=-1000, to=1000, increment=5,
                    textvariable=self.ox_var, width=7).pack(
            side=tk.LEFT, padx=5)
        ttk.Label(offset_row, text="Y:").pack(side=tk.LEFT, padx=(10, 0))
        self.oy_var = tk.IntVar(value=initial.get('offset_y', 0))
        ttk.Spinbox(offset_row, from_=-1000, to=1000, increment=5,
                    textvariable=self.oy_var, width=7).pack(
            side=tk.LEFT, padx=5)
        ttk.Label(offset_row, text="(相对匹配中心)",
                  foreground='gray').pack(side=tk.LEFT, padx=5)

        # 找不到
        nf_frame = ttk.LabelFrame(main, text="找不到时", padding=8)
        nf_frame.pack(fill=tk.X, pady=(0, 8))
        nf_row = ttk.Frame(nf_frame)
        nf_row.pack(fill=tk.X)
        ttk.Label(nf_row, text="处理:").pack(side=tk.LEFT)
        self.nf_var = tk.StringVar(
            value=dict(_IMAGE_NOT_FOUND_LABELS).get(
                initial.get('on_not_found', 'skip'), '跳过本步'))
        ttk.Combobox(nf_row, textvariable=self.nf_var,
                     values=[label for _, label in _IMAGE_NOT_FOUND_LABELS],
                     state='readonly', width=20).pack(side=tk.LEFT, padx=5)

        retry_row = ttk.Frame(nf_frame)
        retry_row.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(retry_row, text="重试时长:").pack(side=tk.LEFT)
        self.retry_var = tk.DoubleVar(
            value=initial.get('retry_seconds', 3.0))
        ttk.Spinbox(retry_row, from_=0.5, to=30.0, increment=0.5,
                    textvariable=self.retry_var, width=7).pack(
            side=tk.LEFT, padx=5)
        ttk.Label(retry_row, text="秒").pack(side=tk.LEFT)
        ttk.Label(retry_row, text="匹配阈值:").pack(side=tk.LEFT, padx=(15, 0))
        self.threshold_var = tk.DoubleVar(
            value=initial.get('threshold', 0.7))
        ttk.Spinbox(retry_row, from_=0.5, to=0.95, increment=0.05,
                    textvariable=self.threshold_var, width=6).pack(
            side=tk.LEFT, padx=5)

        # 按钮
        btn_row = ttk.Frame(main)
        btn_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(btn_row, text="确定",
                   command=self._ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_row, text="取消",
                   command=self.dialog.destroy).pack(side=tk.RIGHT)

        self.dialog.wait_window()

    def _format_img_status(self):
        if self._image_path and os.path.exists(self._image_path):
            return f"已设置 ✓  {os.path.basename(self._image_path)}"
        return "未设置 ✗"

    def _capture(self):
        os.makedirs(self._image_dir, exist_ok=True)
        save_path = os.path.join(
            self._image_dir, f"img_{int(time.time()*1000)}.png")
        self.dialog.grab_release()
        self.dialog.withdraw()
        ok = self._screenshot_cb(save_path)
        self.dialog.deiconify()
        self.dialog.grab_set()
        if ok and os.path.exists(save_path):
            self._image_path = save_path
            self._on_image_added(save_path)
            self.img_status.config(text=self._format_img_status())

    def _ok(self):
        if not self._image_path or not os.path.exists(self._image_path):
            messagebox.showwarning("提示", "请先截图设置图片模板",
                                   parent=self.dialog)
            return
        # 中文 label → 英文 enum 反查
        action_label_to_id = {label: id_ for id_, label in _IMAGE_ACTION_LABELS}
        nf_label_to_id = {label: id_ for id_, label in _IMAGE_NOT_FOUND_LABELS}
        self.result = {
            'type': 'image_search',
            'image_path': self._image_path,
            'offset_x': self.ox_var.get(),
            'offset_y': self.oy_var.get(),
            'on_found': action_label_to_id.get(self.action_var.get(), 'click'),
            'on_not_found': nf_label_to_id.get(self.nf_var.get(), 'skip'),
            'retry_seconds': float(self.retry_var.get()),
            'threshold': float(self.threshold_var.get()),
        }
        self.dialog.destroy()
```

- [ ] **Step 6: 添加 WaitStepDialog (固定 ms)**

```python
class WaitStepDialog:
    def __init__(self, parent, initial=None):
        self.result = None
        initial = initial or {}
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("编辑[等待]")
        self.dialog.geometry("280x110")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        frame = ttk.Frame(self.dialog, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        row = ttk.Frame(frame)
        row.pack(fill=tk.X)
        ttk.Label(row, text="等待时间:").pack(side=tk.LEFT)
        self.ms_var = tk.IntVar(value=initial.get('ms', 500))
        ttk.Spinbox(row, from_=50, to=30000, increment=50,
                    textvariable=self.ms_var, width=8).pack(
            side=tk.LEFT, padx=5)
        ttk.Label(row, text="ms (50 ~ 30000)").pack(side=tk.LEFT)

        btn_row = ttk.Frame(frame)
        btn_row.pack(fill=tk.X, pady=(15, 0))
        ttk.Button(btn_row, text="确定",
                   command=self._ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_row, text="取消",
                   command=self.dialog.destroy).pack(side=tk.RIGHT)

        self.dialog.wait_window()

    def _ok(self):
        self.result = {'type': 'wait', 'ms': self.ms_var.get()}
        self.dialog.destroy()
```

- [ ] **Step 7: 冒烟检查 — 模块导入正常**

Run: `python -c "from custom_tool_dialog import MouseStepDialog, KeyPressStepDialog, HotkeyStepDialog, ImageSearchStepDialog, WaitStepDialog, step_summary; print('ok')"`
Expected: 输出 `ok`, 无 ImportError。

- [ ] **Step 8: Commit**

```bash
git add custom_tool_dialog.py
git commit -m "custom_tool: 新增 5 种步骤的子编辑对话框"
```

---

## Task 5: custom_tool_dialog.py — 主编辑对话框 CustomToolDialog

**Files:**
- Modify: `custom_tool_dialog.py` (在文件末尾追加)

- [ ] **Step 1: 在 custom_tool_dialog.py 末尾添加 CustomToolDialog 类骨架**

```python
class CustomToolDialog:
    """自定义工具的新建/编辑对话框。

    Args:
        parent: 主窗口
        manager: CustomToolManager
        screenshot_callback(path) -> bool: 截图回调
        original_name: 编辑模式下的原工具名; 新建时为 None
    Result:
        self.result: 保存后的工具名 (str), 或 None (取消)
    """

    def __init__(self, parent, manager, screenshot_callback,
                 original_name=None):
        self.result = None
        self._manager = manager
        self._screenshot_cb = screenshot_callback
        self._original_name = original_name
        # 取消时要清理的本次会话新截图
        self._pending_images = []

        # 加载初始数据
        if original_name:
            self._data = manager.load(original_name)
        else:
            self._data = {
                'version': '1.0', 'name': '', 'mode': 'loop',
                'description': '', 'steps': []
            }

        self.dialog = tk.Toplevel(parent)
        title = f"编辑自定义工具: {original_name}" if original_name \
            else "新建自定义工具"
        self.dialog.title(title)
        self.dialog.geometry("580x640")
        self.dialog.minsize(500, 500)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.protocol("WM_DELETE_WINDOW", self._cancel)

        self._create_widgets()
        self._refresh_step_list()
        self.dialog.wait_window()
```

- [ ] **Step 2: 添加 _create_widgets — 基本信息区**

```python
    def _create_widgets(self):
        main = ttk.Frame(self.dialog, padding=12)
        main.pack(fill=tk.BOTH, expand=True)

        # 基本信息
        info = ttk.LabelFrame(main, text="基本信息", padding=8)
        info.pack(fill=tk.X, pady=(0, 8))

        n_row = ttk.Frame(info)
        n_row.pack(fill=tk.X, pady=2)
        ttk.Label(n_row, text="名称:", width=8).pack(side=tk.LEFT)
        self.name_var = tk.StringVar(value=self._data.get('name', ''))
        ttk.Entry(n_row, textvariable=self.name_var, width=30).pack(
            side=tk.LEFT, padx=5)

        m_row = ttk.Frame(info)
        m_row.pack(fill=tk.X, pady=2)
        ttk.Label(m_row, text="模式:", width=8).pack(side=tk.LEFT)
        self.mode_var = tk.StringVar(value=self._data.get('mode', 'loop'))
        ttk.Radiobutton(m_row, text="循环", value='loop',
                        variable=self.mode_var).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(m_row, text="单次", value='once',
                        variable=self.mode_var).pack(side=tk.LEFT)

        d_row = ttk.Frame(info)
        d_row.pack(fill=tk.X, pady=2)
        ttk.Label(d_row, text="说明:", width=8).pack(side=tk.LEFT)
        self.desc_var = tk.StringVar(
            value=self._data.get('description', ''))
        ttk.Entry(d_row, textvariable=self.desc_var, width=40).pack(
            side=tk.LEFT, padx=5)

        # 步骤序列
        step_frame = ttk.LabelFrame(
            main, text="步骤序列 (按顺序执行)", padding=8)
        step_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        list_frame = ttk.Frame(step_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.step_tree = ttk.Treeview(
            list_frame, show='tree', selectmode='extended', height=14)
        scroll = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self.step_tree.yview)
        self.step_tree.configure(yscrollcommand=scroll.set)
        self.step_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.step_tree.bind('<Double-1>', lambda e: self._edit_step())

        # 操作按钮行
        op_row = ttk.Frame(step_frame)
        op_row.pack(fill=tk.X, pady=(6, 0))

        # 添加菜单
        self._add_mb = ttk.Menubutton(op_row, text="+ 添加步骤", width=12)
        menu = tk.Menu(self._add_mb, tearoff=0)
        for label, st_type in [
            ('鼠标移动', 'mouse_move'),
            ('鼠标左键', 'mouse_click'),
            ('鼠标右键', 'mouse_right_click'),
            ('鼠标双击', 'mouse_double_click'),
            ('键盘输入', 'key_press'),
            ('组合键', 'hotkey'),
            ('图片查询', 'image_search'),
            ('等待', 'wait'),
        ]:
            menu.add_command(
                label=label,
                command=lambda t=st_type: self._add_step(t))
        self._add_mb['menu'] = menu
        self._add_mb.pack(side=tk.LEFT, padx=2)

        ttk.Button(op_row, text="编辑", width=6,
                   command=self._edit_step).pack(side=tk.LEFT, padx=2)
        ttk.Button(op_row, text="删除", width=6,
                   command=self._delete_step).pack(side=tk.LEFT, padx=2)
        ttk.Button(op_row, text="上移", width=6,
                   command=self._move_up).pack(side=tk.LEFT, padx=2)
        ttk.Button(op_row, text="下移", width=6,
                   command=self._move_down).pack(side=tk.LEFT, padx=2)
        ttk.Button(op_row, text="复制", width=6,
                   command=self._duplicate_step).pack(side=tk.LEFT, padx=2)

        # 底部确定/取消
        bottom = ttk.Frame(main)
        bottom.pack(fill=tk.X)
        ttk.Button(bottom, text="确定",
                   command=self._save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(bottom, text="取消",
                   command=self._cancel).pack(side=tk.RIGHT)
```

- [ ] **Step 3: 添加 _refresh_step_list (含选中保留)**

```python
    def _refresh_step_list(self):
        prev_indices = sorted(
            self.step_tree.index(it) for it in self.step_tree.selection())
        for child in self.step_tree.get_children():
            self.step_tree.delete(child)
        for i, step in enumerate(self._data['steps']):
            text = f"#{i+1}  {step_summary(step)}"
            self.step_tree.insert('', 'end', iid=str(i), text=text)
        # 恢复选中
        all_iids = self.step_tree.get_children()
        valid_indices = [i for i in prev_indices if i < len(all_iids)]
        if valid_indices:
            self.step_tree.selection_set([all_iids[i] for i in valid_indices])

    def _selected_indices(self):
        """返回选中行的索引列表 (升序)。"""
        return sorted(self.step_tree.index(it)
                      for it in self.step_tree.selection())

    def _img_dir(self):
        """该工具图片专属子目录 (用当前编辑器里的名字, 截图实时落到这里)。

        新建工具时, 名字可能还没填; 用临时目录避免空名问题。
        """
        name = self._manager.sanitize_name(self.name_var.get())
        if not name:
            return os.path.join(self._manager.tools_dir, '_unnamed_temp')
        return self._manager.img_dir(name)
```

- [ ] **Step 4: 添加 _add_step (插入位置 = 最后选中行的下一行)**

```python
    def _add_step(self, step_type):
        # 计算插入位置
        sel = self._selected_indices()
        insert_at = (sel[-1] + 1) if sel else len(self._data['steps'])

        new_step = self._open_step_dialog(step_type, initial=None)
        if not new_step:
            return
        self._data['steps'].insert(insert_at, new_step)
        self._refresh_step_list()
        # 选中新行
        all_iids = self.step_tree.get_children()
        if insert_at < len(all_iids):
            self.step_tree.selection_set(all_iids[insert_at])

    def _open_step_dialog(self, step_type, initial):
        """根据类型派发到子对话框, 返回 step dict 或 None。"""
        if step_type in _MOUSE_TYPE_TITLES:
            d = MouseStepDialog(self.dialog, step_type, initial)
            return d.result
        if step_type == 'key_press':
            d = KeyPressStepDialog(self.dialog, initial)
            return d.result
        if step_type == 'hotkey':
            d = HotkeyStepDialog(self.dialog, initial)
            return d.result
        if step_type == 'image_search':
            d = ImageSearchStepDialog(
                self.dialog, self._screenshot_cb,
                self._img_dir(), self._pending_images.append, initial)
            return d.result
        if step_type == 'wait':
            d = WaitStepDialog(self.dialog, initial)
            return d.result
        return None
```

- [ ] **Step 5: 添加 _edit_step / _delete_step**

```python
    def _edit_step(self):
        sel = self._selected_indices()
        if len(sel) != 1:
            return  # 多选时编辑禁用
        idx = sel[0]
        step = self._data['steps'][idx]
        new_step = self._open_step_dialog(step['type'], initial=step)
        if not new_step:
            return
        self._data['steps'][idx] = new_step
        self._refresh_step_list()
        all_iids = self.step_tree.get_children()
        self.step_tree.selection_set(all_iids[idx])

    def _delete_step(self):
        sel = self._selected_indices()
        if not sel:
            return
        # 倒序删, 避免索引漂移
        for i in reversed(sel):
            self._data['steps'].pop(i)
        self._refresh_step_list()
```

- [ ] **Step 6: 添加 _move_up / _move_down (连续块整体移动)**

```python
    def _move_up(self):
        sel = self._selected_indices()
        if not sel or sel[0] == 0:
            return
        # 连续块判断
        is_contiguous = (sel[-1] - sel[0] + 1) == len(sel)
        steps = self._data['steps']
        if is_contiguous:
            block = steps[sel[0]:sel[-1]+1]
            del steps[sel[0]:sel[-1]+1]
            steps.insert(sel[0]-1, block[0])
            for k, st in enumerate(block[1:], start=1):
                steps.insert(sel[0]-1+k, st)
            new_sel = [i-1 for i in sel]
        else:
            # 非连续: 仅移首项
            i = sel[0]
            steps[i-1], steps[i] = steps[i], steps[i-1]
            new_sel = [i-1]
        self._refresh_step_list()
        all_iids = self.step_tree.get_children()
        self.step_tree.selection_set([all_iids[i] for i in new_sel])

    def _move_down(self):
        sel = self._selected_indices()
        if not sel or sel[-1] == len(self._data['steps']) - 1:
            return
        is_contiguous = (sel[-1] - sel[0] + 1) == len(sel)
        steps = self._data['steps']
        if is_contiguous:
            block = steps[sel[0]:sel[-1]+1]
            del steps[sel[0]:sel[-1]+1]
            steps.insert(sel[0]+1, block[0])
            for k, st in enumerate(block[1:], start=1):
                steps.insert(sel[0]+1+k, st)
            new_sel = [i+1 for i in sel]
        else:
            i = sel[0]
            steps[i], steps[i+1] = steps[i+1], steps[i]
            new_sel = [i+1]
        self._refresh_step_list()
        all_iids = self.step_tree.get_children()
        self.step_tree.selection_set([all_iids[i] for i in new_sel])
```

- [ ] **Step 7: 添加 _duplicate_step (就地复制, 多选时整组按原顺序)**

```python
    def _duplicate_step(self):
        sel = self._selected_indices()
        if not sel:
            return
        import copy
        steps = self._data['steps']
        clones = [copy.deepcopy(steps[i]) for i in sel]
        insert_at = sel[-1] + 1
        for k, c in enumerate(clones):
            steps.insert(insert_at + k, c)
        self._refresh_step_list()
        all_iids = self.step_tree.get_children()
        new_indices = list(range(insert_at, insert_at + len(clones)))
        self.step_tree.selection_set([all_iids[i] for i in new_indices])
```

- [ ] **Step 8: 添加 _save (校验 + 调 manager + 处理临时图片目录搬迁)**

```python
    def _save(self):
        name = self._manager.sanitize_name(self.name_var.get())
        if not name:
            messagebox.showwarning(
                "提示", "请填写有效的名称 (不能为空且不能全是非法字符)",
                parent=self.dialog)
            return
        if not self._data['steps']:
            messagebox.showwarning(
                "提示", "至少要添加一个步骤", parent=self.dialog)
            return

        # 处理"新建工具时图片落在 _unnamed_temp"的搬迁
        temp_dir = os.path.join(self._manager.tools_dir, '_unnamed_temp')
        target_dir = self._manager.img_dir(name)
        if (not self._original_name and os.path.isdir(temp_dir)
                and os.path.exists(temp_dir)):
            os.makedirs(target_dir, exist_ok=True)
            for fname in os.listdir(temp_dir):
                src = os.path.join(temp_dir, fname)
                dst = os.path.join(target_dir, fname)
                if os.path.isfile(src):
                    os.replace(src, dst)
                    # 同步改写 image_path 字段
                    for step in self._data['steps']:
                        if (step.get('type') == 'image_search'
                                and step.get('image_path') == src):
                            step['image_path'] = dst
            try:
                os.rmdir(temp_dir)
            except OSError:
                pass

        self._data['name'] = name
        self._data['mode'] = self.mode_var.get()
        self._data['description'] = self.desc_var.get()

        try:
            saved_name = self._manager.save(
                self._data, original_name=self._original_name)
        except ValueError as e:
            messagebox.showwarning("提示", str(e), parent=self.dialog)
            return

        self.result = saved_name
        self.dialog.destroy()
```

- [ ] **Step 9: 添加 _cancel (清理本次会话新截图 + 删除可能的临时目录)**

```python
    def _cancel(self):
        # 删本次会话新增、但用户取消的截图
        for p in self._pending_images:
            if os.path.isfile(p):
                try:
                    os.remove(p)
                except OSError:
                    pass
        # 清理 _unnamed_temp 目录
        temp_dir = os.path.join(self._manager.tools_dir, '_unnamed_temp')
        if os.path.isdir(temp_dir):
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        self.dialog.destroy()
```

- [ ] **Step 10: 冒烟检查 — 模块导入仍正常**

Run: `python -c "from custom_tool_dialog import CustomToolDialog; print(CustomToolDialog)"`
Expected: 打印类引用, 无 ImportError。

- [ ] **Step 11: Commit**

```bash
git add custom_tool_dialog.py
git commit -m "custom_tool: 新增 CustomToolDialog (步骤树 + 增删改/上下移/复制 + 保存校验)"
```

---

## Task 6: main_gui.py — 接线集成到主界面

**Files:**
- Modify: `main_gui.py` (多处)

- [ ] **Step 1: 在 main_gui.py 顶部 import 区追加自定义工具相关模块**

定位到现有的 `from screenshot_util import take_screenshot` 行之前的 import 块, 末尾追加:

```python
from custom_tool_manager import CustomToolManager
from custom_tool_engine import CustomToolEngine
from custom_tool_dialog import CustomToolDialog
```

- [ ] **Step 2: 在 __init__ 中添加 CustomToolManager**

定位到 `self.get_material_engine = GetMaterialEngine(self.window_manager)` 这一行, 在它之后添加:

```python
        self.custom_tool_manager = CustomToolManager()
        self._selected_custom_name = None
```

- [ ] **Step 3: 在 _create_widgets 中添加"自定义"分类节点**

定位到现有代码:
```python
        # 固定的工具子项
        self.tree.insert(self._tool_node, 'end', text='自动遇敌', ...)
        self.tree.insert(self._tool_node, 'end', text='循环医疗', ...)
        self.tree.insert(self._tool_node, 'end', text='获取材料', ...)
```

在 `获取材料` 那一行之后插入:

```python
        # 自定义工具分类
        self._custom_node = self.tree.insert(
            '', 'end', text='  自定义', open=True, tags=('category',))
```

- [ ] **Step 4: 修改 _refresh_tree, 同时刷新自定义子项**

定位到现有 `_refresh_tree` 方法 (从 `def _refresh_tree(self):` 开始, 到下一个方法定义之前)。整体替换为:

```python
    def _refresh_tree(self):
        """刷新配方 + 自定义工具子项。"""
        # 配方
        for child in self.tree.get_children(self._recipe_node):
            self.tree.delete(child)
        for name in self.recipe_manager.list_recipes():
            self.tree.insert(
                self._recipe_node, 'end', text=name, tags=('recipe',))
        # 自定义工具
        for child in self.tree.get_children(self._custom_node):
            self.tree.delete(child)
        for name in self.custom_tool_manager.list_tools():
            try:
                data = self.custom_tool_manager.load(name)
                mode = data.get('mode', 'loop')
            except Exception:
                mode = '?'
            self.tree.insert(
                self._custom_node, 'end',
                text=f'{name}   ({mode})',
                values=(name,),
                tags=('custom',))
```

- [ ] **Step 5: 修改 _on_tree_select 增加 'custom' / 'custom_root' 分支**

定位到现有 `_on_tree_select` 方法。在最末尾的 `elif parent == self._tool_node:` 块之后追加新的 elif 分支, 同时把开头处理"分类根节点"那一段也扩展加入 `_custom_node`:

把:
```python
        # 点击分类根节点
        if item in (self._recipe_node, self._tool_node):
```

改为:
```python
        # 点击分类根节点
        if item in (self._recipe_node, self._tool_node, self._custom_node):
```

并把这段下面的:
```python
            self._selected_type = None
            self._selected_tool_id = None
            self.selected_recipe = None
```

改为:
```python
            if item == self._custom_node:
                self._selected_type = 'custom_root'
            else:
                self._selected_type = None
            self._selected_tool_id = None
            self._selected_custom_name = None
            self.selected_recipe = None
```

然后在 `elif parent == self._tool_node:` 块之后追加:

```python
        elif parent == self._custom_node:
            values = self.tree.item(item, 'values')
            name = values[0] if values else ''
            self._selected_type = 'custom'
            self._selected_tool_id = None
            self._selected_custom_name = name
            self.selected_recipe = None
            self._show_custom_tool_info(name)
            self._update_buttons()
```

- [ ] **Step 6: 修改 _update_buttons 处理新两种类型**

定位到 `_update_buttons` 方法。在 `else:` (即 `_selected_type` 既非 recipe 也非 tool 的分支) 之前插入 elif:

把整个 `_update_buttons` 改为:

```python
    def _update_buttons(self):
        """根据选中类型更新按钮状态。"""
        if self._selected_type == 'recipe':
            self.new_btn.config(text="新建配方")
            self.edit_btn.config(text="编辑", state=tk.NORMAL)
            self.delete_btn.config(state=tk.NORMAL)
            self.start_btn.config(text="开始制造")
            self.info_frame.config(text="当前配方")
        elif self._selected_type == 'tool':
            self.new_btn.config(text="新建配方")
            self.edit_btn.config(text="配置", state=tk.NORMAL)
            self.delete_btn.config(state=tk.DISABLED)
            if self._selected_tool_id == 'get_material':
                self.start_btn.config(text="执行一次")
            else:
                self.start_btn.config(text="开始执行")
            self.info_frame.config(text="当前工具")
        elif self._selected_type == 'custom':
            self.new_btn.config(text="新建自定义")
            self.edit_btn.config(text="编辑", state=tk.NORMAL)
            self.delete_btn.config(state=tk.NORMAL)
            data = None
            try:
                data = self.custom_tool_manager.load(
                    self._selected_custom_name)
            except Exception:
                pass
            mode = (data or {}).get('mode', 'loop')
            self.start_btn.config(
                text="执行一次" if mode == 'once' else "开始执行")
            self.info_frame.config(text="自定义工具")
        elif self._selected_type == 'custom_root':
            self.new_btn.config(text="新建自定义")
            self.edit_btn.config(text="编辑", state=tk.DISABLED)
            self.delete_btn.config(state=tk.DISABLED)
            self.start_btn.config(text="开始")
        else:
            self.new_btn.config(text="新建配方")
            self.edit_btn.config(text="编辑", state=tk.DISABLED)
            self.delete_btn.config(state=tk.DISABLED)
            self.start_btn.config(text="开始")
```

- [ ] **Step 7: 修改 _on_edit / _new_recipe / _on_start 增加 'custom' 分支**

修改 `_on_edit`:
```python
    def _on_edit(self):
        """编辑/配置按钮"""
        if self._selected_type == 'recipe':
            self._edit_recipe()
        elif self._selected_type == 'tool':
            self._configure_tool()
        elif self._selected_type == 'custom':
            self._edit_custom_tool()
```

修改 `_new_recipe` 按钮的回调函数 — 实际上 `_new_recipe` 仍只用于配方; 我们要让 "新建" 按钮根据当前选中类型分发。改 button 的回调到一个新方法 `_on_new`:

定位到现有的:
```python
        self.new_btn = ttk.Button(
            btn_row, text="新建配方", width=8, command=self._new_recipe)
```

改为:
```python
        self.new_btn = ttk.Button(
            btn_row, text="新建配方", width=8, command=self._on_new)
```

并在类中添加新方法 (放在 `_new_recipe` 旁边):
```python
    def _on_new(self):
        """根据当前选中类型分发: 配方 / 自定义工具。"""
        if self._selected_type in ('custom', 'custom_root'):
            self._new_custom_tool()
        else:
            self._new_recipe()
```

修改 `_on_start`:
```python
    def _on_start(self):
        """统一开始按钮"""
        if self._selected_type == 'recipe':
            self.start_craft()
        elif self._selected_type == 'tool':
            self._start_selected_tool()
        elif self._selected_type == 'custom':
            self._start_custom_tool()
```

- [ ] **Step 8: 添加 _new_custom_tool / _edit_custom_tool / _delete_custom_tool**

放在类中合适位置 (例如 `_configure_tool` 之后):

```python
    # ── 自定义工具 ──

    def _new_custom_tool(self):
        dialog = CustomToolDialog(
            self.root, self.custom_tool_manager, self._screenshot_region)
        if dialog.result:
            self._refresh_tree()

    def _edit_custom_tool(self):
        if not self._selected_custom_name:
            return
        dialog = CustomToolDialog(
            self.root, self.custom_tool_manager, self._screenshot_region,
            original_name=self._selected_custom_name)
        if dialog.result:
            self._selected_custom_name = dialog.result
            self._refresh_tree()
            self._show_custom_tool_info(self._selected_custom_name)

    def _delete_custom_tool(self):
        if not self._selected_custom_name:
            return
        name = self._selected_custom_name
        if not messagebox.askyesno(
                "确认", f"确定删除自定义工具「{name}」? \n图片模板也会一并删除。"):
            return
        self.custom_tool_manager.delete(name)
        self._selected_custom_name = None
        self._selected_type = None
        self.info_label.config(text="请选择配方或工具", foreground='gray')
        self.info_frame.config(text="详情")
        self._refresh_tree()
        self._update_buttons()
```

- [ ] **Step 9: 修改 _delete_recipe 的按钮分发**

定位到 `delete_btn` 的回调:
```python
        self.delete_btn = ttk.Button(
            btn_row, text="删除", width=6, command=self._delete_recipe,
            state=tk.DISABLED)
```

改为分发方法:
```python
        self.delete_btn = ttk.Button(
            btn_row, text="删除", width=6, command=self._on_delete,
            state=tk.DISABLED)
```

并添加 `_on_delete` 方法:
```python
    def _on_delete(self):
        if self._selected_type == 'recipe':
            self._delete_recipe()
        elif self._selected_type == 'custom':
            self._delete_custom_tool()
```

- [ ] **Step 10: 添加 _start_custom_tool**

放在类中 (例如 `_start_loop_healing` 之后):

```python
    def _start_custom_tool(self):
        """启动选中的自定义工具。"""
        if not self.window_manager.is_window_valid():
            messagebox.showwarning("提示", "请先绑定游戏窗口")
            return
        if self.is_running or self._active_tool_engine:
            messagebox.showwarning("提示", "请先停止当前任务")
            return
        if not self._selected_custom_name:
            return
        try:
            tool = self.custom_tool_manager.load(self._selected_custom_name)
        except Exception as e:
            messagebox.showerror("错误", f"加载工具失败: {e}")
            return

        engine = CustomToolEngine(self.window_manager, self._log_message)
        engine.start(tool)
        self._active_tool_engine = engine
        self._tool_stop_callback = self._stop_tool
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        task_name = f"自定义: {self._selected_custom_name}"
        if self._in_mini_mode:
            self._mini_task_label.config(text=task_name)
            self._update_mini_buttons()
        else:
            self._enter_mini_mode(task_name)
        self._monitor_tool_engine()
```

- [ ] **Step 11: 添加 _show_custom_tool_info**

放在 `_show_tool_info` 之后:

```python
    def _show_custom_tool_info(self, name):
        """显示自定义工具详情。"""
        try:
            data = self.custom_tool_manager.load(name)
        except Exception as e:
            self.info_label.config(text=f"加载失败: {e}")
            return
        mode = data.get('mode', 'loop')
        steps = data.get('steps', [])
        desc = data.get('description', '')

        # 第一段
        from custom_tool_dialog import step_summary
        lines = [
            f"自定义工具: {name}",
            f"模式: {'循环' if mode == 'loop' else '单次'}",
        ]
        if desc:
            lines.append(f"说明: {desc}")
        lines.append(f"步骤数: {len(steps)}")
        # 步骤摘要 (前 8 行)
        for i, step in enumerate(steps[:8]):
            lines.append(f"  #{i+1} {step_summary(step)}")
        if len(steps) > 8:
            lines.append(f"  ...还有 {len(steps) - 8} 步")
        self.info_label.config(text='\n'.join(lines), foreground='black')
```

- [ ] **Step 12: 冒烟检查 — 启动 GUI 并目视确认**

Run: `python start_gui.py`
Expected:
- 程序正常启动, 不报错
- 左侧树出现 3 个一级节点: 配方 / 工具 / 自定义
- "自定义"下当前为空
- 点击"自定义"分类节点, 树下方"新建"按钮文案变为"新建自定义"
- 点击"新建自定义", 弹出新建对话框, 8 种步骤都能从 "+ 添加步骤" 菜单加进来
- 添加几个步骤填名字保存, 树里出现这个工具
- 双击该工具能再次打开编辑
- 点"删除"能删掉

> macOS 上 `keyboard` 库的 `read_hotkey()` 录制需要权限, 录制按钮可能不工作, 但其他功能应该都可用。Windows 上不影响。

- [ ] **Step 13: Commit**

```bash
git add main_gui.py
git commit -m "main_gui: 集成自定义工具 (新增树分类 + 按钮分发 + 启停)"
```

---

## Self-Review Notes

**Spec coverage (对照 spec 章节)**:
- ✅ 数据模型 / JSON 格式 / 目录结构 → Task 2
- ✅ 8 种步骤 → Task 1 (post_right_click) + Task 3 (引擎分发) + Task 4 (子对话框) + Task 5 (主对话框 + 菜单)
- ✅ 模式 loop/once → Task 3 (`_run` 分支) + Task 5 (单选) + Task 6 (按钮文案)
- ✅ 树位置 + 按钮动态文案 → Task 6 步骤 3-7
- ✅ 编辑对话框版式 + 多选 + 各按钮多选行为 → Task 5 步骤 2-7
- ✅ 5 种子对话框 → Task 4
- ✅ 图片查询 retry_skip / retry_stop → Task 3 步骤 8
- ✅ 文件命名校验 / 重名 / 改名搬目录 → Task 2 步骤 5
- ✅ 图片模板生命周期 (新建落 _unnamed_temp + 取消清理 _pending_images) → Task 5 步骤 8-9
- ✅ 全局热键 / 迷你模式整合 → Task 6 (`_active_tool_engine` 复用现有 monitor)
- ✅ 不做的事 (流程控制 / 独立快捷键 / 中文大写 / 跨工具复制 / 单元测试) → 计划里都没出现

**Type/接口一致性**:
- `CustomToolEngine.start(tool_data)` 参数即 `manager.load()` 返回的 dict — 一致
- `step['type']` 在 8 处使用 (引擎分发 / 子对话框返回值 / step_summary / 主对话框 _open_step_dialog) — 字符串完全一致 (`mouse_move` / `mouse_click` / ... / `wait`)
- `CustomToolManager.save(tool_data, original_name=None)` 与 Task 5 _save 调用一致
- `step_summary(step)` 返回纯字符串 (不含 `#N`), 主对话框和 main_gui 都用 `f"#{i+1}  {step_summary(step)}"` / `f"  #{i+1} {step_summary(step)}"` — 一致
