#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
强力图标修复脚本
确保exe文件正确显示logo.png图标
"""

import os
import subprocess
import shutil
import time

def force_clean_and_rebuild():
    """强力清理并重新编译"""
    
    print("🧹 开始强力清理...")
    
    # 1. 删除所有编译相关文件
    cleanup_items = [
        'dist',
        'build', 
        '__pycache__',
        '*.spec'
    ]
    
    for item in cleanup_items:
        if '*' in item:
            import glob
            files = glob.glob(item)
            for file in files:
                try:
                    if os.path.isfile(file):
                        os.remove(file)
                        print(f"🗑️  删除文件: {file}")
                except:
                    pass
        else:
            if os.path.exists(item):
                try:
                    if os.path.isdir(item):
                        shutil.rmtree(item)
                        print(f"🗑️  删除目录: {item}")
                    else:
                        os.remove(item)
                        print(f"🗑️  删除文件: {item}")
                except:
                    pass
    
    # 2. 重新生成图标
    print("\n🎨 重新生成图标...")
    if os.path.exists('convert_logo_to_icon.py'):
        subprocess.run([os.sys.executable, 'convert_logo_to_icon.py'])
    
    # 3. 验证图标文件
    if not os.path.exists('app_icon.ico'):
        print("❌ 图标文件生成失败")
        return False
    
    print("✅ 图标文件已生成")
    
    # 4. 使用更直接的PyInstaller命令
    print("\n🔨 开始重新编译...")
    
    # 构建命令，强制指定图标
    cmd = [
        'pyinstaller',
        '--onefile',           # 单文件
        '--windowed',          # 无控制台
        '--clean',             # 清理缓存
        '--noconfirm',         # 不询问覆盖
        f'--name=按键小精灵',    # 程序名
        f'--icon=app_icon.ico', # 图标文件
        '--add-data=*.png;.',  # 添加PNG文件
        '--add-data=*.json;.', # 添加JSON文件
        # 隐藏导入
        '--hidden-import=tkinter',
        '--hidden-import=tkinter.ttk',
        '--hidden-import=tkinter.filedialog',
        '--hidden-import=tkinter.messagebox',
        '--hidden-import=PIL',
        '--hidden-import=cv2',
        '--hidden-import=numpy',
        '--hidden-import=pyautogui',
        '--hidden-import=keyboard',
        'start_gui.py'         # 入口文件
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 编译成功!")
            
            # 检查生成的文件
            exe_path = 'dist/按键小精灵.exe'
            if os.path.exists(exe_path):
                size = os.path.getsize(exe_path)
                print(f"📁 生成的exe文件: {exe_path}")
                print(f"📊 文件大小: {size:,} 字节")
                
                # 复制必要文件
                copy_files_to_dist()
                
                return True
            else:
                print("❌ 未找到生成的exe文件")
                return False
        else:
            print("❌ 编译失败:")
            print(result.stderr)
            return False
            
    except FileNotFoundError:
        print("❌ PyInstaller未找到，尝试安装...")
        subprocess.run([os.sys.executable, '-m', 'pip', 'install', 'pyinstaller'])
        return force_clean_and_rebuild()  # 递归重试
    
    except Exception as e:
        print(f"❌ 编译过程出错: {e}")
        return False

def copy_files_to_dist():
    """复制必要文件到dist目录"""
    files_to_copy = [
        'logo.png',
        'default.json',
        'app_icon_preview.png'
    ]
    
    dist_dir = 'dist'
    for file in files_to_copy:
        if os.path.exists(file):
            try:
                shutil.copy2(file, dist_dir)
                print(f"📄 复制文件: {file}")
            except Exception as e:
                print(f"⚠️  复制失败 {file}: {e}")

def clear_windows_icon_cache():
    """清理Windows图标缓存"""
    print("\n🔄 清理Windows图标缓存...")
    
    try:
        # 刷新图标缓存的命令
        subprocess.run(['ie4uinit.exe', '-show'], timeout=30)
        print("✅ 图标缓存已清理")
        
        # 等待一下让系统更新
        time.sleep(2)
        
    except Exception as e:
        print(f"⚠️  清理图标缓存失败: {e}")

if __name__ == "__main__":
    print("💪 强力图标修复脚本")
    print("=" * 50)
    
    if force_clean_and_rebuild():
        clear_windows_icon_cache()
        
        print("\n🎉 修复完成!")
        print("📋 检查清单:")
        print("1. ✅ 重新生成了图标文件")
        print("2. ✅ 强力清理了编译缓存") 
        print("3. ✅ 使用直接命令重新编译")
        print("4. ✅ 清理了Windows图标缓存")
        
        print("\n🔍 请检查:")
        print("- dist/按键小精灵.exe 的图标")
        print("- 如果图标仍不正确，请重启资源管理器")
        
    else:
        print("\n❌ 修复失败，请检查错误信息")
