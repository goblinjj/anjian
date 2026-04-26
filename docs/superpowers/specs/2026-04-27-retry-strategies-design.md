# 循环医疗 & 制造 — 重试策略改造

日期：2026-04-27
范围：`tool_scripts.py:LoopHealingEngine`、`craft_engine.py:CraftEngine`

---

## 背景

两个引擎在"图片找不到时"的现行行为存在问题：

1. **循环医疗（`LoopHealingEngine._run`，`tool_scripts.py:174-260`）**：每个步骤里若图片未命中，会进入 `while not self.should_stop` 的**无限重试**（移开鼠标 → sleep 0.5s → 再找）。当上一次任务停在中间步骤、游戏处于"目标选择模式"等中间状态时，重启后的 step 1（治疗技能图标）会因为状态干扰而找不到，引擎卡在 step 1 无限重试，日志一直刷"未找到 X，移开重试…"，被用户误认为"还在检测后面步骤"。
2. **制造（`CraftEngine._craft_loop`，`craft_engine.py`）**：`craft_engine.py:237-240` 调用 `_click_template(execute_button_path, ...)` 时，**忽略返回值**直接进入"等待制造完成"。如果用户操作过程中干扰了双击（例如手动移动鼠标），并非全部材料都成功放入制造区、"开始制造"按钮也就没出现，可流程仍按"已点击执行"往下走，造成空转或后续步骤错乱。

---

## 目标

- A. 循环医疗：把"图片找不到"的无限重试改为**有限超时 + 重启本轮**，让中间状态自愈。
- B. 制造：把"双击材料后直接点执行"改为**先验证 `开始制造` 按钮出现，未出现则在材料足够前提下无限重试**；材料不够时回退到现有 organize + 兜底逻辑。

不改：GUI 启停按钮逻辑、配置文件格式、`_find_template` / `_click_template` / `_wait_for_template` 等工具函数签名。

---

## A 段 — 循环医疗：3 秒超时 + 重启本轮

### 改动位置

`tool_scripts.py:LoopHealingEngine`：
- 类属性新增 `RETRY_TIMEOUT = 3.0`
- 私有方法新增 `_find_with_retry(template_path, hwnd, timeout)`（封装"找不到 → 移开 → 限时重试"）
- `_run` 中现有的两段重试块（`tool_scripts.py:200-217` skill 步、`tool_scripts.py:224-241` member 步）改为调用 `_find_with_retry`

### 行为规约

#### `_find_with_retry(template_path, hwnd, timeout)` 语义
1. 取最新 `window_rect`；失败返回 `(None, None)`
2. 立即找一次 `_find_template(template_path, rect)`；命中即返回 `(pos, rect)`
3. 未命中：`bg_input.post_move(hwnd, rect[0]+50, rect[1]+50)`；进入限时循环
4. 循环条件：`time.time() < deadline and not self.should_stop`
   - 每轮：`time.sleep(0.5)` → 重取 `rect` → 再找 → 命中 break / 未命中再 `post_move`
5. 出循环：命中返回 `(pos, rect)`；未命中返回 `(None, last_rect)`

#### `_run` 主循环新行为
- skill 步调用 `pos, rect = self._find_with_retry(skill_image, hwnd, self.RETRY_TIMEOUT)`：
  - `pos is not None` → 像现在一样 `post_click` 并 log "步骤K: 点击治疗技能"
  - `should_stop` → `break` 跳出 for-loop（外层 while 自然退出）
  - 超时未命中 → log `"步骤K: {RETRY_TIMEOUT:.0f}秒未找到，重启本轮"` → `break` 跳出 for-loop（外层 while 进入 count+1 的下一轮，i 从 0 重启）
- member 步同上，只是图片换 `member_image`，命中后用 `mx + offset_x, my + offset_y` 计算点击坐标
- delay 步逻辑不变（`tool_scripts.py:252-259`）

### 为什么能解决用户描述的现象

