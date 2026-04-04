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
