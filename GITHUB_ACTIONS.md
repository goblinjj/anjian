# GitHub Actions 自动构建说明

本项目配置了GitHub Actions来自动构建EXE文件。

## 最新更新 (2025-07-11)
- ✅ 更新 `actions/upload-artifact` 从 v3 到 v4
- ✅ 更新 `actions/setup-python` 从 v4 到 v5  
- ✅ 更新 `softprops/action-gh-release` 从 v1 到 v2
- ✅ 所有actions现在使用最新稳定版本
- ✅ 修复了编码问题
- 🚀 添加了自动Release发布功能

## 🎯 Release发布功能

### 自动发布 (auto-release.yml)
- **触发**: 推送到main/master分支
- **结果**: 自动创建Release并上传exe文件
- **版本**: 自动生成 (v2025.07.11-1430)

### 手动发布 (manual-release.yml)  
- **触发**: Git标签 或 手动运行
- **结果**: 创建指定版本的Release
- **控制**: 完全手动控制版本号和说明

## 📦 用户下载体验

现在用户可以:
1. 🔗 **直接下载**: 项目首页显示最新版本下载链接
2. 📋 **查看历史**: Releases页面显示所有版本  
3. 🚀 **一键运行**: 下载exe直接运行，无需安装

## 工作流程

### 1. 自动构建 (build-exe.yml)
- **触发条件**: 推送到 main/master 分支、Pull Request、手动触发
- **功能**: 自动构建EXE文件并上传为构件(artifact)
- **输出**: `按键小精灵.exe` 和相关资源文件

### 2. 发布构建 (release.yml) 
- **触发条件**: 创建Release、推送、Pull Request、手动触发
- **功能**: 构建EXE并在Release时自动上传到Release页面
- **输出**: Release附件中的可执行文件
