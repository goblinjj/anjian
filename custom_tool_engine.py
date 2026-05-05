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

    def _do_wait(self, idx, step):
        ms = step.get('ms', 500)
        self._log(f"  步骤{idx+1}: 等待 {ms}ms")
        deadline = time.time() + ms / 1000.0
        while time.time() < deadline:
            if self.should_stop:
                return False
            time.sleep(0.05)
        return True

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

        self._log(f"  步骤{idx+1}: 未找到, 重试 {retry_seconds:.1f}秒...")
        deadline = time.time() + retry_seconds
        while not self.should_stop and time.time() < deadline:
            time.sleep(0.5)
            rect = self.window_manager.get_window_rect()
            if not rect:
                self._log(f"  步骤{idx+1}: 重试期间窗口失效, 停止")
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
