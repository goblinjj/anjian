@echo off
echo 启动游戏自动化脚本 GUI 编辑器...
echo.

python start_gui.py

if %errorlevel% neq 0 (
    echo.
    echo 程序启动失败！
    echo 请检查是否已安装Python和必要的依赖项
    echo.
    pause
)