上一次 stop 留下游戏处于"目标选择模式"等中间状态 → 重启后 step 1 找不到技能图标 → 旧代码无限重试看似"还在检测某张图"。新行为：3 秒超时 → 本轮废弃 → 期间 `post_move` 已把鼠标拨开、中间状态在下一轮通常已恢复，下一轮 step 1 命中 → 正常走完。

### 不引入超时配置

3 秒先写死成 `LoopHealingEngine.RETRY_TIMEOUT`。如果未来需要可调，再考虑暴露到配置 / 对话框。

---

## B 段 — 制造：验证按钮出现 + 仅在"重选成功"时重试

### 改动位置

`craft_engine.py:CraftEngine`：
- 私有方法新增 `_try_select_and_place_materials(...) -> bool`：把现有 `craft_engine.py:99-231`（locate_grid + 扫包 + 匹配 + organize 兜底 + 双击 matched slots）原封封装
- `_craft_loop` 中第 6+7 步用一次 `_try_select_and_place_materials` 调用替代原内联块
- 第 7 步与第 8 步之间新增"按钮验证 + 重选"循环

### `_try_select_and_place_materials` 语义

签名：

```python
def _try_select_and_place_materials(
    self, materials, all_mat_paths, recipe_dir,
    window_rect, organize_button_path,
    hwnd, click_pre_delay, click_interval,
    debug_first_scan: bool = False,
) -> bool
```

行为：

1. 检查窗口有效性、`locate_grid`（最多 3 次重试，沿用 `craft_engine.py:99-116`）；任一致命失败 → 返回 `False`（caller 中断主循环）
2. 检查数字模板加载情况（`craft_engine.py:119-123`）；未加载 → 返回 `False`
3. `scan_backpack`（`debug_first_scan=True` 时同步保存 debug 图，对应原 `is_first_scan` 行为）
4. 按 `materials` 顺序 `match_item`；全部命中 → 双击 matched_slots → 返回 `True`
5. 未全部命中：
   - `organize_button_path` 为空或 `should_stop` → log "材料不足，停止任务" → 返回 `False`
   - 否则：`_do_organize` → `locate_grid` → `scan_backpack` → 重新 `match_item`
   - 仍未全部命中 → log "整理背包后材料仍不足，停止任务" → 返回 `False`
   - 全部命中 → 双击 matched_slots → 返回 `True`
6. 任一阶段 `should_stop` → 返回 `False`（caller 通过 `_check_stop()` 判断真正原因）

返回值含义：`True` = 材料已被放入制造区可继续后续；`False` = 调用方应 `break` 退出 `_craft_loop`（与原现内联代码 `break` 行为完全一致）。

### `_craft_loop` 新结构

```
取 settings (execute_button_path / completion_image_path / organize_button_path / 等)
all_mat_paths = [...]                                 # 原有
while not should_stop:
    取 window_rect

    # 步骤 6+7 ＝ 选材并双击
    if not _try_select_and_place_materials(..., debug_first_scan=(craft_count==0)):
        break

    # 新增：步骤 7 ↔ 8 之间的按钮验证 + 重选
    if execute_button_path:
        button_visible = False
        while not should_stop:
            if _find_template(execute_button_path, window_rect):
                button_visible = True
                break                                  # 按钮出现, 进入步骤 8
            _log("未找到开始制造按钮，重新选择材料...")
            if not _try_select_and_place_materials(..., debug_first_scan=False):
                break                                  # 重选时材料不够 + 组织兜底也失败
        if not button_visible:
            break                                      # 中断整个 _craft_loop（用户按了停 / 兜底失败）

    # 步骤 8 — 点击 execute_button (此时已确认存在, 直接点)
    _log("点击执行...")
    if execute_button_path:
        _click_template(execute_button_path, window_rect)
    time.sleep(0.3)
    bg_input.post_move(...)

    # 步骤 9 — 等待制造完成 (沿用 craft_engine.py:247-281)
    ...

    # 步骤 10 — 背包空格子检查 (沿用 craft_engine.py:289-298)
    ...

    time.sleep(0.5)
```

