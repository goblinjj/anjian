# 循环医疗 & 制造重试策略改造 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把"循环医疗每步无限重试"改为 3 秒超时 + 重启本轮；把"制造双击后忽略按钮"改为先验证按钮出现再点，验证失败时仅在材料够时无限重选。

**Architecture:** 两个引擎 (`LoopHealingEngine` / `CraftEngine`) 各自做局部改造，不引入新文件、不动 GUI 上层、不动配置格式。`CraftEngine` 顺手抽出两个私有 helper 把"匹配 + organize 兜底 + 双击"封装好，让"初次选材"和"重选"共用一条路径。

**Tech Stack:** Python 3.11 / OpenCV / PIL / 现有 `bg_input` / `screenshot_util` / `BackpackReader`。`time.time()` + `time.sleep()` 做超时（项目无单元测试框架，验证全部走手动 + 启动冒烟）。

**Spec Reference:** `docs/superpowers/specs/2026-04-27-retry-strategies-design.md`

---

## File Structure

| 文件 | 责任 | 改动 |
| --- | --- | --- |
| `tool_scripts.py` | `LoopHealingEngine` 循环医疗引擎 | 加 `RETRY_TIMEOUT` 类属性、加 `_find_with_retry` 方法、改写 `_run` 中 skill / member 步的内联重试块、加一行设计意图注释 |
| `craft_engine.py` | `CraftEngine` 制造引擎 | 加 `_match_materials` 与 `_try_select_and_place_materials` 两个私有方法、`_craft_loop` 内 step 6+7 用 helper 替换、step 7 与 step 8 之间加按钮验证 + 重选 while 块 |

不创建新文件，不写测试文件（项目无单元测试框架，且 `keyboard` / `mss` / Windows API 在 macOS 上跑不起来）。

---

## Task 1: A 段 — `LoopHealingEngine` 改 3 秒超时 + 重启本轮

**Files:**
- Modify: `tool_scripts.py:105-266`（`LoopHealingEngine` 类整体）

### Step 1.1: 给类加 `RETRY_TIMEOUT` 常量与设计意图注释

- [ ] 编辑 `tool_scripts.py`，把现有类头改为下方版本（增加注释 + 类属性，不动 docstring 已有内容）：

把 `tool_scripts.py:105-119` 的内容替换为：

```python
class LoopHealingEngine:
    """循环医疗引擎

    按自定义步骤序列循环执行，步骤可自由组合:
    - skill: 查找并点击治疗技能
    - member: 在队员基准位置 + 偏移处点击
    每次点击前统一 200ms 延迟。

    设计意图: 每次 main_gui 调用 start() 时, 都会创建一个新的引擎实例
    (见 main_gui.py:_start_loop_healing), 因此 stop → 重新 start 永远从
    第 1 个步骤开始, 不保留任何"上次执行到第几步"的状态。
    若步骤里某张图片在 RETRY_TIMEOUT 秒内仍找不到, 当轮放弃, 外层 while
    自动进入下一轮 (count+1, i 从 0 重启), 让游戏中间状态有机会恢复。
    """

    RETRY_TIMEOUT = 3.0  # 单步图片重试上限 (秒)

    def __init__(self, window_manager, status_callback=None):
        self.window_manager = window_manager
        self.status_callback = status_callback
        self.should_stop = False
        self.is_running = False
        self._thread = None
```

### Step 1.2: 在 `_find_template` 之后、`_run` 之前插入 `_find_with_retry` helper

- [ ] 在 `tool_scripts.py:172` (`return None`) 后面紧跟一个空行，再插入下面这段（位置在 `_find_template` 与 `_run` 之间）：

```python
    def _find_with_retry(self, template_path, hwnd, timeout, label):
        """限时反复查找模板, 找不到时移开鼠标后继续找。

        Args:
            template_path: 模板图片路径
            hwnd: 目标窗口句柄, 用于 post_move
            timeout: 重试时间上限 (秒)
            label: 日志前缀, 例如 "步骤3"

        Returns:
            tuple: (pos, rect)
                pos: (x, y, conf) 或 None (超时 / should_stop / 取窗口失败)
                rect: 最后一次有效的 window_rect, 失败时可能为 None
        """
        rect = self.window_manager.get_window_rect()
        if not rect:
            return None, None
        pos = self._find_template(template_path, rect)
        if pos:
            return pos, rect
        self._log(f"  {label}: 未找到, 移开重试 ({timeout:.0f}秒内)...")
        bg_input.post_move(hwnd, rect[0] + 50, rect[1] + 50)
        deadline = time.time() + timeout
        while not self.should_stop and time.time() < deadline:
            time.sleep(0.5)
            rect = self.window_manager.get_window_rect()
            if not rect:
                return None, None
            pos = self._find_template(template_path, rect)
            if pos:
                return pos, rect
            bg_input.post_move(hwnd, rect[0] + 50, rect[1] + 50)
        return None, rect
```

