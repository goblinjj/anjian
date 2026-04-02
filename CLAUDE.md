# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**按键小精灵 (Key Mouse Spirit)** - A Windows game automation tool using image recognition (OpenCV) and keyboard/mouse automation. Written in Python with tkinter GUI, distributed as a compiled .exe via PyInstaller.

The entire UI and documentation are in **Chinese**.

## Build & Run

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python start_gui.py

# Build Windows executable
python build_exe.py
# Output: dist/按键小精灵.exe
```

There is no formal test suite. `test_antivirus_setup.py` is a standalone antivirus compatibility checker, not a unit test.

## Architecture

**Entry flow:** `start_gui.py` (dependency check) → `main_gui.py` (AutomationGUI, main window)

**Core modules:**
- `main_gui.py` - Main tkinter GUI with step list, edit panel, toolbar, status bar
- `execution_engine.py` - ExecutionEngine (blocking) and AutomationRunner (daemon thread wrapper) that execute automation steps
- `models.py` - ActionStep class with step_type, params dict, enabled flag, description
- `file_manager.py` - ConfigManager for JSON config persistence
- `hotkey_manager.py` - Global hotkey monitoring via `keyboard` library (default: backtick=start, ESC=stop); config persisted to `hotkey_config.json`
- `screenshot_util.py` - Screen capture using `mss` library (fixes RDP/remote desktop black screen issue vs pyautogui)
- `ui_editors.py` - EditPageManager with tabbed editors for 10 step types (dynamic display by step type)
- `dialogs.py` - StepTypeDialog, ScreenshotDialog, HotkeySettingsDialog

**Build utilities:**
- `build_exe.py` - PyInstaller build script
- `generate_hashes.py` - Generates MD5/SHA256 hashes for release artifacts
- `deploy.py`, `force_fix_icon.py` - Deployment and icon helpers

**Step types** (ActionStep.step_type):

Basic operations:
1. `mouse_click` - Click at coordinates with configurable button/count/interval
2. `keyboard_press` - Single key, combo (e.g. "ctrl+c"), or text input
3. `image_search` - OpenCV template matching with confidence threshold, region support, timeout, and optional click action
4. `wait` - Fixed delay or wait-for-image

Flow control (container types with `children`/`else_children`):
5. `if_image` - Conditional: if image found → execute children, else → execute else_children
6. `for_loop` - Loop N times over children
7. `while_image` - Loop while image exists/not exists
8. `break_loop` - Break out of nearest loop

Advanced operations:
9. `random_delay` - Random wait between min/max time
10. `mouse_scroll` - Scroll wheel at coordinates

**Data model:** `ActionStep` supports tree hierarchy via `children` and `else_children` lists. Container types (`if_image`, `for_loop`, `while_image`) can nest other steps. The Treeview displays this as an expandable tree. Mapping dicts `_item_to_step` and `_item_to_parent_list` replace the old flat-index approach.

**Execution model:** `ExecutionEngine` uses recursive `_execute_step_list`/`_execute_one_step` pattern with `ExecutionContext` carrying `should_break` state. Runs in a daemon thread via AutomationRunner with `should_stop` flag for cancellation. HotkeyManager runs its own listener thread.

**Image handling:** Uses `PIL.Image.open()` instead of `pyautogui` for loading images to support Chinese file paths.

## Configuration Format

JSON files with structure: `{ "version": "2.0", "created_time": "...", "description": "...", "steps": [...] }`. Steps can contain `children` and `else_children` arrays for nested flow control. v1.0 configs (without children) are loaded transparently via default empty lists.

## CI/CD

`.github/workflows/auto-release.yml` - Builds exe on windows-latest with Python 3.11 and creates a GitHub Release with tag `v{YYYY.MM.dd}-{HHmm}` on push to main/master.

## Key Dependencies

opencv-python, pyautogui, numpy, Pillow, keyboard, mss, pyinstaller, requests

## Platform Notes

- **Target platform is Windows.** The tool uses Windows-specific libraries (`keyboard` for global hotkeys, `mss` for screen capture). Development can happen on macOS/Linux but full functionality requires Windows.
- The `.exe` output name contains Chinese characters (`按键小精灵.exe`). File paths in configs may also contain Chinese characters — always use `encoding='utf-8'` when reading/writing files.
- The app auto-loads `default.json` on startup. If it doesn't exist, an empty config is created.
