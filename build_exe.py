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

# 设置环境编码，避免在CI环境中出现编码问题
if os.environ.get('CI') or os.environ.get('GITHUB_ACTIONS'):
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    # 在CI环境中重定向标准输出编码
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

def install_pyinstaller():
    """安装PyInstaller"""
    try:
        import PyInstaller
        safe_print("PyInstaller is already installed")
        return True
    except ImportError:
        safe_print("Installing PyInstaller...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            safe_print("PyInstaller installed successfully")
            return True
        except subprocess.CalledProcessError:
            safe_print("Failed to install PyInstaller")
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
    
    safe_print("Created automation_gui.spec file")

def build_exe():
    """构建exe文件"""
    try:
        safe_print("Building exe file...")
        
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
            safe_print("Build successful!")
            safe_print("exe file location: dist/按键小精灵.exe")
            
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
                            safe_print(f"Copied {file} to dist directory")
                        except Exception as e:
                            safe_print(f"Failed to copy file {file}: {e}")
                
                # 复制配置文件
                for config_file in ['default.json', '示例配置.json']:
                    if os.path.exists(config_file):
                        try:
                            shutil.copy2(config_file, dist_dir)
                            safe_print(f"Copied config file {config_file} to dist directory")
                        except Exception as e:
                            safe_print(f"Failed to copy config file {config_file}: {e}")
            
            return True
        else:
            safe_print("Build failed:")
            safe_print(result.stderr)
            return False
            
    except Exception as e:
        safe_print(f"Error during build process: {str(e)}")
        return False

def clean_build_files():
    """清理构建文件"""
    dirs_to_remove = ['build', '__pycache__']
    files_to_remove = ['automation_gui.spec']
    
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            safe_print(f"Cleaned {dir_name} directory")
    
    for file_name in files_to_remove:
        if os.path.exists(file_name):
            os.remove(file_name)
            safe_print(f"Cleaned {file_name} file")

def safe_print(message):
    """安全的打印函数，避免在CI环境中出现编码问题"""
    try:
        print(message)
    except UnicodeEncodeError:
        # 在编码出错时，使用ASCII编码并忽略无法编码的字符
        ascii_message = message.encode('ascii', 'ignore').decode('ascii')
        print(f"[Encoding Issue] {ascii_message}")

def main():
    """主函数"""
    safe_print("Keymouse Spirit Build Script")
    safe_print("=" * 50)
    
    # 检查当前目录
    required_files = ['main_gui.py', 'start_gui.py', 'models.py', 'file_manager.py']
    for file in required_files:
        if not os.path.exists(file):
            safe_print(f"Error: Missing file {file}")
            return
    
    # 安装PyInstaller
    if not install_pyinstaller():
        return
    
    # 创建spec文件
    create_spec_file()
    
    # 构建exe
    if build_exe():
        safe_print("\nBuild completed successfully!")
        safe_print("You can find the executable file in the dist directory")
        
        # 检查是否在CI环境中（GitHub Actions）
        ci_env = os.environ.get('CI') or os.environ.get('GITHUB_ACTIONS')
        
        if ci_env:
            # 在CI环境中自动清理构建文件
            safe_print("In CI environment, automatically cleaning build files")
            clean_build_files()
        else:
            # 询问是否清理构建文件
            while True:
                choice = input("\nClean build files? (y/n): ").lower()
                if choice in ['y', 'yes', '是']:
                    clean_build_files()
                    break
                elif choice in ['n', 'no', '否']:
                    safe_print("Keeping build files")
                    break
                else:
                    safe_print("Please enter y or n")
    else:
        safe_print("Build failed")
        sys.exit(1)  # 在构建失败时退出并返回错误代码

if __name__ == "__main__":
    main()
