#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
一键部署脚本
用于提交代码并触发GitHub Actions自动构建
"""

import subprocess
import sys
import os

def safe_print(message):
    """安全打印函数"""
    try:
        print(message)
    except UnicodeEncodeError:
        ascii_message = message.encode('ascii', 'ignore').decode('ascii')
        print(f"[Encoding Issue] {ascii_message}")

def run_command(command, description):
    """运行命令并显示结果"""
    safe_print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, encoding='utf-8')
        if result.returncode == 0:
            safe_print(f"✅ {description}成功")
            if result.stdout.strip():
                safe_print(f"   输出: {result.stdout.strip()}")
            return True
        else:
            safe_print(f"❌ {description}失败")
            if result.stderr.strip():
                safe_print(f"   错误: {result.stderr.strip()}")
            return False
    except Exception as e:
        safe_print(f"❌ {description}异常: {str(e)}")
        return False

def main():
    """主函数"""
    safe_print("🚀 按键小精灵一键部署")
    safe_print("=" * 50)
    
    # 检查是否在git仓库中
    if not os.path.exists('.git'):
        safe_print("❌ 当前目录不是git仓库")
        safe_print("请先初始化git仓库：")
        safe_print("git init")
        safe_print("git remote add origin <your-repo-url>")
        return False
    
    # 检查git状态
    safe_print("📋 检查git状态...")
    if not run_command("git status --porcelain", "检查git状态"):
        return False
    
    # 添加所有文件
    if not run_command("git add .", "添加文件到暂存区"):
        return False
    
    # 获取提交信息
    safe_print("\n📝 请输入提交信息（回车使用默认）:")
    commit_message = input("提交信息: ").strip()
    if not commit_message:
        commit_message = "更新代码，触发自动构建"
    
    # 提交代码
    commit_cmd = f'git commit -m "{commit_message}"'
    if not run_command(commit_cmd, "提交代码"):
        safe_print("⚠️  可能没有新的更改需要提交")
    
    # 推送代码
    if not run_command("git push", "推送代码到远程仓库"):
        safe_print("💡 如果是首次推送，请使用：")
        safe_print("git push -u origin main")
        return False
    
    safe_print("\n🎉 部署完成！")
    safe_print("📱 GitHub Actions将自动：")
    safe_print("   1. 检出代码")
    safe_print("   2. 构建exe文件")
    safe_print("   3. 生成哈希校验")
    safe_print("   4. 创建Release")
    safe_print("   5. 上传文件")
    
    safe_print("\n🔗 查看构建状态：")
    safe_print("   https://github.com/<username>/<repo>/actions")
    
    safe_print("\n📦 下载Release：")
    safe_print("   https://github.com/<username>/<repo>/releases")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
