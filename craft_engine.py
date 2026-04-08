#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
制造引擎模块
负责自动制造循环的核心逻辑
"""

import os
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
            craft_time = recipe.get('craft_time', 10.0)
            wait_time = recipe.get('wait_time', 3.0)
            execute_button_path = settings.get('execute_button_image')
            completion_image_path = settings.get('completion_image')
            click_pre_delay = settings.get('click_pre_delay', 200) / 1000.0
            click_interval = settings.get('click_interval', 100) / 1000.0
            organize_button_path = settings.get('organize_button_image')
            recipe_dir = settings.get('recipe_dir', '')

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

                # 3. 定位背包网格（最多重试3次）
                self._log("定位背包网格...")
                grid_info = None
                for attempt in range(3):
                    if self._check_stop():
                        break
                    grid, info = self.backpack_reader.locate_grid(window_rect)
                    if grid is not None:
                        grid_info = grid
                        self._log(info)
                        break
                    if attempt < 2:
                        self._log(f"第{attempt+1}次定位失败: {info}，1秒后重试...")
                        time.sleep(1)
                    else:
                        self._log(f"定位失败: {info}")

                if not grid_info:
                    break

                # 4. 检查数字模板
                if not self.backpack_reader.digit_recognizer.is_loaded():
                    loaded = len(self.backpack_reader.digit_recognizer.templates)
                    self._log(f"错误: 数字模板未完整加载 (已加载{loaded}/10)，"
                              f"请在「设置」中截取0-9数字模板")
                    break

                # 5. 扫描20个格子（第一次启用debug保存图片）
                is_first_scan = (self.craft_count == 0)
                slots = self.backpack_reader.scan_backpack(
                    grid_info, debug=is_first_scan)
                if is_first_scan:
                    self._log("调试图片已保存到 debug/ 目录")

                empty_count = sum(1 for s in slots if s.is_empty)
                items_with_qty = sum(1 for s in slots if s.quantity is not None)
                items_no_qty = sum(
                    1 for s in slots if not s.is_empty and s.quantity is None)
                self._log(f"扫描完成: {items_with_qty}个有数量, "
                          f"{items_no_qty}个数量未识别, {empty_count}个空格子")

                if self._check_stop():
                    break

                # 6. 匹配每种材料
                matched_slots = []
                all_matched = True

                for i, mat in enumerate(materials):
                    mat_image_path = os.path.join(recipe_dir, mat['image_file'])
                    required_qty = mat['quantity']

                    slot, info = self.backpack_reader.match_item(
                        slots, mat_image_path, required_qty
                    )

                    if slot is None:
                        qty_desc = "仅匹配" if required_qty == 0 else f"需{required_qty}个"
                        self._log(f"材料{i+1}({qty_desc}): {info}")
                        all_matched = False
                        break

                    matched_slots.append(slot)
                    self._log(f"材料{i+1}: {info}")

                if not all_matched:
                    if not organize_button_path or self._check_stop():
                        self._log("材料不足，停止任务")
                        break

                    # 整理背包后重新检查
                    self._log("材料不足，尝试整理背包后重新检查...")
                    self._do_organize(organize_button_path, window_rect)
                    if self._check_stop():
                        break

                    # 重新扫描并匹配
                    grid2, info2 = self.backpack_reader.locate_grid(window_rect)
                    if not grid2:
                        self._log(f"整理后定位失败: {info2}")
                        break
                    slots2 = self.backpack_reader.scan_backpack(grid2)
                    matched_slots = []
                    all_matched2 = True
                    for i, mat in enumerate(materials):
                        mat_image_path = os.path.join(
                            recipe_dir, mat['image_file'])
                        slot, info = self.backpack_reader.match_item(
                            slots2, mat_image_path, mat['quantity'])
                        if slot is None:
                            self._log(f"材料{i+1}: {info}")
                            all_matched2 = False
                            break
                        matched_slots.append(slot)
                        self._log(f"材料{i+1}: {info}")

                    if not all_matched2:
                        self._log("整理背包后材料仍不足，停止任务")
                        break

                if self._check_stop():
                    break

                # 7. 双击匹配到的格子（移动→等待→单击→间隔→单击）
                for slot in matched_slots:
                    if self._check_stop():
                        break
                    pyautogui.moveTo(slot.screen_x, slot.screen_y)
                    time.sleep(click_pre_delay)
                    pyautogui.click()
                    time.sleep(click_interval)
                    pyautogui.click()
                    time.sleep(0.3)

                if self._check_stop():
                    break

                # 8. 点击执行按钮
                self._log("点击执行...")
                if execute_button_path:
                    self._click_template(execute_button_path, window_rect)
                time.sleep(0.3)

                # 鼠标移开，避免遮挡按钮影响图像识别
                pyautogui.moveTo(window_rect[0] + 50, window_rect[1] + 50)
                time.sleep(0.2)

                # 9. 等待制造完成
                self._log(f"等待制造{craft_time}秒...")
                # 先等待制造时间
                wait_end = time.time() + craft_time
                while time.time() < wait_end and not self._check_stop():
                    time.sleep(0.5)
                if completion_image_path and not self._check_stop():
                    # 再检测完成按钮（最多10秒）
                    self._log("检测制造完成按钮...")
                    completed = self._wait_for_template(
                        completion_image_path, window_rect, timeout=10
                    )
                    if completed and not self._check_stop():
                        # 10. 点击完成按钮（循环确认直到按钮消失）
                        for click_attempt in range(5):
                            if self._check_stop():
                                break
                            self._log(f"点击制造完成按钮(第{click_attempt+1}次)...")
                            self._click_template(completion_image_path, window_rect)
                            pyautogui.moveTo(window_rect[0] + 50, window_rect[1] + 50)
                            time.sleep(0.5)
                            # 确认按钮是否已消失
                            still_found = self._find_template(
                                completion_image_path, window_rect)
                            if not still_found:
                                self._log("确认: 完成按钮已消失")
                                break
                            self._log("完成按钮仍存在，重新点击...")
                        self.success_count += 1
                        time.sleep(1.0)  # 等待画面恢复到背包界面
                    else:
                        self.fail_count += 1
                else:
                    # 无完成按钮图片，等待已在上方完成，直接算成功
                    self.success_count += 1

                self.craft_count += 1
                self._log(f"第 {self.craft_count} 次制造完成 (成功:{self.success_count} 失败:{self.fail_count})")

                if self._check_stop():
                    break

                # 10. 检查背包是否还有空格子，没有则整理
                if organize_button_path and not self._check_stop():
                    grid_chk, _ = self.backpack_reader.locate_grid(window_rect)
                    if grid_chk:
                        chk_slots = self.backpack_reader.scan_backpack(grid_chk)
                        has_empty = any(s.is_empty for s in chk_slots)
                        if not has_empty:
                            self._log("背包无空格子，整理背包...")
                            self._do_organize(organize_button_path, window_rect)
                            self._log("重新扫描背包...")
                            continue

                # 短暂间隔再开始下一轮
                time.sleep(0.5)

        except Exception as e:
            self._log(f"制造出错: {str(e)}")
        finally:
            self.is_running = False
            self._log("制造已停止")

    def _do_organize(self, organize_button_path, window_rect):
        """执行一次整理背包操作"""
        self._log("整理背包: 打开背包...")
        pyautogui.hotkey('ctrl', 'e')
        time.sleep(0.5)
        self._click_template(
            organize_button_path, window_rect,
            pre_delay=0.5, long_press=True)
        time.sleep(1.0)
        self._log("整理背包: 关闭背包...")
        pyautogui.hotkey('ctrl', 'e')
        time.sleep(0.5)
        pyautogui.moveTo(window_rect[0] + 50, window_rect[1] + 50)
        time.sleep(0.5)
        self._log("整理完成")

    def _click_template(self, template_path, window_rect, pre_delay=0.2, long_press=False):
        """在窗口中查找模板并点击

        Args:
            template_path: 模板图片路径
            window_rect: (left, top, width, height)

        Returns:
            bool: 是否找到并点击
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

        name = os.path.basename(template_path)
        if max_val >= 0.7:
            th, tw = tmpl.shape[:2]
            click_x = window_rect[0] + max_loc[0] + tw // 2
            click_y = window_rect[1] + max_loc[1] + th // 2
            self._log(f"[点击] {name} 置信度:{max_val:.2f} 坐标:({click_x},{click_y})")
            pyautogui.moveTo(click_x, click_y)
            time.sleep(pre_delay)
            if long_press:
                pyautogui.mouseDown()
                time.sleep(0.5)
                pyautogui.mouseUp()
            else:
                pyautogui.click()
            return True
        self._log(f"[点击] {name} 未找到，最高置信度:{max_val:.2f}")
        return False

    def _find_template(self, template_path, window_rect, threshold=0.7):
        """检查模板是否存在于窗口中（不点击）"""
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
        _, max_val, _, _ = cv2.minMaxLoc(result)
        return max_val >= threshold

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
