# 自定义工具 (Custom Tool) 设计稿

**日期**: 2026-05-05
**作者**: Claude (Brainstorming with user)
**状态**: 待评审

## 目标

在"魔力宝贝制造助手"中新增 **自定义工具** 功能。用户可在 GUI 内编排一组动作步骤, 保存后自动出现在左侧树的"自定义"分类下, 可像内置工具一样开始/停止运行。

每个自定义工具支持以下 8 种步骤的任意组合:

1. 鼠标移动
2. 鼠标左键
3. 鼠标右键
4. 鼠标双击
5. 键盘输入 (单键 或 ASCII 文本串)
6. 组合键
7. 图片查询 (可设找到后动作 + 偏移; 可设找不到的处理方式)
8. 等待时间 (固定毫秒)

## 关键设计决定

| # | 主题 | 选择 |
|---|---|---|
| 1 | 运行模式 | 用户每个工具自选: 循环 (loop) 或 单次 (once) |
| 2 | 树位置 | 新增独立分类 "自定义", 与"配方"/"工具"并列 |
| 3 | 图片查询语义 | 找到后动作可选 (左键/双击/右键/移动/无), 找不到处理可选 (跳过/重试后跳过/重试后停止) |
| 4 | 鼠标坐标系 | 相对游戏窗口中心的 X/Y 偏移 (与"自动遇敌"一致) |
| 5 | 快捷键 | 不支持独立快捷键, 沿用全局 backtick 启动选中项 |
| 6 | 键盘输入 | 步骤里二选一: 单键 或 ASCII 文本串 (不支持中文/大写) |
| 7 | 等待 | 固定毫秒 |

## 架构

### 新增文件

- `custom_tool_manager.py` — 仿 `recipe_manager.py`, 负责 list / load / save / delete (一个工具 = 一个 JSON)
- `custom_tool_dialog.py` — 编辑对话框 + 8 种步骤的子编辑器
- `custom_tool_engine.py` — 执行引擎 (单次 / 循环, 仿 `LoopHealingEngine` 线程模型)
- `custom_tools/` 目录 — 存自定义工具 JSON + 图片模板

### 修改文件

- `bg_input.py` — 新增 `post_right_click()` 和 `post_text()`
- `main_gui.py` — 树新增"自定义"分类, 串联编辑/启停/状态显示

## 数据模型

### 自定义工具 JSON 格式

`custom_tools/<name>.json`:

```json
{
  "version": "1.0",
  "name": "我的自定义流程",
  "mode": "loop",
  "description": "可选说明",
  "steps": [
    { "type": "mouse_move", "offset_x": 100, "offset_y": -50 },
    { "type": "mouse_click", "offset_x": 100, "offset_y": -50 },
    { "type": "mouse_right_click", "offset_x": 0, "offset_y": 0 },
    { "type": "mouse_double_click", "offset_x": 0, "offset_y": 0 },
    { "type": "key_press", "input_mode": "single", "key": "enter" },
    { "type": "key_press", "input_mode": "text", "text": "hello", "char_interval_ms": 30 },
    { "type": "hotkey", "keys": ["ctrl", "e"] },
    {
      "type": "image_search",
      "image_path": "custom_tools/<name>/img1.png",
      "offset_x": 0,
      "offset_y": 0,
      "on_found": "click",
      "on_not_found": "retry_skip",
      "retry_seconds": 3.0,
      "threshold": 0.7
    },
    { "type": "wait", "ms": 500 }
  ]
}
```

`mode` 取值: `"loop"` | `"once"`
`on_found` 取值: `"click"` | `"double_click"` | `"right_click"` | `"move"` | `"none"`
`on_not_found` 取值: `"skip"` | `"retry_skip"` | `"retry_stop"`

### 目录结构

```
custom_tools/
  ├── 自动战斗.json
  ├── 自动战斗/                  # 该工具的图片模板隔离子目录
  │   └── img_20260505_120000.png
  ├── 进背包.json
  └── 进背包/
      └── ...
```

## UI 设计

### 左侧树

