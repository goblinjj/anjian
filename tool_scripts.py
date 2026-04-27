#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
工具脚本引擎
包含自动遇敌、循环医疗和获取材料三个工具
"""

import time
import threading
import pyautogui  # 仅用于 pyautogui.position() 读取真实鼠标位置 (不会移动鼠标)
import cv2
import numpy as np
from PIL import Image
import screenshot_util
from screenshot_util import take_screenshot
import bg_input


class AutoEncounterEngine:
    """自动遇敌引擎

    在绑定窗口中心的左下和右上两个偏移点之间循环移动并点击。
    """

    def __init__(self, window_manager, status_callback=None):
        self.window_manager = window_manager
        self.status_callback = status_callback
        self.should_stop = False
        self.is_running = False
        self._thread = None

    def start(self, point1_x=-200, point1_y=200, point2_x=200, point2_y=-200,
              click_delay=500):
        if self.is_running:
            return
        self.should_stop = False
        self.is_running = True
        self._thread = threading.Thread(
            target=self._run,
            args=(point1_x, point1_y, point2_x, point2_y, click_delay),
            daemon=True)
        self._thread.start()

    def stop(self):
        self.should_stop = True

    def _log(self, message):
        if self.status_callback:
            self.status_callback(message)

    def _run(self, point1_x, point1_y, point2_x, point2_y, click_delay):
        screenshot_util.set_capture_hwnd(self.window_manager.hwnd)
        try:
            if not self.window_manager.is_window_valid():
                self._log("错误: 未绑定游戏窗口")
                return

            rect = self.window_manager.get_window_rect()
            if not rect:
                self._log("错误: 无法获取窗口坐标")
                return

            left, top, width, height = rect
            center_x = left + width // 2
            center_y = top + height // 2

            # 基于窗口中心的两个偏移点
            bl_x = center_x + point1_x
            bl_y = center_y + point1_y
            tr_x = center_x + point2_x
            tr_y = center_y + point2_y

            delay_sec = click_delay / 1000.0

            self._log(f"窗口中心: ({center_x}, {center_y})")
            self._log(f"点1: ({bl_x}, {bl_y}), 点2: ({tr_x}, {tr_y})")
            self._log(f"点击延迟: {click_delay}ms")
            self._log("开始自动遇敌循环...")

            hwnd = self.window_manager.hwnd
            count = 0
            while not self.should_stop:
                count += 1

                bg_input.post_click(hwnd, bl_x, bl_y, pre_delay=delay_sec)
                time.sleep(delay_sec)
                if self.should_stop:
                    break

                bg_input.post_click(hwnd, tr_x, tr_y, pre_delay=delay_sec)
                time.sleep(delay_sec)

                if count % 10 == 0:
                    self._log(f"已循环 {count} 次")

        except Exception as e:
            self._log(f"自动遇敌出错: {str(e)}")
        finally:
            screenshot_util.set_capture_hwnd(None)
            self.is_running = False
            self._log("自动遇敌已停止")


class LoopHealingEngine:
    """循环医疗引擎

    按自定义步骤序列循环执行，步骤可自由组合:
    - skill: 查找并点击治疗技能
    - member: 在队员基准位置 + 偏移处点击
    每次点击前统一 200ms 延迟。

    设计意图: 每次 main_gui 调用 start() 时, 都会创建一个新的引擎实例
    (见 main_gui.py:_start_loop_healing), 因此 stop → 重新 start 永远从
    第 1 个步骤开始, 不保留任何"上次执行到第几步"的状态。
    若步骤里某张图片在 RETRY_TIMEOUT 秒内仍找不到, 当轮放弃, 外层 while
    自动进入下一轮 (count+1, i 从 0 重启), 让游戏中间状态有机会恢复。
    """

    RETRY_TIMEOUT = 3.0  # 单步图片重试上限 (秒)

    def __init__(self, window_manager, status_callback=None):
        self.window_manager = window_manager
        self.status_callback = status_callback
        self.should_stop = False
        self.is_running = False
        self._thread = None

    def start(self, skill_image, member_image, steps):
        """
        Args:
            skill_image: 治疗技能图片路径
            member_image: 队员定位图片路径
            steps: list of dict, 每项为 {'type':'skill'} 或
                   {'type':'member', 'offset_x':N, 'offset_y':N}
        """
        if self.is_running:
            return
        self.should_stop = False
        self.is_running = True
        self._thread = threading.Thread(
            target=self._run,
            args=(skill_image, member_image, steps),
            daemon=True
        )
        self._thread.start()

    def stop(self):
        self.should_stop = True

    def _log(self, message):
        if self.status_callback:
            self.status_callback(message)

    def _find_template(self, template_path, window_rect, threshold=0.7):
        """在窗口中查找模板图片

        Returns:
            tuple: (center_x, center_y, confidence) 或 None
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

        if max_val >= threshold:
            th, tw = tmpl.shape[:2]
            click_x = window_rect[0] + max_loc[0] + tw // 2
            click_y = window_rect[1] + max_loc[1] + th // 2
            return (click_x, click_y, max_val)
        return None

    def _find_with_retry(self, template_path, hwnd, timeout, label):
        """限时反复查找模板, 找不到时移开鼠标后继续找。

        Args:
            template_path: 模板图片路径
            hwnd: 目标窗口句柄, 用于 post_move
            timeout: 重试时间上限 (秒)
            label: 日志前缀, 例如 "步骤3"

        Returns:
            tuple: (pos, rect)
                pos: (x, y, conf) 或 None (超时 / should_stop / 取窗口失败)
                rect: 最后一次有效的 window_rect, 失败时可能为 None
        """
        rect = self.window_manager.get_window_rect()
        if not rect:
            return None, None
        pos = self._find_template(template_path, rect)
        if pos:
            return pos, rect
        self._log(f"  {label}: 未找到, 移开重试 ({timeout:.0f}秒内)...")
        bg_input.post_move(hwnd, rect[0] + 50, rect[1] + 50)
        deadline = time.time() + timeout
        while not self.should_stop and time.time() < deadline:
            time.sleep(0.5)
            rect = self.window_manager.get_window_rect()
            if not rect:
                return None, None
            pos = self._find_template(template_path, rect)
            if pos:
                return pos, rect
            bg_input.post_move(hwnd, rect[0] + 50, rect[1] + 50)
        return None, rect

    def _run(self, skill_image, member_image, steps):
        screenshot_util.set_capture_hwnd(self.window_manager.hwnd)
        try:
            if not self.window_manager.is_window_valid():
                self._log("错误: 未绑定游戏窗口")
                return

            self._log(f"开始循环医疗 (共{len(steps)}个步骤)...")
            hwnd = self.window_manager.hwnd
            count = 0

            while not self.should_stop:
                count += 1
                self._log(f"[第{count}轮]")

                # 按步骤序列依次执行，按需检测对应图片
                for i, step in enumerate(steps):
                    if self.should_stop:
                        break

                    rect = self.window_manager.get_window_rect()
                    if not rect:
                        self._log("错误: 无法获取窗口坐标")
                        self.should_stop = True
                        break

                    if step['type'] == 'skill':
                        # 查找治疗技能图片 (限时重试)
                        skill_pos, rect = self._find_with_retry(
                            skill_image, hwnd, self.RETRY_TIMEOUT,
                            label=f"步骤{i+1}")
                        if self.should_stop:
                            break
                        if not skill_pos:
                            self._log(
                                f"  步骤{i+1}: {self.RETRY_TIMEOUT:.0f}秒未找到治疗技能, 重启本轮")
                            break
                        sx, sy, _ = skill_pos
                        if self.should_stop:
                            break
                        bg_input.post_click(hwnd, sx, sy, pre_delay=0.2)
                        self._log(f"  步骤{i+1}: 点击治疗技能")

                    elif step['type'] == 'member':
                        # 查找队员定位图片 (限时重试)
                        member_pos, rect = self._find_with_retry(
                            member_image, hwnd, self.RETRY_TIMEOUT,
                            label=f"步骤{i+1}")
                        if self.should_stop:
                            break
                        if not member_pos:
                            self._log(
                                f"  步骤{i+1}: {self.RETRY_TIMEOUT:.0f}秒未找到队员定位, 重启本轮")
                            break
                        mx, my, _ = member_pos
                        ox = step.get('offset_x', 0)
                        oy = step.get('offset_y', 0)
                        click_x = mx + ox
                        click_y = my + oy
                        if self.should_stop:
                            break
                        bg_input.post_click(hwnd, click_x, click_y, pre_delay=0.2)
                        self._log(f"  步骤{i+1}: 队员({ox},{oy})")

                    elif step['type'] == 'delay':
                        delay_ms = step.get('delay_ms', 500)
                        self._log(f"  步骤{i+1}: 延迟 {delay_ms}ms")
                        delay_end = time.time() + delay_ms / 1000.0
                        while time.time() < delay_end:
                            if self.should_stop:
                                break
                            time.sleep(0.05)

        except Exception as e:
            self._log(f"循环医疗出错: {str(e)}")
        finally:
            screenshot_util.set_capture_hwnd(None)
            self.is_running = False
            self._log("循环医疗已停止")


