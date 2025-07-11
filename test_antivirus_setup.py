#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试构建参数和反病毒优化
"""

import subprocess
import sys
import os

def test_pyinstaller_args():
    """测试PyInstaller参数"""
    print("🔍 测试PyInstaller反病毒优化参数...")
    
    # 基本参数检查
    basic_args = [
        "--onefile",
        "--windowed",
        "--noupx",
        "--clean",
        "--noconfirm"
    ]
    
    print("✅ 基本参数:")
    for arg in basic_args:
        print(f"  {arg}")
    
    # 检查版本文件
    if os.path.exists("version_info.txt"):
        print("✅ 版本信息文件: version_info.txt")
    else:
        print("❌ 缺少版本信息文件")
    
    # 检查图标文件
    if os.path.exists("logo.ico"):
        print("✅ 图标文件: logo.ico")
    else:
        print("❌ 缺少图标文件")
    
    print("\n📋 反病毒优化策略:")
    print("  1. 使用 --noupx 避免UPX压缩误报")
    print("  2. 添加版本信息提高可信度")  
    print("  3. 包含详细元数据和公司信息")
    print("  4. 自动生成文件哈希验证")
    print("  5. 提供用户指导文档")

def show_build_preview():
    """显示构建预览"""
    print("\n🚀 构建命令预览:")
    print("python build_exe.py")
    
    print("\n📦 构建输出:")
    print("  - dist/按键小精灵.exe (带版本信息和图标)")
    print("  - dist/按键小精灵_hashes.txt (哈希验证文件)")
    print("  - dist/*.png (图片资源)")
    print("  - dist/*.json (配置文件)")

def main():
    """主函数"""
    print("🛡️ 反病毒优化测试")
    print("=" * 50)
    
    test_pyinstaller_args()
    show_build_preview()
    
    print(f"\n📚 相关文档:")
    print("  - WINDOWS_DEFENDER_GUIDE.md - 用户解决指南")
    print("  - ANTIVIRUS_COMPLETE_SOLUTION.md - 完整解决方案")
    print("  - version_info.txt - 版本信息文件")
    
    print(f"\n🎯 下一步:")
    print("  1. 运行 python build_exe.py 构建程序")
    print("  2. 测试Windows Defender反应")
    print("  3. 推送到GitHub自动发布")

if __name__ == "__main__":
    main()
