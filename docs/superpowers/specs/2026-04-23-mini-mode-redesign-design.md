# 迷你模式重设计 + 移除工具脚本日志

## 背景

当前迷你模式（main_gui.py:212-246, 693-731）在主窗口内通过隐藏 `_main_frame` / 显示 `_mini_frame` 实现，包含任务名、步骤、统计、3 个按钮（开始/停止/还原）和热键提示，约 400×140，仍带系统标题栏。三个工具脚本（自动遇敌、循环医疗、获取材料）通过 `status_callback=self._log_message` 把所有运行细节写入主窗口日志框和迷你模式的步骤标签。

用户希望：
1. 三个工具脚本完全静默，不输出任何运行日志
2. 迷你模式简化为单按钮 + 任务名，更小更紧凑，可拖动，双击还原

## 修改 1：移除三个工具的运行日志

将以下位置的引擎初始化改为不传 `status_callback`（即传 `None`）：
- `main_gui.py:77-78` — `GetMaterialEngine`
- `main_gui.py:583` — `AutoEncounterEngine`
- `main_gui.py:622` — `LoopHealingEngine`

引擎内部 `_log()` 方法已经判断 `if self.status_callback`，传 `None` 时所有 `_log()` 调用自动变成 no-op，无需改 `tool_scripts.py`。

错误消息（如「未绑定游戏窗口」、「执行出错」）也一并静默 —— 用户已确认完全静默。

`main_gui.py:672` 的 `self._log_message("获取材料: 未配置材料图片，请先配置")` 改为 `messagebox.showwarning`，因为这是配置缺失的提示，用户操作触发，需要可见反馈。

`制造` 功能（`CraftEngine`）的日志保持不变。

## 修改 2：迷你模式重设计

### 布局
```
┌────────────────────────────┐
│   配方: 高级回复药         │   ← _mini_task_label
│        [  开始  ]          │   ← _mini_toggle_btn
└────────────────────────────┘
```

### 行为
- **窗口**：`overrideredirect(True)` 移除系统标题栏，置顶；尺寸约 220×80；带 1px 边框（`tk.Frame(relief='solid', borderwidth=1)`）便于辨认窗口边界
- **任务名**：根据 `_selected_type`/`_selected_recipe`/`_selected_tool_id` 显示「配方: XXX」或「工具: XXX」
- **单按钮**：根据 `is_running or _active_tool_engine` 显示「开始」或「停止」，点击切换
- **拖动**：除按钮外区域绑定 `<ButtonPress-1>` 记录起点、`<B1-Motion>` 移动 `root.geometry(+x+y)`
- **还原**：除按钮外区域绑定 `<Double-Button-1>` 调用 `_exit_mini_mode`
- **任务完成**：保持迷你模式，按钮自动变回「开始」（不再像现在自动 `_exit_mini_mode`）

### 进入条件
- 未选择配方/工具时点击「迷你窗口」：弹 `messagebox.showinfo("提示", "请先选择配方或工具")`，不进入
- 选中配方时启动制造：进入迷你模式（同现在）
- 选中工具时启动：进入迷你模式（同现在）
- 「获取材料」是即时全局功能，无运行态，迷你模式下也不应通过开始按钮触发；显示「工具: 获取材料」时按钮置灰显示「（请用快捷键）」

### 删除元素
原 `_mini_frame` 中以下控件全部移除：
- `_mini_step_label`（步骤显示）
- `_mini_stats_label`（成功/失败统计）
- `_mini_hotkey_label`（热键提示）
- `_mini_stop_btn`（独立停止按钮，合并到 toggle 按钮）
- `_mini_restore_btn`（还原按钮，改用双击）

`_append_log` 中向 `_mini_step_label` 写入的逻辑（main_gui.py:867-871）一并移除。

### 退出迷你模式时的窗口恢复
- `_exit_mini_mode`：`overrideredirect(False)` 恢复装饰，`attributes('-topmost', False)`，恢复 `geometry` 到 `_saved_geometry`，pack 回 `_main_frame`

## 影响范围

仅修改 `main_gui.py`：
- `_create_widgets` 中的迷你模式区构建（212-246）
- `_enter_mini_mode` / `_exit_mini_mode` / `_toggle_mini_mode`（678-731）
- `_update_mini_buttons`（733-740）
- `_mini_start` / `_mini_stop` 合并为 `_mini_toggle`（742-753）
- 三处引擎初始化去掉 callback（77-78, 583, 622）
- `_trigger_get_material` 的未配置提示改为 `messagebox`（672）
- `_append_log` 中迷你模式步骤更新逻辑删除（867-871）
- 制造/工具运行结束时不再自动 `_exit_mini_mode`（537, 649, 665）

`tool_scripts.py` 不修改。

## 验证

由于工具运行需要 Windows + 游戏窗口环境，本地无法跑通。验收依据：
1. `python -c "import main_gui"` 无语法错误
2. 启动后主窗口正常，点击「迷你窗口」按钮：
   - 未选时弹提示
   - 选中配方/工具后进入小窗
3. 小窗可拖动、双击还原、单按钮切换
4. 还原后主窗口尺寸/位置回到原状
