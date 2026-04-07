#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
工具脚本引擎
包含自动遇敌和循环医疗两个工具
"""

import time
import threading
import pyautogui
import cv2
import numpy as np
from PIL import Image
from screenshot_util import take_screenshot


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

    def start(self, offset=200):
        if self.is_running:
            return
        self.should_stop = False
        self.is_running = True
        self._thread = threading.Thread(
            target=self._run, args=(offset,), daemon=True)
        self._thread.start()

    def stop(self):
        self.should_stop = True

    def _log(self, message):
        if self.status_callback:
            self.status_callback(message)

    def _run(self, offset):
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

            # 左下: X减小, Y增大（屏幕坐标Y向下增大）
            bl_x = center_x - offset
            bl_y = center_y + offset
            # 右上: X增大, Y减小
            tr_x = center_x + offset
            tr_y = center_y - offset

            self._log(f"窗口中心: ({center_x}, {center_y})")
            self._log(f"左下: ({bl_x}, {bl_y}), 右上: ({tr_x}, {tr_y})")
            self._log("开始自动遇敌循环...")

            count = 0
            while not self.should_stop:
                count += 1

                pyautogui.moveTo(bl_x, bl_y)
                time.sleep(0.5)
                if self.should_stop:
                    break
                pyautogui.click()
                time.sleep(0.5)
                if self.should_stop:
                    break

                pyautogui.moveTo(tr_x, tr_y)
                time.sleep(0.5)
                if self.should_stop:
                    break
                pyautogui.click()
                time.sleep(0.5)

                if count % 10 == 0:
                    self._log(f"已循环 {count} 次")

        except Exception as e:
            self._log(f"自动遇敌出错: {str(e)}")
        finally:
            self.is_running = False
            self._log("自动遇敌已停止")


class LoopHealingEngine:
    """循环医疗引擎

    循环执行: 查找并点击治疗技能 → 查找队员定位图片 → 依次点击各偏移位置。
    """

    def __init__(self, window_manager, status_callback=None):
        self.window_manager = window_manager
        self.status_callback = status_callback
        self.should_stop = False
        self.is_running = False
        self._thread = None

    def start(self, skill_image, member_image, offsets):
        """
        Args:
            skill_image: 治疗技能图片路径
            member_image: 队员定位图片路径
            offsets: list of dict, 每项包含 offset_x, offset_y, delay_ms
        """
        if self.is_running:
            return
        self.should_stop = False
        self.is_running = True
        self._thread = threading.Thread(
            target=self._run,
            args=(skill_image, member_image, offsets),
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

    def _run(self, skill_image, member_image, offsets):
        try:
            if not self.window_manager.is_window_valid():
                self._log("错误: 未绑定游戏窗口")
                return

            self._log("开始循环医疗...")
            count = 0

            while not self.should_stop:
                count += 1
                rect = self.window_manager.get_window_rect()
                if not rect:
                    self._log("错误: 无法获取窗口坐标")
                    break

                # 1. 查找并点击治疗技能
                skill_pos = self._find_template(skill_image, rect)
                if not skill_pos:
                    self._log("未找到治疗技能，等待重试...")
                    time.sleep(1)
                    continue

                sx, sy, conf = skill_pos
                self._log(f"[第{count}轮] 找到治疗技能 置信度:{conf:.2f}")
                pyautogui.moveTo(sx, sy)
                time.sleep(0.1)
                if self.should_stop:
                    break
                pyautogui.click()
                time.sleep(0.3)
                if self.should_stop:
                    break

                # 2. 查找队员定位图片获取基准坐标
                member_pos = self._find_template(member_image, rect)
                if not member_pos:
                    self._log("未找到队员定位图片，等待重试...")
                    time.sleep(1)
                    continue

                mx, my, conf = member_pos
                self._log(f"找到队员基准位置 ({mx},{my}) 置信度:{conf:.2f}")

                # 3. 依次点击各偏移位置
                for i, off in enumerate(offsets):
                    if self.should_stop:
                        break
                    ox = off.get('offset_x', 0)
                    oy = off.get('offset_y', 0)
                    delay = off.get('delay_ms', 500) / 1000.0

                    click_x = mx + ox
                    click_y = my + oy
                    pyautogui.moveTo(click_x, click_y)
                    time.sleep(0.1)
                    pyautogui.click()
                    self._log(f"  点击偏移{i+1}: ({ox},{oy}) → 屏幕({click_x},{click_y})")
                    time.sleep(delay)

        except Exception as e:
            self._log(f"循环医疗出错: {str(e)}")
        finally:
            self.is_running = False
            self._log("循环医疗已停止")
