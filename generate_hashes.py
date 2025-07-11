#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文件哈希生成器
用于生成exe文件的MD5、SHA1、SHA256哈希值
供用户验证文件完整性
"""

import hashlib
import os
import sys

# 设置编码，避免在CI环境中出现编码问题
if os.environ.get('CI') or os.environ.get('GITHUB_ACTIONS'):
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

def safe_print(message):
    """安全的打印函数，避免在CI环境中出现编码问题"""
    try:
        print(message)
    except UnicodeEncodeError:
        # 在编码出错时，使用ASCII编码并忽略无法编码的字符
        ascii_message = message.encode('ascii', 'ignore').decode('ascii')
        print(f"[Encoding Issue] {ascii_message}")

def calculate_hash(file_path, hash_algorithm):
    """计算文件哈希值"""
    hash_obj = hashlib.new(hash_algorithm)
    
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except FileNotFoundError:
        return None

def generate_hash_file(exe_path):
    """生成哈希文件"""
    if not os.path.exists(exe_path):
        print(f"文件不存在: {exe_path}")
        return
    
    # 计算各种哈希值
    md5_hash = calculate_hash(exe_path, 'md5')
    sha1_hash = calculate_hash(exe_path, 'sha1')
    sha256_hash = calculate_hash(exe_path, 'sha256')
    
    # 获取文件大小
    file_size = os.path.getsize(exe_path)
    
    # 生成哈希信息
    hash_info = f"""文件哈希验证信息
====================================

文件名: {os.path.basename(exe_path)}
文件大小: {file_size:,} bytes ({file_size / 1024 / 1024:.2f} MB)

MD5:    {md5_hash}
SHA1:   {sha1_hash}
SHA256: {sha256_hash}

验证方法:
--------
Windows PowerShell:
Get-FileHash -Algorithm MD5 "按键小精灵.exe"
Get-FileHash -Algorithm SHA1 "按键小精灵.exe"  
Get-FileHash -Algorithm SHA256 "按键小精灵.exe"

Windows CMD:
certutil -hashfile "按键小精灵.exe" MD5
certutil -hashfile "按键小精灵.exe" SHA1
certutil -hashfile "按键小精灵.exe" SHA256

Linux/macOS:
md5sum "按键小精灵.exe"
sha1sum "按键小精灵.exe"
sha256sum "按键小精灵.exe"

在线验证:
上传到 https://www.virustotal.com/ 进行多引擎安全扫描

生成时间: {os.path.getctime(exe_path)}
"""
    
    # 保存哈希文件
    hash_file_path = exe_path.replace('.exe', '_hashes.txt')
    with open(hash_file_path, 'w', encoding='utf-8') as f:
        f.write(hash_info)
    
    safe_print(f"Hash file generated: {hash_file_path}")
    safe_print(f"MD5: {md5_hash}")
    safe_print(f"SHA256: {sha256_hash}")
    
    return hash_file_path

def main():
    """主函数"""
    exe_path = "dist/按键小精灵.exe"
    
    if os.path.exists(exe_path):
        generate_hash_file(exe_path)
    else:
        safe_print("EXE file not found")
        safe_print("Please run 'python build_exe.py' first")

if __name__ == "__main__":
    main()
