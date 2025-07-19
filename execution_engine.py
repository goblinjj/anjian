#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
执行引擎模块
负责执行自动化操作步骤
"""

import time
import threading
import pyautogui
import keyboard
import cv2
import numpy as np
from PIL import Image
import os

class ExecutionEngine:
    """执行引擎类"""
    
    def __init__(self, status_callback=None):
        self.status_callback = status_callback
        self.is_running = False
        self.should_stop = False
        self.saved_region = None  # 保存的搜索区域
    
    def locate_on_screen_chinese(self, image_path, region=None, confidence=0.8):
        """支持中文路径的屏幕图片搜索"""
        try:
            # 使用PIL和numpy读取图片，支持中文路径
            template = Image.open(image_path)
            template = np.array(template)
            
            # 如果是RGBA，转换为RGB
            if template.shape[2] == 4:
                template = cv2.cvtColor(template, cv2.COLOR_RGBA2RGB)
            # 如果是RGB，转换为BGR（OpenCV格式）
            elif template.shape[2] == 3:
                template = cv2.cvtColor(template, cv2.COLOR_RGB2BGR)
            
            # 截取屏幕
            screenshot = pyautogui.screenshot(region=region)
            screenshot = np.array(screenshot)
            screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
            
            # 进行模板匹配
            result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            # 检查匹配度
            if max_val >= confidence:
                # 计算匹配位置
                h, w = template.shape[:2]
                left = max_loc[0]
                top = max_loc[1]
                
                # 如果指定了搜索区域，需要调整坐标
                if region:
                    left += region[0]
                    top += region[1]
                
                # 返回类似pyautogui.Box的对象
                class MatchResult:
                    def __init__(self, left, top, width, height):
                        self.left = left
                        self.top = top
                        self.width = width
                        self.height = height
                
                return MatchResult(left, top, w, h)
            
            return None
        except Exception as e:
            print(f"图片搜索错误: {str(e)}")
            return None
        
    def execute_steps(self, steps, loop_mode=False, loop_interval=0.5):
        """执行步骤列表"""
        self.is_running = True
        self.should_stop = False
        self.saved_region = None  # 重置保存的区域
        
        try:
            loop_count = 0
            
            while True:
                if loop_mode:
                    loop_count += 1
                    self.update_status(f"第 {loop_count} 次循环执行")
                
                # 执行所有步骤
                for i, step in enumerate(steps):
                    if self.should_stop:
                        break
                        
                    if not step.enabled:
                        continue
                    
                    if loop_mode:
                        self.update_status(f"第 {loop_count} 次循环 - 步骤 {i+1}/{len(steps)}: {step.description}")
                    else:
                        self.update_status(f"执行步骤 {i+1}/{len(steps)}: {step.description}")
                    
                    try:
                        self.execute_single_step(step)
                    except Exception as e:
                        if loop_mode:
                            self.update_status(f"第 {loop_count} 次循环 - 步骤 {i+1} 执行失败: {str(e)}")
                        else:
                            self.update_status(f"步骤 {i+1} 执行失败: {str(e)}")
                        break
                    
                    # 步骤间延迟
                    if not self.should_stop:
                        time.sleep(0.1)
                
                # 检查是否需要停止或继续循环
                if self.should_stop:
                    break
                
                # 如果不是循环模式，执行完一次就退出
                if not loop_mode:
                    self.update_status("所有步骤执行完成")
                    break
                
                # 循环间延迟，分解为小段以便及时响应停止
               # if loop_mode:
                 #   sleep_time = loop_interval
                  #  while sleep_time > 0 and not self.should_stop:
                  #      time.sleep(min(0.1, sleep_time))
                   #     sleep_time -= 0.1
        
        except Exception as e:
            self.update_status(f"执行出错: {str(e)}")
        
        finally:
            self.is_running = False
            self.should_stop = False
    
    def execute_single_step(self, step):
        """执行单个步骤"""
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
            pyautogui.typewrite(text, interval=0.05)
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
        
        start_time = time.time()
        found_location = None
        
        while time.time() - start_time < timeout:
            if self.should_stop:
                break
            
            try:
                # 搜索图片 - 使用支持中文路径的方法
                if search_region:
                    location = self.locate_on_screen_chinese(image_path, region=search_region, confidence=confidence)
                else:
                    location = self.locate_on_screen_chinese(image_path, confidence=confidence)
                
                if location:
                    found_location = location
                    break
                
            except Exception:
                pass
            
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
        
        # 截取屏幕
        screenshot = pyautogui.screenshot()
        
        # 搜索区域：从起始位置向上搜索
        search_height = 200  # 向上搜索200像素
        search_region = (
            max(0, start_x - 100),  # 左边界
            max(0, start_y - search_height),  # 上边界
            min(screenshot.width, start_x + 100),  # 右边界
            start_y  # 下边界
        )
        
        try:
            # 在指定区域搜索 - 使用支持中文路径的方法
            location = self.locate_on_screen_chinese(target_image, region=search_region, confidence=confidence)
            if location:
                return (location.left + location.width // 2, location.top + location.height // 2)
        except:
            pass
        
        return None
    
    def execute_wait(self, step):
        """执行等待"""
        params = step.params
        wait_type = params.get('wait_type', 'time')
        wait_time = params.get('time', 1.0)
        wait_image = params.get('wait_image', '')
        
        if wait_type == 'time':
            # 固定时间等待
            time.sleep(wait_time)
        elif wait_type == 'image' and wait_image:
            # 等待图片出现
            start_time = time.time()
            timeout = params.get('timeout', 10)
            
            while time.time() - start_time < timeout:
                if self.should_stop:
                    break
                
                try:
                    # 使用支持中文路径的方法
                    location = self.locate_on_screen_chinese(wait_image, confidence=0.8)
                    if location:
                        break
                except:
                    pass
                
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
            try:
                self.engine.execute_single_step(step)
                self.engine.update_status("测试完成")
            except Exception as e:
                self.engine.update_status(f"测试失败: {str(e)}")
        
        thread = threading.Thread(target=test_thread, daemon=True)
        thread.start()
        return True