### 关键设计决定

1. **execute_button_path 未配置时不启用验证循环**——保持现状"双击完直接走下去"行为。否则一上来就死循环。
2. **重选 = 重扫 + 重匹配 + 重双击**——不复用上一次的 `matched_slots`（已可能因材料移入制造区而失效）。
3. **重选时若材料不够 → 走 organize 兜底**——直接复用 `_try_select_and_place_materials` 内部已有的逻辑分支，与初次选材完全同一条路。仍不够则 `break` 整个 `_craft_loop`，等用户介入。
4. **每次重选 / 按钮检测前后频繁判 `should_stop`**——保持快速响应停止键，符合现有 engine 风格。
5. **`craft_count`、`success_count`、`fail_count` 计数语义不变**——只在第 9 步的"等待 + 完成按钮"成功 / 超时时增长。重选不计入失败。

### 显式接受的小风险

- 如果某些材料**已经在制造区**而背包恰好还有同款余量，重选会把背包余量也双击进去，可能造成"超量放置"。游戏端通常会拒绝多放，但这是"宁可重做也不漏 button"的代价，已与用户沟通确认。

---

## C 段 — 不动的东西

- `main_gui.py` 启停按钮 / `_start_loop_healing` / `_stop_tool` 逻辑：每次 start 都已经 `new` 一个新 engine，从上层就保证"重启从第 1 步起"。**不改代码**，但在 `LoopHealingEngine` 顶部加一行注释说明这个设计意图，方便日后维护。
- 配置文件格式、`hotkey_config.json`、recipe 数据结构。
- `_click_template` / `_find_template` / `_wait_for_template` 函数签名与实现。

---

## 测试要点

由于项目无单元测试 (`CLAUDE.md`)、`keyboard` / `mss` / windows API 是 Windows-only，自动化覆盖困难。本次走**手动验证清单**：

### 循环医疗
- [ ] **基本回归**：步骤齐全、图片可命中 → 多轮无异常
- [ ] **超时重启**：人为遮挡治疗技能 ≥ 3 秒（如打开聊天框）→ 日志出现 "步骤1: 3秒未找到，重启本轮"，松开后下一轮恢复
- [ ] **重启自愈（用户原始诉求）**：跑到 step 3+ → 按 ESC 停 → 立即按 ` 重启 → 不应永远卡在 "步骤1: 未找到"，最多 3 秒后会重启本轮直至命中
- [ ] **停止响应**：超时重试期间按 ESC → 1 秒内退出
- [ ] **delay 步**：行为不变，可正常计时

### 制造
- [ ] **基本回归**：材料齐全 → 一切正常
- [ ] **触发重选**：双击过程中人为干扰 → 部分材料未送进 → 按钮未出现 → 看到 "未找到开始制造按钮，重新选择材料..." → 在材料够的前提下，最终按钮出现并继续
- [ ] **重选→材料不够 → 走兜底**：重选时背包确实只剩一部分材料 → 触发 organize → 仍不够 → 整个任务停止（与原"材料不足"行为一致）
- [ ] **未配置 execute_button_image**：验证循环被跳过，行为同改造前
- [ ] **停止响应**：重选循环中按 ESC → 1 秒内退出
- [ ] **多轮制造稳定**：连续 5 轮以上无重选场景下表现与改造前一致（craft_count / success_count / fail_count 计数正常）

---

## 实施顺序（交给 writing-plans 拆步）

1. `LoopHealingEngine` 加 `RETRY_TIMEOUT` 常量、`_find_with_retry` 方法、改写 skill / member 步的内联重试块
2. `CraftEngine` 抽出 `_try_select_and_place_materials`（纯重构，行为不变）
3. `CraftEngine._craft_loop` 在第 7 步与第 8 步之间插入按钮验证 + 重选 while 块
4. 手动按测试要点逐项过一遍
