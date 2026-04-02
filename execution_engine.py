#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
执行引擎模块
负责执行自动化操作步骤
"""

import time
import random
import threading
import gc
import pyautogui
import keyboard
import cv2
import numpy as np
from PIL import Image
import os
from screenshot_util import take_screenshot


class ExecutionContext:
    """执行上下文，用于跨步骤传递状态"""
    def __init__(self):
        self.should_break = False  # break_loop 标志

class MatchResult:
    """模板匹配结果"""
    def __init__(self, left, top, width, height):
        self.left = left
        self.top = top
        self.width = width
        self.height = height

class ExecutionEngine:
    """执行引擎类"""
    
    def __init__(self, status_callback=None):
        self.status_callback = status_callback
        self.is_running = False
        self.should_stop = False
        self.saved_region = None  # 保存的搜索区域
    
    def locate_on_screen_chinese(self, image_path, region=None, confidence=0.8, exclude_rects=None):
        """支持中文路径的屏幕图片搜索，支持多尺度匹配以适应不同分辨率

        Args:
            exclude_rects: 排除区域列表，每项为 (x, y, w, h)，坐标相对于截图区域（非屏幕绝对坐标）
        """
        pil_template = None
        pil_screenshot = None
        try:
            # 使用PIL和numpy读取图片，支持中文路径
            pil_template = Image.open(image_path)
            template = np.array(pil_template)
            pil_template.close()
            pil_template = None

            # 处理不同通道数
            if len(template.shape) == 2:
                template = cv2.cvtColor(template, cv2.COLOR_GRAY2BGR)
            elif template.shape[2] == 4:
                template = cv2.cvtColor(template, cv2.COLOR_RGBA2BGR)
            elif template.shape[2] == 3:
                template = cv2.cvtColor(template, cv2.COLOR_RGB2BGR)

            # 截取屏幕
            pil_screenshot = take_screenshot(region=region)
            screenshot = np.array(pil_screenshot)
            pil_screenshot.close()
            pil_screenshot = None
            screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)

            th, tw = template.shape[:2]
            sh, sw = screenshot.shape[:2]

            best_val = -1
            best_loc = None
            best_w = 0
            best_h = 0

            # 优先尝试原始尺寸（1x），大多数场景分辨率固定
            if tw <= sw and th <= sh:
                result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
                # 屏蔽排除区域
                if exclude_rects:
                    self._mask_exclude_rects(result, exclude_rects, tw, th)
                _, max_val, _, max_loc = cv2.minMaxLoc(result)
                del result
                if max_val >= confidence:
                    best_val = max_val
                    best_loc = max_loc
                    best_w = tw
                    best_h = th

            # 原始尺寸未匹配时，再做多尺度搜索
            if best_val < confidence:
                for scale in [s / 100.0 for s in range(50, 205, 5)]:
                    if scale == 1.0:
                        continue  # 已尝试过
                    new_w = int(tw * scale)
                    new_h = int(th * scale)

                    if new_w > sw or new_h > sh or new_w < 5 or new_h < 5:
                        continue

                    scaled = cv2.resize(template, (new_w, new_h), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
                    result = cv2.matchTemplate(screenshot, scaled, cv2.TM_CCOEFF_NORMED)
                    if exclude_rects:
                        self._mask_exclude_rects(result, exclude_rects, new_w, new_h)
                    _, max_val, _, max_loc = cv2.minMaxLoc(result)
                    del result
                    del scaled

                    if max_val > best_val:
                        best_val = max_val
                        best_loc = max_loc
                        best_w = new_w
                        best_h = new_h

                    # 找到高置信度匹配就提前退出
                    if best_val >= min(confidence + 0.1, 0.98):
                        break

            # 释放大数组
            del template
            del screenshot

            if best_val >= confidence and best_loc is not None:
                left = best_loc[0]
                top = best_loc[1]

                if region:
                    left += region[0]
                    top += region[1]

                return MatchResult(left, top, best_w, best_h)

            return None
        except Exception as e:
            print(f"图片搜索错误: {str(e)}")
            return None
        finally:
            if pil_template:
                pil_template.close()
            if pil_screenshot:
                pil_screenshot.close()

    def _mask_exclude_rects(self, result_matrix, exclude_rects, template_w, template_h):
        """在匹配结果矩阵中屏蔽排除区域

        Args:
            result_matrix: cv2.matchTemplate 的结果矩阵，坐标是模板左上角位置
            exclude_rects: 排除区域列表，每项为 (x, y, w, h)，坐标相对于截图
            template_w: 当前模板宽度
            template_h: 当前模板高度
        """
        rh, rw = result_matrix.shape[:2]
        for ex, ey, ew, eh in exclude_rects:
            # 排除区域覆盖的匹配矩阵范围：
            # 模板左上角在 (rx, ry) 时，模板中心在 (rx + tw/2, ry + th/2)
            # 如果模板中心落在排除区域内，则屏蔽该位置
            rx1 = max(0, ex - template_w // 2)
            ry1 = max(0, ey - template_h // 2)
            rx2 = min(rw, ex + ew - template_w // 2)
            ry2 = min(rh, ey + eh - template_h // 2)
            if rx2 > rx1 and ry2 > ry1:
                result_matrix[ry1:ry2, rx1:rx2] = -1.0

    def _resolve_exclude_regions(self, exclude_items, search_region, confidence):
        """解析排除项列表，定位每个排除图片并计算排除矩形

        Args:
            exclude_items: [{"image_path": "...", "radius": 50}, ...]
            search_region: 当前搜索区域 (x, y, w, h) 或 None
            confidence: 匹配置信度

        Returns:
            list of (x, y, w, h) 排除矩形，坐标相对于截图区域
        """
        exclude_rects = []
        for item in exclude_items:
            exc_path = item.get('image_path', '')
            radius = item.get('radius', 50)
            if not exc_path or not os.path.exists(exc_path):
                continue  # 排除图片不存在则跳过
            try:
                # 在当前搜索区域中定位排除图片
                loc = self.locate_on_screen_chinese(exc_path, region=search_region, confidence=confidence)
                if loc:
                    # 排除图片中心（相对于截图区域）
                    center_x = loc.left + loc.width // 2
                    center_y = loc.top + loc.height // 2
                    # 如果有search_region，坐标需要转为相对于截图的坐标
                    if search_region:
                        center_x -= search_region[0]
                        center_y -= search_region[1]
                    # 正方形排除区域
                    ex = max(0, center_x - radius)
                    ey = max(0, center_y - radius)
                    ew = radius * 2
                    eh = radius * 2
                    exclude_rects.append((ex, ey, ew, eh))
            except Exception:
                pass  # 排除图片搜索失败则跳过
        return exclude_rects

    def execute_steps(self, steps, loop_mode=False, loop_interval=0.5):
        """执行步骤列表"""
        self.is_running = True
        self.should_stop = False
        self.saved_region = None
        ctx = ExecutionContext()

        try:
            loop_count = 0

            while True:
                if loop_mode:
                    loop_count += 1
                    self.update_status(f"第 {loop_count} 次循环执行")

                self._execute_step_list(steps, ctx)

                if self.should_stop:
                    break

                if not loop_mode:
                    self.update_status("所有步骤执行完成")
                    break

                # 每轮循环结束后回收内存
                gc.collect()

                # 循环间延迟
                sleep_time = loop_interval
                while sleep_time > 0 and not self.should_stop:
                    time.sleep(min(0.1, sleep_time))
                    sleep_time -= 0.1

        except Exception as e:
            self.update_status(f"执行出错: {str(e)}")

        finally:
            self.is_running = False
            self.should_stop = False

    def _execute_step_list(self, steps, ctx):
        """递归执行步骤列表"""
        for i, step in enumerate(steps):
            if self.should_stop or ctx.should_break:
                break

            if not step.enabled:
                continue

            self.update_status(f"执行: {step.description or step.step_type}")

            try:
                self._execute_one_step(step, ctx)
            except Exception as e:
                self.update_status(f"步骤执行失败: {str(e)}")
                break

            if not self.should_stop and not ctx.should_break:
                time.sleep(0.1)

    def _execute_one_step(self, step, ctx):
        """执行单个步骤（支持容器类型的递归分发）"""
        if step.step_type == 'if_image':
            self._execute_if_image(step, ctx)
        elif step.step_type == 'for_loop':
            self._execute_for_loop(step, ctx)
        elif step.step_type == 'while_image':
            self._execute_while_image(step, ctx)
        elif step.step_type == 'break_loop':
            ctx.should_break = True
        elif step.step_type == 'random_delay':
            self._execute_random_delay(step)
        elif step.step_type == 'mouse_scroll':
            self._execute_mouse_scroll(step)
        else:
            self.execute_single_step(step)

    def _check_image_exists(self, image_path, confidence=0.8, timeout=3):
        """检查图片是否在屏幕上存在，返回 True/False"""
        if not os.path.exists(image_path):
            return False
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.should_stop:
                return False
            try:
                location = self.locate_on_screen_chinese(image_path, confidence=confidence)
                if location:
                    return True
            except Exception:
                pass
            time.sleep(0.1)
        return False

    def _execute_if_image(self, step, ctx):
        """执行条件判断步骤"""
        image_path = step.params.get('image_path', '')
        confidence = step.params.get('confidence', 0.8)
        timeout = step.params.get('timeout', 3)

        found = self._check_image_exists(image_path, confidence, timeout)

        if found:
            self.update_status("条件成立: 找到图片")
            self._execute_step_list(step.children, ctx)
        else:
            self.update_status("条件不成立: 未找到图片")
            self._execute_step_list(step.else_children, ctx)

    def _execute_for_loop(self, step, ctx):
        """执行循环(N次)步骤"""
        count = step.params.get('count', 1)
        for i in range(count):
            if self.should_stop or ctx.should_break:
                break
            self.update_status(f"循环第 {i + 1}/{count} 次")
            self._execute_step_list(step.children, ctx)
        ctx.should_break = False  # 重置break标志

    def _execute_while_image(self, step, ctx):
        """执行条件循环步骤"""
        image_path = step.params.get('image_path', '')
        confidence = step.params.get('confidence', 0.8)
        condition = step.params.get('condition', 'exists')
        max_iterations = step.params.get('max_iterations', 100)

        iteration = 0
        while not self.should_stop and not ctx.should_break:
            iteration += 1
            if iteration > max_iterations:
                self.update_status(f"条件循环已达最大次数 {max_iterations}")
                break

            found = self._check_image_exists(image_path, confidence, timeout=2)
            should_continue = (found if condition == 'exists' else not found)

            if not should_continue:
                self.update_status("条件循环结束: 条件不再满足")
                break

            self.update_status(f"条件循环第 {iteration} 次")
            self._execute_step_list(step.children, ctx)
        ctx.should_break = False

    def _execute_random_delay(self, step):
        """执行随机延迟"""
        min_time = step.params.get('min_time', 0.5)
        max_time = step.params.get('max_time', 2.0)
        delay = random.uniform(min_time, max_time)
        self.update_status(f"随机延迟 {delay:.1f} 秒")
        remaining = delay
        while remaining > 0 and not self.should_stop:
            time.sleep(min(0.1, remaining))
            remaining -= 0.1

    def _execute_mouse_scroll(self, step):
        """执行鼠标滚轮"""
        x = step.params.get('x', 0)
        y = step.params.get('y', 0)
        clicks = step.params.get('clicks', 3)
        pyautogui.scroll(clicks, x=x, y=y)

    def execute_single_step(self, step):
        """执行单个基本步骤（叶子节点）"""
        if step.step_type == "mouse_click":
            self.execute_mouse_click(step)
        elif step.step_type == "keyboard_press":
            self.execute_keyboard_press(step)
        elif step.step_type == "image_search":
            self.execute_image_search(step)
        elif step.step_type == "wait":
            self.execute_wait(step)
        else:
            raise ValueError(f"未知的步骤类型: {step.step_type}")
    
    def execute_mouse_click(self, step):
        """执行鼠标点击"""
        params = step.params
        x = params.get('x', 0)
        y = params.get('y', 0)
        button = params.get('button', 'left')
        click_count = params.get('click_count', 1)
        click_interval = params.get('click_interval', 0.1)
        
        for _ in range(click_count):
            if self.should_stop:
                break
            
            if button == 'left':
                # 延时0.05按下，延时0.05弹起
                pyautogui.mouseDown(x, y, button='left')
                time.sleep(0.05)
                pyautogui.mouseUp(x, y, button='left')
                #time.sleep(0.05)
            elif button == 'right':
                # 延时0.05按下，延时0.05弹起
                pyautogui.mouseDown(x, y, button='right')
                time.sleep(0.05)
                pyautogui.mouseUp(x, y, button='right')
                #time.sleep(0.05)
            elif button == 'middle':
                pyautogui.middleClick(x, y)
            
            if click_count > 1:
                time.sleep(click_interval)
    
    def execute_keyboard_press(self, step):
        """执行键盘按键"""
        params = step.params
        key = params.get('key', '')
        text = params.get('text', '')
        key_type = params.get('key_type', 'single')
        duration = params.get('duration', 0.05)
        
        if key_type == 'text' and text:
            # 使用 keyboard.write 支持中文等非 ASCII 字符
            keyboard.write(text, delay=0.05)
        elif key_type == 'combo':
            # 组合键处理
            keys = key.split('+')
            if len(keys) > 1:
                pyautogui.hotkey(*keys)
            else:
                pyautogui.keyDown(key)
                time.sleep(duration)
                pyautogui.keyUp(key)
        else:
            # 单个按键
            pyautogui.keyDown(key)
            time.sleep(duration)
            pyautogui.keyUp(key)
    
    def execute_image_search(self, step):
        """执行图片搜索"""
        params = step.params
        image_path = params.get('image_path', '')
        confidence = params.get('confidence', 0.8)
        action = params.get('action', 'none')
        offset_x = params.get('offset_x', 0)
        offset_y = params.get('offset_y', 0)
        timeout = params.get('timeout', 5)
        search_above = params.get('search_above', False)
        target_image = params.get('target_image', '')
        
        # 区域相关参数
        search_region_type = params.get('search_region', 'full')  # 'full' 或 'region'
        region_x1 = params.get('region_x1', 0)
        region_y1 = params.get('region_y1', 0)
        region_x2 = params.get('region_x2', 100)
        region_y2 = params.get('region_y2', 100)
        save_region = params.get('save_region', False)  # 是否保存区域供后续步骤使用
        use_saved_region = params.get('use_saved_region', False)  # 是否使用之前保存的区域
        
        # 检查图片文件是否存在
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"找不到图片文件: {image_path}")
        
        # 确定搜索区域
        search_region = None
        if use_saved_region and self.saved_region:
            # 使用之前保存的区域
            search_region = self.saved_region
            self.update_status(f"使用保存的搜索区域: {search_region}")
        elif search_region_type == 'region':
            # 使用指定区域
            search_region = (region_x1, region_y1, region_x2 - region_x1, region_y2 - region_y1)
            if save_region:
                # 保存区域供后续步骤使用
                self.saved_region = search_region
                self.update_status(f"保存搜索区域: {search_region}")
        
        # 排除区域参数
        exclude_enabled = params.get('exclude_enabled', False)
        exclude_items = params.get('exclude_items', [])

        start_time = time.time()
        found_location = None
        search_count = 0

        # 解析排除区域（每次搜索循环都重新解析，因为排除图片可能移动）
        exclude_rects = None

        while time.time() - start_time < timeout:
            if self.should_stop:
                break

            try:
                # 如果启用排除区域，先解析排除矩形
                if exclude_enabled and exclude_items:
                    exclude_rects = self._resolve_exclude_regions(exclude_items, search_region, confidence)
                    if exclude_rects:
                        self.update_status(f"排除 {len(exclude_rects)} 个区域后搜索")

                # 搜索图片 - 使用支持中文路径的方法
                location = self.locate_on_screen_chinese(
                    image_path, region=search_region, confidence=confidence,
                    exclude_rects=exclude_rects
                )

                if location:
                    found_location = location
                    break

            except Exception:
                pass

            search_count += 1
            # 每搜索10次强制回收一次内存，防止RDP等环境下内存泄漏
            if search_count % 10 == 0:
                gc.collect()

            time.sleep(0.1)
        
        if not found_location:
            region_info = f" (区域: {search_region})" if search_region else ""
            raise Exception(f"在 {timeout} 秒内未找到图片: {image_path}{region_info}")
        
        # 计算点击位置
        center_x = found_location.left + found_location.width // 2
        center_y = found_location.top + found_location.height // 2
        
        # 特殊功能：向上搜索目标图片
        if search_above and target_image:
            target_location = self.search_image_above(center_x, center_y, target_image, confidence)
            if target_location:
                center_x = target_location[0]
                center_y = target_location[1]
        
        # 应用偏移量
        click_x = center_x + offset_x
        click_y = center_y + offset_y
        
        # 移动鼠标到目标位置
        pyautogui.moveTo(click_x, click_y)
        
        time.sleep(0.05)
        
        # 执行动作
        if action == 'left_click':
            pyautogui.mouseDown(click_x, click_y, button='left')
            time.sleep(0.05)
            pyautogui.mouseUp(click_x, click_y, button='left')
        elif action == 'right_click':
            pyautogui.mouseDown(click_x, click_y, button='right')
            time.sleep(0.05)
            pyautogui.mouseUp(click_x, click_y, button='right')
        elif action == 'double_click':
            pyautogui.doubleClick(click_x, click_y)
    
    def search_image_above(self, start_x, start_y, target_image, confidence):
        """从指定位置向上搜索目标图片"""
        if not os.path.exists(target_image):
            return None

        # 截取屏幕（仅用于获取尺寸，然后立即关闭）
        screenshot = take_screenshot()
        screen_width = screenshot.width
        screenshot.close()

        # 搜索区域：从起始位置向上搜索 (left, top, width, height)
        search_height = 200  # 向上搜索200像素
        region_left = max(0, start_x - 100)
        region_top = max(0, start_y - search_height)
        region_width = min(screen_width, start_x + 100) - region_left
        region_height = start_y - region_top
        search_region = (region_left, region_top, region_width, region_height)
        
        try:
            # 在指定区域搜索 - 使用支持中文路径的方法
            location = self.locate_on_screen_chinese(target_image, region=search_region, confidence=confidence)
            if location:
                return (location.left + location.width // 2, location.top + location.height // 2)
        except Exception:
            pass
        
        return None
    
    def execute_wait(self, step):
        """执行等待"""
        params = step.params
        wait_type = params.get('wait_type', 'time')
        wait_time = params.get('time', 1.0)
        wait_image = params.get('wait_image', '')
        
        if wait_type == 'time':
            # 固定时间等待，分段sleep以便响应停止
            remaining = wait_time
            while remaining > 0 and not self.should_stop:
                time.sleep(min(0.1, remaining))
                remaining -= 0.1
        elif wait_type == 'image' and wait_image:
            # 等待图片出现
            start_time = time.time()
            timeout = params.get('timeout', 10)
            search_count = 0

            while time.time() - start_time < timeout:
                if self.should_stop:
                    break

                try:
                    # 使用支持中文路径的方法
                    location = self.locate_on_screen_chinese(wait_image, confidence=0.8)
                    if location:
                        break
                except Exception:
                    pass

                search_count += 1
                if search_count % 10 == 0:
                    gc.collect()

                time.sleep(0.1)
    
    def clear_saved_region(self):
        """清除保存的区域"""
        self.saved_region = None
        if self.status_callback:
            self.status_callback("已清除保存的搜索区域")
    
    def get_saved_region(self):
        """获取保存的区域"""
        return self.saved_region
    
    def stop(self):
        """停止执行"""
        self.should_stop = True
    
    def update_status(self, message):
        """更新状态"""
        if self.status_callback:
            self.status_callback(message)

class AutomationRunner:
    """自动化运行器"""
    
    def __init__(self, status_callback=None):
        self.engine = ExecutionEngine(status_callback)
        self.execution_thread = None
    
    def start_execution(self, steps, loop_mode=False, loop_interval=0.5):
        """开始执行"""
        if self.is_running():
            return False
        
        self.execution_thread = threading.Thread(
            target=self.engine.execute_steps,
            args=(steps, loop_mode, loop_interval),
            daemon=True
        )
        self.execution_thread.start()
        return True
    
    def stop_execution(self):
        """停止执行"""
        if self.is_running():
            self.engine.stop()
            if self.execution_thread:
                self.execution_thread.join(timeout=2)
    
    def is_running(self):
        """检查是否正在运行"""
        return self.engine.is_running
    
    def test_single_step(self, step):
        """测试单个步骤"""
        if self.is_running():
            return False

        def test_thread():
            self.engine.is_running = True
            self.engine.should_stop = False
            try:
                ctx = ExecutionContext()
                self.engine._execute_one_step(step, ctx)
                self.engine.update_status("测试完成")
            except Exception as e:
                self.engine.update_status(f"测试失败: {str(e)}")
            finally:
                self.engine.is_running = False
                self.engine.should_stop = False

        thread = threading.Thread(target=test_thread, daemon=True)
        thread.start()
        return True