### Step 1.3: 改写 `_run` 中 skill 步的内联重试块

- [ ] 把 `tool_scripts.py:200-222`（`if step['type'] == 'skill':` 整段）替换为：

```python
                    if step['type'] == 'skill':
                        # 查找治疗技能图片 (限时重试)
                        skill_pos, rect = self._find_with_retry(
                            skill_image, hwnd, self.RETRY_TIMEOUT,
                            label=f"步骤{i+1}")
                        if self.should_stop:
                            break
                        if not skill_pos:
                            self._log(
                                f"  步骤{i+1}: {self.RETRY_TIMEOUT:.0f}秒未找到治疗技能, 重启本轮")
                            break
                        sx, sy, _ = skill_pos
                        if self.should_stop:
                            break
                        bg_input.post_click(hwnd, sx, sy, pre_delay=0.2)
                        self._log(f"  步骤{i+1}: 点击治疗技能")
```

### Step 1.4: 改写 `_run` 中 member 步的内联重试块

- [ ] 把 `tool_scripts.py:224-250`（`elif step['type'] == 'member':` 整段）替换为：

```python
                    elif step['type'] == 'member':
                        # 查找队员定位图片 (限时重试)
                        member_pos, rect = self._find_with_retry(
                            member_image, hwnd, self.RETRY_TIMEOUT,
                            label=f"步骤{i+1}")
                        if self.should_stop:
                            break
                        if not member_pos:
                            self._log(
                                f"  步骤{i+1}: {self.RETRY_TIMEOUT:.0f}秒未找到队员定位, 重启本轮")
                            break
                        mx, my, _ = member_pos
                        ox = step.get('offset_x', 0)
                        oy = step.get('offset_y', 0)
                        click_x = mx + ox
                        click_y = my + oy
                        if self.should_stop:
                            break
                        bg_input.post_click(hwnd, click_x, click_y, pre_delay=0.2)
                        self._log(f"  步骤{i+1}: 队员({ox},{oy})")
```

### Step 1.5: 冒烟检查 — 模块可正常 import

- [ ] 运行：

```bash
python -c "import tool_scripts; print(tool_scripts.LoopHealingEngine.RETRY_TIMEOUT)"
```

Expected output: `3.0`（无 SyntaxError / ImportError）。

### Step 1.6: 提交

- [ ] 提交：

```bash
git add tool_scripts.py
git commit -m "$(cat <<'EOF'
循环医疗: 单步图片找不到改 3 秒超时 + 重启本轮

- 加 LoopHealingEngine.RETRY_TIMEOUT = 3.0
- 加 _find_with_retry(template_path, hwnd, timeout, label) helper
- _run 中 skill / member 两段内联无限重试块改用新 helper
- 超时未命中 → log "K秒未找到, 重启本轮" → 跳出当轮 for-loop,
  外层 while 自动进入下一轮 (count+1, i 从 0)
- 类 docstring 增加"重启从第1步起"的设计意图说明
EOF
)"
```

---

## Task 2: B 段 — 抽出 `_match_materials` + `_try_select_and_place_materials`（纯重构）

> 这一任务**只移动代码不改行为**，是为下一步加重选 retry 做准备。完成后跑制造功能应当与改造前完全一致。

**Files:**
- Modify: `craft_engine.py:20-308`（`CraftEngine` 类）

### Step 2.1: 在类内部加 `_match_materials` helper

- [ ] 在 `craft_engine.py` 的 `_do_organize` 方法之前（约 `craft_engine.py:310` `def _do_organize(...)` 行的上方）插入：

```python
    def _match_materials(self, slots, materials, all_mat_paths, recipe_dir):
        """按 materials 顺序在 slots 中匹配每种材料, 同一格子不可重复使用。

        Returns:
            (matched_slots, all_matched):
                matched_slots: 命中顺序的 SlotInfo 列表
                all_matched: 是否全部材料都成功匹配
        """
        matched_slots = []
        used_positions = set()
        all_matched = True

        for i, mat in enumerate(materials):
            mat_image_path = os.path.join(recipe_dir, mat['image_file'])
            required_qty = mat['quantity']

            competing_paths = [
                p for j, p in enumerate(all_mat_paths) if j != i
            ]

            slot, info = self.backpack_reader.match_item(
                slots, mat_image_path, required_qty,
                exclude_slots=used_positions,
                competing_image_paths=competing_paths
            )

            if slot is None:
                qty_desc = "仅匹配" if required_qty == 0 else f"需{required_qty}个"
                self._log(f"材料{i+1}({qty_desc}): {info}")
                all_matched = False
                break

            matched_slots.append(slot)
            used_positions.add((slot.grid_x, slot.grid_y))
            self._log(f"材料{i+1}: {info}")

        return matched_slots, all_matched
```