```
配方
  └── (用户的配方)
工具
  ├── 自动遇敌
  ├── 循环医疗
  └── 获取材料
自定义                           ← 新增分类节点 (粗体, open)
  ├── 自动战斗   (loop)          ← 文本后缀显示模式
  └── 进背包     (once)
```

空时分类下显示一行不可选灰字: `暂无自定义工具, 点击下方「新建自定义」`。

### 树下方按钮的动态文案

| 选中类型 | "新建" | "编辑" | "删除" | "开始" |
|---|---|---|---|---|
| 配方 | 新建配方 | 编辑 | 删除 | 开始制造 |
| 工具(内置) | 新建配方 | 配置 | 禁用 | 开始执行 / 执行一次 |
| 自定义工具 | 新建自定义 | 编辑 | 删除 | 开始执行 / 执行一次 |
| 自定义分类节点 | 新建自定义 | 禁用 | 禁用 | 禁用 |
| 配方/工具分类节点 | 新建配方 | 禁用 | 禁用 | 禁用 |

### 关键交互

- 选中"自定义"分类节点 → "新建"按钮变 `新建自定义`, 点击弹出编辑对话框 (空模板)
- 选中某个自定义工具 → 右侧详情区显示模式 + 步骤摘要
- 双击自定义工具 ≡ 点"编辑"
- "开始"按钮文案随 `mode` 切换: `loop` → "开始执行" (含停止), `once` → "执行一次"
- 执行中: 复用现有的"迷你模式 + 状态栏 + 日志区", 迷你模式标签显示 `自定义: <name>`
- 全局 backtick 走现有 `start_selected()` 入口, 在 `_on_start()` 增加 `'custom'` 分支
- 全局 ESC 走 `_active_tool_engine.stop()`, 自动适配

### 编辑对话框 (CustomToolDialog)

尺寸 ~560 × 640, 模态, 可纵向拉伸。

```
┌─ 自定义工具编辑 ───────────────────────────────────────┐
│ ┌─ 基本信息 ─────────────────────────────────────────┐ │
│ │ 名称:    [          ]                               │ │
│ │ 模式:    (•) 循环   ( ) 单次                        │ │
│ │ 说明:    [                                       ]  │ │
│ └────────────────────────────────────────────────────┘ │
│                                                        │
│ ┌─ 步骤序列 (按顺序执行) ────────────────────────────┐ │
│ │ ┌──────────────────────────────────────────────┐  │ │
│ │ │ #1  鼠标左键    偏移(100, -50)               │  │ │
│ │ │ #2  等待        500ms                        │  │ │
│ │ │ #3  图片查询    enemy.png  找到→点击 偏移... │  │ │
│ │ │ ...                                          │  │ │
│ │ └──────────────────────────────────────────────┘  │ │
│ │                                                    │ │
│ │ [+ 添加步骤 ▼]  [编辑] [删除] [上移] [下移] [复制] │ │
│ └────────────────────────────────────────────────────┘ │
│                                                        │
│                                       [确定]   [取消]  │
└────────────────────────────────────────────────────────┘
```

**步骤列表**:

- `ttk.Treeview` + 滚动条
- `selectmode='extended'` (支持 Ctrl 点选 + Shift 范围选)
- 双击行 ≡ 编辑

**+ 添加步骤** 是 `ttk.Menubutton`, 弹下拉菜单 8 项:
```
+ 添加步骤 ▼
  ├ 鼠标移动
  ├ 鼠标左键
  ├ 鼠标右键
  ├ 鼠标双击
  ├ 键盘输入
  ├ 组合键
  ├ 图片查询
  └ 等待
```

**新步骤插入位置**:

| 当前选中状态 | 插入位置 |
|---|---|
| 单选某步骤 | 该步骤的下一行 |
| 多选 | 最后一个选中行的下一行 |
| 无选中 / 选中分类节点 | 列表末尾 |

新步骤插入后自动选中, 方便连按"+ 添加步骤"做连续编排。

**按钮在多选时的行为**:

