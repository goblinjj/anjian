#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
版本检查和更新提醒
"""

import requests
import json
import tkinter as tk
from tkinter import messagebox
import webbrowser
import threading

# GitHub仓库信息 - 请替换为您的实际仓库信息
GITHUB_REPO = "yourusername/yourrepo"  # 格式: owner/repo
CURRENT_VERSION = "v2025.07.11"  # 当前版本，构建时需要更新

def check_latest_version():
    """检查GitHub最新版本"""
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            latest_version = data['tag_name']
            download_url = None
            
            # 查找exe文件下载链接
            for asset in data['assets']:
                if asset['name'].endswith('.exe'):
                    download_url = asset['browser_download_url']
                    break
            
            return {
                'version': latest_version,
                'download_url': download_url,
                'release_url': data['html_url'],
                'body': data['body']
            }
    except Exception as e:
        print(f"检查版本失败: {e}")
    
    return None

def compare_versions(current, latest):
    """比较版本号"""
    # 简单的版本比较，可以根据需要优化
    return current != latest

def show_update_dialog(latest_info):
    """显示更新对话框"""
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    
    message = f"""发现新版本！

当前版本: {CURRENT_VERSION}
最新版本: {latest_info['version']}

是否立即下载新版本？"""
    
    result = messagebox.askyesno(
        "版本更新",
        message,
        icon='question'
    )
    
    if result:
        if latest_info['download_url']:
            webbrowser.open(latest_info['download_url'])
        else:
            webbrowser.open(latest_info['release_url'])
    
    root.destroy()

def check_update_async():
    """异步检查更新"""
    def check():
        latest_info = check_latest_version()
        if latest_info and compare_versions(CURRENT_VERSION, latest_info['version']):
            show_update_dialog(latest_info)
    
    thread = threading.Thread(target=check, daemon=True)
    thread.start()

def check_update_sync():
    """同步检查更新（用于命令行）"""
    print("正在检查更新...")
    latest_info = check_latest_version()
    
    if not latest_info:
        print("无法获取版本信息")
        return
    
    if compare_versions(CURRENT_VERSION, latest_info['version']):
        print(f"发现新版本: {latest_info['version']}")
        print(f"当前版本: {CURRENT_VERSION}")
        print(f"下载地址: {latest_info['release_url']}")
    else:
        print("已是最新版本")

if __name__ == "__main__":
    check_update_sync()