class GetMaterialEngine:
    """获取材料引擎

    每次调用 execute() 执行一次:
    1. 在当前鼠标位置双击
    2. 查找配置的图片并点击
    3. 按 Ctrl+E 打开背包
    """

    def __init__(self, window_manager, status_callback=None):
        self.window_manager = window_manager
        self.status_callback = status_callback
        self._busy = False
        self.should_stop = False

    def _log(self, message):
        if self.status_callback:
            self.status_callback(message)

    def _find_template(self, template_path, window_rect, threshold=0.7):
        """在窗口中查找模板图片"""
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
            click_x = window_rect[0] + max_loc[0] + tw // 2
            click_y = window_rect[1] + max_loc[1] + th // 2
            return (click_x, click_y, max_val)
        return None

    def stop(self):
        self.should_stop = True

    def execute(self, material_image):
        """执行一次获取材料流程（在后台线程中运行）"""
        if self._busy:
            self._log("获取材料: 正在执行中，请稍候")
            return
        self.should_stop = False
        self._busy = True
        threading.Thread(
            target=self._run, args=(material_image,), daemon=True
        ).start()

    def _run(self, material_image):
        screenshot_util.set_capture_hwnd(self.window_manager.hwnd)
        try:
            if not self.window_manager.is_window_valid():
                self._log("获取材料: 未绑定游戏窗口")
                return

            self._log("获取材料: 开始执行")
            hwnd = self.window_manager.hwnd

            rect = self.window_manager.get_window_rect()
            if not rect:
                self._log("  错误: 无法获取窗口坐标")
                return

            # 1. 以用户当前鼠标指向的屏幕位置为目标, 用后台消息双击
            x, y = pyautogui.position()
            bg_input.post_double_click(hwnd, x, y)
            time.sleep(0.2)
            if self.should_stop:
                self._log("获取材料: 已取消")
                return
            bg_input.post_move(hwnd, rect[0] + 50, rect[1] + 50)
            self._log(f"  双击目标位置 ({x}, {y})")

            # 2. 等待 300ms
            time.sleep(0.3)
            if self.should_stop:
                self._log("获取材料: 已取消")
                return

            # 3. 循环查找材料图片，找到后点击
            pos = None
            for attempt in range(30):  # 最多重试30次(约6秒)
                if self.should_stop:
                    self._log("获取材料: 已取消")
                    return
                pos = self._find_template(material_image, rect)
                if pos:
                    break
                time.sleep(0.2)

            if not pos:
                self._log("  未找到材料图片")
                return

            if self.should_stop:
                self._log("获取材料: 已取消")
                return

            mx, my, _ = pos
            bg_input.post_click(hwnd, mx, my)
            self._log(f"  点击材料图片 ({mx}, {my})")

            # 4. 等待 300ms
            time.sleep(0.3)
            if self.should_stop:
                self._log("获取材料: 已取消")
                return

            # 5. Ctrl+E 打开背包
            bg_input.post_hotkey(hwnd, 'ctrl', 'e')
            self._log("  按下 Ctrl+E")

            self._log("获取材料: 执行完成")

        except Exception as e:
            self._log(f"获取材料出错: {str(e)}")
        finally:
            screenshot_util.set_capture_hwnd(None)
            self._busy = False
