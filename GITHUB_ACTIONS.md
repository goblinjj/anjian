# GitHub Actions 自动构建说明

本项目配置了GitHub Actions来自动构建EXE文件。

## 工作流程

### 1. 自动构建 (build-exe.yml)
- **触发条件**: 推送到 main/master 分支、Pull Request、手动触发
- **功能**: 自动构建EXE文件并上传为构件(artifact)
- **输出**: `按键小精灵.exe` 和相关资源文件

### 2. 发布构建 (release.yml) 
- **触发条件**: 创建Release、推送、Pull Request、手动触发
- **功能**: 构建EXE并在Release时自动上传到Release页面
- **输出**: Release附件中的可执行文件

## 使用方法

### 手动触发构建
1. 进入GitHub仓库的 "Actions" 页面
2. 选择 "Build EXE" 或 "Build and Release" 工作流
3. 点击 "Run workflow" 按钮
4. 构建完成后在 "Artifacts" 中下载EXE文件

### 自动构建
- 每次推送代码到主分支时自动触发构建
- 创建Pull Request时会进行构建测试

### 创建Release
1. 在GitHub仓库中点击 "Releases"
2. 点击 "Create a new release"
3. 创建标签 (例如: v1.0.0)
4. 填写Release信息
5. 发布后会自动构建并上传EXE文件到Release

## 构建环境
- **操作系统**: Windows Latest
- **Python版本**: 3.11
- **构建工具**: PyInstaller
- **图标**: logo.ico

## 输出文件
构建完成后会生成以下文件：
- `按键小精灵.exe` - 主程序
- `*.png` - 图片资源文件
- `*.json` - 配置文件

## 注意事项
1. 确保 `logo.ico` 文件存在于根目录
2. 确保所有依赖都在 `requirements.txt` 中列出
3. 构建失败时检查Actions日志获取详细错误信息