### Step 2.2: 紧接着加 `_try_select_and_place_materials` helper

- [ ] 在 `_match_materials` 下方（仍在 `_do_organize` 之前）继续插入：

```python
    def _try_select_and_place_materials(self, materials, all_mat_paths,
                                         recipe_dir, window_rect,
                                         organize_button_path, hwnd,
                                         click_pre_delay, click_interval,
                                         debug_first_scan=False):
        """定位背包 → 扫描 → 匹配 (材料不够时走 organize 兜底) → 双击 matched slots。

        Returns:
            bool:
                True  = 材料已成功放入制造区, 调用方可继续后续步骤
                False = 调用方应中断 _craft_loop
                        (材料确实不够 / 致命错误 / 用户停止)
        """
        # 定位背包网格 (最多重试3次)
        self._log("定位背包网格...")
        grid_info = None
        for attempt in range(3):
            if self._check_stop():
                return False
            grid, info = self.backpack_reader.locate_grid(window_rect)
            if grid is not None:
                grid_info = grid
                self._log(info)
                break
            if attempt < 2:
                self._log(f"第{attempt+1}次定位失败: {info}，1秒后重试...")
                time.sleep(1)
            else:
                self._log(f"定位失败: {info}")

        if not grid_info:
            return False

        # 检查数字模板
        if not self.backpack_reader.digit_recognizer.is_loaded():
            loaded = len(self.backpack_reader.digit_recognizer.templates)
            self._log(f"错误: 数字模板未完整加载 (已加载{loaded}/10)，"
                      f"请在「设置」中截取0-9数字模板")
            return False

        # 扫描20个格子
        slots = self.backpack_reader.scan_backpack(
            grid_info, debug=debug_first_scan)
        if debug_first_scan:
            self._log("调试图片已保存到 debug/ 目录")

        empty_count = sum(1 for s in slots if s.is_empty)
        items_with_qty = sum(1 for s in slots if s.quantity is not None)
        items_no_qty = sum(
            1 for s in slots if not s.is_empty and s.quantity is None)
        self._log(f"扫描完成: {items_with_qty}个有数量, "
                  f"{items_no_qty}个数量未识别, {empty_count}个空格子")

        if self._check_stop():
            return False

        # 匹配每种材料
        matched_slots, all_matched = self._match_materials(
            slots, materials, all_mat_paths, recipe_dir)

        if not all_matched:
            if not organize_button_path or self._check_stop():
                self._log("材料不足，停止任务")
                return False

            # 整理背包后重新检查
            self._log("材料不足，尝试整理背包后重新检查...")
            self._do_organize(organize_button_path, window_rect)
            if self._check_stop():
                return False

            grid2, info2 = self.backpack_reader.locate_grid(window_rect)
            if not grid2:
                self._log(f"整理后定位失败: {info2}")
                return False
            slots2 = self.backpack_reader.scan_backpack(grid2)
            matched_slots, all_matched2 = self._match_materials(
                slots2, materials, all_mat_paths, recipe_dir)
            if not all_matched2:
                self._log("整理背包后材料仍不足，停止任务")
                return False

        if self._check_stop():
            return False

        # 双击匹配到的格子
        for slot in matched_slots:
            if self._check_stop():
                return False
            bg_input.post_double_click(
                hwnd, slot.screen_x, slot.screen_y,
                pre_delay=click_pre_delay, interval=click_interval)
            time.sleep(0.3)

        if self._check_stop():
            return False

        return True
```

### Step 2.3: 把 `_craft_loop` 中 step 3-7 的内联块替换为 helper 调用

- [ ] 把 `craft_engine.py:98-234`（从注释 `# 3. 定位背包网格...` 开始到 step 7 双击结束、`if self._check_stop(): break` 为止）整段替换为：