| 按钮 | 单选 | 多选 |
|---|---|---|
| 编辑 | 弹子对话框 | 灰禁用 |
| 删除 | 删 1 个 | 删全部选中 |
| 上移 / 下移 | 移 1 个 | 选中区视作连续块整体上下移; 非连续则用首项 |
| 复制 | 复制 1 步, 插到自身下一行 | 复制全部选中, 整组按原顺序插到最后选中行下一行; 复制后的新行变为选中 |

**复制语义**: 就地复制 (duplicate in place), 没有"粘贴"动作, 不维护剪贴板。

**步骤行显示格式**:
```
#1  鼠标左键    偏移(100, -50)
#2  等待        500 ms
#3  图片查询    enemy.png  找到→点击 偏移(0,0)  3秒未找到→重试停止
#4  键盘输入    单键: enter
#5  键盘输入    文本: "hello"
#6  组合键      ctrl + e
```

**确定按钮校验**:
- 名称非空且文件名合法
- 至少 1 个步骤
- 编辑模式下若新名 == 原名 → 直接覆盖
- 若新名 != 原名且新名已存在 → 拒绝

**取消按钮**: 直接关闭, 不写盘 (但要清理本次会话临时新增的图片, 见下文"图片模板生命周期")。

## 子对话框 (8 种步骤)

### 鼠标类 (4 种共用一个)

适用于: `mouse_move` / `mouse_click` / `mouse_right_click` / `mouse_double_click`。参数完全一致, 仅标题不同。

```
┌─ 编辑[鼠标左键] ─────────────────┐
│ X 偏移: [  100 ⇅]                │
│ Y 偏移: [  -50 ⇅]                │
│ (相对游戏窗口中心, 正X右/正Y下)  │
│                  [确定] [取消]   │
└──────────────────────────────────┘
```

- 范围 `-2000 ~ 2000`, 步进 10

### 键盘输入 (key_press)

```
┌─ 编辑[键盘输入] ─────────────────────────────┐
│ 模式: (•)单键    ( )文本串                   │
│                                              │
│ ── 单键模式 ──                               │
│ 按键: [ enter        ▼]                      │
│                                              │
│ ── 文本串模式 ──                             │
│ 文本: [_____________________________]        │
│       仅 ASCII (不支持中文/大写)             │
│ 字间隔: [ 30 ⇅] ms                           │
│                                              │
│                          [确定] [取消]       │
└──────────────────────────────────────────────┘
```

- 模式切换时只显示对应那组字段, 另一组隐藏
- 单键 Combobox 的下拉项: `enter / space / tab / esc / backspace / delete / up / down / left / right / home / end / f1~f12`, 同时允许直接输入单字符
- 文本串校验: 包含非 ASCII 字符 (中文等) 或大写字母时, 弹 messagebox 提示用户修改, 拒绝保存 (不静默 lower 化, 避免用户误以为生效)

### 组合键 (hotkey)

```
┌─ 编辑[组合键] ───────────────────────────────┐
│ 组合键:  [ ctrl+e            ] [录制]        │
│ 例: ctrl+c / alt+f4 / ctrl+shift+s           │
│                          [确定] [取消]       │
└──────────────────────────────────────────────┘
```

- 输入框直接填 `ctrl+e` 风格, 保存时拆 `+` 调 `_vk_of()` 校验
- "录制"按钮复用 `GetMaterialDialog` 已有的 `keyboard.read_hotkey()` 逻辑

### 图片查询 (image_search)

```
┌─ 编辑[图片查询] ─────────────────────────────────┐
│ ┌─ 图片模板 ───────────────────────────────────┐ │
│ │ 当前: enemy.png  [✓]   [截图] [更换]         │ │
│ └──────────────────────────────────────────────┘ │
│                                                  │
│ ┌─ 找到后动作 ─────────────────────────────────┐ │
│ │ 动作: [ 左键单击 ▼ ]                         │ │
│ │ 偏移: X [ 0 ⇅]  Y [ 0 ⇅]  (相对匹配中心)     │ │
│ └──────────────────────────────────────────────┘ │
│                                                  │
│ ┌─ 找不到时 ───────────────────────────────────┐ │
│ │ 处理: [ 重试后跳过本步 ▼ ]                   │ │
│ │ 重试时长: [ 3.0 ⇅] 秒                        │ │
│ │ 匹配阈值: [ 0.7 ⇅]                           │ │
│ └──────────────────────────────────────────────┘ │
│                              [确定] [取消]       │
└──────────────────────────────────────────────────┘
```

