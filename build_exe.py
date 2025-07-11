#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
按键小精灵打包脚本
使用PyInstaller将程序打包成exe文件
"""

import os
import sys
import subprocess
import shutil
import glob

def install_pyinstaller():
    """安装PyInstaller"""
    try:
        import PyInstaller
        print("PyInstaller 已安装")
        return True
    except ImportError:
        print("正在安装 PyInstaller...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("PyInstaller 安装成功")
            return True
        except subprocess.CalledProcessError:
            print("PyInstaller 安装失败")
            return False

def create_spec_file():
    """创建spec文件"""
    # 获取当前目录中的所有图片文件
    import glob
    current_dir = os.getcwd()
    image_files = []
    
    # 查找所有图片文件
    for ext in ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.bmp']:
        files = glob.glob(ext)
        for file in files:
            image_files.append(f"('{file}', '.')")
    
    # 查找文档文件和配置文件
    doc_files = []
    for doc in ['README.md', 'requirements.txt', 'GUI_README.md', '使用说明.md', 'default.json']:
        if os.path.exists(doc):
            doc_files.append(f"('{doc}', '.')")
    
    # 生成datas列表
    datas_list = image_files + doc_files
    datas_str = ',\n        '.join(datas_list) if datas_list else ""
    
    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['start_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        {datas_str}
    ],
    hiddenimports=[
        'PIL._tkinter_finder',
        'tkinter',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.simpledialog',
        'tkinter.ttk',
        'cv2',
        'numpy',
        'pyautogui',
        'keyboard',
        'main_gui',
        'models',
        'dialogs',
        'execution_engine',
        'ui_editors',
        'file_manager',
        'hotkey_manager',
        'threading',
        'time',
        'json',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='按键小精灵',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='logo.ico' if os.path.exists('logo.ico') else None,
)
"""
    
    with open('automation_gui.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("已创建 automation_gui.spec 文件")

def build_exe():
    """构建exe文件"""
    try:
        print("正在构建exe文件...")
        
        # 先尝试简化的打包方式
        simple_cmd = [
            sys.executable, "-m", "PyInstaller",
            "--onefile",
            "--windowed", 
            "--name=按键小精灵",
            "--icon=logo.ico",
            "--add-data=*.png;.",
            "--add-data=*.json;.",
            "--hidden-import=PIL._tkinter_finder",
            "--hidden-import=cv2",
            "--hidden-import=numpy", 
            "--hidden-import=pyautogui",
            "--hidden-import=keyboard",
            "--hidden-import=tkinter",
            "--hidden-import=tkinter.ttk",
            "--hidden-import=tkinter.filedialog",
            "--hidden-import=tkinter.messagebox",
            "--hidden-import=tkinter.simpledialog",
            "--hidden-import=main_gui",
            "--hidden-import=models",
            "--hidden-import=dialogs",
            "--hidden-import=execution_engine",
            "--hidden-import=ui_editors",
            "--hidden-import=file_manager",
            "--hidden-import=hotkey_manager",
            "--hidden-import=threading",
            "--hidden-import=time",
            "--hidden-import=json",
            "start_gui.py"
        ]
        
        result = subprocess.run(simple_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("构建成功！")
            print("exe文件位置：dist/按键小精灵.exe")
            
            # 复制图片文件和配置文件到dist目录
            dist_dir = os.path.join("dist")
            if os.path.exists(dist_dir):
                import glob
                # 复制图片文件
                for ext in ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.bmp']:
                    files = glob.glob(ext)
                    for file in files:
                        try:
                            shutil.copy2(file, dist_dir)
                            print(f"已复制 {file} 到 dist 目录")
                        except Exception as e:
                            print(f"复制文件 {file} 失败: {e}")
                
                # 复制配置文件
                for config_file in ['default.json', '示例配置.json']:
                    if os.path.exists(config_file):
                        try:
                            shutil.copy2(config_file, dist_dir)
                            print(f"已复制 {config_file} 到 dist 目录")
                        except Exception as e:
                            print(f"复制配置文件 {config_file} 失败: {e}")
            
            return True
        else:
            print("构建失败：")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"构建过程中出错：{str(e)}")
        return False

def clean_build_files():
    """清理构建文件"""
    dirs_to_remove = ['build', '__pycache__']
    files_to_remove = ['automation_gui.spec']
    
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"已清理 {dir_name} 目录")
    
    for file_name in files_to_remove:
        if os.path.exists(file_name):
            os.remove(file_name)
            print(f"已清理 {file_name} 文件")

def main():
    """主函数"""
    print("按键小精灵打包脚本")
    print("=" * 50)
    
    # 检查当前目录
    required_files = ['main_gui.py', 'start_gui.py', 'models.py', 'file_manager.py']
    for file in required_files:
        if not os.path.exists(file):
            print(f"错误：找不到文件 {file}")
            return
    
    # 安装PyInstaller
    if not install_pyinstaller():
        return
    
    # 创建spec文件
    create_spec_file()
    
    # 构建exe
    if build_exe():
        print("\n构建完成！")
        print("你可以在 dist 目录中找到可执行文件")
        
        # 询问是否清理构建文件
        while True:
            choice = input("\n是否清理构建文件？(y/n): ").lower()
            if choice in ['y', 'yes', '是']:
                clean_build_files()
                break
            elif choice in ['n', 'no', '否']:
                print("保留构建文件")
                break
            else:
                print("请输入 y 或 n")
    else:
        print("构建失败")

if __name__ == "__main__":
    main()