```python
                # 3-7. 选材并双击 (含 organize 兜底)
                hwnd = self.window_manager.hwnd
                all_mat_paths = [
                    os.path.join(recipe_dir, m['image_file'])
                    for m in materials
                ]
                if not self._try_select_and_place_materials(
                        materials, all_mat_paths, recipe_dir,
                        window_rect, organize_button_path,
                        hwnd, click_pre_delay, click_interval,
                        debug_first_scan=(self.craft_count == 0)):
                    break

                if self._check_stop():
                    break
```

### Step 2.4: 冒烟检查 — 模块可正常 import 且类签名完整

- [ ] 运行：

```bash
python -c "import craft_engine; assert hasattr(craft_engine.CraftEngine, '_try_select_and_place_materials'); assert hasattr(craft_engine.CraftEngine, '_match_materials'); print('ok')"
```

Expected output: `ok`。

### Step 2.5: 提交（明确标注是纯重构）

- [ ] 提交：

```bash
git add craft_engine.py
git commit -m "$(cat <<'EOF'
制造: 抽出 _match_materials / _try_select_and_place_materials (纯重构)

把 _craft_loop 中 step 3-7 (定位 + 扫包 + 匹配 + organize 兜底 + 双击)
封装为两个私有方法, 行为与改造前完全一致, 为下一步"按钮验证 + 重选"
让 _craft_loop 调用同一条选材路径做铺垫。

无功能变化。
EOF
)"
```

---

## Task 3: B 段 — 加入"开始制造按钮"验证 + 重选 while 块

**Files:**
- Modify: `craft_engine.py`（`_craft_loop` 内, step 7 与 step 8 之间）

### Step 3.1: 在 step 8 之前插入按钮验证 + 重选循环

- [ ] 在 `craft_engine.py:_craft_loop` 中，找到刚改造完的 "3-7. 选材并双击" 块结尾的 `if self._check_stop(): break`（紧跟 helper 调用之后），在它和原有的 `# 8. 点击执行按钮` 注释之间插入：

```python
                # 7.5. 验证"开始制造"按钮出现, 否则在材料够的前提下无限重选
                #     重选 = 重新调用 _try_select_and_place_materials, 内部已含
                #     organize 兜底; 兜底也失败 (返回 False) 则中断整个 _craft_loop
                if execute_button_path:
                    button_visible = False
                    while not self._check_stop():
                        window_rect = self.window_manager.get_window_rect()
                        if not window_rect:
                            self._log("错误: 无法获取窗口坐标")
                            break
                        if self._find_template(execute_button_path, window_rect):
                            button_visible = True
                            break
                        self._log("未找到开始制造按钮，重新选择材料...")
                        if not self._try_select_and_place_materials(
                                materials, all_mat_paths, recipe_dir,
                                window_rect, organize_button_path,
                                hwnd, click_pre_delay, click_interval,
                                debug_first_scan=False):
                            break
                    if not button_visible:
                        break
```

### Step 3.2: 简化原 step 8 的按钮点击（按钮已确认存在，无需再判 `if execute_button_path:` 但保留以兼容未配置场景）

- [ ] 不动原 step 8 代码（保留 `if execute_button_path:` 与 `_click_template`）。原因：当 `execute_button_path` 为空时，新增的验证循环被 `if execute_button_path:` 跳过，原 step 8 的同一判断仍需保留，行为与改造前一致。

> 这一步只是确认 — 不需要编辑任何代码，只需读一遍 `craft_engine.py` 中 `# 8. 点击执行按钮` 这一段（约 `craft_engine.py:236-244`）确保未被前面的 edit 误伤。

### Step 3.3: 冒烟检查

- [ ] 运行：

```bash
python -c "import craft_engine; print('ok')"
```

Expected output: `ok`。

- [ ] 用 `grep` 确认两处 helper 调用点都在：

```bash
grep -n "_try_select_and_place_materials" craft_engine.py
```

Expected output: 至少 3 行——一处方法定义 (`def _try_select_and_place_materials`)、一处初次选材调用、一处重选调用。

### Step 3.4: 提交

- [ ] 提交：

```bash
git add craft_engine.py
git commit -m "$(cat <<'EOF'
制造: 双击材料后必须先确认开始制造按钮出现才往下走

- step 7 与 step 8 之间加 while 循环: 找按钮 → 找到 break → 找不到
  日志后调用 _try_select_and_place_materials 重选 → 回 while 头
- 重选时材料够 → 重双击; 重选时材料不够 → 走 organize 兜底, 仍不够
  则中断整个 _craft_loop (与原"材料不足停止任务"行为一致)
- execute_button_path 未配置时整段验证被跳过, 行为同改造前
- 已与用户确认"超量放置"小风险可接受
EOF
)"
```

---

