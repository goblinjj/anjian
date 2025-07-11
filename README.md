# 按键小精灵

一个基于图像识别和键盘鼠标操作的游戏自动化工具。

[![GitHub release](https://img.shields.io/github/v/release/goblinjj/anjian?style=flat-square)](https://github.com/goblinjj/anjian/releases)
[![GitHub downloads](https://img.shields.io/github/downloads/goblinjj/anjian/total?style=flat-square)](https://github.com/goblinjj/anjian/releases)
[![Build Status](https://img.shields.io/github/actions/workflow/status/goblinjj/anjian/auto-release.yml?style=flat-square)](https://github.com/goblinjj/anjian/actions)

## 🚀 快速下载

### 💾 直接下载 (推荐)
👉 **[点击下载最新版本](https://github.com/goblinjj/anjian/releases/latest/download/按键小精灵.exe)**

或访问 **[Releases页面](https://github.com/goblinjj/anjian/releases)** 查看所有版本

### 📋 系统要求
- Windows 10/11
- 无需安装Python或其他依赖
- 下载即用，绿色软件

## 功能特性

- 🖼️ **图像识别**: 基于OpenCV的模板匹配，支持自定义置信度
- 🖱️ **鼠标操作**: 左键/右键点击，支持坐标偏移
- ⌨️ **键盘操作**: 按键模拟，支持组合键
- 🔄 **循环执行**: 可设置执行次数和延迟时间
- ⚡ **快捷键**: 全局快捷键控制启动/停止
- 💾 **配置管理**: 保存和加载自动化方案
- 🎯 **可视化编辑**: 直观的GUI界面，所见即所得

## 🚀 使用方法

### 直接运行 (推荐)
1. [下载最新版本](https://github.com/goblinjj/anjian/releases/latest)
2. 双击 `按键小精灵.exe` 运行
3. 无需安装，立即使用！

### ⚠️ Windows防火墙提示
如果Windows Defender误报为病毒：
- ✅ **这是误报** - 程序完全安全，代码开源透明
- 🛡️ **解决方法** - 查看 [Windows防火墙解决指南](WINDOWS_DEFENDER_GUIDE.md)
- 📁 **快速解决** - 将程序添加到Windows Defender排除列表

### 🔒 安全保证
- ✅ 完全开源，代码透明
- ✅ 无网络通信，无隐私收集  
- ✅ 无恶意代码，仅用于合法自动化
- ✅ 可通过VirusTotal等服务验证安全性

### 开发者安装

### 开发者安装

#### 1. 安装依赖
```bash
# 自动安装
双击运行 "安装依赖.bat"

# 或手动安装
pip install -r requirements.txt
```

### 2. 启动程序
```bash
# GUI启动
双击运行 "启动GUI.bat"

# 或命令行启动
python start_gui.py
```

### 3. 基本使用

1. **添加步骤**: 点击"添加步骤"按钮
2. **选择类型**: 
   - 图像搜索: 上传图片，设置点击动作
   - 键盘按键: 设置要按下的键
3. **配置参数**: 设置置信度、偏移量等
4. **运行测试**: 点击"开始执行"测试效果
5. **保存方案**: 保存为配置文件供后续使用

### 4. 编译程序
```bash
python build_exe.py
```
编译后的程序位于 `dist` 目录中。

## 配置文件

程序启动时会自动加载 `default.json` 配置文件。如果文件不存在，会创建一个空配置。

### 配置文件格式
```json
{
  "version": "1.0",
  "description": "自动化配置",
  "steps": [
    {
      "step_type": "image_search",
      "params": {
        "image_path": "target.png",
        "confidence": 0.8,
        "action": "left_click"
      },
      "enabled": true,
      "description": "点击目标图片"
    }
  ]
}
```

## 快捷键

- `F9`: 开始/停止执行
- `F10`: 紧急停止
- `F11`: 单步执行
- `F12`: 截图模式

## 注意事项

1. **管理员权限**: 某些游戏可能需要管理员权限运行
2. **屏幕分辨率**: 图片模板需要与目标屏幕分辨率匹配
3. **置信度设置**: 建议设置在0.7-0.9之间，过高可能导致识别失败
4. **安全性**: 请勿用于违反游戏条款的行为

## 故障排除

### 常见问题

1. **识别不到图片**
   - 检查图片是否清晰
   - 调整置信度参数
   - 确保屏幕分辨率匹配

2. **程序无响应**
   - 使用F10紧急停止
   - 检查是否有无限循环

3. **快捷键不生效**
   - 确保程序有足够权限
   - 检查是否被其他程序占用

## 技术支持

如有问题，请检查以下文件：
- `requirements.txt`: 依赖列表
- `示例配置.json`: 配置示例
- `default.json`: 默认配置

---
*按键小精灵 v1.0*
