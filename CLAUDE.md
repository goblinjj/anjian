# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**魔力宝贝制造助手 (Cross Gate Crafting Assistant)** — A Windows-only automation tool for the game 魔力宝贝 (Cross Gate / Magic Baby). Uses OpenCV image recognition, template-based digit recognition, and **background input via `PostMessage`** (game responds without moving the real cursor / stealing focus). Python + tkinter GUI, distributed as a PyInstaller .exe.

The repo was previously a generic automation tool ("按键小精灵") with a tree-based step editor; that architecture is **gone**. Don't restore it. The README.md is also stale and describes the old project — trust this file.

The entire UI and code comments are in **Chinese**.

## Build & Run

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application (Windows only — pywin32, keyboard, BitBlt are required)
python start_gui.py

# Build Windows executable
python build_exe.py
# Output: dist/魔力宝贝制造助手.exe   (CI builds an ASCII name then renames)

# Run unit tests
python -m pytest tests/
python -m pytest tests/test_recipe_manager.py -v   # single file
```

`test_antivirus_setup.py` at the repo root is a standalone antivirus checker, **not** a unit test. Real unit tests live in `tests/`.

## Architecture

**Entry flow:** `start_gui.py` (deps check) → `main_gui.py:CraftAssistantGUI`.

The main window has three top-level work modes selected from a Treeview on the left:

1. **配方 (Recipe)** — automated crafting loop driven by `CraftEngine` against a list of materials.
2. **工具 (Built-in tools)** — three fixed scripts: `auto_encounter` (双点循环点击), `loop_healing` (技能 + 队员偏移), `get_material` (热键触发的一次性脚本).
3. **自定义 (Custom tools)** — user-defined step sequences (`once` or `loop` mode) with mouse / keyboard / image-search steps.

### Core modules

| Module | Responsibility |
|---|---|
| `main_gui.py` — `CraftAssistantGUI` | Main window. Owns all managers/engines, wires the Treeview categories, top-bar window-bind/settings/hotkey buttons, log panel, and mini-mode. |
| `window_manager.py` — `WindowManager` | "Click-to-bind" any window via a low-level mouse hook (`SetWindowsHookEx`/`WH_MOUSE_LL`); stores `hwnd`. All input/screenshot relies on this hwnd. |
| `screenshot_util.py` | `take_screenshot(region=...)` — when bound, uses Win32 `BitBlt` from the window DC (no flicker, works even if the game is occluded), with mss as fallback. Always call `set_capture_hwnd(hwnd)` before a run and `set_capture_hwnd(None)` after. |
| `bg_input.py` | Background mouse/keyboard via `PostMessage` (`WM_MOUSEMOVE`/`WM_LBUTTONDOWN`/...). Takes **screen coordinates**, internally converts via `ScreenToClient`. The real cursor never moves — this is the project's central trick. **Don't replace with `pyautogui`.** |
| `craft_engine.py` — `CraftEngine` | Daemon-thread crafting loop. Iterates `recipe.materials`, clicks slots, presses 执行, waits for completion image, periodically presses 整理. `should_stop` flag for cancellation. |
| `backpack_reader.py` — `BackpackReader` | Locates the 5×4 backpack grid (`GRID_COLS=5`, `GRID_ROWS=4`) by template-matching `backpack_title` and `empty_cell`, then crops each cell into icon+digit-region for matching. |
| `digit_recognizer.py` — `DigitRecognizer` | 0–9 template matching with CLAHE-preprocessed grayscale **and** a G–R channel variant (青色数字 vs background); reads quantities from backpack cells. |
| `recipe_manager.py` — `RecipeManager` | Per-recipe directory under `recipes/<name>/recipe.json` plus material image files. CRUD + rename (renames dir and rewrites `name`). |
| `tool_scripts.py` | Three engines: `AutoEncounterEngine`, `LoopHealingEngine`, `GetMaterialEngine`. Each is a daemon-thread runner with `should_stop`. |
| `tool_dialog.py` | Config dialogs for the three built-in tools, plus `load_tool_config` / `save_tool_config` (`tool_config.json`). |
| `custom_tool_manager.py` — `CustomToolManager` | One-tool-per-JSON under `custom_tools/<name>.json` plus same-name image subdir; handles sanitize/save/rename (renames subdir + rewrites every `image_path` field). |
| `custom_tool_engine.py` — `CustomToolEngine` | Executes a custom-tool's `steps` list (`once` or infinite `loop` mode). Carries `_last_target` so a `coord_mode='current'` mouse step can reuse the previous step's resolved coordinates. |
| `custom_tool_dialog.py` | Editor for custom tools — 8 step types: `mouse_move` / `mouse_click` / `mouse_right_click` / `mouse_double_click` / `mouse_down` / `mouse_up` / `key_press` / `hotkey` / `image_search`. |
| `hotkey_manager.py` — `HotkeyManager` | Global hotkeys via `keyboard` lib. Defaults: `` ` ``=start, `esc`=stop, `+`=get-material. **Foreground gate:** hotkeys only fire when the bound game window is the foreground top-level window — supports running multiple instances bound to different game windows. Persists to `hotkey_config.json` (and reads `tool_config.json` for the get-material hotkey). |
| `settings_dialog.py` | Global settings (`settings.json`) — template paths for the 5 location anchors (背包定位 / 空格子 / 执行按钮 / 制造完成 / 整理背包), grid geometry, click delays, digit/icon regions. |
| `recipe_dialog.py` / `hotkey_dialog.py` / `tool_dialog.py` / `custom_tool_dialog.py` | Tk Toplevel editors. |

