# 🛡️ Windows防火墙误报解决指南

## ⚠️ 常见问题

**问题**: 下载的`按键小精灵.exe`被Windows Defender删除或阻止运行

**原因**: 这是误报！由于程序包含自动化功能（鼠标键盘操作），可能被误认为是恶意软件。

## ✅ 安全说明

- ✅ **完全开源** - 所有代码公开在GitHub: https://github.com/goblinjj/anjian
- ✅ **无恶意代码** - 仅用于合法的自动化任务
- ✅ **无网络通信** - 程序不会上传任何数据
- ✅ **无隐私收集** - 不收集用户信息

## 🔧 解决方法

### 方法1: 添加排除项 (推荐)

1. **打开Windows安全中心**
   - 按 `Win + I` 打开设置
   - 点击 `更新和安全` → `Windows安全中心`
   - 点击 `病毒和威胁防护`

2. **添加排除项**
   - 点击 `病毒和威胁防护设置` 下的 `管理设置`
   - 滚动到 `排除项` 部分
   - 点击 `添加或删除排除项`
   - 点击 `添加排除项` → `文件`
   - 选择 `按键小精灵.exe` 文件

3. **添加文件夹排除**
   - 也可以选择 `文件夹`
   - 选择存放程序的整个文件夹

### 方法2: 临时禁用实时保护

1. **临时禁用** (不推荐长期使用)
   - 进入 `病毒和威胁防护`
   - 点击 `病毒和威胁防护设置` 下的 `管理设置`
   - 暂时关闭 `实时保护`
   - 运行程序后记得重新开启

### 方法3: 从隔离区恢复

如果文件已被删除：
1. 打开 `Windows安全中心`
2. 进入 `病毒和威胁防护`
3. 点击 `保护历史记录`
4. 找到被删除的文件
5. 点击 `操作` → `允许`

## 📱 移动端/其他杀毒软件

如果使用第三方杀毒软件（如360、火绒等）：
1. 打开杀毒软件设置
2. 找到 `白名单` 或 `信任区`
3. 添加 `按键小精灵.exe` 到白名单

## 🔍 验证文件安全性

### 在线扫描
可以使用VirusTotal等在线服务扫描文件：
1. 访问 https://www.virustotal.com/
2. 上传 `按键小精灵.exe` 文件
3. 查看多个杀毒引擎的检测结果

### 文件哈希验证
每个Release都会提供文件哈希值，可以验证文件完整性。

## 📞 反馈问题

如果问题持续存在：
1. 在GitHub仓库提Issue: https://github.com/goblinjj/anjian/issues
2. 提供Windows版本和杀毒软件信息
3. 我们会持续改进以减少误报

## ⚡ 快速解决方案

**最快方法**:
1. 下载文件到桌面
2. 右键文件 → `属性`
3. 勾选 `解除阻止` (如果有)
4. 将文件夹添加到Windows Defender排除列表
5. 正常使用

---

**记住**: 这是开源软件，代码完全透明，可以放心使用！