## Task 4: 手动验证清单

> 项目无单元测试 (`CLAUDE.md`)，且 `keyboard` / `mss` / Windows API 仅 Windows 可用。**这些项必须在 Windows + 真实游戏环境逐项跑过。**用户在 Windows 上进行验证。

### Step 4.1: 启动应用确认无运行时报错

- [ ] 在 Windows 上：`python start_gui.py`，确认主窗口正常打开、无 Python 异常弹窗、状态栏显示就绪。

### Step 4.2: 循环医疗 — 基本回归

- [ ] 配置一组步骤齐全、图片可命中的循环医疗任务
- [ ] 启动 → 至少跑通 3 轮无异常 → 停止
- [ ] 日志中应能看到 `[第1轮]` `[第2轮]` `[第3轮]`，每轮的 `步骤K: 点击治疗技能` / `步骤K: 队员(X,Y)`

### Step 4.3: 循环医疗 — 超时重启

- [ ] 启动循环医疗
- [ ] 在 step 1 (skill) 进行中，**人为遮挡治疗技能图标 ≥ 3 秒**（如打开聊天框 / 把游戏 UI 挡住）
- [ ] 日志应出现：`步骤1: 未找到, 移开重试 (3秒内)...` → 然后 `步骤1: 3秒未找到治疗技能, 重启本轮`
- [ ] 松开遮挡后，下一轮 `[第N+1轮]` 应正常恢复

### Step 4.4: 循环医疗 — 重启自愈（用户原始诉求）

- [ ] 启动循环医疗，让它跑到 step 3 或更后
- [ ] 立即按停止热键 (默认 ESC)
- [ ] 立即按启动热键 (默认 \`)
- [ ] 期望：**最多 3 秒内**应进入正常的下一轮，**不应**永远卡死在 `步骤1: 未找到, 移开重试...`

### Step 4.5: 循环医疗 — 停止响应

- [ ] 把治疗技能持续遮挡（让 step1 一直找不到）
- [ ] 在重试期间按 ESC
- [ ] 期望：1 秒内日志出现 `循环医疗已停止`，状态栏返回就绪

### Step 4.6: 循环医疗 — delay 步行为不变

- [ ] 配置一组带 `delay` 步的步骤
- [ ] 启动观察日志：`步骤K: 延迟 XXXms`，期间按 ESC 应在 0.1 秒内退出

### Step 4.7: 制造 — 基本回归

- [ ] 选好配方、材料齐全
- [ ] 启动 → 至少跑完 3 轮制造（success_count = 3）
- [ ] 日志中应有 `点击执行...` `等待制造Xs` `第 N 次制造完成`，**不应**出现 `未找到开始制造按钮`

### Step 4.8: 制造 — 触发重选并恢复

- [ ] 选好配方、材料齐全
- [ ] 启动后，在双击材料阶段**人为移动鼠标**干扰一两次，让部分材料没送进去
- [ ] 期望日志：`未找到开始制造按钮，重新选择材料...` → 重新扫包匹配双击 → 最终按钮出现 → `点击执行...` 继续

### Step 4.9: 制造 — 重选时材料不够 → 走 organize 兜底

- [ ] 配置 `organize_button_image`
- [ ] 选一个材料数量恰好够 1 次的配方
- [ ] 跑一轮成功后立即手动消耗 / 移走部分材料让数量不够
- [ ] 等待下一轮：应先看到 `材料不足，尝试整理背包后重新检查...`，再看到 `整理背包后材料仍不足，停止任务`
- [ ] 任务完整停止，状态栏回到就绪

### Step 4.10: 制造 — 未配置 `execute_button_image` 时跳过验证

- [ ] 在设置里清空 `execute_button_image`（或保持未配置）
- [ ] 启动一轮制造
- [ ] 日志**不应**出现 `未找到开始制造按钮，重新选择材料...`，行为与改造前一致

### Step 4.11: 制造 — 停止响应

- [ ] 在新增的"按钮验证 + 重选"循环中（人为干扰让按钮不出现），按 ESC
- [ ] 期望：1 秒内日志出现 `制造已停止`，主线程状态栏回到就绪

### Step 4.12: 编译打包冒烟

- [ ] `python build_exe.py` 应能成功生成 `dist/按键小精灵.exe`，无新增 PyInstaller warning（与改造前对比）

### Step 4.13: 完成清单后提交一份 verification 报告

- [ ] 在 PR / commit message / 简短笔记里列出 4.1-4.12 各项的实际结果（通过 / 跳过 / 失败 + 日志摘录），确认全部通过后再视为本任务完成。
