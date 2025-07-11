# 🚀 Release 发布指南

本项目配置了多种方式来自动发布Release，让用户可以直接从GitHub首页下载编译好的exe文件。

## 📋 发布方式

### 1. 自动发布 (推荐)
**文件**: `.github/workflows/auto-release.yml`

- **触发条件**: 推送代码到main/master分支
- **版本号**: 自动生成 (格式: v2025.07.11-1430)
- **功能**: 自动构建并发布到Releases页面

**使用方法**:
```bash
git add .
git commit -m "更新功能"
git push
```
推送后会自动创建新的Release！

### 2. 手动发布
**文件**: `.github/workflows/manual-release.yml`

#### 方式A: 使用Git标签
```bash
git tag v1.0.0
git push origin v1.0.0
```

#### 方式B: 手动触发
1. 进入GitHub仓库的"Actions"页面
2. 选择"Manual Release"工作流
3. 点击"Run workflow"
4. 输入版本号 (如: v1.0.0)
5. 选择是否为预发布版本
6. 点击运行

### 3. 标签发布 (原有方式)
**文件**: `.github/workflows/release.yml`
- 当创建Release时自动构建并上传文件

## 📦 Release内容

每个Release都包含:
- **按键小精灵.exe** - 主程序 (带logo.ico图标)
- ***.png** - 图片资源文件  
- ***.json** - 配置文件

## 🎯 用户下载体验

用户可以在项目首页看到:
1. **Latest Release** - 最新版本下载链接
2. **All Releases** - 所有历史版本
3. **直接下载** - 点击exe文件即可下载

## 📱 Release页面展示

每个Release包含:
- 🎉 版本标题和编号
- 📝 详细的更新说明
- 📦 下载文件列表
- 🕒 构建时间和提交信息
- ✨ 功能特性介绍
- 🚀 使用方法说明

## 🔧 自定义配置

### 修改自动发布触发条件
编辑 `.github/workflows/auto-release.yml`:
```yaml
on:
  push:
    branches: [ main ]  # 只在main分支触发
    paths-ignore:
      - '**.md'         # 忽略文档更改
```

### 修改版本号格式
在 `auto-release.yml` 中修改:
```powershell
$version = "v$date-$time"  # 当前格式
# 改为:
$version = "v1.$env:GITHUB_RUN_NUMBER"  # 递增版本号
```

### 自定义Release说明
修改工作流文件中的 `body:` 部分来自定义Release描述。

## 🚨 注意事项

1. **自动发布**会在每次推送时创建新Release
2. **手动发布**需要手动触发或使用git标签
3. 建议开发时使用自动发布，正式版本使用手动发布
4. Release一旦创建就会出现在项目首页
5. 用户可以直接从首页下载最新版本

## 📊 推荐工作流

1. **日常开发**: 使用自动发布，方便测试
2. **正式版本**: 使用手动发布，控制版本号
3. **重要更新**: 添加详细的Release Notes

现在推送代码就会自动在项目首页创建Release供用户下载！