- "截图": 复用 `_screenshot_region` 回调, 存到 `custom_tools/<工具名>/img_<时间戳>.png`
- "动作"下拉: 左键单击 / 左键双击 / 右键单击 / 仅移动 / 什么也不做
- "处理"下拉: 跳过本步 / 重试后跳过本步 / 重试后停止整个工具
- 阈值默认 0.7, 范围 0.5 ~ 0.95

### 等待 (wait)

```
┌─ 编辑[等待] ──────────────────────────────┐
│ 等待时间: [ 500 ⇅] ms (50 ~ 30000)        │
│                       [确定] [取消]       │
└───────────────────────────────────────────┘
```

## 执行引擎 (CustomToolEngine)

仿 `LoopHealingEngine` 的线程模型 + `should_stop` 旗标。

### 类骨架

```python
class CustomToolEngine:
    def __init__(self, window_manager, status_callback=None):
        self.window_manager = window_manager
        self.status_callback = status_callback
        self.should_stop = False
        self.is_running = False
        self._thread = None

    def start(self, tool_data):
        ...

    def stop(self):
        self.should_stop = True

    def _run(self, tool_data):
        # set_capture_hwnd → 校验窗口 → 主循环 → finally 清理
        mode = tool_data.get('mode', 'loop')
        steps = tool_data.get('steps', [])
        if mode == 'once':
            self._execute_steps(steps)
        else:
            count = 0
            while not self.should_stop:
                count += 1
                self._log(f"[第{count}轮]")
                if not self._execute_steps(steps):
                    break  # image_search 的 retry_stop 走到这

    def _execute_steps(self, steps) -> bool:
        for i, step in enumerate(steps):
            if self.should_stop:
                return False
            ok = self._execute_one(i, step)
            if not ok:
                return False
        return True

    def _execute_one(self, idx, step) -> bool:
        # dispatch by step['type']
        ...
```

### 单步执行细则

| 步骤类型 | 实现 |
|---|---|
| `mouse_move` | `_resolve_offset()` → `bg_input.post_move(hwnd, x, y)` |
| `mouse_click` | `bg_input.post_click(hwnd, x, y)` |
| `mouse_right_click` | `bg_input.post_right_click(hwnd, x, y)` |
| `mouse_double_click` | `bg_input.post_double_click(hwnd, x, y)` |
| `key_press` (single) | `bg_input.post_key(hwnd, step['key'])` |
| `key_press` (text) | `bg_input.post_text(hwnd, step['text'], step['char_interval_ms']/1000)` |
| `hotkey` | `bg_input.post_hotkey(hwnd, *step['keys'])` |
| `image_search` | 见下文 |
| `wait` | 分片 sleep 50ms 检查 should_stop |

### `_resolve_offset(offset_x, offset_y)`

```python
rect = self.window_manager.get_window_rect()
cx = rect[0] + rect[2] // 2
cy = rect[1] + rect[3] // 2
return cx + offset_x, cy + offset_y
```

每步实时查 rect, 期间窗口被拖也能跟上 (与 `craft_engine` 同思路)。

### `image_search` 步骤逻辑