### Persistence layout

```
settings.json                         # global settings (templates, geometry, delays)
hotkey_config.json                    # start/stop hotkeys
tool_config.json                      # 3 built-in tools' params (incl. get-material hotkey)
templates/                            # bundled anchor PNGs (backpack_title, empty_cell, ...)
templates/digits/0.png ... 9.png      # digit templates
recipes/<name>/recipe.json            # one recipe per dir; material images alongside
recipes/<name>/<material>.png
custom_tools/<name>.json              # one custom tool per JSON
custom_tools/<name>/<step>.png        # image-search templates for that tool only
```

### Threading & control flow

- Every engine (`CraftEngine`, the three `tool_scripts` engines, `CustomToolEngine`) runs in its own **daemon thread** with a `should_stop` flag and chunked sleeps for prompt cancellation. `is_running` flips while active. The GUI thread polls these flags / awaits via `root.after`.
- The hotkey listener runs in its own thread inside the `keyboard` library; `_is_my_game_foreground()` ensures hotkeys don't fire across instances.
- `get_material` is special: it can run **concurrently** with crafting/tool scripts (separate engine instance, separate hotkey).

### Key invariants — read before changing things

- **Always call `screenshot_util.set_capture_hwnd(hwnd)` at engine start and `set_capture_hwnd(None)` at end.** Otherwise capture falls back to mss and breaks under occlusion.
- **Coordinates passed to `bg_input` are screen coordinates**, not client coordinates. `ScreenToClient` happens inside.
- **Use `PIL.Image.open()`, not `cv2.imread()` or `pyautogui`, when loading template images** — file paths often contain Chinese characters.
- **All file I/O uses `encoding='utf-8'`** for the same reason.
- **Don't reintroduce `pyautogui` mouse/keyboard calls.** `pyautogui` is still imported (e.g. `pyautogui.position()` to read cursor) but only because it's read-only — actuation must go through `bg_input` so the real mouse stays put.
- **Custom-tool image paths are stored relative to repo root** (e.g. `custom_tools/<tool>/<file>.png`). Renaming a tool requires walking every `image_path` and rewriting the prefix; `CustomToolManager.save` already does this — keep it that way.

## CI/CD

`.github/workflows/auto-release.yml` — on push to `main`/`master` (excluding `**.md`, `.gitignore`, `docs/**`), Windows runner with Python 3.11 builds the exe via `build_exe.py` and publishes a GitHub Release tagged `v{YYYY.MM.dd}-{HHmm}`. CI builds with the ASCII name `MoliCraftAssistant.exe` then renames to `魔力宝贝制造助手.exe` to dodge encoding issues.

## Key dependencies

`opencv-python`, `numpy`, `Pillow`, `mss`, `keyboard`, `pywin32` (win32gui/win32ui/win32con — required for BitBlt capture), `pyautogui` (read-only, for `position()`), `pyinstaller`. Target Python is 3.11.

## Platform notes

- **Windows-only at runtime.** `bg_input.PostMessage`, `window_manager`'s low-level mouse hook, and the BitBlt capture path all hard-depend on the Win32 API. Code can be edited on macOS/Linux but cannot be exercised end-to-end there.
- The exe filename and many user files contain Chinese; always pass `encoding='utf-8'` and prefer PIL over cv2 for path-based loads.