```
1. 取 window_rect, 用 step['threshold'] 调 _find_template (复用 LoopHealingEngine 的实现)
2. 找到:
   match_x, match_y = matched_pos
   target_x = match_x + step['offset_x']
   target_y = match_y + step['offset_y']
   action = step['on_found']
   if action == 'click':         post_click(target_x, target_y)
   elif action == 'double_click':post_double_click(...)
   elif action == 'right_click': post_right_click(...)
   elif action == 'move':        post_move(...)
   elif action == 'none':        pass
   return True
3. 没找到:
   on_not_found = step['on_not_found']
   if on_not_found == 'skip':
       return True
   # retry_skip / retry_stop:
   deadline = time.time() + step['retry_seconds']
   while not should_stop and time.time() < deadline:
       time.sleep(0.5)
       重新取 rect, 重新 _find_template
       找到 → 走步骤 2 的动作 → return True
   # 仍没找到:
   return True if on_not_found == 'retry_skip' else False
```

### 与 main_gui 的对接

```python
def _start_custom_tool(self):
    tool = self.custom_tool_manager.load(self._selected_custom_name)
    engine = CustomToolEngine(self.window_manager, self._log_message)
    engine.start(tool)
    self._active_tool_engine = engine
```

复用现有 `_monitor_tool_engine()` 轮询 `is_running` 自动还原 UI 状态; 单次模式工具走完 `_run` 后自动结束, 无需用户手动停止。

### bg_input.py 新增

```python
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
MK_RBUTTON = 0x0002

def post_right_click(hwnd, screen_x, screen_y, pre_delay=0.0, hold_time=0.05):
    """右键单击, 与 post_click 完全镜像。"""
    ...

def post_text(hwnd, text, char_interval=0.03):
    """逐字符 post_key, 仅 ASCII 小写/数字/常见符号。"""
    for c in text:
        post_key(hwnd, c)
        time.sleep(char_interval)
```

**大小写限制说明**: `_vk_of` 把 'A' 和 'a' 都映射成 VK_A, 但游戏收到 WM_KEYDOWN 不会自动加 Shift。所以第一版只支持小写 ASCII / 数字 / 常见标点; 子对话框里有灰字提示。

## 文件命名 & 校验

`CustomToolManager.save()`:
- 工具名 → 文件名: 去除 `< > : " / \ | ? *` 等 Windows 非法字符, trim 空白
- 空名 / 全非法字符 → 拒绝保存, 返回错误给对话框
- 重名: 编辑时若新名 == 老名直接覆盖; 若新名 != 老名且新名已存在则拒绝

## 图片模板生命周期

每个工具有专属子目录 `custom_tools/<工具名>/`:
- 新建 image_search 截图 → 存到该子目录, 文件名 `img_<时间戳>.png`
- **重命名工具**: `_save()` 时检测到名变 → 把整个旧子目录 rename, 同时把所有 `image_search` 步骤的 `image_path` 字段批量改写指向新路径
- **删除工具**: 删 JSON 同时递归删该子目录 (用 `messagebox.askyesno` 二次确认)
- **取消编辑**: 用 `_pending_images` 列表收集本次会话新增的截图; 取消时清理掉, 已存在的图不动

## 右侧详情区显示

格式仿现有 `_show_tool_info()`:

```
自定义工具: 自动战斗
模式: 循环
说明: (用户填的)
步骤数: 6
  #1 鼠标左键 偏移(100,-50)
  #2 等待 500ms
  #3 图片查询 enemy.png ...
  ...
```

步骤数 > 8 时只摘要前 8 行, 末尾加 `...还有 N 步`。

## 与现有迷你模式 / 热键的整合

- 启动后 `_enter_mini_mode("自定义: <name>")` — 与 "工具: 自动遇敌" 同样的标签格式
- 全局 backtick 走现有 `start_selected()` 入口, 只需在 `_on_start()` 里加 `'custom'` 分支
- 全局 ESC 已是停 `_active_tool_engine.stop()`, 自定义工具自动复用

## 不在第一版做的事 (YAGNI 边界)

明确 **不** 包含:

- ❌ if/while/for 等流程控制
- ❌ 自定义工具独立快捷键
- ❌ 中文/大写字母文本输入
- ❌ 步骤级注释/启用禁用开关
- ❌ 工具间复制粘贴 (仅"就地复制"在单工具内)
- ❌ 局部独立测试程序 (用 GitHub Actions 编译后在 Windows 手动验证即可)
